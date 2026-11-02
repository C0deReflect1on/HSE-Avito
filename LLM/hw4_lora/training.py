import json
import time
from pathlib import Path

import torch
import transformers
import peft

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"


def load_base_model(model_name, *, revision, dtype, device):
    """Загрузка исходной модели закреплённой ревизии для независимого опыта.

    model_name и revision задают модель и версию файлов Hugging Face.
    dtype задаёт тип весов, device — устройство. Загрузка и перенос модели
    выполняются до измерения времени обучения. Каждый опыт использует
    исходные веса; Full FT обучает все параметры без квантования.
    """
    model = transformers.AutoModelForCausalLM.from_pretrained(
        model_name,
        revision=revision,
        dtype=dtype,
    )
    model.to(device)
    return model


def attach_lora(model, config):
    lora_config = peft.LoraConfig(**config)
    model = peft.get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    print(model)
    return model


def count_parameters(model):
    """Подсчёт общего числа и числа обучаемых элементов тензоров параметров.

    Возвращает dict с целыми trainable_parameters и total_parameters.
    requires_grad определяет, входит ли параметр в обучаемую часть.
    """
    total = 0
    trainable = 0
    params = model.parameters()
    for p in params:
        n = p.numel()
        total += n
        if p.requires_grad:
            trainable += n

    return {
        "trainable_parameters": trainable,
        "total_parameters": total,
    }


def train_model(
    model,
    tokenizer,
    train_dataset,
    validation_dataset,
    data_collator,
    config,
    output_dir,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    args = transformers.TrainingArguments(
        output_dir=str(output_dir),
        **config
    )

    trainer = transformers.Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        data_collator=data_collator,
        processing_class=tokenizer,
    )

    device = model.device

    torch.cuda.synchronize(device)
    torch.cuda.reset_peak_memory_stats(device)
    
    started = time.perf_counter()

    trainer.train()

    torch.cuda.synchronize(device)
    train_seconds = time.perf_counter() - started
    peak_memory = torch.cuda.max_memory_allocated(device)

    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(output_dir)

    with (output_dir / "log_history.json").open("w") as file:
        json.dump(trainer.state.log_history, file, indent=2)

    return {
        "train_seconds": train_seconds,
        "peak_gpu_memory_gb": peak_memory / 1024**3, # GiB
        **count_parameters(model)
    }



def make_lora_experiments(baseline):
    """Независимые конфигурации LoRA с изменением одного параметра baseline.

    Возвращает dict {имя_опыта: аргументы_LoraConfig}, включая baseline.
    Варианты: r — 8 и 32; lora_alpha — 16 и 64; lora_dropout — 0.0 и 0.1;
    target_modules — q_proj, k_proj, v_proj, o_proj вместе.
    Исходный baseline не изменяется. При фиксированном lora_alpha
    изменение r также меняет масштаб alpha/r.
    """
    exp_params = {
        'r_8': ('r', 8),
        'r_32': ('r', 32),
        'alpha_16': ('lora_alpha', 16),
        'alpha_64': ('lora_alpha', 64),
        'dp_0.0': ('lora_dropout', 0.0),
        'dp_0.1': ('lora_dropout', 0.1),
        'qkvo': ('target_modules', ['q_proj', 'k_proj', 'v_proj', 'o_proj']),
    }

    experiments = {'baseline': baseline.copy()}

    for name, (param, value) in exp_params.items():
        config = baseline.copy()
        config[param] = value
        experiments[name] = config
    
    return experiments