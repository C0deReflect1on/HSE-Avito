# Мониторинг сервиса модерации с Prometheus и Grafana

Этот документ описывает систему мониторинга для сервиса модерации, включающую Prometheus для сбора метрик и Grafana для визуализации.

## Архитектура

- **Prometheus** - сервер для сбора и хранения метрик (порт 9090)
- **Grafana** - платформа для визуализации метрик (порт 3000)
- **FastAPI приложение** - сервис модерации с эндпоинтом `/metrics` (порт 8003)

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Запуск инфраструктуры (PostgreSQL, Redis, Kafka, Prometheus, Grafana)

```bash
docker-compose up -d
```

Это запустит:
- PostgreSQL (порт 5432)
- PostgreSQL Test (порт 5433)
- Redis (порт 6379)
- Redpanda/Kafka (порт 9092)
- Kafka Console (порт 8080)
- Prometheus (порт 9090)
- Grafana (порт 3000)

### 3. Доступ к сервисам

- **Prometheus UI**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - Логин: `admin`
  - Пароль: `admin`
- **Kafka Console**: http://localhost:8080

### 3. Запуск приложения локально

```bash
# Основное приложение
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# В отдельных терминалах запустите workers:
python -m app.workers.moderation_worker
python -m app.workers.dlq_worker
```

### 4. Доступ к метрикам

- **API**: http://localhost:8003
- **API метрики**: http://localhost:8003/metrics

## Метрики

### Стандартные HTTP метрики (автоматические)

Эти метрики автоматически собираются с помощью `prometheus-fastapi-instrumentator`:

- `http_requests_total` - общее количество HTTP запросов
- `http_request_duration_seconds` - время обработки HTTP запросов
- `http_requests_in_progress` - количество запросов в обработке

### Кастомные метрики бизнес-логики

#### 1. `predictions_total` (Counter)
Общее количество предсказаний модели с разбивкой по результату.

**Labels:**
- `result`: `violation` или `no_violation`

**Пример запроса:**
```promql
rate(predictions_total{result="violation"}[1m])
```

#### 2. `prediction_duration_seconds` (Histogram)
Время выполнения предсказания ML-модели (только инференс).

**Buckets:** [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]

**Пример запроса (p95):**
```promql
histogram_quantile(0.95, rate(prediction_duration_seconds_bucket[5m]))
```

#### 3. `prediction_errors_total` (Counter)
Количество ошибок при предсказании.

**Labels:**
- `error_type`: `model_unavailable` или `prediction_error`

**Пример запроса:**
```promql
rate(prediction_errors_total[1m])
```

#### 4. `db_query_duration_seconds` (Histogram)
Время выполнения запросов к PostgreSQL.

**Labels:**
- `query_type`: `select`, `insert`, `update`, `delete`

**Buckets:** [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]

**Пример запроса (p50 для SELECT):**
```promql
histogram_quantile(0.50, rate(db_query_duration_seconds_bucket{query_type="select"}[5m]))
```

#### 5. `model_prediction_probability` (Histogram)
Распределение вероятностей нарушений от ML-модели.

**Buckets:** [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

**Пример запроса:**
```promql
histogram_quantile(0.50, rate(model_prediction_probability_bucket[5m]))
```

## Grafana Dashboard

Dashboard автоматически загружается при старте Grafana и включает следующие панели:

### 1. RPS (Requests Per Second)
Количество входящих запросов в секунду с разбивкой по эндпоинтам.

**PromQL:**
```promql
rate(http_requests_total[1m])
```

### 2. Request Latency (p50, p95, p99)
Перцентили времени обработки запросов.

**PromQL:**
```promql
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

### 3. Error Rate
Процент запросов, завершившихся с HTTP-статусом 4xx/5xx.

**PromQL:**
```promql
sum(rate(http_requests_total{status=~"4..|5.."}[1m])) / sum(rate(http_requests_total[1m]))
```

### 4. Predictions by Result
Разбивка предсказаний по результату (violation vs no_violation).

**PromQL:**
```promql
rate(predictions_total{result="violation"}[1m])
rate(predictions_total{result="no_violation"}[1m])
```

### 5. ML Model Inference Time (p50, p95)
Перцентили времени инференса ML-модели.

**PromQL:**
```promql
histogram_quantile(0.50, rate(prediction_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(prediction_duration_seconds_bucket[5m]))
```

### 6. Database Query Duration
Время выполнения запросов к БД с разбивкой по типам операций.

**PromQL:**
```promql
histogram_quantile(0.50, rate(db_query_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))
```

### 7. Prediction Errors by Type
Частота ошибок при предсказаниях с разбивкой по типу ошибки.

**PromQL:**
```promql
rate(prediction_errors_total[1m])
```

### 8. Model Prediction Probability Distribution
Распределение вероятностей от ML-модели.

**PromQL:**
```promql
histogram_quantile(0.50, rate(model_prediction_probability_bucket[5m]))
histogram_quantile(0.95, rate(model_prediction_probability_bucket[5m]))
```

## Структура файлов

```
HSE-Avito/Backend/
├── app/
│   ├── main.py                          # FastAPI приложение с Instrumentator
│   ├── metrics.py                       # Определение кастомных метрик
│   ├── services/
│   │   └── moderation.py               # Сервис с трекингом метрик
│   └── repositories/
│       ├── moderation_repository.py    # Репозиторий с метриками БД
│       ├── items.py                    # Репозиторий items с метриками
│       └── users.py                    # Репозиторий users с метриками
├── docker-compose.yaml                 # Конфигурация Docker
├── prometheus.yml                      # Конфигурация Prometheus
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml         # Автонастройка источника данных
│   │   └── dashboards/
│   │       └── default.yml            # Автозагрузка дашбордов
│   └── dashboards/
│       └── moderation_dashboard.json  # JSON дашборда
└── requirements.txt                    # Python зависимости
```

## Настройка Prometheus

Конфигурация Prometheus находится в `prometheus.yml`:

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "moderation-service"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["host.docker.internal:8003"]
```

### Изменение target для Docker

Если приложение работает внутри Docker-сети, измените target:

```yaml
static_configs:
  - targets: ["app:8003"]  # где 'app' - имя сервиса в docker-compose
```

## Troubleshooting

### Метрики не собираются

1. Проверьте доступность эндпоинта `/metrics`:
   ```bash
   curl http://localhost:8003/metrics
   ```

2. Проверьте targets в Prometheus UI:
   - Откройте http://localhost:9090/targets
   - Убедитесь, что target "moderation-service" в состоянии UP

### Grafana не показывает данные

1. Проверьте подключение Prometheus как источника данных:
   - Configuration → Data Sources → Prometheus
   - Нажмите "Test" для проверки соединения

2. Проверьте, что данные есть в Prometheus:
   - Откройте Prometheus UI (http://localhost:9090)
   - Выполните тестовый запрос: `up{job="moderation-service"}`

### Dashboard не загрузился автоматически

1. Вручную импортируйте дашборд:
   - Grafana → Dashboards → Import
   - Загрузите файл `grafana/dashboards/moderation_dashboard.json`

## Полезные PromQL запросы

### Общая статистика

```promql
# Среднее время обработки запросов
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Количество запросов по эндпоинтам
sum by (handler) (rate(http_requests_total[1m]))

# Процент нарушений
rate(predictions_total{result="violation"}[5m]) / rate(predictions_total[5m])
```

### Производительность БД

```promql
# Самые медленные запросы (p99)
histogram_quantile(0.99, sum by (query_type, le) (rate(db_query_duration_seconds_bucket[5m])))

# Количество запросов к БД по типу
sum by (query_type) (rate(db_query_duration_seconds_count[1m]))
```

### Ошибки

```promql
# Общее количество ошибок в секунду
sum(rate(http_requests_total{status=~"5.."}[1m]))

# Ошибки предсказаний
sum by (error_type) (rate(prediction_errors_total[1m]))
```

## Рекомендации по мониторингу

1. **Алерты**: Настройте алерты в Prometheus для критических метрик:
   - Error rate > 5%
   - p99 latency > 1s
   - ML inference time > 500ms

2. **Retention**: По умолчанию Prometheus хранит данные 15 дней. Для изменения добавьте флаг в `docker-compose.yaml`:
   ```yaml
   command:
     - '--storage.tsdb.retention.time=30d'
   ```

3. **Dashboards**: Дополните дашборд панелями для ресурсов (CPU, Memory) при необходимости.

## Дополнительные ресурсы

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
