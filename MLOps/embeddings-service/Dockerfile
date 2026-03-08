FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app

ARG MODEL_NAME=sergeyzh/rubert-mini-frida
ENV MODEL_NAME=${MODEL_NAME}
ENV HOST=0.0.0.0
ENV PORT=8000

# Build image with preloaded model to make runtime deterministic.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${MODEL_NAME}', device='cpu')"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
