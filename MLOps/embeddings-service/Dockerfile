FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY scripts /app/scripts

ARG MODEL_NAME=sergeyzh/rubert-mini-frida
ARG INFERENCE_BACKEND=hf
ENV MODEL_NAME=${MODEL_NAME}
ENV INFERENCE_BACKEND=${INFERENCE_BACKEND}
ENV ONNX_MODEL_DIR=/app/artifacts/onnx
ENV ONNX_EXECUTION_PROVIDER=CPUExecutionProvider
ENV HOST=0.0.0.0
ENV PORT=8000

# Build image with preloaded artifacts to make runtime deterministic.
RUN if [ "${INFERENCE_BACKEND}" = "onnx" ]; then \
      python /app/scripts/convert_to_onnx.py --model-name "${MODEL_NAME}" --output-dir "${ONNX_MODEL_DIR}"; \
    else \
      python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${MODEL_NAME}', device='cpu')"; \
    fi

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
