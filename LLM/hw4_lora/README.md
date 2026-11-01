# HW4. Full FT и LoRA

Дообучение `Qwen/Qwen2.5-1.5B-Instruct` на WikiWhy. Рядом сравниваются полное дообучение и LoRA, затем по одному меняются `r`, `lora_alpha`, `lora_dropout` и `target_modules`.

Качество на задаче измеряется ROUGE-L по тестовым ответам WikiWhy. Перенос на другой экзамен измеряется точностью на исторической части MMLU-Pro. Выводы, таблица и график лежат в `03_evaluation_report.ipynb`.

## Запуск

Нужна GPU. Команды запускаются из этой папки. На драйвере 570 дефолтное колесо `torch==2.8.0` с PyPI не подходит: оно собрано под CUDA 13. В таком случае ставьте `torch==2.8.0+cu126` с индекса `https://download.pytorch.org/whl/cu126`, как в HW3.

```bash
bash setup_env.sh
.venv/bin/python download_data.py
```

Ядро Jupyter называется `Python (hw4_lora)`. Дальше по порядку: `01_data.ipynb`, `02_training.ipynb`, `03_evaluation_report.ipynb`. Данные появятся в `data/`, веса и метрики в `runs/`. Оба каталога в git не входят.

Обучение Full FT и LoRA baseline в ноутбуке шло с микробатчем 1 и накоплением градиента 16. Остальные LoRA-опыты запускались с батчем 32 без накопления, поэтому их время и память нельзя ставить рядом с baseline как чистый эффект гиперпараметра.
