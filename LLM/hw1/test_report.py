"""Run with Python and Matplotlib: python3 hw1/test_report.py."""

import contextlib
import io
import json
import math
import re
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from plot_logs import ARTIFACTS, ROOT, RUNS, main, write_png


def check():
    with patch("plot_logs.write_png") as draw, contextlib.redirect_stdout(io.StringIO()):
        main()
    calls = {Path(call.args[0]).relative_to(ARTIFACTS).as_posix(): call.args for call in draw.call_args_list}
    assert len(calls) == 10
    series = calls["comparison.png"][4]
    linear = next(item for item in series if item["label"].startswith("scheduler_linear "))
    assert linear["marker_x"] == 800  # The selected checkpoint precedes the final training step.
    assert linear["points"][-1][0] == 801
    assert len(linear["marks"]) == 9  # Exclude the explicit evaluation after trainer.train().
    token_axis = calls["comparison_tokens.png"][5]
    assert token_axis(linear, 800, linear["marker"]) == 13_107_200

    report = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in RUNS:
        folder = ARTIFACTS / name
        history = json.loads((folder / "loss.json").read_text())
        metrics = json.loads((folder / "metrics.json").read_text())
        trace = json.loads((folder / "trace.json").read_text())
        boundary = next(i for i, entry in enumerate(history) if "train_runtime" in entry)
        eval_seconds = sum(entry.get("eval_runtime", 0) for entry in history[:boundary])
        fraction = 100 * eval_seconds / trace["total_seconds"]
        mean_loss = sum(entry["loss"] for entry in history if "loss" in entry and entry["step"] > trace["optimizer_steps"] - 50) / 50
        assert f"{metrics['eval_loss']:.4f}" in report
        assert f"{metrics['perplexity']:.2f}" in report
        assert f"{mean_loss:.4f}" in report
        assert f"{eval_seconds:.2f} | {fraction:.1f}%" in report
        assert math.isclose(math.exp(metrics["eval_loss"]), metrics["perplexity"])

    for target in re.findall(r"\]\(([^)]+)\)", report):
        if not target.startswith("https://"):
            assert (ROOT / target).is_file(), target
    for png in ARTIFACTS.rglob("*.png"):
        data = png.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", png
        assert struct.unpack(">II", data[16:24]) == (1980, 1080), png
    assert not list(ARTIFACTS.rglob("*.svg"))
    with TemporaryDirectory() as directory:
        output = Path(directory) / "loss.png"
        write_png(output, "Проверка PNG", "Loss", "Шаги оптимизатора", [linear])
        assert output.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    print("PASS: report metrics, checkpoint 800, evaluation boundaries, links, and PNG output")


if __name__ == "__main__":
    check()
