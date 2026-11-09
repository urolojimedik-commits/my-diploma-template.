"""Данные для графиков: реальные и явно помеченные учебные примеры.

Правило системы (требование «не выдумывать статистику»):

* ``provenance = "real"``      — значение извлечено из **проверенного** источника
  (абстракт / выверенная выдержка). Каждая строка хранит ключи источников,
  и они же печатаются в подписи рисунка;
* ``provenance = "synthetic"`` — учебный пример: данные смоделированы, рисунок
  получает подпись «Учебный пример (данные смоделированы)»;
* ``provenance = "diagram"``   — авторская схема, данных не содержит.

Ни один числовой показатель не генерируется «из головы»: извлечение идёт
только по текстам проверенных фактов (см. :func:`extract_metrics`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..model import DataRow, Dataset, Source

PERCENT_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[,.]\d{1,2})?)\s*(?:%|проц)", re.I)
COUNT_WORDS = (
    "изображени",
    "пациент",
    "случа",
    "срез",
    "обследованн",
    "больн",
    "наблюдени",
    "сканировани",
)
COUNT_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[\s ]?\d{3})+|\d{2,6})\s*(?=(" + "|".join(COUNT_WORDS) + r"))", re.I)
DECIMAL_RE = re.compile(r"(0[,.]\d{2,4})")


@dataclass
class Metric:
    """Числовой показатель, извлечённый из проверенного источника."""

    label: str
    value: float
    unit: str  # % | ед. | с
    context: str
    source_keys: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "context": self.context,
            "source_keys": self.source_keys,
        }


def _to_float(raw: str) -> float:
    return float(raw.replace(" ", "").replace(" ", "").replace(",", "."))


def _short_label(source: Source) -> str:
    if source.authors:
        return f"{source.authors[0].family} и др., {source.year}" if len(source.authors) > 1 else f"{source.authors[0].family}, {source.year}"
    return f"{source.title[:28]}…, {source.year}"


def _context_around(text: str, start: int, span: int = 60) -> str:
    left = max(0, start - span)
    right = min(len(text), start + span)
    ctx = text[left:right].strip(" ,;:—-")
    ctx = re.sub(r"\s+", " ", ctx)
    return ctx


def extract_metrics(sources: list[Source], kinds: tuple[str, ...] = ("percent", "count")) -> list[Metric]:
    """Извлекает числовые показатели из проверенных фактов и выдержек.

    Возвращаются только явно присутствующие в тексте числа; если абстракт
    недоступен, показатель просто не извлекается (ничего не придумывается).
    """
    metrics: list[Metric] = []
    for s in sources:
        if not s.verified:
            continue
        texts: list[str] = []
        if s.summary_ru:
            texts.append(s.summary_ru)
        texts.extend(s.facts)
        if s.abstract:
            texts.append(s.abstract)
        label = _short_label(s)
        seen: set[tuple[str, float]] = set()
        for text in texts:
            if "percent" in kinds:
                for m in PERCENT_RE.finditer(text):
                    try:
                        value = _to_float(m.group(1))
                    except ValueError:
                        continue
                    if not 0 < value <= 100:
                        continue
                    ctx = _context_around(text, m.start())
                    key = ("%", value)
                    if key in seen:
                        continue
                    seen.add(key)
                    metrics.append(Metric(label, value, "%", ctx, [s.key]))
            if "count" in kinds:
                for m in COUNT_RE.finditer(text):
                    try:
                        value = _to_float(m.group(1))
                    except ValueError:
                        continue
                    if value < 10:
                        continue
                    ctx = _context_around(text, m.start())
                    key = ("n", value)
                    if key in seen:
                        continue
                    seen.add(key)
                    metrics.append(Metric(label, value, "ед.", ctx, [s.key]))
            for m in DECIMAL_RE.finditer(text):
                ctx = _context_around(text, m.start())
                if not re.search(r"(AUC|auc|площад)", ctx):
                    continue
                try:
                    value = _to_float(m.group(1))
                except ValueError:
                    continue
                if not 0 < value <= 1:
                    continue
                if ("auc", value) in seen:
                    continue
                seen.add(("auc", value))
                metrics.append(Metric(label, value, "AUC", ctx, [s.key]))
    return metrics


def metrics_dataset(metrics: list[Metric], unit: str = "%", key: str = "metrics") -> Dataset:
    rows = [
        DataRow(
            values={
                "Исследование": m.label,
                "Значение": m.value,
                "Единица": m.unit,
                "Контекст": m.context,
                "DOI": "",
            },
            source_keys=m.source_keys,
            note=m.context,
        )
        for m in metrics
        if m.unit == unit
    ]
    return Dataset(
        key=key,
        title=f"Количественные показатели ({unit}), извлечённые из проверенных источников",
        columns=["Исследование", "Значение", "Единица", "Контекст", "DOI"],
        rows=rows,
        provenance="real",
        description="Значения извлечены автоматически из выверенных выдержек и фактов проверенных источников.",
        unit=unit,
    )


def studies_dataset(sources: list[Source]) -> Dataset:
    """Сводная таблица включённых исследований (библиографические данные)."""
    rows = []
    for s in sources:
        rows.append(
            DataRow(
                values={
                    "Источник": s.authors_ru,
                    "Год": s.year or "",
                    "Название": s.title_display,
                    "Издание": s.venue or "",
                    "DOI": s.doi or "",
                },
                source_keys=[s.key],
            )
        )
    return Dataset(
        key="studies",
        title="Характеристика включённых источников",
        columns=["Источник", "Год", "Название", "Издание", "DOI"],
        rows=rows,
        provenance="real",
        description="Библиографические данные проверенных источников (Crossref).",
    )


# --------------------------------------------------------------------------- #
# Учебный пример (смоделированные данные)
# --------------------------------------------------------------------------- #


def synthetic_roc_dataset(seed: int = 20261109) -> Dataset:
    """ROC-кривые: **учебный пример**, данные смоделированы.

    Используется только для демонстрации оформления: кривые получены
    моделированием биномиального распределения и не являются результатом
    какого-либо исследования. В подписи рисунка это указывается явно.
    """
    import math
    import random

    rng = random.Random(seed)
    rows: list[DataRow] = []

    def simulated_curve(auc_target: float, points: int = 40) -> list[tuple[float, float]]:
        # Моделирование: чувствительность = FPR^(k), k подобрано под целевой AUC
        curve = []
        for i in range(points + 1):
            fpr = i / points
            k = max(0.05, (1 - auc_target) / max(auc_target, 0.01) * 3)
            tpr = fpr ** k
            noise = (rng.random() - 0.5) * 0.02
            curve.append((round(fpr, 4), round(min(1.0, max(0.0, tpr + noise)), 4)))
        return curve

    for name, auc in (("Модель A (AUC≈0,82)", 0.82), ("Модель B (AUC≈0,95)", 0.95)):
        for fpr, tpr in simulated_curve(auc):
            rows.append(DataRow(values={"Модель": name, "FPR": fpr, "TPR": tpr}))
    return Dataset(
        key="roc_demo",
        title="ROC-кривые (учебный пример, данные смоделированы)",
        columns=["Модель", "FPR", "TPR"],
        rows=rows,
        provenance="synthetic",
        description=(
            "УЧЕБНЫЙ ПРИМЕР. Кривые построены по смоделированным данным и не являются "
            "результатом реального исследования; значение AUC задано как параметр примера."
        ),
    )


SYNTHETIC_NOTE = (
    "Учебный пример: данные смоделированы автором работы и не являются "
    "результатом реального исследования"
)


def write_datasets(datasets: list[Dataset], out_dir) -> list[str]:
    from pathlib import Path

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for d in datasets:
        p = out_dir / f"{d.key}.csv"
        p.write_text(d.to_csv(), encoding="utf-8")
        paths.append(str(p))
    return paths
