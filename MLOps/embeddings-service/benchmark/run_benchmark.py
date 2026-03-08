import argparse
import asyncio
import csv
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import httpx
import numpy as np


@dataclass
class ScenarioResult:
    scenario: str
    batch_size: int
    concurrency: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    req_per_sec: float
    texts_per_sec: float
    avg_cpu_percent: float
    max_rss_mb: float


def _payload(batch_size: int) -> dict[str, list[str]]:
    texts = [f"Это тестовый текст номер {i}" for i in range(batch_size)]
    return {"texts": texts}


def _parse_memory_to_mb(raw_value: str) -> float:
    units = {
        "b": 1 / (1024 * 1024),
        "kib": 1 / 1024,
        "kb": 1 / 1024,
        "mib": 1,
        "mb": 1,
        "gib": 1024,
        "gb": 1024,
        "tib": 1024 * 1024,
        "tb": 1024 * 1024,
    }
    value = raw_value.strip().lower()
    numeric = ""
    suffix = ""
    for char in value:
        if char.isdigit() or char == ".":
            numeric += char
        else:
            suffix += char
    if not numeric:
        return 0.0
    factor = units.get(suffix.strip(), 1.0)
    return float(numeric) * factor


async def _read_docker_stats(container_name: str) -> tuple[float, float]:
    proc = await asyncio.create_subprocess_exec(
        "docker",
        "stats",
        container_name,
        "--no-stream",
        "--format",
        "{{.CPUPerc}}|{{.MemUsage}}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"docker stats failed for container '{container_name}': {stderr.decode().strip()}"
        )

    line = stdout.decode().strip()
    cpu_str, mem_str = line.split("|", maxsplit=1)
    cpu_percent = float(cpu_str.strip().replace("%", ""))
    mem_current = mem_str.split("/", maxsplit=1)[0].strip()
    rss_mb = _parse_memory_to_mb(mem_current)
    return cpu_percent, rss_mb


async def _resource_sampler(container_name: str, stop_event: asyncio.Event) -> tuple[list[float], list[float]]:
    cpu_values: list[float] = []
    rss_values: list[float] = []
    while not stop_event.is_set():
        cpu_percent, rss_mb = await _read_docker_stats(container_name)
        cpu_values.append(cpu_percent)
        rss_values.append(rss_mb)
        await asyncio.sleep(0.2)
    return cpu_values, rss_values


async def run_scenario(
    base_url: str,
    container_name: str,
    scenario_name: str,
    batch_size: int,
    concurrency: int,
    total_requests: int,
) -> ScenarioResult:
    semaphore = asyncio.Semaphore(concurrency)
    latencies_ms: list[float] = []
    successful_requests = 0
    failed_requests = 0

    stop_event = asyncio.Event()
    sampler_task = asyncio.create_task(_resource_sampler(container_name, stop_event))

    client_limits = httpx.Limits(max_connections=max(32, concurrency * 2), max_keepalive_connections=0)
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0, limits=client_limits) as client:
        async def _one_request() -> None:
            nonlocal successful_requests, failed_requests
            async with semaphore:
                last_error: Exception | None = None
                for attempt in range(3):
                    started = time.perf_counter()
                    try:
                        response = await client.post("/embed", json=_payload(batch_size))
                        elapsed_ms = (time.perf_counter() - started) * 1000
                        if response.status_code == 200:
                            successful_requests += 1
                            latencies_ms.append(elapsed_ms)
                            return
                        last_error = RuntimeError(f"HTTP {response.status_code}: {response.text}")
                    except httpx.HTTPError as exc:
                        last_error = exc
                    # Small exponential backoff for transient connection resets.
                    await asyncio.sleep(0.1 * (2**attempt))
                failed_requests += 1
                if last_error:
                    print(f"Request failed after retries: {type(last_error).__name__}: {last_error}")

        started_all = time.perf_counter()
        await asyncio.gather(*[_one_request() for _ in range(total_requests)])
        elapsed_all = time.perf_counter() - started_all

    stop_event.set()
    cpu_values, rss_values = await sampler_task

    if not latencies_ms:
        raise RuntimeError(f"No successful requests in scenario '{scenario_name}'")

    latencies_arr = np.array(latencies_ms)
    req_per_sec = successful_requests / elapsed_all
    texts_per_sec = (successful_requests * batch_size) / elapsed_all

    return ScenarioResult(
        scenario=scenario_name,
        batch_size=batch_size,
        concurrency=concurrency,
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        p50_ms=float(np.percentile(latencies_arr, 50)),
        p95_ms=float(np.percentile(latencies_arr, 95)),
        p99_ms=float(np.percentile(latencies_arr, 99)),
        req_per_sec=req_per_sec,
        texts_per_sec=texts_per_sec,
        avg_cpu_percent=mean(cpu_values) if cpu_values else 0.0,
        max_rss_mb=max(rss_values) if rss_values else 0.0,
    )


def print_markdown(results: list[ScenarioResult]) -> None:
    print("| Scenario | Batch | Concurrency | Requests | Success | Failed | p50 ms | p95 ms | p99 ms | req/s | texts/s | CPU avg % | RAM max MB |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in results:
        print(
            f"| {row.scenario} | {row.batch_size} | {row.concurrency} | {row.total_requests} | {row.successful_requests} | {row.failed_requests} "
            f"| {row.p50_ms:.2f} | {row.p95_ms:.2f} | {row.p99_ms:.2f} "
            f"| {row.req_per_sec:.2f} | {row.texts_per_sec:.2f} | {row.avg_cpu_percent:.2f} | {row.max_rss_mb:.2f} |"
        )


def write_csv(results: list[ScenarioResult], run_name: str) -> Path:
    output_dir = Path("benchmark/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{run_name}.csv"

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "scenario",
                "batch_size",
                "concurrency",
                "total_requests",
                "successful_requests",
                "failed_requests",
                "p50_ms",
                "p95_ms",
                "p99_ms",
                "req_per_sec",
                "texts_per_sec",
                "avg_cpu_percent",
                "max_rss_mb",
            ]
        )
        for row in results:
            writer.writerow(
                [
                    row.scenario,
                    row.batch_size,
                    row.concurrency,
                    row.total_requests,
                    row.successful_requests,
                    row.failed_requests,
                    f"{row.p50_ms:.4f}",
                    f"{row.p95_ms:.4f}",
                    f"{row.p99_ms:.4f}",
                    f"{row.req_per_sec:.4f}",
                    f"{row.texts_per_sec:.4f}",
                    f"{row.avg_cpu_percent:.4f}",
                    f"{row.max_rss_mb:.4f}",
                ]
            )

    return output_path


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run embedding service benchmarks")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--container-name", default="embeddings-service")
    parser.add_argument("--arg", required=True, dest="run_name", help="Benchmark run name for CSV file")
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:
        health = await client.get("/health")
        if health.status_code != 200:
            raise RuntimeError(f"Healthcheck failed: HTTP {health.status_code}")
        # Warmup request to reduce first-request noise and catch early model issues.
        warmup = await client.post("/embed", json=_payload(1))
        if warmup.status_code != 200:
            raise RuntimeError(f"Warmup failed: HTTP {warmup.status_code} {warmup.text}")

    scenarios = [
        ("single_request", 1, 1, 30),
        ("concurrent_load", 1, 16, 200),
        ("batch_sweep", 1, 4, 120),
        ("batch_sweep", 8, 4, 120),
        ("batch_sweep", 16, 4, 120),
        ("batch_sweep", 32, 4, 120),
    ]

    results: list[ScenarioResult] = []
    for scenario in scenarios:
        result = await run_scenario(
            base_url=args.base_url,
            container_name=args.container_name,
            scenario_name=scenario[0],
            batch_size=scenario[1],
            concurrency=scenario[2],
            total_requests=scenario[3],
        )
        results.append(result)
        print(f"Finished scenario: {result.scenario} (batch={result.batch_size})")

    print()
    print_markdown(results)
    csv_path = write_csv(results, args.run_name)
    print()
    print(f"CSV saved to: {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
