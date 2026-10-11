"""Run the six HW2 configurations and repeat the two fastest challengers."""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
INDEX = RESULTS / "experiment_index.json"

CASES = {
    "B0": dict(batch=32, accumulation=2, attention="sdpa", padding_free=False, packing=False),
    "B1": dict(batch=64, accumulation=1, attention="sdpa", padding_free=False, packing=False),
    "B2": dict(batch=32, accumulation=2, attention="flash_attention_2", padding_free=False, packing=False),
    "B3": dict(batch=32, accumulation=2, attention="flash_attention_2", padding_free=True, packing=False),
    "B4": dict(batch=32, accumulation=2, attention="flash_attention_2", padding_free=True, packing=True),
    "B5": dict(batch=64, accumulation=1, attention="flash_attention_2", padding_free=True, packing=True),
}


class CudaOOM(RuntimeError):
    def __init__(self, case_id: str, batch: int, output: Path) -> None:
        super().__init__(f"CUDA OOM: {output.name}; подробности в {output / 'run.log'}")
        self.case_id = case_id
        self.batch = batch


def summary(output: Path) -> dict:
    values = json.loads((output / "summary.json").read_text())
    for key in ("tokens_per_second", "validation_loss", "peak_allocated_gib", "optimizer_steps"):
        value = values[key]
        if value is None or not math.isfinite(value) or (key != "validation_loss" and value <= 0):
            raise ValueError(f"Некорректное поле {key} в {output / 'summary.json'}: {value}")
    return values


def is_cuda_oom(output: Path) -> bool:
    log = output / "run.log"
    if not log.exists():
        return False
    message = log.read_text(errors="replace").lower()
    return "out of memory" in message and ("cuda" in message or "gpu" in message)


def run_case(case_id: str, config: dict, *, final: bool = False) -> Path:
    seconds = 300 if final or case_id == "B0" else 90
    label = f"{'F_' if final else ''}{case_id}_{config['batch']}x{config['accumulation']}"
    output = RESULTS / label
    if (output / "summary.json").exists():
        summary(output)
        print(f"Уже готово: {label}", flush=True)
        return output
    if output.exists():
        if is_cuda_oom(output):
            raise CudaOOM(case_id, config["batch"], output)
        raise RuntimeError(f"Незавершённый каталог {output}. Проверьте run.log и переименуйте каталог перед повтором.")

    command = [
        sys.executable, "train.py", "--output-dir", str(output), "--seconds", str(seconds),
        "--batch-size", str(config["batch"]),
        "--gradient-accumulation-steps", str(config["accumulation"]),
        "--attention", config["attention"],
    ]
    if config["padding_free"]:
        command.append("--padding-free")
    if config["packing"]:
        command.append("--packing")
    print(f"Запуск {label}: {seconds} с; {config}", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        if is_cuda_oom(output):
            raise CudaOOM(case_id, config["batch"], output)
        raise RuntimeError(f"Ошибка {label} (код {result.returncode}); подробности в {output / 'run.log'}")
    summary(output)
    return output


def run_screen() -> dict[str, str]:
    selected = {}
    small_batch = False
    for case_id, original in CASES.items():
        config = original.copy()
        if small_batch and case_id in ("B1", "B5"):
            config.update(batch=16, accumulation=4)
        try:
            output = run_case(case_id, config)
        except CudaOOM:
            if case_id not in ("B1", "B5") or small_batch:
                raise
            small_batch = True
            print("64×1 не помещается в GPU. Для B1 и B5 используется 16×4.", flush=True)
            config.update(batch=16, accumulation=4)
            output = run_case(case_id, config)
            if case_id == "B5":
                alternative = CASES["B1"] | dict(batch=16, accumulation=4)
                selected["B1"] = str(run_case("B1", alternative).relative_to(ROOT))
        selected[case_id] = str(output.relative_to(ROOT))
    return selected


def run_finals(screen: dict[str, str]) -> dict[str, str]:
    candidates = sorted(
        (case_id for case_id in CASES if case_id != "B0"),
        key=lambda case_id: summary(ROOT / screen[case_id])["tokens_per_second"],
        reverse=True,
    )[:2]
    finals = {}
    for case_id in candidates:
        config = CASES[case_id].copy()
        used = json.loads((ROOT / screen[case_id] / "config.json").read_text())["training_config"]
        config.update(batch=used["per_device_train_batch_size"], accumulation=used["gradient_accumulation_steps"])
        finals[case_id] = str(run_case(case_id, config, final=True).relative_to(ROOT))
    return finals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Показать конфигурации без запуска")
    args = parser.parse_args()
    if args.list:
        for case_id, config in CASES.items():
            print(case_id, 300 if case_id == "B0" else 90, config)
        return

    RESULTS.mkdir(exist_ok=True)
    index = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    screen = index.get("screen") or run_screen()
    for output in screen.values():
        summary(ROOT / output)
    index["screen"] = screen
    INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")

    finals = index.get("finals")
    while not finals:
        try:
            finals = run_finals(screen)
        except CudaOOM as error:
            if error.case_id not in ("B1", "B5") or error.batch != 64:
                raise
            print("Полный запуск 64×1 не поместился в GPU. Повторяем B1 и B5 с 16×4.", flush=True)
            for case_id in ("B1", "B5"):
                config = CASES[case_id] | dict(batch=16, accumulation=4)
                screen[case_id] = str(run_case(case_id, config).relative_to(ROOT))
            index["screen"] = screen
            INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    index["finals"] = finals
    full = {"B0": screen["B0"], **finals}
    winner = max(full, key=lambda case_id: summary(ROOT / full[case_id])["tokens_per_second"])
    index["winner"] = winner
    index["speedup"] = summary(ROOT / full[winner])["tokens_per_second"] / summary(ROOT / screen["B0"])["tokens_per_second"]
    INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    print(f"Лучший полный запуск: {winner}; S={index['speedup']:.3f}", flush=True)
    print("Постройте графики: python plot_results.py", flush=True)


if __name__ == "__main__":
    main()
