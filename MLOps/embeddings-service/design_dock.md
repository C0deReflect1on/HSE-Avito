Ты прав, я ушёл в детали реализации. Переделываю — только структура, абстракции, контракты и API.

---

# Дизайн-документ: Часть 1 — Базовый инференс

---

## 1. Структура проекта

```
embeddings-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── embed.py
│   ├── service/
│   │   ├── __init__.py
│   │   ├── embedder.py
│   │   └── inference_service.py
│   └── schemas/
│       ├── __init__.py
│       └── embed.py
├── benchmark/
│   ├── run_benchmark.py
│   └── requirements.txt
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 2. Абстракции и их связь

```
┌──────────┐       ┌───────────────────┐       ┌────────────┐
│  routes/  │──────▶│  InferenceService │──────▶│  Embedder  │
│  embed.py │       │                   │       │ (Protocol) │
└──────────┘       └───────────────────┘       └────────────┘
                                                     ▲
                                               ┌─────┴──────┐
                                               │ Часть 2:   │
                                               │ OnnxEmbedder│
                                               └─────────────┘
```

### `Embedder` — Protocol

Контракт, которому подчиняются все реализации.

```
embed(texts: list[str]) -> list[list[float]]
```

### `InferenceService`

Фасад. Единственное, что знают роуты. Принимает любой объект, удовлетворяющий `Embedder`.

```
__init__(embedder: Embedder)
embed(texts: list[str]) -> list[list[float]]
```

> **Часть 3:** батчирование встраивается **внутрь** `InferenceService` — роуты не меняются.

### `config.py`

Все настройки сервиса из ENV (model name, host, port, max batch size и т.д.).

### `main.py`

- lifespan: создаёт `Embedder` → `InferenceService` → кладёт в `app.state`
- подключает роутер

---

## 3. API

### `POST /embed`

**Request:**
```json
{
  "texts": ["текст 1", "текст 2"]
}
```

**Response:**
```json
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
  "texts_count": 2,
  "inference_time_ms": 12.3
}
```

### `GET /health`

**Response:**
```json
{"status": "ok"}
```

---

## 4. Docker

- Единый `Dockerfile` — собирает и запускает сервис
- Модель скачивается на этапе `docker build` (образ самодостаточный)
- CPU-only torch
- `CMD`: uvicorn

---

## 5. Бенчмарки

### Метрики

| Метрика | Обоснование |
|---|---|
| Latency p50 / p95 / p99 | Хвосты важнее среднего |
| Throughput (req/s и texts/s) | texts/s нужен для сравнения с батчированием в Части 3 |
| RAM (RSS) | Capacity planning на CPU |
| CPU % | Понять, упираемся ли в процессор |

### Сценарии

- Single request (1 текст)
- Concurrent load (N параллельных клиентов)
- Batch size sweep (1 / 8 / 16 / 32 текста в запросе)

Результаты фиксируются таблицей в `README.md`.

---

## 6. Расширяемость

| Часть | Что добавляется | Что меняется |
|---|---|---|
| **Часть 2** | `service/onnx_embedder.py` (реализует `Embedder`) | `main.py` — выбор embedder по ENV |
| **Часть 3** | Батчирование внутри `InferenceService` (очередь + worker) | `inference_service.py`. Роуты **не трогаем** |

---
