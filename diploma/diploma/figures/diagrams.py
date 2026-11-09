"""Научные иллюстрации (схемы), которые не содержат числовых данных.

Схемы рисуются средствами matplotlib — это векторный по своей природе
подход, дающий одинаковый результат в DOCX и PDF без внешних редакторов.
Содержание схемы полностью определяется структурой работы (планом), поэтому
ничего не выдумывается: блоки — это этапы исследования из плана.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

PALETTE = ["#2f5d8a", "#3f7ca8", "#4f9bc0", "#5fb3cc"]
BG = "#eef4f9"


def _wrap_label(text: str, width: int = 30) -> str:
    parts, line = [], ""
    for word in str(text).split():
        if len(line) + len(word) + 1 > width and line:
            parts.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    parts.append(line)
    return "\n".join(parts)


def pipeline_diagram(
    stages: list[str],
    output: Path,
    title: str = "",
    subtitle: str = "",
    figsize: tuple[float, float] = (7.2, 5.6),
    dpi: int = 200,
) -> Path:
    """Вертикальная схема этапов исследования со стрелками."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    n = len(stages)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, n * 1.6 + 0.6)
    ax.axis("off")

    box_h = 0.95
    gap = 0.65
    for i, stage in enumerate(stages):
        y = (n - 1 - i) * (box_h + gap) + 0.35
        color = PALETTE[i % len(PALETTE)]
        box = FancyBboxPatch(
            (1.0, y),
            8.0,
            box_h,
            boxstyle="round,pad=0.08,rounding_size=0.18",
            linewidth=1.4,
            edgecolor=color,
            facecolor=BG,
        )
        ax.add_patch(box)
        ax.text(
            5.0,
            y + box_h / 2,
            _wrap_label(stage),
            ha="center",
            va="center",
            fontsize=11,
            color="#123",
        )
        ax.text(
            1.35,
            y + box_h / 2,
            str(i + 1),
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="white",
        )
        circle = plt.Circle((1.35, y + box_h / 2), 0.24, color=color, zorder=3)
        ax.add_patch(circle)
        if i < n - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (5.0, y),
                    (5.0, y - gap + 0.02),
                    arrowstyle="-|>",
                    mutation_scale=14,
                    linewidth=1.4,
                    color="#556",
                )
            )
    if title:
        ax.set_title(title, fontsize=12, pad=10)
    if subtitle:
        fig.text(0.5, 0.02, subtitle, ha="center", fontsize=9, color="#556")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(output, dpi=dpi, facecolor="white")
    plt.close(fig)
    return output


def structure_diagram(
    blocks: list[tuple[str, list[str]]],
    output: Path,
    title: str = "",
    figsize: tuple[float, float] = (8.0, 4.6),
    dpi: int = 200,
) -> Path:
    """Горизонтальная схема: несколько столбцов с подпунктами."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    n = len(blocks)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_xlim(0, n * 3.2 + 0.4)
    ax.set_ylim(0, 5.4)
    ax.axis("off")
    width = 2.8
    for i, (head, items) in enumerate(blocks):
        x = 0.2 + i * (width + 0.4)
        ax.add_patch(
            FancyBboxPatch(
                (x, 3.3),
                width,
                1.4,
                boxstyle="round,pad=0.06,rounding_size=0.16",
                linewidth=1.4,
                edgecolor=PALETTE[i % len(PALETTE)],
                facecolor=PALETTE[i % len(PALETTE)],
            )
        )
        ax.text(
            x + width / 2,
            4.0,
            _wrap_label(head, 24),
            ha="center",
            va="center",
            fontsize=11,
            color="white",
            fontweight="bold",
        )
        for j, item in enumerate(items[:4]):
            y = 2.6 - j * 0.72
            ax.add_patch(
                FancyBboxPatch(
                    (x, y),
                    width,
                    0.58,
                    boxstyle="round,pad=0.04,rounding_size=0.1",
                    linewidth=1.0,
                    edgecolor=PALETTE[i % len(PALETTE)],
                    facecolor=BG,
                )
            )
            ax.text(x + width / 2, y + 0.29, _wrap_label(item, 28), ha="center", va="center", fontsize=9)
        if i < n - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + width, 4.0),
                    (x + width + 0.4, 4.0),
                    arrowstyle="-|>",
                    mutation_scale=14,
                    linewidth=1.4,
                    color="#556",
                )
            )
    if title:
        ax.set_title(title, fontsize=12, pad=10)
    fig.tight_layout()
    fig.savefig(output, dpi=dpi, facecolor="white")
    plt.close(fig)
    return output
