"""Построение графиков и диаграмм на основе данных (шаг 5).

Используется matplotlib. Все графики строятся только по :class:`Dataset`,
поэтому их происхождение (реальные данные / учебный пример) всегда известно и
переносится в подпись рисунка.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from ..model import Dataset  # noqa: E402

# DejaVu содержит кириллицу и поставляется вместе с matplotlib —
# это избавляет документ от «квадратов» вместо русских букв.
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.autolayout": False,
        "savefig.bbox": "tight",
    }
)

PALETTE = [
    "#2f5d8a",
    "#c0504d",
    "#4f81a8",
    "#9bbb59",
    "#8064a2",
    "#4bacc6",
    "#f79646",
    "#7f7f7f",
]

WATERMARKS = {
    "synthetic": "УЧЕБНЫЙ ПРИМЕР (данные смоделированы)",
}


@dataclass
class ChartSpec:
    kind: str  # bar | barh | grouped_bar | pie | line | scatter | hist | heatmap
    dataset: Dataset
    output: Path
    title: str = ""
    x: str = ""
    y: str = ""
    group: str = ""
    xlabel: str = ""
    ylabel: str = ""
    rotate_xticks: int = 0
    log_scale: bool = False
    value_labels: bool = True
    figsize: tuple[float, float] = (8.0, 4.5)
    dpi: int = 200
    legend: bool = True
    extra: dict = field(default_factory=dict)


def _rows(dataset: Dataset) -> list[dict]:
    return [r.values for r in dataset.rows]


def _fmt_num(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value))}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _add_watermark(fig: "matplotlib.figure.Figure", dataset: Dataset) -> None:
    mark = WATERMARKS.get(dataset.provenance)
    if not mark:
        return
    fig.text(
        0.5,
        0.02,
        mark,
        ha="center",
        fontsize=9,
        color="#b03030",
        style="italic",
    )


def render_chart(spec: ChartSpec) -> Path:
    """Строит график и сохраняет его в PNG."""
    output = Path(spec.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = _rows(spec.dataset)
    if not rows:
        raise ValueError(f"Набор данных «{spec.dataset.key}» пуст — строить график не по чему")

    fig, ax = plt.subplots(figsize=spec.figsize, dpi=spec.dpi)
    kind = spec.kind

    if kind == "bar":
        _bar(ax, spec, rows)
    elif kind == "barh":
        _barh(ax, spec, rows)
    elif kind == "grouped_bar":
        _grouped_bar(ax, spec, rows)
    elif kind == "pie":
        _pie(ax, spec, rows)
    elif kind == "line":
        _line(ax, spec, rows)
    elif kind == "scatter":
        _scatter(ax, spec, rows)
    elif kind == "hist":
        _hist(ax, spec, rows)
    elif kind == "heatmap":
        _heatmap(ax, spec, rows)
    else:
        raise ValueError(f"Неизвестный тип графика: {kind}")

    if spec.title:
        ax.set_title(spec.title, pad=12)
    if spec.xlabel:
        ax.set_xlabel(spec.xlabel)
    if spec.ylabel:
        ax.set_ylabel(spec.ylabel)

    if spec.dataset.provenance == "synthetic":
        for spine in ax.spines.values():
            spine.set_edgecolor("#b03030")
            spine.set_linewidth(1.2)

    _add_watermark(fig, spec.dataset)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output, dpi=spec.dpi, facecolor="white")
    plt.close(fig)
    return output


# --------------------------------------------------------------------------- #
# Отдельные типы графиков
# --------------------------------------------------------------------------- #


def _wrap(text: str, width: int = 22) -> str:
    parts, line = [], ""
    for word in str(text).split():
        if len(line) + len(word) + 1 > width and line:
            parts.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    parts.append(line)
    return "\n".join(parts)


def _bar(ax, spec: ChartSpec, rows: list[dict]) -> None:
    x = [ _wrap(r.get(spec.x, "")) for r in rows ]
    y = [_to_f(r.get(spec.y)) for r in rows]
    bars = ax.bar(x, y, color=PALETTE[0], edgecolor="white", width=0.62)
    if spec.value_labels:
        for b, v in zip(bars, y):
            ax.annotate(
                _fmt_num(v),
                (b.get_x() + b.get_width() / 2, b.get_height()),
                ha="center",
                va="bottom",
                fontsize=9,
            )
    ax.set_xticks(range(len(x)))
    ax.set_xticklabels(x, rotation=spec.rotate_xticks, ha=("right" if spec.rotate_xticks else "center"))
    if spec.log_scale:
        ax.set_yscale("log")
    _shade_synthetic(ax, spec)


def _barh(ax, spec: ChartSpec, rows: list[dict]) -> None:
    x = [str(r.get(spec.x, "")) for r in rows]
    y = [_to_f(r.get(spec.y)) for r in rows]
    bars = ax.barh(x, y, color=PALETTE[: len(rows)], edgecolor="white")
    if spec.value_labels:
        for b, v in zip(bars, y):
            ax.annotate(
                _fmt_num(v),
                (b.get_width(), b.get_y() + b.get_height() / 2),
                va="center",
                ha="left",
                fontsize=9,
                xytext=(3, 0),
                textcoords="offset points",
            )
    ax.invert_yaxis()
    if spec.log_scale:
        ax.set_xscale("log")
    _shade_synthetic(ax, spec)


def _grouped_bar(ax, spec: ChartSpec, rows: list[dict]) -> None:
    import numpy as np

    groups: list[str] = []
    for r in rows:
        g = str(r.get(spec.x, ""))
        if g not in groups:
            groups.append(g)
    series: list[str] = []
    for r in rows:
        s = str(r.get(spec.group, ""))
        if s not in series:
            series.append(s)
    width = 0.8 / max(len(series), 1)
    x = np.arange(len(groups))
    for i, s in enumerate(series):
        values = []
        for g in groups:
            v = next(
                (_to_f(r.get(spec.y)) for r in rows if str(r.get(spec.x)) == g and str(r.get(spec.group)) == s),
                0.0,
            )
            values.append(v)
        pos = x - 0.4 + width / 2 + i * width
        bars = ax.bar(pos, values, width=width, label=s, color=PALETTE[i % len(PALETTE)], edgecolor="white")
        if spec.value_labels:
            for b, v in zip(bars, values):
                ax.annotate(
                    _fmt_num(v),
                    (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
    ax.set_xticks(x)
    ax.set_xticklabels([_wrap(g) for g in groups], rotation=spec.rotate_xticks)
    if spec.legend:
        ax.legend(frameon=False, fontsize=9)
    _shade_synthetic(ax, spec)


def _pie(ax, spec: ChartSpec, rows: list[dict]) -> None:
    labels = [str(r.get(spec.x, "")) for r in rows]
    values = [_to_f(r.get(spec.y)) for r in rows]
    ax.pie(
        values,
        labels=labels,
        autopct=lambda p: f"{p:.1f} %",
        colors=PALETTE[: len(values)],
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1.2},
        textprops={"fontsize": 10},
    )
    ax.grid(False)


def _line(ax, spec: ChartSpec, rows: list[dict]) -> None:
    series: list[str] = []
    for r in rows:
        s = str(r.get(spec.group or "", ""))
        if s and s not in series:
            series.append(s)
    if series:
        for i, s in enumerate(series):
            pts = [(_to_f(r.get(spec.x)), _to_f(r.get(spec.y))) for r in rows if str(r.get(spec.group)) == s]
            pts.sort()
            ax.plot(
                [p[0] for p in pts],
                [p[1] for p in pts],
                marker="o",
                markersize=3,
                linewidth=1.8,
                label=s,
                color=PALETTE[i % len(PALETTE)],
            )
        if spec.legend:
            ax.legend(frameon=False, fontsize=9)
    else:
        pts = [(_to_f(r.get(spec.x)), _to_f(r.get(spec.y))) for r in rows]
        pts.sort()
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", markersize=3, color=PALETTE[0])
    _shade_synthetic(ax, spec)


def _scatter(ax, spec: ChartSpec, rows: list[dict]) -> None:
    series: list[str] = []
    for r in rows:
        s = str(r.get(spec.group or "", ""))
        if s and s not in series:
            series.append(s)
    if series:
        for i, s in enumerate(series):
            pts = [(_to_f(r.get(spec.x)), _to_f(r.get(spec.y))) for r in rows if str(r.get(spec.group)) == s]
            ax.scatter(
                [p[0] for p in pts],
                [p[1] for p in pts],
                s=28,
                alpha=0.8,
                label=s,
                color=PALETTE[i % len(PALETTE)],
            )
        if spec.legend:
            ax.legend(frameon=False, fontsize=9)
    else:
        ax.scatter(
            [_to_f(r.get(spec.x)) for r in rows],
            [_to_f(r.get(spec.y)) for r in rows],
            s=28,
            color=PALETTE[0],
        )
    _shade_synthetic(ax, spec)


def _hist(ax, spec: ChartSpec, rows: list[dict]) -> None:
    values = [_to_f(r.get(spec.x or spec.y)) for r in rows]
    ax.hist(values, bins=spec.extra.get("bins", 12), color=PALETTE[0], edgecolor="white")
    _shade_synthetic(ax, spec)


def _heatmap(ax, spec: ChartSpec, rows: list[dict]) -> None:
    import numpy as np

    x_labels: list[str] = []
    y_labels: list[str] = []
    for r in rows:
        if str(r.get(spec.x)) not in x_labels:
            x_labels.append(str(r.get(spec.x)))
        if str(r.get(spec.y)) not in y_labels:
            y_labels.append(str(r.get(spec.y)))
    matrix = np.zeros((len(y_labels), len(x_labels)))
    for r in rows:
        i = y_labels.index(str(r.get(spec.y)))
        j = x_labels.index(str(r.get(spec.x)))
        matrix[i, j] = _to_f(r.get(spec.group or "Значение"))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=spec.rotate_xticks or 45, ha="right")
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.grid(False)
    for i in range(len(y_labels)):
        for j in range(len(x_labels)):
            ax.text(j, i, _fmt_num(matrix[i, j]), ha="center", va="center", fontsize=9)
    ax.figure.colorbar(im, ax=ax, shrink=0.8)


def _shade_synthetic(ax, spec: ChartSpec) -> None:
    if spec.dataset.provenance == "synthetic":
        ax.set_facecolor("#fff7f7")


def _to_f(value) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace(" ", ""))
    if not m:
        return 0.0
    return float(m.group(0).replace(",", "."))


def thousands_formatter():
    return FuncFormatter(lambda v, _pos: f"{int(v):,}".replace(",", " "))
