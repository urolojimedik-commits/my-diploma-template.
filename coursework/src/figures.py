# -*- coding: utf-8 -*-
"""Генератсияи расмҳо, диаграммаҳо ва схемаҳои кори курсӣ."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

plt.rcParams["font.family"] = "DejaVu Serif"
plt.rcParams["font.size"] = 10

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")
os.makedirs(OUT, exist_ok=True)


def _save(fig, name, fs=1.0):
    import matplotlib.text as mtext
    if fs != 1.0:
        for t in fig.findobj(mtext.Text):
            t.set_fontsize(t.get_fontsize() * fs)
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", path)


def box(ax, x, y, w, h, text, fs=9, fc="#ffffff", ec="#1a1a1a", style="round,pad=0.02"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle=style, linewidth=0.9,
                                facecolor=fc, edgecolor=ec))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, wrap=True)


def arrow(ax, x1, y1, x2, y2, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=9, linewidth=0.9,
                                 color="#1a1a1a", linestyle=ls,
                                 shrinkA=0, shrinkB=0))


def line(ax, x1, y1, x2, y2):
    ax.plot([x1, x2], [y1, y2], color="#1a1a1a", linewidth=0.9)


def fig_1_1():
    """Дарахти синтаксисии ҷумла (tree diagram)."""
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.4); ax.axis("off")

    ax.text(5, 6.15, "S", ha="center", va="center", fontsize=11, fontweight="bold")
    nodes = {
        "NP1": (2.6, 4.85), "VP": (7.2, 4.85),
        "D1": (1.2, 3.55), "N1": (3.2, 3.55), "V": (5.9, 3.55), "NP2": (8.0, 3.55),
        "D2": (7.0, 2.25), "A": (8.2, 2.25), "N2": (9.3, 2.25),
    }
    labels = {"NP1": "NP", "VP": "VP", "D1": "Det", "N1": "N", "V": "V",
              "NP2": "NP", "D2": "Det", "A": "Adj", "N2": "N"}
    for k, (x, y) in nodes.items():
        ax.text(x, y, labels[k], ha="center", va="center", fontsize=10)

    line(ax, 4.75, 6.02, 2.75, 5.02); line(ax, 5.25, 6.02, 7.05, 5.02)
    line(ax, 2.2, 4.72, 1.35, 3.72); line(ax, 3.0, 4.72, 3.15, 3.72)
    line(ax, 6.9, 4.72, 6.0, 3.72); line(ax, 7.5, 4.72, 7.9, 3.72)
    line(ax, 7.7, 3.42, 7.15, 2.42); line(ax, 8.0, 3.42, 8.15, 2.42); line(ax, 8.3, 3.42, 9.2, 2.42)

    words = {"D1": "The", "N1": "student", "V": "reads", "D2": "an", "A": "interesting", "N2": "book"}
    for k, (x, y) in nodes.items():
        if k in words:
            ax.text(x, y - 0.92, words[k], ha="center", va="center", fontsize=9,
                    style="italic", color="#1f3864")
    ax.text(5.0, 0.55, "The student reads an interesting book.",
            ha="center", va="center", fontsize=9.5)
    _save(fig, "fig_1_1_tree.png")


def fig_1_2():
    """Схемаи таснифи ҷумлаҳо (схемаи сохторӣ)."""
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.5); ax.axis("off")
    box(ax, 5.0, 5.9, 2.7, 0.60, "ҶУМЛА", fs=10.5, fc="#dbe5f1")
    box(ax, 2.6, 4.62, 3.4, 0.62, "Аз рӯи мақсади баён", fs=9.5, fc="#f7f9fc")
    box(ax, 7.5, 4.62, 3.2, 0.62, "Аз рӯи сохтор", fs=9.5, fc="#f7f9fc")
    line(ax, 4.55, 5.60, 3.65, 4.94); line(ax, 5.45, 5.60, 6.35, 4.94)

    def branch(parent_x, parent_y, trunk_x, ys, texts, box_x, bw, side):
        line(ax, parent_x, parent_y, parent_x, parent_y - 0.22)
        line(ax, parent_x, parent_y - 0.22, trunk_x, parent_y - 0.22)
        line(ax, trunk_x, parent_y - 0.22, trunk_x, ys[-1])
        for y, t in zip(ys, texts):
            box(ax, box_x, y, bw, 0.58, t, fs=8.6, fc="#eef3fa")
            x_edge = box_x + bw / 2 if side == "left" else box_x - bw / 2
            line(ax, trunk_x, y, x_edge, y)

    left = ["Ҳикоявӣ (Declarative)", "Саволӣ (Interrogative)",
            "Амрӣ (Imperative)", "Эҳсосӣ (Exclamatory)"]
    right = ["Содда (Simple)", "Пайваст (Compound)", "Тобеъ (Complex)"]
    ys_l = [3.55 - i * 0.85 for i in range(4)]
    ys_r = [3.55 - i * 0.85 for i in range(3)]
    branch(2.6, 4.31, 0.45, ys_l, left, 2.85, 3.6, "right")
    branch(7.5, 4.31, 9.55, ys_r, right, 7.30, 3.3, "left")
    ax.text(5.0, 0.30, "Таснифи ҷумлаҳои забони англисӣ",
            ha="center", va="center", fontsize=8.5, style="italic")
    _save(fig, "fig_1_2_classification.png", fs=1.18)


def fig_2_1():
    """Диаграммаи сутунӣ: равишҳои истифодашаванда (маълумоти шартӣ)."""
    labels = ["Грамматикӣ-\nтарҷумонӣ", "Аудио-\nлингвалӣ", "Комму-\nникативӣ",
              "Фаъолият-\nманд", "Омехта"]
    vals = [34, 41, 78, 62, 55]
    fig, ax = plt.subplots(figsize=(6.8, 3.5))
    bars = ax.bar(labels, vals, color="#2e5c8a", width=0.6)
    ax.set_ylabel("Ҳиссаи пурсидашудагон, %", fontsize=9)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", linestyle=":", linewidth=0.6, color="#999999")
    ax.set_axisbelow(True)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, str(v), ha="center", fontsize=8.5)
    ax.tick_params(labelsize=8.2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, "fig_2_1_bar.png", fs=1.22)


def fig_2_2():
    """Диаграммаи доирӣ: тақсими вақти дарс."""
    labels = ["Муаррифӣ\n(Presentation)\n25%", "Машқ\n(Practice)\n45%",
              "Истеҳсол\n(Production)\n20%", "Бозхонд\n(Reflection)\n10%"]
    vals = [25, 45, 20, 10]
    colors = ["#2e5c8a", "#8faadc", "#a9c0e0", "#d9e2f3"]
    fig, ax = plt.subplots(figsize=(5.6, 3.5))
    ax.pie(vals, labels=labels, colors=colors, startangle=90,
           autopct=None, wedgeprops={"edgecolor": "white", "linewidth": 1.2},
           textprops={"fontsize": 8.2})
    ax.axis("equal")
    _save(fig, "fig_2_2_pie.png", fs=1.15)


def fig_2_3():
    """Графики хаттии динамикаи азхудкунӣ (маълумоти шартӣ)."""
    weeks = np.arange(1, 9)
    g1 = [42, 47, 51, 53, 56, 58, 60, 61]
    g2 = [41, 52, 61, 68, 73, 78, 82, 85]
    g3 = [43, 50, 57, 61, 66, 69, 71, 73]
    fig, ax = plt.subplots(figsize=(6.8, 3.5))
    ax.plot(weeks, g1, marker="o", markersize=3.5, linewidth=1.4, label="Гурӯҳи назоратӣ")
    ax.plot(weeks, g2, marker="s", markersize=3.5, linewidth=1.4, label="Гурӯҳи озмоишӣ (модели пешниҳодшуда)")
    ax.plot(weeks, g3, marker="^", markersize=3.5, linewidth=1.4, label="Гурӯҳи муқоисавӣ (равиши анъанавӣ)")
    ax.set_xlabel("Ҳафтаҳои таълим", fontsize=9)
    ax.set_ylabel("Холҳои миёна (аз 100)", fontsize=9)
    ax.set_xticks(weeks)
    ax.set_ylim(35, 95)
    ax.grid(linestyle=":", linewidth=0.6, color="#999999")
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    ax.tick_params(labelsize=8.2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, "fig_2_3_line.png", fs=1.22)


def fig_3_1():
    """Схемаи раванди омӯзиши сохтори ҷумла (алгоритм)."""
    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8.6); ax.axis("off")
    steps = [
        (7.9, "1. Муайян кардани намунаи сохторӣ\n(S → NP + VP)", "#dbe5f1"),
        (6.6, "2. Ҷудо кардани ҷузъҳои бевосита\n(таҳлили қавсӣ)", "#e7eef8"),
        (5.3, "3. Муайян кардани вазифаҳои\nсинтаксисӣ ва шаклҳои калима", "#eef3fa"),
        (4.0, "4. Моделсозӣ ва визуализатсия\n(дарахт, схема, ҷадвали ивазкунанда)", "#f4f7fc"),
        (2.7, "5. Машқҳои ивазкунанда,\nтабдилдиҳӣ ва омезиш", "#e7eef8"),
        (1.4, "6. Истеҳсоли нутқи озод\n(маҳсулот) ва арзёбӣ", "#dbe5f1"),
    ]
    for y, t, fc in steps:
        box(ax, 5.0, y, 7.6, 0.95, t, fs=9, fc=fc)
    for i in range(len(steps) - 1):
        arrow(ax, 5.0, steps[i][0] - 0.48, 5.0, steps[i + 1][0] + 0.48)
    ax.annotate("", xy=(9.0, 1.4), xytext=(9.0, 7.9),
                arrowprops=dict(arrowstyle="-|>", color="#7f7f7f", linewidth=0.9,
                                linestyle="--", connectionstyle="arc3,rad=-0.25"))
    ax.text(9.75, 4.6, "Бозхонд\nва такрор", rotation=90, ha="center", va="center",
            fontsize=8.5, color="#404040")
    _save(fig, "fig_3_1_algorithm.png", fs=1.15)


def fig_3_2():
    """Диаграммаи муқоисавии натиҷаҳои санҷиши ташхисӣ (маълумоти шартӣ)."""
    cats = ["Муайян кардани\nмубтадо", "Тартиби\nкалима", "Ҷузъҳои\nбевосита",
            "Ҷумлаҳои\nмураккаб", "Вазъи\nхабар"]
    before = [78, 64, 41, 37, 52]
    after = [92, 88, 74, 69, 81]
    x = np.arange(len(cats)); w = 0.36
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    b1 = ax.bar(x - w / 2, before, w, label="То озмоиш", color="#9db7d5")
    b2 = ax.bar(x + w / 2, after, w, label="Баъд аз озмоиш", color="#2e5c8a")
    ax.set_ylabel("Иҷрои дуруст, %", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=8)
    ax.set_ylim(0, 108)
    ax.grid(axis="y", linestyle=":", linewidth=0.6, color="#999999")
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, frameon=False, loc="lower center",
              bbox_to_anchor=(0.5, 1.0), ncol=2)
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5,
                    str(int(b.get_height())), ha="center", fontsize=7.5)
    ax.tick_params(labelsize=8.2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, "fig_3_2_compare.png", fs=1.2)


if __name__ == "__main__":
    fig_1_1(); fig_1_2(); fig_2_1(); fig_2_2(); fig_2_3(); fig_3_1(); fig_3_2()
