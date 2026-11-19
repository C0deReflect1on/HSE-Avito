"""Запуск vLLM и замеров AIPerf на GPU-сервере."""

import csv
import hashlib
import json
import math
import os
import signal
import socket
import subprocess
import time
from contextlib import contextmanager, suppress
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
DATA_SHA256 = "67c48379e5ae2608f7ca08650fd346facdc01f766a3e8eecea6459d7cec00ebc"
MODEL = "Qwen/Qwen3-8B"
IMAGE_TAG = "hw6-safin:v0"
SERVER_PORT = 18110
HF_CACHE = Path("/home/edu/.cache/huggingface")
ALLOWED_GPU = "0"
FIXED_RPM = 120
CAPACITY_SECONDS = 300
SLA_SECONDS = 15
CAPACITY_STEP = 15
BASELINE_NGRAMS = {"baseline_ngram3": 3, "baseline_ngram5": 5}
PLAIN_CONFIGS = {
    "baseline": [],
    "prefill_2048": ["--max-num-batched-tokens", "2048"],
    "prefill_4096_seqs_32": [
        "--max-num-batched-tokens", "4096",
        "--max-num-seqs", "32",
    ],
}


class MeasurementError(RuntimeError):
    """Запуск или выгрузка не дали пригодного результата."""


def docker_cmd(*args):
    return ["sudo", "-n", "docker", *args]


def base_image_from_dockerfile():
    for line in (ROOT / "Dockerfile").read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == "FROM":
            return fields[1]
    raise MeasurementError("В Dockerfile не найден FROM.")


def docker_output(*args, timeout=60):
    return subprocess.check_output(docker_cmd(*args), text=True, timeout=timeout).strip()


def ensure_image():
    inspect = subprocess.run(
        docker_cmd("image", "inspect", IMAGE_TAG),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if inspect.returncode != 0:
        print(f"Сборка {IMAGE_TAG}", flush=True)
        subprocess.run(docker_cmd("build", "-t", IMAGE_TAG, str(ROOT)), check=True)
    return IMAGE_TAG


def image_toolchain():
    versions = docker_output(
        "run", "--rm", "--entrypoint", "/opt/benchmark/bin/python", IMAGE_TAG, "-c",
        "from importlib.metadata import version\n"
        "print(version('aiperf'))\n"
        "print(version('transformers'))\n",
        timeout=180,
    ).splitlines()
    if len(versions) != 2:
        raise MeasurementError(f"Не удалось прочитать версии в {IMAGE_TAG}: {versions!r}")
    aiperf, transformers = versions
    if aiperf != "0.13.0":
        raise MeasurementError(f"В {IMAGE_TAG} стоит AIPerf {aiperf}, нужен 0.13.0.")
    curl = docker_output(
        "run", "--rm", "--entrypoint", "bash", IMAGE_TAG, "-lc", "command -v curl",
        timeout=60,
    )
    if not curl:
        raise MeasurementError(f"В {IMAGE_TAG} нет curl.")
    return aiperf, transformers


def gpu_info(device):
    if str(device) != ALLOWED_GPU:
        raise MeasurementError("Можно занимать только GPU 0.")
    env = os.environ.copy()
    env.pop("CUDA_VISIBLE_DEVICES", None)
    raw = subprocess.check_output([
        "nvidia-smi", "-i", ALLOWED_GPU,
        "--query-gpu=uuid,name,memory.total,driver_version", "--format=csv,noheader",
    ], text=True, timeout=20, env=env).strip()
    return tuple(field.strip() for field in raw.split(","))


def port_is_free(port):
    """Слушающий сокет занят. TIME_WAIT после AIPerf портом не считается."""
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def wait_until_port_free(port, timeout=120):
    deadline = time.monotonic() + timeout
    while True:
        if port_is_free(port):
            return
        if time.monotonic() >= deadline:
            raise MeasurementError(f"Порт 127.0.0.1:{port} не освободился за {timeout} с.")
        time.sleep(2)


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def run_logged(command, log_path, timeout, on_cancel=None):
    """Записывает вывод и останавливает группу процессов при прерывании ноутбука."""
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=log,
            stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            return process.wait(timeout=timeout)
        finally:
            if process.poll() is None:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    with suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                if on_cancel:
                    with suppress(Exception):
                        on_cancel()


def read_measurement(profile, expected, rpm, duration):
    """Берёт E2E из сводки AIPerf, фактическую подачу из записей profiling."""
    stats = json.loads((profile / "profile_export_aiperf.json").read_text())
    starts = []
    errors = 0
    with (profile / "profile_export.jsonl").open() as records:
        for line in records:
            record = json.loads(line)
            metadata = record["metadata"]
            if metadata["benchmark_phase"] != "profiling":
                continue
            starts.append(metadata["request_start_ns"])
            errors += bool(record.get("error") or metadata.get("was_cancelled"))

    attempted = len(starts)
    completed = attempted - errors
    latency = stats.get("request_latency", {})
    mean_s = None
    p90_s = None
    if completed:
        if latency.get("unit") != "ms" or latency.get("count") != completed:
            raise MeasurementError("Число или единицы E2E-замеров расходятся с записями AIPerf.")
        mean_s = latency["avg"] / 1000
        p90_s = latency["p90"] / 1000
        if not all(math.isfinite(value) and value > 0 for value in (mean_s, p90_s)):
            raise MeasurementError("AIPerf вернул некорректную E2E latency.")

    span = (max(starts) - min(starts)) / 1e9 if attempted > 1 else 0
    offered_rpm = (attempted - 1) * 60 / span if span > 0 else 0
    if duration:
        # У первого и последнего запроса нет интервалов до границ 300-секундного окна.
        on_schedule = (
            abs(attempted - expected) <= max(1, expected // 100)
            and span >= duration - max(3, 2 * 60 / rpm)
        )
    else:
        on_schedule = attempted == expected
    on_schedule = on_schedule and abs(offered_rpm / rpm - 1) <= 0.02
    return {
        "attempted": attempted,
        "completed": completed,
        "errors": errors,
        "offered_rpm": offered_rpm,
        "send_span_s": span,
        "on_schedule": on_schedule and not stats.get("was_cancelled", False),
        "mean_e2e_s": mean_s,
        "p90_e2e_s": p90_s,
        "request_throughput_rps": stats.get("request_throughput", {}).get("avg"),
        "mean_output_tokens": stats.get("output_sequence_length", {}).get("avg"),
        "output_throughput_tps": stats.get("output_token_throughput", {}).get("avg"),
    }


def best_fixed(rows, names=None):
    candidates = [
        row for row in rows
        if row["phase"] == "fixed" and row["status"] == "ok"
        and (names is None or row["config"] in names)
    ]
    return min(candidates, key=lambda row: (row["mean_e2e_s"], row["p90_e2e_s"]), default=None)


def ngram_args(tokens):
    return ["--speculative-config", json.dumps({
        "method": "ngram",
        "num_speculative_tokens": tokens,
        "prompt_lookup_min": 2,
        "prompt_lookup_max": 5,
    })]


def search_capacity(check, max_rpm):
    """Уточняет границу SLA с шагом CAPACITY_STEP между успешной и провальной точками."""
    probe = FIXED_RPM // CAPACITY_STEP
    ceiling = max_rpm // CAPACITY_STEP
    passed = 0
    while check(probe * CAPACITY_STEP):
        passed = probe
        if probe == ceiling:
            return
        probe = min(2 * probe, ceiling)

    failed = probe
    while failed - passed > 1:
        probe = (passed + failed) // 2
        if check(probe * CAPACITY_STEP):
            passed = probe
        else:
            failed = probe


class Experiment:
    def __init__(self, gpu_device, spec_rpms, max_capacity_rpm):
        self.spec_rpms = sorted(set(spec_rpms))
        self.max_capacity_rpm = max_capacity_rpm
        if not self.spec_rpms or self.spec_rpms[0] < 1:
            raise ValueError("Для сравнения нужны положительные значения RPM.")
        if max_capacity_rpm < FIXED_RPM or max_capacity_rpm % CAPACITY_STEP:
            raise ValueError(f"Предел SLA должен быть ≥ {FIXED_RPM} и кратен {CAPACITY_STEP} RPM.")

        if not HF_CACHE.is_dir():
            raise MeasurementError(f"Нет кэша Hugging Face: {HF_CACHE}")
        data = (ROOT / "data/requests.jsonl").read_bytes()
        dataset_hash = hashlib.sha256(data).hexdigest()
        if dataset_hash != DATA_SHA256:
            raise MeasurementError("Проверьте исходный data/requests.jsonl. Его SHA-256 отличается.")
        self.request_count = len(data.splitlines())
        resume = os.environ.get("HW6_RESUME")
        self.resume = Path(resume).resolve() if resume else None
        if self.resume:
            meta = json.loads((self.resume / "environment.json").read_text())
            self.short = str(meta.get("profile", "")).startswith("short")
            self.bench_requests = int(meta["bench_requests"])
            self.warmup_requests = int(meta["warmup_requests"])
            self._resume_meta = meta
        else:
            self.short = os.environ.get("HW6_SHORT") == "1"
            self.bench_requests = int(os.environ.get("HW6_REQUESTS") or (120 if self.short else self.request_count))
            self.warmup_requests = int(os.environ.get("HW6_WARMUP") or (8 if self.short else 40))
            self._resume_meta = None
        if not 1 <= self.bench_requests <= self.request_count:
            raise MeasurementError("HW6_REQUESTS должен быть от 1 до числа строк датасета.")
        self.image = ensure_image()
        self.base_image = base_image_from_dockerfile()
        aiperf, transformers = image_toolchain()
        self.gpu_uuid, gpu_name, gpu_memory, gpu_driver = gpu_info(gpu_device)
        self.container = None

        if self.resume:
            self.directory = self.resume
            self.rows = json.loads((self.directory / "results.json").read_text())
            self._resume_meta["profile"] = "short+2"
            write_json(self.directory / "environment.json", self._resume_meta)
        else:
            self.directory = ROOT / "results" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            self.directory.mkdir(parents=True)
            self.rows = []
            write_json(self.directory / "environment.json", {
            "model": MODEL,
            "vllm_image": self.base_image,
            "runtime_image": self.image,
            "aiperf": aiperf,
            "transformers": transformers,
            "gpu_index": ALLOWED_GPU,
            "gpu_name": gpu_name,
            "gpu_memory": gpu_memory,
            "gpu_driver": gpu_driver,
            "gpu_uuid": self.gpu_uuid,
            "dataset_sha256": dataset_hash,
            "dataset_requests": self.request_count,
            "profile": "short" if self.short else "full",
            "bench_requests": self.bench_requests,
            "warmup_requests": self.warmup_requests,
            "fixed_rpm": FIXED_RPM,
            "spec_rpms": self.spec_rpms,
            "capacity_seconds": CAPACITY_SECONDS,
            "capacity_step_rpm": CAPACITY_STEP,
            "max_capacity_rpm": self.max_capacity_rpm,
            "sla_p90_s": SLA_SECONDS,
            })
        print(
            f"GPU {ALLOWED_GPU}: {gpu_name} ({gpu_memory}), {self.gpu_uuid}. "
            f"Результаты: {self.directory}",
            flush=True,
        )
        if self.resume:
            print("Продолжаю ту же папку: prefill_2048 и baseline_ngram5.", flush=True)
        elif self.short:
            print(
                f"Короткий прогон: 3 конфига, {self.bench_requests} запросов, "
                f"прогрев {self.warmup_requests}. Цель около 20 минут.",
                flush=True,
            )

    def stop_aiperf(self):
        if not self.container:
            return
        subprocess.run(
            docker_cmd(
                "exec", self.container, "bash", "-lc",
                "if command -v pkill >/dev/null; then pkill -f 'aiperf profile' || true; fi",
            ),
            capture_output=True, check=False, timeout=30,
        )

    @contextmanager
    def server(self, phase, config, args):
        wait_until_port_free(SERVER_PORT)
        log_dir = self.directory / "logs" / phase
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{config}-vllm.log"
        name = f"hw6-safin-{uuid4().hex[:12]}"
        self.container = name
        url = f"http://127.0.0.1:{SERVER_PORT}"
        command = docker_cmd(
            "run", "--detach", "--name", name,
            "--gpus", f"device={self.gpu_uuid}", "--ipc", "host", "--network", "host",
            "--mount", f"type=bind,source={ROOT},target={ROOT}",
            "--mount", f"type=bind,source={HF_CACHE},target=/root/.cache/huggingface",
            "--env", "HF_HOME=/root/.cache/huggingface",
            "--entrypoint", "bash", self.image,
            str(ROOT / "serve.sh"), "--host", "127.0.0.1", "--port", str(SERVER_PORT), *args,
        )
        print(f"{phase} / {config}: запуск vLLM на GPU {ALLOWED_GPU}", flush=True)
        started = False
        try:
            with log_path.open("wb") as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
            started = True
            opener = build_opener(ProxyHandler({}))
            deadline = time.monotonic() + 3600
            while time.monotonic() < deadline:
                try:
                    with opener.open(f"{url}/health", timeout=2):
                        pass
                    with opener.open(f"{url}/version", timeout=5) as response:
                        actual_version = json.load(response)["version"]
                    break
                except (URLError, ConnectionError, TimeoutError, json.JSONDecodeError):
                    if docker_output("inspect", "--format", "{{.State.Running}}", name) != "true":
                        raise MeasurementError(f"vLLM завершился при запуске. Лог: {log_path}") from None
                    time.sleep(3)
            else:
                raise MeasurementError(f"vLLM не запустился за час. Лог: {log_path}")

            if actual_version.split("+", 1)[0] != "0.22.0":
                raise MeasurementError(f"Ожидался vLLM 0.22.0, получен {actual_version}.")
            print(f"{phase} / {config}: vLLM готов, {url}", flush=True)
            yield url
        finally:
            try:
                if started:
                    with log_path.open("ab") as log:
                        subprocess.run(
                            docker_cmd("logs", name), stdout=log,
                            stderr=subprocess.STDOUT, timeout=30, check=False,
                        )
            finally:
                self.container = None
                subprocess.run(
                    docker_cmd("rm", "-f", name), capture_output=True,
                    check=False, timeout=60,
                )
                with suppress(MeasurementError):
                    wait_until_port_free(SERVER_PORT)

    def save(self, row):
        self.rows.append(row)
        write_json(self.directory / "results.json", self.rows)
        columns = dict.fromkeys(key for item in self.rows for key in item)
        temporary = self.directory / "results.csv.tmp"
        with temporary.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(columns))
            writer.writeheader()
            for item in self.rows:
                writer.writerow({**item, "engine_args": json.dumps(item["engine_args"])})
        temporary.replace(self.directory / "results.csv")

    def measure(self, phase, config, args, rpm, url):
        output = self.directory / phase / config / f"{rpm}rpm"
        log = self.directory / "logs" / phase / f"{config}-{rpm}rpm-aiperf.log"
        duration = CAPACITY_SECONDS if phase == "capacity" else None
        expected = rpm * duration // 60 if duration else self.bench_requests
        row = {
            "phase": phase, "config": config, "engine_args": args, "rpm": rpm,
            "duration_s": duration, "expected_attempted": expected,
            "artifacts": str(output.relative_to(self.directory)),
            "client_log": str(log.relative_to(self.directory)),
        }
        print(f"{phase} / {config} / {rpm} RPM: замер", flush=True)
        try:
            if duration:
                inner = ["bash", str(ROOT / "load_test.sh"), str(rpm), str(output)]
            else:
                inner = ["bash", str(ROOT / "benchmark.sh"), str(output), str(rpm)]
            command = docker_cmd(
                "exec",
                "-e", f"URL={url}",
                "-e", f"REQUEST_COUNT={self.bench_requests}",
                "-e", f"WARMUP_REQUEST_COUNT={self.warmup_requests}",
                "-e", "NO_PROXY=127.0.0.1,localhost",
                "-e", "no_proxy=127.0.0.1,localhost",
                "-w", str(ROOT),
                self.container,
                *inner,
            )
            timeout = 600 + (duration or expected * 60 / rpm)
            returncode = run_logged(command, log, timeout, on_cancel=self.stop_aiperf)
            row["exit_code"] = returncode
            row.update(read_measurement(output / "profile", expected, rpm, duration))
            if returncode or not row["on_schedule"]:
                row["status"] = "invalid"
                row["detail"] = "AIPerf завершился с ошибкой." if returncode else "Подача отличается от плана."
            else:
                row["status"] = "request_errors" if row["errors"] else "ok"
        except (OSError, ValueError, KeyError, MeasurementError, subprocess.TimeoutExpired) as exc:
            row["status"] = "invalid"
            row["detail"] = str(exc)

        if phase == "fixed" and row["status"] == "ok":
            baseline = best_fixed(self.rows, {"baseline"}) if config != "baseline" else row
            row["speedup_vs_baseline"] = baseline["mean_e2e_s"] / row["mean_e2e_s"]
        if duration and row["status"] != "invalid":
            row["sla_pass"] = row["status"] == "ok" and row["p90_e2e_s"] < SLA_SECONDS

        self.save(row)
        p90 = row.get("p90_e2e_s")
        result = f"P90 {p90:.3f} с" if p90 is not None else row.get("detail", "P90 отсутствует")
        print(f"{phase} / {config} / {rpm} RPM: {row['status']}, {result}", flush=True)
        return row

    def measure_config(self, phase, config, args, rates):
        completed_rates = set()
        try:
            with self.server(phase, config, args) as url:
                for rpm in rates:
                    self.measure(phase, config, args, rpm, url)
                    completed_rates.add(rpm)
        except (OSError, MeasurementError, subprocess.SubprocessError) as exc:
            for rpm in rates:
                if rpm not in completed_rates:
                    self.save({
                        "phase": phase, "config": config, "engine_args": args, "rpm": rpm,
                        "status": "server_error", "detail": str(exc),
                        "server_log": f"logs/{phase}/{config}-vllm.log",
                    })
            print(f"{phase} / {config}: {exc}", flush=True)

    def run_fixed(self):
        self.measure_config("fixed", "baseline", PLAIN_CONFIGS["baseline"], [FIXED_RPM])
        if best_fixed(self.rows, {"baseline"}) is None:
            raise MeasurementError(f"Не получен валидный замер бейзлайна. Логи в {self.directory / 'logs'}.")
        if self.short:
            self.measure_config(
                "fixed", "prefill_4096_seqs_32", PLAIN_CONFIGS["prefill_4096_seqs_32"], [FIXED_RPM],
            )
            self.measure_config("fixed", "baseline_ngram3", ngram_args(3), [FIXED_RPM])
            return best_fixed(self.rows)

        for config in PLAIN_CONFIGS:
            if config != "baseline":
                self.measure_config("fixed", config, PLAIN_CONFIGS[config], [FIXED_RPM])
        best_plain = best_fixed(self.rows, PLAIN_CONFIGS)

        for config, tokens in BASELINE_NGRAMS.items():
            self.measure_config("fixed", config, ngram_args(tokens), [FIXED_RPM])
        best_spec = best_fixed(self.rows, BASELINE_NGRAMS)
        if best_spec and best_plain["config"] != "baseline":
            config = f"{best_plain['config']}_{best_spec['config'].removeprefix('baseline_')}"
            args = [*best_plain["engine_args"], *best_spec["engine_args"]]
            self.measure_config("fixed", config, args, [FIXED_RPM])
        return best_fixed(self.rows)

    def run_extra(self):
        """Два дополнительных конфига в уже начатую папку короткого прогона."""
        done = {
            row["config"] for row in self.rows
            if row.get("phase") == "fixed" and row.get("status") == "ok"
        }
        if "baseline" not in done:
            raise MeasurementError(f"В {self.directory} нет валидного baseline.")
        print("Дописываю prefill_2048 и baseline_ngram5.", flush=True)
        if "prefill_2048" not in done:
            self.measure_config("fixed", "prefill_2048", PLAIN_CONFIGS["prefill_2048"], [FIXED_RPM])
        if "baseline_ngram5" not in done:
            self.measure_config("fixed", "baseline_ngram5", ngram_args(5), [FIXED_RPM])
        return best_fixed(self.rows)

    def run_spec(self):
        best_spec = best_fixed(self.rows, BASELINE_NGRAMS)
        if best_spec is None:
            print("Для сравнения не получен валидный замер n-gram при 120 RPM.", flush=True)
            return

        rates = [rpm for rpm in self.spec_rpms if rpm != FIXED_RPM]
        if rates:
            self.measure_config("spec", "baseline", PLAIN_CONFIGS["baseline"], rates)
            self.measure_config("spec", best_spec["config"], best_spec["engine_args"], rates)

    def run_capacity(self):
        best = best_fixed(self.rows)
        config = best["config"]
        with self.server("capacity", config, best["engine_args"]) as url:
            def check(rpm):
                row = self.measure("capacity", config, best["engine_args"], rpm, url)
                if row["status"] == "invalid":
                    raise MeasurementError(f"Нельзя оценить SLA при {rpm} RPM. См. {row['client_log']}.")
                return row["sla_pass"]

            search_capacity(check, self.max_capacity_rpm)


def main():
    experiment = Experiment(ALLOWED_GPU, [60, 120, 240, 480, 960, 1920], 3840)
    try:
        if experiment.resume:
            winner = experiment.run_extra()
        else:
            winner = experiment.run_fixed()
        if winner:
            print(
                f"{winner['config']}: {winner['speedup_vs_baseline']:.3f}× к бейзлайну",
                flush=True,
            )
        if not experiment.short:
            experiment.run_spec()
            if best_fixed(experiment.rows):
                experiment.run_capacity()
    finally:
        from hw6_results import write_results
        print(write_results(experiment.directory), flush=True)


if __name__ == "__main__":
    main()
