# Design Doc: Benchmarking Embedding Service

## 1. Цель

Получить **воспроизводимые и достоверные** метрики производительности сервиса эмбеддингов (ONNX / sentence-transformers в Docker) для принятия решений по sizing, выбору рантайма и SLA.

---

## 2. Что измеряем

| Метрика | Зачем |
|---|---|
| Latency p50 / p95 / p99 | SLA, UX |
| Throughput (req/s, texts/s) | Capacity planning |
| CPU utilization (avg, peak) | Sizing |
| RSS Memory (avg, peak) | Лимиты контейнера |
| Cold start time | Время деплоя |

---

## 3. Сценарии

```
┌─────────────────────────────────────────────────────┐
│              Benchmark Scenarios                     │
├──────────────┬──────┬─────────────┬────────────────┤
│ Scenario     │Batch │ Concurrency │ Что проверяем  │
├──────────────┼──────┼─────────────┼────────────────┤
│ baseline     │  1   │      1      │ Чистая латент. │
│ batch_sweep  │1/8/  │      4      │ Оптим. батч    │
│              │16/32 │             │                │
│ conc_sweep   │  8   │  1/4/8/16/  │ Точка деградац.│
│              │      │    32/64    │                │
│ sustained    │  8   │      16     │ Стабильность   │
│ (5 min)      │      │             │ под нагрузкой  │
│ cold_start   │  1   │      1      │ Время старта   │
│              │      │             │ контейнера     │
└──────────────┴──────┴─────────────┴────────────────┘
```

---

## 4. Тестовые данные

```python
# Не одинаковые строки! Разная длина — как в проде.
TEXT_POOL = {
    "short":  ["Продам велосипед", "Куплю iPhone", ...],          # 3-5 токенов
    "medium": ["Продам велосипед горный, 21 скорость, ...", ...],  # 20-40 токенов
    "long":   ["Большое описание объявления на 200+ слов...", ...] # 100-512 токенов
}

def make_payload(batch_size: int) -> dict:
    # Случайная выборка из пула, mixed lengths
    texts = random.choices(TEXT_POOL["short"] + TEXT_POOL["medium"] + TEXT_POOL["long"], k=batch_size)
    return {"texts": texts}
```

---

## 5. Архитектура бенчмарка

```
┌──────────────────┐         ┌─────────────────────────┐
│  Benchmark Runner │   HTTP  │   Docker Container      │
│  (python, httpx)  │───────►│                         │
│                    │        │  FastAPI / Flask         │
│  - warmup          │        │  ┌───────────────────┐  │
│  - scenarios        │        │  │ ONNX Runtime /    │  │
│  - metrics collect  │        │  │ sentence-transf.  │  │
│                    │        │  └───────────────────┘  │
│  - CSV / markdown  │        │                         │
└────────┬───────────┘        └────────┬────────────────┘
         │                             │
         │  docker stats / cAdvisor    │
         └─────────────────────────────┘
```

---

## 6. Ключевые принципы

### 6.1. Warmup — обязательно

```python
# Минимум 20-50 запросов, результаты выбрасываем
for _ in range(50):
    await client.post("/embed", json=make_payload(8))
```

Что прогревается:
- ONNX Runtime thread pool & memory allocator
- CPU кэши (L1/L2/L3)
- HTTP connection pool
- Python JIT (если используется)

### 6.2. Coordinated Omission — не допускать

```python
# ❌ НЕПРАВИЛЬНО: время ожидания в очереди не учтено
async def _one_request():
    async with semaphore:
        start = time.perf_counter()  # старт ПОСЛЕ захвата семафора
        resp = await client.post(...)
        latency = time.perf_counter() - start

# ✅ ПРАВИЛЬНО: замер от момента «пользователь отправил запрос»
async def _one_request(enqueued_at: float):
    async with semaphore:
        resp = await client.post(...)
        latency = time.perf_counter() - enqueued_at  # включает ожидание
```

### 6.3. Повторные прогоны

```
Каждый сценарий → N=5 прогонов → берём медиану
                                → считаем std dev
                                → отбрасываем выбросы (>2σ)
```

### 6.4. Изоляция между сценариями

```python
for scenario in scenarios:
    result = await run_scenario(scenario)
    results.append(result)
    
    # Пауза для стабилизации
    await asyncio.sleep(5)
    
    # Проверяем, что сервис жив и стабилен
    await healthcheck(client)
```

### 6.5. Keep-Alive — как в проде

```python
# Отражаем реальную конфигурацию
limits = httpx.Limits(
    max_connections=concurrency * 2,
    max_keepalive_connections=concurrency,  # НЕ 0
)
```

---

## 7. Сбор ресурсных метрик

### Вариант A: docker stats (простой, грубый)

```python
# Семплинг ~1 раз в секунду (чаще бессмысленно — docker stats сам усредняет)
async def sample_resources(container: str, interval: float = 1.0):
    ...
```

### Вариант B: Prometheus + cAdvisor (точный) *(рекомендуется)*

```yaml
# docker-compose.benchmark.yml
services:
  embeddings-service:
    ...
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    ports:
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /sys:/sys:ro
```

---

## 8. Фиксация окружения

Записываем в каждый отчёт:

```json
{
  "env": {
    "cpu_model": "Intel Xeon E5-2686 v4",
    "cpu_cores": 4,
    "ram_gb": 16,
    "docker_cpus": 4,
    "docker_memory_limit": "4g",
    "onnx_runtime_version": "1.17.0",
    "model_name": "all-MiniLM-L6-v2",
    "onnx_threads": 4,
    "python_version": "3.11.9",
    "os": "Ubuntu 22.04"
  }
}
```

**Без этого результаты невоспроизводимы.**

---

## 9. Формат вывода

### CSV (для анализа)

```
scenario,batch,concurrency,run,p50,p95,p99,rps,texts_s,cpu_avg,ram_max
baseline,1,1,1,12.3,14.1,15.2,78.5,78.5,45.2,312.4
baseline,1,1,2,12.1,13.9,15.0,79.1,79.1,44.8,312.1
...
```

### Markdown (для PR / отчёта)

```
| Scenario | Batch | p50 ms | p95 ms | p99 ms | texts/s |
|----------|------:|-------:|-------:|-------:|--------:|
| baseline |     1 |   12.2 |   14.0 |   15.1 |    78.8 |
```

---

## 10. Чеклист перед запуском

```
[ ] Docker контейнер с фиксированными ресурсами (--cpus, --memory)
[ ] Никаких фоновых нагрузок на хосте
[ ] Зафиксированы версии всех зависимостей
[ ] Warmup 50 запросов
[ ] Минимум 5 прогонов каждого сценария
[ ] Тексты разной длины
[ ] Keep-alive как в проде
[ ] Замер латентности с учётом Coordinated Omission
[ ] Пауза между сценариями
[ ] Метаданные окружения записаны
```

---

## 11. Чего этот бенчмарк НЕ покрывает

- **Сетевая латентность** — бенчмарк локальный, в проде будет +N ms
- **Конкуренция за ресурсы** — в k8s рядом живут другие поды
- **Деградация на длинных дистанциях** — нужен отдельный soak test (часы)
- **Разные модели** — для A/B сравнения моделей нужен одинаковый прогон на каждой