# -*- coding: utf-8 -*-
"""Сохтани расмҳои кори курсӣ оид ба секретсияи экзокринии ғадуди зери меъда."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(BASE, "figures")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                     "axes.edgecolor": "#333333"})


def _save(fig, name, fs=1.0):
    for t in fig.findobj(matplotlib.text.Text):
        t.set_fontsize(t.get_fontsize() * fs)
    fig.savefig(os.path.join(OUT, name), dpi=300, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


def canvas(w, h):
    """Бистар бо координатаҳо баробари дюйм (1 воҳид = 72 pt)."""
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fs=11, fc="#eef3fb", ec="#2f5597"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.08",
                                linewidth=1.4, edgecolor=ec, facecolor=fc,
                                zorder=2))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=3,
            linespacing=1.3)


def arrow(ax, p1, p2, color="#2f5597", ls="-", lw=1.6, rad=0.0):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=13,
                                 linewidth=lw, color=color, linestyle=ls,
                                 shrinkA=1, shrinkB=1, zorder=1,
                                 connectionstyle=f"arc3,rad={rad}"))


# ---------------------------------------------------------------- Расми 1.1
def fig_acinus():
    fig, ax = canvas(14.0, 5.0)

    cx, cy = 1.5, 3.3
    for dx, dy in ((-0.5, 0.42), (0.02, 0.62), (0.55, 0.34),
                   (-0.55, -0.30), (0.02, -0.62), (0.55, -0.30)):
        ax.add_patch(Circle((cx + dx, cy + dy), 0.40, facecolor="#fdf1e0",
                            edgecolor="#c55a11", linewidth=1.3, zorder=2))
    ax.add_patch(Circle((cx, cy), 0.17, facecolor="white", edgecolor="#c55a11",
                        linewidth=1.2, zorder=3))
    ax.text(cx, cy + 1.35, "нурчаи марказӣ", ha="center", fontsize=9.5,
            style="italic")
    arrow(ax, (cx, cy + 1.22), (cx, cy + 0.68), lw=1.0)

    boxes = [(4.35, 3.3, 2.4, 1.0, "Дуктулаи\nбайниацинӣ"),
             (7.05, 3.3, 2.3, 1.0, "Дуктулаи\nдохилобӣ"),
             (9.75, 3.3, 2.4, 1.0, "Дуктулаи\nбайнилобулӣ"),
             (12.45, 3.3, 2.4, 1.0, "Дуктаи асосӣ\n(Вирсунг)"),
             (12.45, 1.85, 2.4, 0.95, "Ампулаи\nВатер"),
             (12.45, 0.55, 2.6, 0.75, "Рӯдаи дувоздаҳангушта")]
    for x, y, w, h, lab in boxes:
        box(ax, x, y, w, h, lab, fs=10.5, fc="#e8f1e4", ec="#548235")

    ax.text(cx, 1.55, "Ацинус\n(ҳуҷайраҳои ацинӣ)", ha="center", fontsize=10.5,
            linespacing=1.3)
    arrow(ax, (cx + 1.0, cy), (4.35 - 1.2, 3.3))
    arrow(ax, (5.55, 3.3), (5.9, 3.3))
    arrow(ax, (8.2, 3.3), (8.55, 3.3))
    arrow(ax, (10.95, 3.3), (11.25, 3.3))
    arrow(ax, (12.45, 2.8), (12.45, 2.33))
    arrow(ax, (12.45, 1.38), (12.45, 0.93))
    _save(fig, "fig_1_1_acinus.png", fs=1.0)


# ---------------------------------------------------------------- Расми 1.2
def fig_composition():
    """Муқоисаи таркиби ионҳои плазма ва секрети панкреатӣ."""
    fig, ax = plt.subplots(figsize=(9.4, 5.0))
    ions = ["Na⁺", "K⁺", "HCO₃⁻", "Cl⁻"]
    plasma = [142, 4.5, 25, 104]
    juice = [140, 5.0, 120, 60]
    y = range(len(ions))
    h = 0.36
    b1 = ax.barh([i + h / 2 for i in y], plasma, h, label="Плазмаи хун",
                 color="#a6a6a6", edgecolor="#404040", linewidth=1.1)
    b2 = ax.barh([i - h / 2 for i in y], juice, h,
                 label="Секрети панкреатӣ", color="#2e75b6",
                 edgecolor="#1f3864", linewidth=1.1)
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_width() + 2, b.get_y() + b.get_height() / 2,
                    f"{b.get_width():.3g}".replace(".", ","), va="center",
                    fontsize=11.5, weight="bold")
    ax.set_yticks(list(y))
    ax.set_yticklabels(ions, fontsize=13)
    ax.set_xlim(0, 168)
    ax.set_xlabel("Консентратсия (мЭкв/л)", fontsize=12)
    ax.set_title("Таркиби ионҳои плазмаи хун ва секрети панкреатӣ",
                 fontsize=13, pad=14)
    ax.legend(fontsize=12, loc="upper right", framealpha=1.0)
    ax.grid(axis="x", linestyle=":", alpha=0.6)
    ax.set_axisbelow(True)
    _save(fig, "fig_1_2_ions.png", fs=1.1)


# ---------------------------------------------------------------- Расми 1.3
def fig_phases():
    fig, ax = plt.subplots(figsize=(9.6, 5.0))
    names = ["Фазаи байнимағзӣ\n(дидан, бӯй, фикр\nва чавшавии хӯрок)",
             "Фазаи меъдавӣ\n(кашишхӯрии меъда,\nгастрин)",
             "Фазаи рӯда\n(маҳсулоти ҳазм дар\nрӯдаи дувоздаҳангушта)"]
    vals = [20, 10, 70]
    cols = ["#8faadc", "#ffc000", "#70ad47"]
    bars = ax.bar(names, vals, color=cols, edgecolor="#404040", width=0.55,
                  linewidth=1.2)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.8, f"{v} %", ha="center",
                fontsize=13, weight="bold")
    ax.set_ylim(0, 85)
    ax.set_ylabel("Ҳиссаи секретсия (%)\nдар ҳаҷми умумии шабонарӯзӣ", fontsize=12)
    ax.set_title("Ҳиссаи фазаҳои секретсия дар ҳаҷми умумии секрети панкреатӣ",
                 fontsize=13, pad=14)
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=10.5)
    _save(fig, "fig_1_3_phases.png", fs=1.1)


# ---------------------------------------------------------------- Расми 2.1
def fig_cascade():
    fig, ax = canvas(12.6, 6.2)

    row1 = [(1.55, 2.7, "Ацетилхолин\n(аз n. vagus)", "#eef3fb", "#2f5597"),
            (4.60, 2.7, "M₃-рецептор\n(мембранаи\nҳуҷайра)", "#eef3fb", "#2f5597"),
            (7.75, 2.8, "Gq-сафеда →\nфосфолипаза C", "#eef3fb", "#2f5597"),
            (11.05, 2.7, "PIP₂ →\nIP₃ + DAG", "#eef3fb", "#2f5597")]
    for x, w, lab, fc, ec in row1:
        box(ax, x, 5.3, w, 1.15, lab, fs=10.5, fc=fc, ec=ec)
    arrow(ax, (2.9, 5.3), (3.25, 5.3))
    arrow(ax, (5.95, 5.3), (6.35, 5.3))
    arrow(ax, (9.15, 5.3), (9.7, 5.3))

    box(ax, 4.35, 3.55, 3.5, 1.0, "IP₃ → рецептор дар\nшабакаи эндоплазмавӣ",
        fs=10.5, fc="#fdf1e0", ec="#c55a11")
    arrow(ax, (10.0, 4.75), (6.1, 3.7), color="#c55a11")

    box(ax, 4.35, 2.05, 3.5, 0.95, "Баландшавии Ca²⁺\nдар ситоплазма",
        fs=10.5, fc="#fdf1e0", ec="#c55a11")
    arrow(ax, (4.35, 3.05), (4.35, 2.53), color="#c55a11")

    box(ax, 4.9, 0.65, 5.2, 0.9, "Эксоцитози гранулаҳои зимоген →\nсекретсияи ферментҳо",
        fs=10.5, fc="#e8f1e4", ec="#548235")
    arrow(ax, (4.35, 1.57), (4.6, 1.1), color="#548235")

    box(ax, 10.2, 2.05, 3.4, 1.05, "DAG + Ca²⁺ →\nпротеинкиназаи C",
        fs=10.5, fc="#eee4f5", ec="#7030a0")
    arrow(ax, (11.05, 4.72), (10.35, 2.58), color="#7030a0", ls="--")
    _save(fig, "fig_2_1_cascade.png", fs=1.0)


# ---------------------------------------------------------------- Расми 2.2
def fig_hormones():
    fig, ax = plt.subplots(figsize=(9.8, 5.2))
    groups = ["Ҳаҷми секрет", "Бикарбонатҳо", "Ферментҳо"]
    secretin = [100, 100, 15]
    cck = [35, 25, 100]
    x = range(len(groups))
    w = 0.36
    b1 = ax.bar([i - w / 2 for i in x], secretin, w, label="Секретин",
                color="#2e75b6", edgecolor="#1f3864", linewidth=1.1)
    b2 = ax.bar([i + w / 2 for i in x], cck, w, label="Холесистокинин (CCK)",
                color="#ed7d31", edgecolor="#843c0c", linewidth=1.1)
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 2.5,
                    f"{int(b.get_height())}", ha="center", fontsize=11.5,
                    weight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(groups, fontsize=12.5)
    ax.set_ylim(0, 122)
    ax.set_ylabel("Таъсири нисбӣ (% аз ҳадди аксар)", fontsize=12)
    ax.set_title("Таъсири секретин ва холесистокинин ба ҷузъҳои секрети панкреатӣ",
                 fontsize=12.5, pad=14)
    ax.legend(fontsize=12, loc="upper center", ncol=2,
              bbox_to_anchor=(0.5, -0.13))
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    ax.set_axisbelow(True)
    _save(fig, "fig_2_2_hormones.png", fs=1.1)


# ---------------------------------------------------------------- Расми 2.3
def fig_integration():
    fig, ax = canvas(13.0, 6.4)

    box(ax, 2.0, 5.5, 2.9, 0.85, "Хӯрок\n(маҳсулоти ҳазм)", fs=10.5,
        fc="#fbe9e7", ec="#c00000")
    box(ax, 6.0, 5.5, 3.2, 0.85, "Рӯдаи дувоздаҳангушта\n(pH < 4,5)", fs=10.5,
        fc="#fbe9e7", ec="#c00000")
    box(ax, 10.3, 5.5, 2.9, 0.85, "S-ҳуҷайраҳо →\nсекретин", fs=10.5,
        fc="#deebf7", ec="#2e75b6")
    box(ax, 10.3, 4.2, 2.9, 0.85, "I-ҳуҷайраҳо →\nхолесистокинин", fs=10.5,
        fc="#fce4d6", ec="#c55a11")

    box(ax, 6.4, 3.1, 4.6, 1.0, "Ғадуди зери меъда: об,\nбикарбонатҳо, ферментҳо",
        fs=10.5, fc="#e8f1e4", ec="#548235")
    box(ax, 8.2, 1.2, 4.2, 0.9, "Ишқорикунонии дуоденум,\nҳазми маводи ғизоӣ",
        fs=10.5, fc="#f2f2f2", ec="#7f7f7f")
    box(ax, 11.9, 2.2, 2.0, 0.85, "n. vagus\n(ацетилхолин)", fs=9.5,
        fc="#eee4f5", ec="#7030a0")

    arrow(ax, (3.45, 5.5), (4.4, 5.5))
    arrow(ax, (7.6, 5.5), (8.85, 5.5))
    arrow(ax, (10.3, 5.08), (10.3, 4.63))
    arrow(ax, (5.65, 5.08), (5.65, 3.6))
    arrow(ax, (9.15, 4.2), (8.6, 3.6), color="#c55a11")
    arrow(ax, (7.6, 2.6), (7.9, 1.65))
    arrow(ax, (10.9, 2.25), (8.75, 2.95), color="#7030a0")
    arrow(ax, (6.15, 1.2), (4.35, 5.05), color="#c00000", ls="--", rad=-0.5)
    ax.text(2.15, 2.95, "бозхӯрд:\nқатъшавӣ ҳангоми\nишқорикунонӣ",
            fontsize=9.5, color="#c00000", ha="center", linespacing=1.3)
    _save(fig, "fig_2_3_integration.png", fs=1.0)


# ---------------------------------------------------------------- Расми 1.3
def fig_protein():
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    labels = ["Протеазаҳо", "Липазаҳо", "α-амилаза", "Дигар ферментҳо"]
    vals = [60, 25, 10, 5]
    colors = ["#2e75b6", "#ed7d31", "#70ad47", "#a6a6a6"]
    ax.pie(vals, labels=labels, colors=colors, startangle=90,
           autopct="%1.0f %%", textprops={"fontsize": 12.5},
           explode=(0, 0.04, 0.08, 0.12),
           wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax.set_title("Таркиби тақрибии сафедаҳои секрети панкреатӣ",
                 fontsize=13, pad=16)
    _save(fig, "fig_1_3_protein.png", fs=1.12)


# ---------------------------------------------------------------- Расми 1.4
def fig_dynamics():
    fig, ax = plt.subplots(figsize=(9.8, 4.9))
    t = [0, 30, 60, 90, 120, 150, 180, 210, 240]
    v = [18, 42, 88, 122, 118, 96, 70, 44, 26]
    ax.plot(t, v, marker="o", markersize=7, linewidth=2.2, color="#2e75b6",
            markerfacecolor="white", markeredgewidth=2, label="Ҳаҷми секрет")
    ax.axvline(60, linestyle="--", color="#c00000", linewidth=1.2)
    ax.text(64, 118, "қабули хӯрок", fontsize=10.5, color="#c00000")
    ax.set_xlabel("Вақт (дақиқа)", fontsize=12)
    ax.set_ylabel("Ҳаҷми секрет (мл/соат)", fontsize=12)
    ax.set_title("Динамикаи секретсияи экзокринӣ баъд аз қабули хӯрок",
                 fontsize=13, pad=14)
    ax.set_ylim(0, 140)
    ax.set_xlim(0, 245)
    ax.grid(linestyle=":", alpha=0.6)
    ax.set_axisbelow(True)
    _save(fig, "fig_1_4_dynamics.png", fs=1.1)


if __name__ == "__main__":
    fig_acinus()
    fig_composition()
    fig_phases()
    fig_protein()
    fig_dynamics()
    fig_cascade()
    fig_hormones()
    fig_integration()
    print("figures done:", sorted(os.listdir(OUT)))
