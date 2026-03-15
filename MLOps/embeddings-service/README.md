# Embeddings Service (Part 1: Basic Inference)

CPU-only HTTP сервис для инференса эмбеддингов на модели `sergeyzh/rubert-mini-frida`.

## Реализовано

- загрузка модели `sergeyzh/rubert-mini-frida` с Hugging Face;
- инференс через `sentence_transformers` на CPU;
- HTTP API на FastAPI (`POST /embed`, `GET /health`);
- бенчмарк latency/throughput/CPU/RAM;
- фиксация метрик в этом отчете.

## Структура

```
embeddings-service/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── routes/embed.py
│   ├── service/embedder.py
│   ├── service/inference_service.py
│   └── schemas/embed.py
├── benchmark/
│   ├── run_benchmark.py
│   └── requirements.txt
├── Dockerfile
├── requirements.txt
└── README.md
```

## API

### POST `/embed`

Request:

```json
{
  "texts": ["текст 1", "текст 2"]
}
```

Response:

```json
{
  "embeddings": [[0.1, 0.2], [0.3, 0.4]],
  "texts_count": 2,
  "inference_time_ms": 12.3
}
```

### GET `/health`

```json
{"status": "ok"}
```

## Запуск локально

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Запуск в Docker

```bash
docker build -t embeddings-service .
docker run --rm -p 8000:8000 embeddings-service
```

## Бенчмарк

Метрики выбраны по требованиям производственного инференса:

- `p50/p95/p99 latency`: средняя скорость и хвостовые задержки;
- `throughput req/s`: пропускная способность API как сервиса;
- `throughput texts/s`: полезная пропускная способность для сравнения с батчированием;
- `RAM RSS`: оценка потребления памяти процесса;
- `CPU %`: проверка, ограничен ли сервис процессором.

Запуск:

```bash
pip install -r benchmark/requirements.txt
python benchmark/run_benchmark.py --base-url http://127.0.0.1:8000 --container-name embeddings-service --arg run_2026_03_08
```

Перед запуском убедитесь, что контейнер сервиса запущен:

```bash
docker ps --filter "name=embeddings-service"
```

Результаты каждого запуска сохраняются в CSV:

```bash
benchmark/results/<arg>.csv
```

## Результаты

> Хост: Apple Silicon laptop (CPU-only), локальный запуск, модель `sergeyzh/rubert-mini-frida`.
>
> Ссылка на модель: [https://huggingface.co/sergeyzh/rubert-mini-frida](https://huggingface.co/sergeyzh/rubert-mini-frida).

| Scenario | Batch | Concurrency | Requests | Success | Failed | p50 ms | p95 ms | p99 ms | req/s | texts/s | CPU avg % | RAM max MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| single_request | 1 | 1 | 30 | 30 | 0 | 16.06 | 27.65 | 34.66 | 55.40 | 55.40 | 263.55 | 379.10 |
| concurrent_load | 1 | 16 | 200 | 200 | 0 | 299.38 | 341.37 | 354.22 | 53.16 | 53.16 | 419.58 | 451.00 |
| batch_sweep | 1 | 4 | 120 | 120 | 0 | 50.77 | 57.98 | 69.69 | 76.94 | 76.94 | 304.10 | 451.00 |
| batch_sweep | 8 | 4 | 120 | 120 | 0 | 58.17 | 63.29 | 79.53 | 67.65 | 541.19 | 451.99 | 466.10 |
| batch_sweep | 16 | 4 | 120 | 120 | 0 | 76.65 | 82.20 | 309.33 | 48.44 | 775.00 | 267.79 | 470.50 |
| batch_sweep | 32 | 4 | 120 | 120 | 0 | 98.43 | 106.22 | 121.05 | 40.37 | 1291.79 | 335.25 | 484.40 |
