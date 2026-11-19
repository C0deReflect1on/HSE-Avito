"""Сводка и автономный ноутбук с таблицами и графиками."""

import base64
import json

import nbformat
from matplotlib.figure import Figure

from hw6_experiments import BASELINE_NGRAMS, FIXED_RPM, best_fixed, write_json


def format_value(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def table(rows, columns):
    headers = " | ".join(label for _, label in columns)
    separators = " | ".join("---" for _ in columns)
    lines = [f"| {headers} |", f"| {separators} |"]
    for row in rows:
        values = " | ".join(format_value(row.get(key)) for key, _ in columns)
        lines.append(f"| {values} |")
    return "\n".join(lines)


def figure_cell(figure, path, alt):
    figure.savefig(path, dpi=155, bbox_inches="tight")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return nbformat.v4.new_markdown_cell(
        f"![{alt}](attachment:{path.name})",
        attachments={path.name: {"image/png": payload}},
    )


def spec_points(rows, rates, speculative):
    by_config = {
        (row["config"], row["rpm"]): row
        for row in rows
        if row["phase"] in {"fixed", "spec"} and row["status"] == "ok"
    }
    points = []
    for rpm in sorted({FIXED_RPM, *rates}):
        baseline = by_config.get(("baseline", rpm), {}).get("p90_e2e_s")
        spec = by_config.get((speculative, rpm), {}).get("p90_e2e_s")
        delta = spec - baseline if spec is not None and baseline is not None else None
        points.append({"rpm": rpm, "baseline_p90_s": baseline, "ngram_p90_s": spec, "delta_s": delta})
    return points


def spec_figure(points, speculative, first_worse):
    figure = Figure(figsize=(8.2, 4.3), layout="constrained")
    ax = figure.subplots()
    rates = [point["rpm"] for point in points]
    for key, label, color in (
        ("baseline_p90_s", "Бейзлайн", "#2a6088"),
        ("ngram_p90_s", speculative, "#a54c25"),
    ):
        values = [point[key] if point[key] is not None else float("nan") for point in points]
        ax.plot(rates, values, marker="o", color=color, label=label)
    if first_worse:
        rpm = first_worse["rpm"]
        ax.axvline(rpm, color="#666666", linestyle=":", label=f"n-gram медленнее при {rpm} RPM")
    ax.set_xscale("log", base=2)
    ax.set_xticks(rates, [str(rpm) for rpm in rates])
    ax.set(xlabel="Заданная нагрузка, RPM", ylabel="P90 E2E, с")
    ax.grid(alpha=0.25)
    ax.legend()
    return figure


def capacity_figure(rows, sla, highest_pass, first_fail):
    figure = Figure(figsize=(8.2, 4.3), layout="constrained")
    ax = figure.subplots()
    measured = [row for row in rows if row.get("sla_pass") is not None]
    ax.plot(
        [row["rpm"] for row in measured],
        [row["p90_e2e_s"] if row["p90_e2e_s"] is not None else float("nan") for row in measured],
        color="#707b84", linewidth=1.4,
    )
    ax.axhline(sla, linestyle="--", color="#666666", label=f"SLA < {sla} с")
    for passed, color, marker, label in (
        (True, "#28784c", "o", "SLA пройден"),
        (False, "#b0443c", "x", "SLA нарушен"),
    ):
        points = [row for row in measured if row["sla_pass"] is passed and row["p90_e2e_s"] is not None]
        if points:
            ax.scatter(
                [row["rpm"] for row in points],
                [row["p90_e2e_s"] for row in points],
                color=color, marker=marker, label=label, zorder=3,
            )
    missing = [row["rpm"] for row in measured if row["p90_e2e_s"] is None]
    if missing:
        ax.scatter(
            missing, [0.035] * len(missing), transform=ax.get_xaxis_transform(),
            marker="v", color="#b0443c", label="SLA нарушен · P90 отсутствует", zorder=3,
        )
    for row, color, label in (
        (highest_pass, "#28784c", "Наибольший пройденный"),
        (first_fail, "#b0443c", "Ближайший провал выше"),
    ):
        if row:
            rpm = row["rpm"]
            ax.axvline(rpm, color=color, linestyle=":", label=f"{label} · {rpm} RPM")
    ax.set(xlabel="Заданная нагрузка, RPM", ylabel="P90 E2E, с")
    ax.grid(alpha=0.25)
    ax.legend()
    return figure


def write_results(directory):
    metadata = json.loads((directory / "environment.json").read_text())
    measurements = directory / "results.json"
    rows = json.loads(measurements.read_text()) if measurements.exists() else []
    best = best_fixed(rows)
    speculative = best_fixed(rows, BASELINE_NGRAMS)
    ngram_attempts = {row["config"] for row in rows if row["phase"] == "fixed"}
    if speculative:
        points = spec_points(rows, metadata["spec_rpms"], speculative["config"])
        spec_status = "complete" if all(point["delta_s"] is not None for point in points) else "partial"
    elif ngram_attempts.issuperset(BASELINE_NGRAMS):
        points = []
        spec_status = "no_valid_ngram_candidate"
    else:
        points = []
        spec_status = "not_started"
    first_worse = next((point for point in points if (point["delta_s"] or 0) > 0), None)

    capacity = sorted((row for row in rows if row["phase"] == "capacity"), key=lambda row: row["rpm"])
    highest_pass = next((row for row in reversed(capacity) if row.get("sla_pass") is True), None)
    passing_rpm = highest_pass["rpm"] if highest_pass else 0
    first_fail = next(
        (row for row in capacity if row.get("sla_pass") is False and row["rpm"] > passing_rpm), None
    )
    capacity_status = "not_started"
    if capacity:
        capacity_status = "partial"
        if highest_pass and passing_rpm == metadata["max_capacity_rpm"]:
            capacity_status = "search_ceiling_passed"
        elif first_fail and first_fail["rpm"] - passing_rpm == metadata["capacity_step_rpm"]:
            capacity_status = "bracketed" if highest_pass else "lowest_rate_failed"

    write_json(directory / "summary.json", {
        "best_fixed": best,
        "spec_status": spec_status,
        "speculative_config": speculative["config"] if speculative else None,
        "spec_points": points,
        "first_spec_worse": first_worse,
        "capacity_status": capacity_status,
        "max_tested_passing": highest_pass,
        "next_tested_failing": first_fail,
    })

    model = metadata["model"]
    gpu = metadata["gpu_name"]
    driver = metadata["gpu_driver"]
    cells = [nbformat.v4.new_markdown_cell(
        f"# HW6. Результаты инференса\n\n{model}, vLLM 0.22.0, AIPerf {metadata['aiperf']}. "
        f"GPU {gpu} ({metadata['gpu_memory']}), драйвер {driver}. "
        f"Датасет содержит {metadata['dataset_requests']} исходных запросов. "
        "Для каждого запроса использованы temperature 0, seed 42, max_tokens 512 и enable_thinking false."
    )]

    fixed_rows = [row for row in rows if row["phase"] == "fixed"]
    if fixed_rows:
        fixed_note = "Ожидается валидный замер."
        if best:
            fixed_note = (
                f"Лучшая конфигурация **{best['config']}**. Ускорение "
                f"**{best['speedup_vs_baseline']:.3f}×**, P90 **{best['p90_e2e_s']:.3f} с**."
            )
        cells.append(nbformat.v4.new_markdown_cell(
            f"## Фиксированная нагрузка {FIXED_RPM} RPM\n\n{fixed_note}\n\n"
            + table(fixed_rows, [
                ("config", "Конфигурация"), ("engine_args", "Аргументы vLLM"),
                ("mean_e2e_s", "Mean E2E, с"), ("p90_e2e_s", "P90 E2E, с"),
                ("speedup_vs_baseline", "S"), ("completed", "Ответы"), ("status", "Статус"),
            ])
        ))

    if points:
        spec_note = "Среди валидных пар ухудшение от n-gram не наблюдалось."
        if first_worse:
            spec_note = (
                f"Первый измеренный RPM, где n-gram медленнее по P90 — **{first_worse['rpm']}**. "
                f"Разница составляет **{first_worse['delta_s']:.3f} с**."
            )
        if spec_status == "partial":
            spec_note += " Для части нагрузок пока нет валидных пар замеров."
        cells.append(nbformat.v4.new_markdown_cell(
            f"## Спекулятивное декодирование\n\n{spec_note}\n\n"
            + table(points, [
                ("rpm", "RPM"), ("baseline_p90_s", "P90 бейзлайна, с"),
                ("ngram_p90_s", "P90 n-gram, с"), ("delta_s", "n-gram − бейзлайн, с"),
            ])
        ))
        cells.append(figure_cell(
            spec_figure(points, speculative["config"], first_worse),
            directory / "spec_p90.png", "P90 для бейзлайна и n-gram",
        ))
    elif spec_status == "no_valid_ngram_candidate":
        cells.append(nbformat.v4.new_markdown_cell(
            "## Спекулятивное декодирование\n\n"
            "Оба варианта n-gram завершились без валидного замера при 120 RPM. "
            "Сравнение по нагрузкам не состоялось. Статусы и детали доступны ниже."
        ))

    if capacity:
        note = {
            "bracketed": f"Наибольшая проверенная нагрузка под SLA — **{passing_rpm} RPM**. "
            f"Ближайшая проверенная точка провала выше — **{first_fail['rpm'] if first_fail else '—'} RPM**.",
            "search_ceiling_passed": f"Предел поиска **{passing_rpm} RPM** выдержан.",
            "lowest_rate_failed": "SLA нарушен на минимальной точке сетки.",
            "partial": f"Граница ещё не установлена. Лучший подтверждённый RPM — {passing_rpm or '—'}.",
        }[capacity_status]
        cells.append(nbformat.v4.new_markdown_cell(
            f"## Нагрузочное тестирование по {metadata['capacity_seconds']} с на точку\n\n"
            f"{note} Конфигурация **{capacity[0]['config']}**.\n\n"
            + table(capacity, [
                ("rpm", "RPM"), ("offered_rpm", "Фактические RPM"), ("attempted", "Отправлено"),
                ("errors", "Ошибки"), ("p90_e2e_s", "P90 E2E, с"), ("sla_pass", "SLA"),
                ("status", "Статус"),
            ])
        ))
        cells.append(figure_cell(
            capacity_figure(capacity, metadata["sla_p90_s"], highest_pass, first_fail),
            directory / "capacity_p90.png", "P90 и граница SLA",
        ))

    if rows:
        cells.append(nbformat.v4.new_markdown_cell(
            "## Артефакты замеров\n\n"
            + table(rows, [
                ("phase", "Этап"), ("config", "Конфигурация"), ("rpm", "RPM"),
                ("artifacts", "Артефакты AIPerf"), ("status", "Статус"), ("detail", "Детали"),
            ])
        ))
    notebook = nbformat.v4.new_notebook(cells=cells)
    path = directory / "results_notebook.ipynb"
    nbformat.write(notebook, path)
    return path
