# ДЗ 2: запуск на A100

Запускайте команды из `LLM/hw2`. Нужна одна A100 с 80 ГБ памяти. Docker сохраняет данные и результаты в текущей папке.

```bash
docker build -t llm-hw2 .
docker run --rm --gpus all --ipc=host --user "$(id -u):$(id -g)" \
  -e HF_HOME=/app/.cache/huggingface -e MPLCONFIGDIR=/app/.cache/matplotlib \
  -v "$PWD:/app" -w /app llm-hw2 python run_experiments.py
docker run --rm --user "$(id -u):$(id -g)" \
  -e MPLCONFIGDIR=/app/.cache/matplotlib -v "$PWD:/app" -w /app \
  llm-hw2 python plot_results.py
```

`python train.py` без аргументов запускает исходную конфигурацию на 300 секунд и пишет `results/baseline`. Запускатор использует отдельный каталог для каждого опыта. Он выполняет шесть конфигураций, затем повторяет два самых быстрых коротких опыта по 300 секунд. Повторный вызов пропускает готовые результаты. Незавершённый каталог без `summary.json` требует проверки `run.log` и переименования перед новым запуском. Для CUDA OOM при батче 64 × 1 запускатор сам заменяет B1 и B5 на 16 × 4. Старые каталоги он сохраняет.

В каждом каталоге запуска находятся `config.json`, `summary.json` и `run.log`. В `results/experiment_index.json` записаны выбранные каталоги, итоговый опыт и ускорение S. Используйте эти файлы для заполнения `report.md`. Графики появятся в `throughput_memory.png` и `full_runs.png`. Сохраните `summary.json` успешных запусков и оба PNG в репозитории.

ETA в `run.log` относится к текущему этапу. Время загрузки данных и финальной валидации не входит в 300 секунд обучения.

Реализуйте три функции в `collectives.py`. Затем запустите notebook `communications.ipynb` из этой папки. Он проверит операции на 2 и 4 процессах. Сохраните notebook с выводом `OK` для обоих запусков. Те же проверки доступны без notebook:

```bash
python -m torch.distributed.run --standalone --nproc-per-node=2 check.py
python -m torch.distributed.run --standalone --nproc-per-node=4 check.py
```
