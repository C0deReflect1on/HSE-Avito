import argparse
from pathlib import Path

from optimum.exporters.onnx import main_export
from transformers import AutoTokenizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export HF model to ONNX format")
    parser.add_argument("--model-name", default="sergeyzh/rubert-mini-frida")
    parser.add_argument("--output-dir", default="artifacts/onnx")
    parser.add_argument("--opset", type=int, default=17)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    main_export(
        model_name_or_path=args.model_name,
        output=output_dir,
        task="feature-extraction",
        opset=args.opset,
    )
    AutoTokenizer.from_pretrained(args.model_name).save_pretrained(output_dir)
    print(f"ONNX export complete: {output_dir / 'model.onnx'}")


if __name__ == "__main__":
    main()
