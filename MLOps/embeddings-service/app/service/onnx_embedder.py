from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer


class OnnxEmbedder:
    def __init__(self, model_name: str, onnx_model_dir: str, provider: str = "CPUExecutionProvider") -> None:
        model_path = Path(onnx_model_dir) / "model.onnx"
        if not model_path.exists():
            raise FileNotFoundError(
                f"ONNX model is missing at '{model_path}'. Run conversion before starting the service."
            )

        available_providers = ort.get_available_providers()
        if provider not in available_providers:
            raise RuntimeError(
                f"ONNX provider '{provider}' is unavailable. Available providers: {available_providers}"
            )

        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._session = ort.InferenceSession(str(model_path), providers=[provider])

    def embed(self, texts: list[str]) -> list[list[float]]:
        tokens = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="np",
        )

        ort_inputs = {
            "input_ids": tokens["input_ids"].astype(np.int64),
            "attention_mask": tokens["attention_mask"].astype(np.int64),
        }

        outputs = self._session.run(None, ort_inputs)
        return outputs[1]
