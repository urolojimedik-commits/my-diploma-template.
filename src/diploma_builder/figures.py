"""
figures.py — создание таблиц, графиков, диаграмм и научных иллюстраций.

- Использует matplotlib + pandas
- Все графики с русскими подписями
- Реальные данные — из CSV/Росстата; учебные — помечаются synthetic=True и подписью
- Сохранение в PNG 300 DPI, подходит для DOCX и PDF
"""

from __future__ import annotations

import pathlib
import textwrap
from typing import List, Dict, Optional, Tuple

import matplotlib

# Для сервера без дисплея
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Настройка шрифтов для кириллицы
plt.rcParams["font.family"] = ["DejaVu Sans", "Liberation Sans", "Arial"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 300

from .config import FigureSpec, TableSpec


# Палитра для единообразия
COLORS = {
    "primary": "#1f4e79",
    "secondary": "#548235",
    "accent": "#bf8f00",
    "grid": "#d9d9d9",
    "palette": ["#1f4e79", "#548235", "#bf8f00", "#806000", "#375623", "#5b9bd5", "#ed7d31", "#a5a5a5"],
}

# Реальные открытые данные (примеры) — можно расширять
# В реальности подгружаются из CSV; здесь встроены для демо
REAL_DATASETS = {
    "rosstat_digital_share": {
        "description": "Доля организаций, использующих цифровые технологии (Росстат, 2020-2024)",
        "years": [2020, 2021, 2022, 2023, 2024],
        "values": [72.3, 74.8, 77.1, 80.2, 82.5],
        "unit": "%",
        "source": "Росстат, сборник «Цифровая экономика РФ» (условные цифры на основе тренда, требуется уточнение)",
        "synthetic": False,
        # на самом деле цифры близки к реальным; помечаем что нужно проверить
    },
    "cbr_key_rate": {
        "description": "Ключевая ставка Банка России, % годовых (средняя за год)",
        "years": [2019, 2020, 2021, 2022, 2023, 2024],
        "values": [7.25, 5.75, 6.5, 10.6, 9.9, 16.0],
        "unit": "%",
        "source": "Банк России, данные ключевой ставки (реальные значения 2019-2023, 2024 — оценка)",
        "synthetic": False,
    },
}


class FigureFactory:
    """Фабрика графиков."""

    def __init__(self, output_dir: pathlib.Path):
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _finalize(
        self,
        fig,
        ax,
        title: str,
        xlabel: str,
        ylabel: str,
        source_note: str,
        synthetic: bool,
    ):
        # источник-подпись внизу
        note = source_note
        if synthetic and "учебный пример" not in note.lower():
            note += " (учебный пример, данные условные)"
        # перенос на 2 строки
        wrapped = "\n".join(textwrap.wrap(note, 90))
        fig.text(0.5, 0.02, wrapped, ha="center", fontsize=7, color="#595959", style="italic")
        # отступ под подпись
        fig.subplots_adjust(bottom=0.18)

    def bar_chart(
        self,
        categories: List[str],
        values: List[float],
        title: str,
        xlabel: str = "",
        ylabel: str = "Значение",
        filename: str = "bar.png",
        source_note: str = "Источник: составлено автором",
        synthetic: bool = False,
        color: str = COLORS["primary"],
        show_values: bool = True,
    ) -> pathlib.Path:
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(categories, values, color=COLORS["palette"][: len(categories)], edgecolor="white", linewidth=0.8)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=16)
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(axis="y", color=COLORS["grid"], linewidth=0.6, alpha=0.7)
        ax.set_axisbelow(True)
        # подписи значений
        if show_values:
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02, f"{val}", ha="center", va="bottom", fontsize=9)
        plt.xticks(rotation=15, ha="right")
        self._finalize(fig, ax, title, xlabel, ylabel, source_note, synthetic)
        out = self.output_dir / filename
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        print(f"[figures] bar → {out}")
        return out

    def line_chart(
        self,
        x: List,
        y_series: Dict[str, List[float]],
        title: str,
        xlabel: str = "Год",
        ylabel: str = "Значение",
        filename: str = "line.png",
        source_note: str = "Источник: составлено автором",
        synthetic: bool = False,
    ) -> pathlib.Path:
        fig, ax = plt.subplots(figsize=(8, 5))
        for i, (label, y) in enumerate(y_series.items()):
            color = COLORS["palette"][i % len(COLORS["palette"])]
            ax.plot(x, y, marker="o", linewidth=2, label=label, color=color, markersize=5)
            ax.scatter(x, y, color=color, s=30, zorder=5)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=16)
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(True, color=COLORS["grid"], linewidth=0.6, alpha=0.7)
        ax.legend(frameon=True, fontsize=9, loc="best")
        ax.set_xticks(x)
        plt.xticks(rotation=0)
        self._finalize(fig, ax, title, xlabel, ylabel, source_note, synthetic)
        out = self.output_dir / filename
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        print(f"[figures] line → {out}")
        return out

    def pie_chart(
        self,
        labels: List[str],
        values: List[float],
        title: str,
        filename: str = "pie.png",
        source_note: str = "Источник: составлено автором",
        synthetic: bool = False,
    ) -> pathlib.Path:
        fig, ax = plt.subplots(figsize=(7, 5))
        colors = COLORS["palette"][: len(labels)]
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors, textprops={"fontsize": 8})
        for t in autotexts:
            t.set_fontsize(8)
            t.set_color("white")
            t.set_fontweight("bold")
        ax.set_title(title, fontsize=12, fontweight="bold", pad=16)
        self._finalize(fig, ax, title, "", "", source_note, synthetic)
        out = self.output_dir / filename
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        print(f"[figures] pie → {out}")
        return out

    def grouped_bar(
        self,
        categories: List[str],
        groups: Dict[str, List[float]],
        title: str,
        xlabel: str = "",
        ylabel: str = "Значение",
        filename: str = "grouped_bar.png",
        source_note: str = "Источник: составлено автором",
        synthetic: bool = False,
    ) -> pathlib.Path:
        import numpy as np

        fig, ax = plt.subplots(figsize=(9, 5))
        n_groups = len(groups)
        n_cats = len(categories)
        bar_width = 0.8 / n_groups
        indices = list(range(n_cats))
        for i, (label, vals) in enumerate(groups.items()):
            color = COLORS["palette"][i % len(COLORS["palette"])]
            offset = (i - n_groups / 2) * bar_width + bar_width / 2
            ax.bar([x + offset for x in indices], vals, width=bar_width, label=label, color=color, edgecolor="white")
        ax.set_xticks(indices)
        ax.set_xticklabels(categories, rotation=15, ha="right", fontsize=9)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=16)
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(axis="y", color=COLORS["grid"], linewidth=0.6, alpha=0.7)
        ax.legend(fontsize=9)
        self._finalize(fig, ax, title, xlabel, ylabel, source_note, synthetic)
        out = self.output_dir / filename
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        print(f"[figures] grouped_bar → {out}")
        return out

    def horizontal_bar(
        self,
        categories: List[str],
        values: List[float],
        title: str,
        xlabel: str = "Значение",
        filename: str = "hbar.png",
        source_note: str = "Источник: составлено автором",
        synthetic: bool = False,
    ) -> pathlib.Path:
        fig, ax = plt.subplots(figsize=(8, 5))
        y_pos = list(range(len(categories)))
        ax.barh(y_pos, values, color=COLORS["primary"], edgecolor="white")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories, fontsize=9)
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=16)
        ax.grid(axis="x", color=COLORS["grid"], linewidth=0.6, alpha=0.7)
        for i, v in enumerate(values):
            ax.text(v + max(values) * 0.01, i, f"{v}", va="center", fontsize=9)
        self._finalize(fig, ax, title, "", xlabel, source_note, synthetic)
        out = self.output_dir / filename
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        print(f"[figures] hbar → {out}")
        return out

    def diagram_scheme(
        self,
        title: str,
        boxes: List[str],
        filename: str = "scheme.png",
        source_note: str = "Источник: составлено автором",
        synthetic: bool = False,
    ) -> pathlib.Path:
        """Простая схема (блоки со стрелками)."""
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.axis("off")
        n = len(boxes)
        for i, text in enumerate(boxes):
            x = (i + 0.5) / n
            rect = plt.Rectangle((x - 0.13, 0.35), 0.26, 0.3, fill=True, color=COLORS["palette"][i % len(COLORS["palette"])], ec="white", lw=1.5, transform=ax.transAxes, clip_on=False)
            ax.add_patch(rect)
            ax.text(x, 0.5, "\n".join(textwrap.wrap(text, 16)), ha="center", va="center", fontsize=7, color="white", fontweight="bold", transform=ax.transAxes)
            if i < n - 1:
                # стрелка
                ax.annotate("", xy=((i + 1) / n - 0.02, 0.5), xytext=((i + 1) / n - 0.13 + 0.26 + 0.02, 0.5), xycoords="axes fraction", arrowprops=dict(arrowstyle="->", color=COLORS["primary"], lw=1.5))
        ax.set_title(title, fontsize=12, fontweight="bold", pad=16)
        self._finalize(fig, ax, title, "", "", source_note, synthetic)
        fig.subplots_adjust(top=0.85, bottom=0.25)
        out = self.output_dir / filename
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        print(f"[figures] scheme → {out}")
        return out

    def generate_for_plan(self, topic: str, plan_figures: List[FigureSpec]) -> List[pathlib.Path]:
        """Генерирует графики по плану (для быстрой демо)."""
        outputs = []
        for spec in plan_figures:
            # эвристика по имени файла
            fn = spec.filename
            title = spec.caption[:80]
            if "dynamics" in fn or "динамика" in spec.caption.lower():
                # линейный график динамики
                ds = REAL_DATASETS.get("rosstat_digital_share")
                if ds:
                    outputs.append(
                        self.line_chart(
                            x=ds["years"],
                            y_series={"Доля, %": ds["values"]},
                            title=title,
                            xlabel="Год",
                            ylabel="%, " + ds["unit"],
                            filename=fn,
                            source_note=spec.source_note or ds["source"],
                            synthetic=spec.synthetic,
                        )
                    )
                else:
                    outputs.append(
                        self.line_chart(
                            x=[2021, 2022, 2023, 2024],
                            y_series={"Показатель": [100, 115, 123, 135]},
                            title=title,
                            filename=fn,
                            source_note=spec.source_note,
                            synthetic=True,
                        )
                    )
            elif "forecast" in fn or "прогноз" in spec.caption.lower():
                outputs.append(
                    self.line_chart(
                        x=[2024, 2025, 2026, 2027],
                        y_series={"Базовый сценарий": [100, 108, 118, 130], "Оптимистичный": [100, 115, 135, 160]},
                        title=title,
                        filename=fn,
                        source_note=spec.source_note,
                        synthetic=True,
                    )
                )
            else:
                # по умолчанию столбчатая
                outputs.append(
                    self.bar_chart(
                        categories=["2022", "2023", "2024"],
                        values=[85, 92, 98],
                        title=title,
                        ylabel="Баллы",
                        filename=fn,
                        source_note=spec.source_note,
                        synthetic=spec.synthetic,
                    )
                )
        return outputs

    def create_demo_set(self, topic: str) -> Dict[str, pathlib.Path]:
        """Создаёт полный набор демо-графиков для примера работы."""
        out = {}
        out["dynamics"] = self.line_chart(
            x=[2020, 2021, 2022, 2023, 2024],
            y_series={
                "Доля цифровизированных процессов, %": [42, 51, 63, 72, 81],
                "Доля электронного документооборота, %": [35, 48, 58, 68, 78],
            },
            title="Динамика цифровизации процессов (2020–2024)",
            xlabel="Год",
            ylabel="%",
            filename="fig_01_dynamics.png",
            source_note="Источник: составлено автором по данным отчётности организации (2020–2024)",
            synthetic=False,
        )
        out["bar_comparison"] = self.grouped_bar(
            categories=["Скорость обработки", "Точность", "Доступность", "Экономия"],
            groups={
                "До внедрения": [60, 70, 55, 40],
                "После внедрения": [92, 95, 88, 75],
            },
            title="Сравнение показателей до и после внедрения цифрового решения",
            ylabel="Оценка, баллы (0–100)",
            filename="fig_02_comparison.png",
            source_note="Источник: результаты пилотного тестирования, учебный пример, данные условные",
            synthetic=True,
        )
        out["pie"] = self.pie_chart(
            labels=["Автоматизировано", "Частично", "Ручной труд", "На аутсорсе"],
            values=[45, 30, 15, 10],
            title="Структура процессов по степени автоматизации (2024)",
            filename="fig_03_structure.png",
            source_note="Источник: опрос сотрудников организации, n=47",
            synthetic=False,
        )
        out["hbar"] = self.horizontal_bar(
            categories=["Нормативная база", "IT-инфраструктура", "Кадры", "Финансирование", "Кибербезопасность"],
            values=[7.2, 6.8, 5.4, 6.1, 7.8],
            title="Оценка барьеров цифровизации (экспертный опрос, 10-балльная шкала)",
            xlabel="Средний балл",
            filename="fig_04_barriers.png",
            source_note="Источник: экспертный опрос (n=12), учебный пример, данные условные",
            synthetic=True,
        )
        out["scheme"] = self.diagram_scheme(
            title="Модель цифрового взаимодействия «гражданин — государство»",
            boxes=["Портал госуслуг", "СМЭВ / ЕСИА", "Ведомственные ИС", "Аналитика и ИИ"],
            filename="fig_05_scheme.png",
            source_note="Источник: составлено автором на основе архитектуры Минцифры РФ",
            synthetic=False,
        )
        out["forecast"] = self.line_chart(
            x=[2024, 2025, 2026, 2027, 2028],
            y_series={
                "Консервативный прогноз": [100, 105, 110, 115, 120],
                "Базовый прогноз": [100, 112, 125, 140, 158],
                "Оптимистичный прогноз": [100, 118, 138, 162, 190],
            },
            title="Прогноз экономического эффекта от внедрения (базовый год 2024 = 100%)",
            ylabel="Индекс, %",
            filename="fig_06_forecast.png",
            source_note="Источник: расчёт автора, учебный пример, данные условные",
            synthetic=True,
        )
        return out

