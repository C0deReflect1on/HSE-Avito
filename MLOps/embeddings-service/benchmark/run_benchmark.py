"""
Minimal benchmark for embeddings service.
See benchmarking_design.md for rationale.
"""
import argparse
import asyncio
import csv
import platform
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

import httpx
import numpy as np

# Тексты разной длины — как в проде (design §4)
TEXT_POOL = {
    "short": [
        "Продам велосипед",
        "Куплю iPhone",
        "Отдам котёнка",
        "Нужен репетитор",
        "Сдам квартиру",
    ],
    "medium": [
        "Продам велосипед горный, 21 скорость, амортизатор. Состояние отличное, пробег 500 км.",
        "Куплю iPhone 14 или 15 в хорошем состоянии. Бюджет до 80к. Москва.",
        "Отдам котёнка в добрые руки. Мальчик, 2 месяца. Приучен к лотку.",
        "Ищу репетитора по математике для подготовки к ЕГЭ. 2 раза в неделю.",
        "Сдам 2-комнатную квартиру на год. Мебель, техника. Рядом метро.",
    ],
    "long": [
        "Продаю горный велосипед Trek 2022 года. Рама 19 дюймов, дисковые тормоза, "
        "21 скорость Shimano. Прошёл всего 500 км, как новый. Причина продажи — переезд. "
        "В комплекте замок, насос, запасная камера. Торг уместен. Звоните в любое время."
        * 2,
        "Ищу iPhone 14 или 15 Pro. Важно: 256 ГБ, хорошая батарея, без царапин на экране. "
        "Готов рассмотреть варианты с небольшими сколами на корпусе. Бюджет до 85 000. "
        "Могу приехать сам или встреча в метро. Предоплата только при личной встрече."
        * 2,
    ],
}


def make_payload(batch_size: int) -> dict:
    pool = TEXT_POOL["short"] + TEXT_POOL["medium"] + TEXT_POOL["long"]
    texts = random.choices(pool, k=batch_size)
    return {"texts": texts}


@dataclass
class ScenarioResult:
    scenario: str
    batch_size: int
    concurrency: int
    run: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    rps: float
    texts_s: float
    cpu_avg: float
    ram_max: float


def _parse_memory_mb(raw: str) -> float:
    """docker stats: '312.4MiB' or '1.5GiB'."""
    raw = raw.strip().replace(" ", "").lower()
    units = {"kib": 1 / 1024, "mb": 1, "mib": 1, "gb": 1024, "gib": 1024}
    for suf, mult in units.items():
        if raw.endswith(suf):
            try:
                return float(raw[:-len(suf)]) * mult
            except ValueError:
                return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


async def _read_docker_stats(container: str) -> tuple[float, float]:
    proc = await asyncio.create_subprocess_exec(
        "docker", "stats", container, "--no-stream",
        "--format", "{{.CPUPerc}}|{{.MemUsage}}",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"docker stats failed: {err.decode().strip()}")
    cpu_s, mem_s = out.decode().strip().split("|", 1)
    try:
        cpu = float(cpu_s.replace("%", "").strip())
    except ValueError:
        cpu = 0.0
    mem_current = mem_s.split("/")[0].strip()
    return cpu, _parse_memory_mb(mem_current)


async def _resource_sampler(
    container: str, stop: asyncio.Event, interval: float = 1.0
) -> tuple[list[float], list[float]]:
    cpu_list, ram_list = [], []
    if not container:
        while not stop.is_set():
            await asyncio.sleep(interval)
        return cpu_list, ram_list
    while not stop.is_set():
        try:
            c, r = await _read_docker_stats(container)
            cpu_list.append(c)
            ram_list.append(r)
        except Exception:
            pass
        await asyncio.sleep(interval)
    return cpu_list, ram_list


async def _run_single_scenario(
    client: httpx.AsyncClient,
    container: str,
    scenario: str,
    batch: int,
    concurrency: int,
    total_requests: int,
) -> ScenarioResult:
    """Замер с учётом Coordinated Omission: latency от enqueue, не от semaphore."""
    sem = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    success = 0

    stop_ev = asyncio.Event()
    sampler = asyncio.create_task(_resource_sampler(container, stop_ev))

    async def one_req() -> None:
        nonlocal success
        enqueued_at = time.perf_counter()
        async with sem:
            try:
                r = await client.post("/embed", json=make_payload(batch))
                if r.status_code == 200:
                    success += 1
                    latencies.append((time.perf_counter() - enqueued_at) * 1000)
            except Exception:
                pass

    start = time.perf_counter()
    await asyncio.gather(*[one_req() for _ in range(total_requests)])
    elapsed = time.perf_counter() - start

    stop_ev.set()
    cpu_vals, ram_vals = await sampler

    if not latencies:
        raise RuntimeError(f"No successful requests: {scenario}")

    arr = np.array(latencies)
    return ScenarioResult(
        scenario=scenario, batch_size=batch, concurrency=concurrency, run=0,
        p50_ms=float(np.percentile(arr, 50)),
        p95_ms=float(np.percentile(arr, 95)),
        p99_ms=float(np.percentile(arr, 99)),
        rps=success / elapsed,
        texts_s=success * batch / elapsed,
        cpu_avg=mean(cpu_vals) if cpu_vals else 0,
        ram_max=max(ram_vals) if ram_vals else 0,
    )


async def run_scenario_n_times(
    base_url: str,
    container: str,
    scenario: str,
    batch: int,
    concurrency: int,
    total_requests: int,
    n_runs: int,
    sleep_between: float,
) -> tuple[ScenarioResult, list[ScenarioResult]]:
    """N прогонов → медиана метрик (design §6.3). Возвращает (median, all_runs)."""
    limits = httpx.Limits(
        max_connections=max(32, concurrency * 2),
        max_keepalive_connections=concurrency,  # design §6.5
    )
    results: list[ScenarioResult] = []

    async with httpx.AsyncClient(base_url=base_url, timeout=60, limits=limits) as client:
        for run in range(n_runs):
            r = await _run_single_scenario(
                client, container, scenario, batch, concurrency, total_requests
            )
            r.run = run + 1
            results.append(r)
            if run < n_runs - 1:
                await asyncio.sleep(sleep_between)
                resp = await client.get("/health")
                if resp.status_code != 200:
                    raise RuntimeError("Healthcheck failed between runs")

    median_result = ScenarioResult(
        scenario=scenario, batch_size=batch, concurrency=concurrency, run=0,
        p50_ms=median(r.p50_ms for r in results),
        p95_ms=median(r.p95_ms for r in results),
        p99_ms=median(r.p99_ms for r in results),
        rps=median(r.rps for r in results),
        texts_s=median(r.texts_s for r in results),
        cpu_avg=median(r.cpu_avg for r in results),
        ram_max=median(r.ram_max for r in results),
    )
    return median_result, results


def write_csv(all_runs: list[ScenarioResult], path: Path, env: dict) -> None:
    """CSV: каждая строка — один прогон (design §9)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "batch", "concurrency", "run", "p50", "p95", "p99", "rps", "texts_s", "cpu_avg", "ram_max"])
        for r in all_runs:
            w.writerow([r.scenario, r.batch_size, r.concurrency, r.run, f"{r.p50_ms:.2f}", f"{r.p95_ms:.2f}", f"{r.p99_ms:.2f}", f"{r.rps:.2f}", f"{r.texts_s:.2f}", f"{r.cpu_avg:.2f}", f"{r.ram_max:.2f}"])
        w.writerow([])
        w.writerow(["env", str(env)])


def print_md(rows: list[ScenarioResult]) -> None:
    print("| Scenario | Batch | p50 ms | p95 ms | p99 ms | texts/s |")
    print("|----------|------:|-------:|-------:|-------:|--------:|")
    for r in rows:
        print(f"| {r.scenario} | {r.batch_size:>5} | {r.p50_ms:>6.1f} | {r.p95_ms:>6.1f} | {r.p99_ms:>6.1f} | {r.texts_s:>7.1f} |")


def get_env() -> dict:
    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "os": platform.system(),
    }


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--container", default="embeddings-service",
                   help="Docker container for CPU/RAM stats; use '' to skip")
    p.add_argument("--run-name", default="benchmark")
    p.add_argument("--runs", type=int, default=5, help="Runs per scenario (design: 5)")
    p.add_argument("--skip-sustained", action="store_true")
    args = p.parse_args()

    limits = httpx.Limits(max_connections=32, max_keepalive_connections=8)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=30, limits=limits) as client:
        h = await client.get("/health")
        if h.status_code != 200:
            raise SystemExit(f"Healthcheck failed: {h.status_code}")

        # Warmup 50 запросов (design §6.1)
        for _ in range(50):
            await client.post("/embed", json=make_payload(8))
        print("Warmup done")

    # Сценарии из design §3
    scenarios = [
        ("baseline", 1, 1, 50),
        ("batch_sweep", 1, 4, 80),
        ("batch_sweep", 8, 4, 80),
        ("batch_sweep", 16, 4, 80),
        ("batch_sweep", 32, 4, 80),
        ("conc_sweep", 8, 1, 50),
        ("conc_sweep", 8, 4, 80),
        ("conc_sweep", 8, 8, 80),
        ("conc_sweep", 8, 16, 80),
        ("conc_sweep", 8, 32, 80),
        ("conc_sweep", 8, 64, 80),
    ]
    if not args.skip_sustained:
        # ~5 min: 16 conc * 8 batch * req. При ~2 rps = 600 req за 5 мин
        scenarios.append(("sustained", 8, 16, 600))

    median_results: list[ScenarioResult] = []
    all_runs: list[ScenarioResult] = []
    for name, batch, conc, nreq in scenarios:
        print(f"Running {name} batch={batch} conc={conc}...")
        median_r, runs = await run_scenario_n_times(
            args.base_url, args.container,
            name, batch, conc, nreq,
            n_runs=args.runs, sleep_between=5,
        )
        median_results.append(median_r)
        all_runs.extend(runs)
        # Изоляция между сценариями (design §6.4)
        await asyncio.sleep(5)

    print()
    print_md(median_results)
    out = Path(__file__).parent / "results" / f"{args.run_name}.csv"
    write_csv(all_runs, out, get_env())
    print(f"\nCSV: {out}")


if __name__ == "__main__":
    asyncio.run(main())
