"""Загрузка и сохранение исходных данных. Промпты и обработка для модели — в data.py."""

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from urllib.request import urlopen


WIKIWHY_REVISION = "2739d74043e9e97e53974e9c25b6e9f82f5b71dc"
MMLU_REVISION = "b189ec765aa7ed75c8acfea42df31fdae71f97be"
WIKIWHY_BASE = f"https://raw.githubusercontent.com/matt-seb-ho/WikiWhy/{WIKIWHY_REVISION}"
MMLU_URL = (
    f"https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro/resolve/{MMLU_REVISION}"
    "/data/test-00000-of-00001.parquet"
)
WIKIWHY_HASHES = {
    "context.json": "854e2637e96fb89eb2fa45a3f6c7940c91f70585c1f4d061c217ee28e8f2752e",
    "question.json": "f8c1e2ddcc354fc39e2cd0e229313f672291db2732232767b9bec592969d532c",
    "cause.json": "5d5a49ccd25503562a25cfca89451c442e7a5e44dde50866e59213fa33f47276",
    "effect.json": "5fce2b8d0f89340da0d0d09ad4e760c4af13c7cf098bab0da332736bc8c8391c",
    "explanation.json": "929bb3537b8c06d961c5494e9f672e5ee4e7e3d53efc1fb36f487c69baf07f71",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Загрузка: {url}", flush=True)
    with urlopen(url, timeout=60) as response, path.open("wb") as target:
        shutil.copyfileobj(response, target)


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        for row in rows:
            target.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def prepare_wikiwhy(root):
    """Соединение исходных колонок по строковым индексам, как у авторов."""
    columns = {}
    for filename, expected_hash in WIKIWHY_HASHES.items():
        path = root / "raw" / "wikiwhy" / filename
        download(f"{WIKIWHY_BASE}/dataset/v1.2/{filename}", path)
        if sha256(path) != expected_hash:
            raise ValueError(f"Контрольная сумма WikiWhy не совпала: {filename}")
        columns.update(json.loads(path.read_text(encoding="utf-8")))
    ids = list(columns["question"])
    if any(set(column) != set(ids) for column in columns.values()):
        raise ValueError("Индексы колонок WikiWhy не совпадают")
    rows = [{"id": row_id, **{key: value[row_id] for key, value in columns.items()}}
            for row_id in ids]
    if set(columns["split"].values()) != {"train", "dev", "test"}:
        raise ValueError("Неожиданные названия split в WikiWhy")
    counts = {}
    for source_split, target_split in [("train", "train"), ("dev", "validation"), ("test", "test")]:
        selected = [row for row in rows if row["split"] == source_split]
        write_jsonl(root / "wikiwhy" / f"{target_split}.jsonl", selected)
        counts[target_split] = len(selected)
    download(f"{WIKIWHY_BASE}/LICENSE", root / "raw" / "wikiwhy" / "LICENSE")
    return counts


def prepare_history(root):
    """Сохранение исторической части внешнего теста, не участвующей в обучении."""
    import pyarrow.parquet as pq

    path = root / "raw" / "mmlu_pro_test.parquet"
    download(MMLU_URL, path)
    rows = [row for row in pq.read_table(path).to_pylist() if row["category"] == "history"]
    if not rows or len({row["question_id"] for row in rows}) != len(rows):
        raise ValueError("Исторический тест MMLU-Pro пуст или содержит повторные question_id")
    write_jsonl(root / "mmlu_history" / "test.jsonl", rows)
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    output = parser.parse_args().output_dir.resolve()
    if output.exists():
        manifest_path = output / "manifest.json"
        if not manifest_path.is_file():
            raise FileExistsError(f"В {output} уже есть данные без manifest.json. Для повторной загрузки требуется другой --output-dir.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for filename, expected_hash in manifest["files_sha256"].items():
            path = output / filename
            if not path.is_file() or sha256(path) != expected_hash:
                raise ValueError(f"Сохранённые данные изменены или неполны: {filename}")
        print(f"Данные уже готовы, контрольные суммы совпадают: {output}")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        counts = prepare_wikiwhy(staging)
        history_count = prepare_history(staging)
        manifest = {
            "wikiwhy": {"repository": "https://github.com/matt-seb-ho/WikiWhy",
                        "revision": WIKIWHY_REVISION, "version": "v1.2", "counts": counts,
                        "split_policy": "Official splits; dev is saved as validation. Original split field is preserved."},
            "mmlu_history": {"repository": "https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro",
                             "revision": MMLU_REVISION, "source_split": "test",
                             "filter": "category == history", "count": history_count},
            "files_sha256": {str(path.relative_to(staging)): sha256(path)
                             for path in sorted(staging.rglob("*")) if path.is_file()},
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(f"Готово: WikiWhy {counts}; MMLU-Pro/history {history_count}; {output}")


if __name__ == "__main__":
    main()
