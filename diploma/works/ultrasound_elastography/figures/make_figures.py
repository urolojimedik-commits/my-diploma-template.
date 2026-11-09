#!/usr/bin/env python3
"""Расмҳои кори курсӣ: схемаҳо ва графикҳо.

Принципи муҳим: графикҳои оморӣ танҳо аз маълумоти воқеии нашршуда
(бо истинод ба манбаъ) сохта мешаванд; схемаҳо — сохтории таълимӣ,
бо қайди «схемаи муаллифӣ» дар сарлавҳа.

    python figures/make_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager, rcParams  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "png"

FONTS = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
for name in ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSans.ttf"):
    if (FONTS / name).exists():
        font_manager.fontManager.addfont(str(FONTS / name))
rcParams["font.family"] = "DejaVu Serif"
rcParams["axes.unicode_minus"] = False
rcParams["figure.facecolor"] = "white"

BLUE = "#2E6F9E"
LIGHT = "#9EC7E8"
GREY = "#D9D9D9"


def box(ax, x, y, w, h, text, color=LIGHT, fontsize=9, weight="normal"):
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.02", linewidth=0.8,
            edgecolor="#333333", facecolor=color,
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, fontweight=weight, wrap=True)


def arrow(ax, x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", lw=0.9, color="#333333"))


def canvas(w=7.0, h=4.6):
    fig, ax = plt.subplots(figsize=(w, h), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


# --------------------------------------------------------------------------- #
# Расми 1. Таснифи усулҳои эластография (схема)
# --------------------------------------------------------------------------- #

def fig1_tasnif() -> Path:
    fig, ax = canvas(7.2, 4.8)
    box(ax, 0.30, 0.86, 0.40, 0.10, "ЭЛАСТОГРАФИЯИ УЛТРАСАДОӢ", BLUE, 10, "bold")

    # гурӯҳи 1: strain
    box(ax, 0.02, 0.60, 0.44, 0.15, "1. Усулҳои деформатсионӣ\n(strain elastography)", LIGHT, 9, "bold")
    box(ax, 0.03, 0.44, 0.20, 0.12, "Фишурдани дастӣ\n(квазистатикӣ)", "white", 8)
    box(ax, 0.25, 0.44, 0.20, 0.12, "Фишурдани физиологӣ\n(набз, нафас)", "white", 8)
    box(ax, 0.03, 0.30, 0.42, 0.10, "Натиҷа: нисбатӣ (сифатӣ), бе воҳиди ченак", GREY, 8)

    # гурӯҳи 2: shear wave
    box(ax, 0.54, 0.60, 0.44, 0.15, "2. Усулҳои мавҷи буриш\n(shear wave elastography)", LIGHT, 9, "bold")
    box(ax, 0.55, 0.44, 0.20, 0.12, "Эластографияи\nгузаранда (TE)", "white", 8)
    box(ax, 0.77, 0.44, 0.20, 0.12, "Такони қувваи\nакустикӣ (ARFI)", "white", 8)
    box(ax, 0.55, 0.30, 0.42, 0.10, "Натиҷа: миқдорӣ — кПа ё м/с", GREY, 8)
    box(ax, 0.62, 0.15, 0.28, 0.11, "pSWE  •  2D-SWE  •  SSI", "white", 8)

    arrow(ax, 0.50, 0.86, 0.24, 0.76)
    arrow(ax, 0.50, 0.86, 0.76, 0.76)
    arrow(ax, 0.24, 0.60, 0.13, 0.42)
    arrow(ax, 0.76, 0.60, 0.65, 0.42)

    ax.text(0.5, 0.02, "Схемаи муаллифӣ (аз рӯйи дастурамалҳои EFSUMB ва WFUMB)",
            ha="center", fontsize=7, style="italic", color="#555555")
    path = OUT / "fig1.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- #
# Расми 2. Принсипи физикӣ (схема)
# --------------------------------------------------------------------------- #

def fig2_prinsip() -> Path:
    fig, ax = canvas(7.2, 4.2)
    ax.text(0.5, 0.94, "Принсипи физикии эластография", ha="center",
            fontsize=10, fontweight="bold")

    # чап: strain
    ax.text(0.25, 0.84, "А) Усули деформатсионӣ", ha="center", fontsize=9, fontweight="bold")
    ax.add_patch(mpatches.Rectangle((0.06, 0.52), 0.38, 0.22, facecolor=LIGHT,
                                    edgecolor="#333333", lw=0.8))
    ax.text(0.25, 0.63, "бофтаи чандир", ha="center", fontsize=8)
    ax.annotate("", xy=(0.25, 0.50), xytext=(0.25, 0.58),
                arrowprops=dict(arrowstyle="->", lw=1.2, color="#333333"))
    ax.text(0.33, 0.505, "фишурдан (F)", fontsize=8)
    ax.add_patch(mpatches.Rectangle((0.06, 0.36), 0.38, 0.12, facecolor="#BBDEFB",
                                    edgecolor="#333333", lw=0.8))
    ax.text(0.25, 0.42, "деформатсияи кам", ha="center", fontsize=8)
    ax.text(0.25, 0.24, "Бофтаи сахт кам деформатсия мешавад\nε = ΔL / L  (нисбатӣ)",
            ha="center", fontsize=8)

    # рост: shear wave
    ax.text(0.75, 0.84, "Б) Усули мавҷи буриш", ha="center", fontsize=9, fontweight="bold")
    ax.add_patch(mpatches.Rectangle((0.56, 0.52), 0.38, 0.22, facecolor=LIGHT,
                                    edgecolor="#333333", lw=0.8))
    ax.text(0.75, 0.63, "бофта", ha="center", fontsize=8)
    ax.annotate("", xy=(0.95, 0.63), xytext=(0.60, 0.63),
                arrowprops=dict(arrowstyle="->", lw=1.0, color="#C0392B"))
    ax.text(0.66, 0.665, "мавҷи буриш (cₛ)", fontsize=7.5, color="#C0392B")
    ax.text(0.75, 0.40, "E ≈ 3 ρ cₛ²      cₛ — суръати мавҷи буриш\n"
                        "E — модули Юнг, ρ — зичии бофта",
            ha="center", fontsize=8)
    ax.text(0.75, 0.24, "Бофтаи сахт: cₛ ва E баландтар\n(ченак: кПа ё м/с)",
            ha="center", fontsize=8)

    ax.text(0.5, 0.02, "Схемаи муаллифӣ (аз рӯйи Sarvazyan, 1998; Gennisson, 2013)",
            ha="center", fontsize=7, style="italic", color="#555555")
    path = OUT / "fig2.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- #
# Расми 3. AUROC — маълумоти воқеӣ
# --------------------------------------------------------------------------- #

def fig3_auroc() -> Path:
    """Маълумот аз мета-таҳлилҳо:
    TE — Friedrich-Rust, 2008 (50 таҳқиқот);
    ARFI — Friedrich-Rust, 2012 (518 бемор);
    SSI — Bavu, 2011 (113 бемор).
    """
    stages = ["Фибрози назаррас\n(F ≥ 2)", "Фибрози шадид\n(F ≥ 3)", "Сирроз\n(F = 4)"]
    te = [0.84, 0.89, 0.94]
    arfi = [0.87, 0.91, 0.93]
    ssi = [0.948, 0.962, 0.968]

    x = range(len(stages))
    width = 0.26
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=220)
    ax.bar([i - width for i in x], te, width, label="TE (FibroScan)", color=LIGHT, edgecolor="#333")
    ax.bar(list(x), arfi, width, label="ARFI (pSWE)", color=BLUE, edgecolor="#333")
    ax.bar([i + width for i in x], ssi, width, label="SSI (2D-SWE)", color="#14507A", edgecolor="#333")

    for i, (a, b, c) in enumerate(zip(te, arfi, ssi)):
        ax.text(i - width, a + 0.008, f"{a:.3f}".replace(".", ","), ha="center", fontsize=7.5)
        ax.text(i, b + 0.008, f"{b:.3f}".replace(".", ","), ha="center", fontsize=7.5)
        ax.text(i + width, c + 0.008, f"{c:.3f}".replace(".", ","), ha="center", fontsize=7.5)

    ax.set_xticks(list(x))
    ax.set_xticklabels(stages, fontsize=9)
    ax.set_ylim(0.75, 1.02)
    ax.set_ylabel("AUROC", fontsize=10)
    ax.set_title("Дақиқии эластография дар марҳилабандии фибрози ҷигар (AUROC)",
                 fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    fig.text(0.5, 0.01,
             "Сарчашма: Friedrich-Rust, 2008 (TE); Friedrich-Rust, 2012 (ARFI); Bavu, 2011 (SSI)",
             ha="center", fontsize=7, style="italic", color="#555555")
    path = OUT / "fig3.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- #
# Расми 4. Диапазони чандирӣ — маълумоти воқеӣ (Bavu, 2011)
# --------------------------------------------------------------------------- #

def fig4_kpa() -> Path:
    labels = ["SSI (2D-SWE)", "FibroScan (TE)"]
    lows = [4.50, 2.60]
    highs = [33.96, 46.50]
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=220)
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        ax.barh(i, hi - lo, left=lo, height=0.45, color=[BLUE, LIGHT][i], edgecolor="#333")
        ax.text(lo - 0.6, i, f"{lo:.2f}".replace(".", ","), va="center", ha="right", fontsize=8)
        ax.text(hi + 0.6, i, f"{hi:.2f}".replace(".", ","), va="center", ha="left", fontsize=8)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Чандирии ҷигар, кПа", fontsize=10)
    ax.set_xlim(0, 52)
    ax.set_title("Диапазони ченкунии чандирии ҷигар дар 113 бемори гепатити C", fontsize=10)
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    fig.text(0.5, 0.01, "Сарчашма: Bavu, 2011 (DOI: 10.1016/j.ultrasmedbio.2011.05.016)",
             ha="center", fontsize=7, style="italic", color="#555555")
    path = OUT / "fig4.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- #
# Расми 5. Алгоритми ташхис (схема)
# --------------------------------------------------------------------------- #

def fig5_algorithm() -> Path:
    fig, ax = canvas(7.2, 5.0)
    ax.text(0.5, 0.96, "Алгоритми истифодаи эластография дар амалияи клиникӣ",
            ha="center", fontsize=10, fontweight="bold")

    steps = [
        (0.86, "1. Бемори дорои хавфи фиброз\n(гепатити музмин, NAFLD, дигар)"),
        (0.70, "2. Арзёбии омилҳои халал:\nфарбеҳӣ, хӯрокхӯрӣ, илтиҳоб, варами ҷигар"),
        (0.54, "3. Интихоби усул:\nTE / pSWE (ARFI) / 2D-SWE"),
        (0.38, "4. Ченкунӣ: 10 андозагирӣ,\nмедиана, IQR/med ≤ 30 %"),
        (0.22, "5. Баҳодиҳӣ бо ҳудудҳои дастурамал\n(EFSUMB, WFUMB, EASL)"),
        (0.06, "6. Қарор: мушоҳида, биопсия\nё табобати зиддифиброзӣ"),
    ]
    for y, text in steps:
        box(ax, 0.12, y, 0.76, 0.13, text, LIGHT if y > 0.5 else "#F2F2F2", 8.5)
    for y in (0.86, 0.70, 0.54, 0.38, 0.22):
        arrow(ax, 0.5, y, 0.5, y - 0.03)

    ax.text(0.5, 0.0, "Схемаи муаллифӣ (аз рӯйи дастурамалҳои EFSUMB 2017 ва WFUMB 2015)",
            ha="center", fontsize=7, style="italic", color="#555555")
    path = OUT / "fig5.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (fig1_tasnif, fig2_prinsip, fig3_auroc, fig4_kpa, fig5_algorithm):
        path = fn()
        print(f"[ok] {path} ({path.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
