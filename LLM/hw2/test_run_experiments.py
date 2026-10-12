"""Small CPU-only check for the paired CUDA OOM fallback."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_experiments as experiments


class ExperimentTests(unittest.TestCase):
    def test_oom_in_b5_replaces_both_batch_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls = []

            def run_case(case_id, config, *, final=False):
                calls.append((case_id, config["batch"], config["accumulation"]))
                if case_id == "B5" and config["batch"] == 64:
                    raise experiments.CudaOOM(case_id, 64, root / "B5_64x1")
                return root / f"{case_id}_{config['batch']}x{config['accumulation']}"

            with patch.object(experiments, "ROOT", root), patch.object(experiments, "run_case", side_effect=run_case):
                selected = experiments.run_screen()

            self.assertEqual(selected["B1"], "B1_16x4")
            self.assertEqual(selected["B5"], "B5_16x4")
            self.assertIn(("B1", 64, 1), calls)
            self.assertIn(("B1", 16, 4), calls)

    def test_full_series_selects_best_300_second_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "results"
            calls = []

            def fake_train(command, *, cwd, check):
                output = Path(command[command.index("--output-dir") + 1])
                seconds = int(float(command[command.index("--seconds") + 1]))
                case_id = output.name.split("_")[1 if output.name.startswith("F_") else 0]
                throughput = {"B0": 100, "B1": 110, "B2": 150, "B3": 140, "B4": 130, "B5": 120}[case_id]
                if output.name.startswith("F_"):
                    throughput = {"B2": 145, "B3": 155}[case_id]
                output.mkdir()
                (output / "summary.json").write_text(json.dumps(dict(
                    tokens_per_second=throughput, validation_loss=3.0,
                    peak_allocated_gib=40.0, optimizer_steps=20,
                )))
                (output / "config.json").write_text(json.dumps(dict(training_config=dict(
                    per_device_train_batch_size=int(command[command.index("--batch-size") + 1]),
                    gradient_accumulation_steps=int(command[command.index("--gradient-accumulation-steps") + 1]),
                ))))
                calls.append((case_id, seconds))
                return SimpleNamespace(returncode=0)

            with patch.object(experiments, "ROOT", root), patch.object(experiments, "RESULTS", results), patch.object(experiments, "INDEX", results / "experiment_index.json"), patch.object(experiments.subprocess, "run", side_effect=fake_train), patch.object(sys, "argv", ["run_experiments.py"]):
                experiments.main()

            index = json.loads((results / "experiment_index.json").read_text())
            self.assertEqual(index["winner"], "B3")
            self.assertEqual(index["speedup"], 1.55)
            self.assertEqual(set(index["finals"]), {"B2", "B3"})
            self.assertEqual(len(calls), 8)
            self.assertEqual([seconds for _, seconds in calls], [300, 90, 90, 90, 90, 90, 300, 300])


if __name__ == "__main__":
    unittest.main()
