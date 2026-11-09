"""Нумерация рисунков и таблиц, перекрёстные ссылки (шаг 6)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import Figure, Table


@dataclass
class Registry:
    """Присваивает номера «номер главы . порядковый номер».

    Если материал относится к разделу без номера главы (введение, заключение,
    приложение), используется сквозная нумерация — это соответствует
    требованиям ГОСТ Р 7.0.32-2017 (допускаются оба способа, но не смесь
    внутри одного документа без необходимости).
    """

    mode: str = "chapter"  # chapter | continuous
    fig_counters: dict[str, int] = field(default_factory=dict)
    tbl_counters: dict[str, int] = field(default_factory=dict)
    continuous_fig: int = 0
    continuous_tbl: int = 0
    labels: dict[str, tuple[str, str]] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    def number_figure(self, figure: Figure, chapter: str | None = None) -> str:
        number = self._next(self.fig_counters, "continuous_fig", chapter)
        figure.number = number
        figure.label = figure.label or f"fig:{figure.key}"
        self.labels[figure.label] = ("fig", number)
        return number

    def number_table(self, table: Table, chapter: str | None = None) -> str:
        number = self._next(self.tbl_counters, "continuous_tbl", chapter)
        table.number = number
        table.label = table.label or f"tbl:{table.key}"
        self.labels[table.label] = ("tbl", number)
        return number

    def _next(self, counters: dict[str, int], cont_attr: str, chapter: str | None) -> str:
        if self.mode == "continuous" or not chapter:
            setattr(self, cont_attr, getattr(self, cont_attr) + 1)
            return str(getattr(self, cont_attr))
        counters[chapter] = counters.get(chapter, 0) + 1
        return f"{chapter}.{counters[chapter]}"

    # ------------------------------------------------------------------ #
    def ref(self, label: str, capitalize: bool = False) -> str:
        """Текст перекрёстной ссылки: «рис. 2.1» / «табл. 2.1»."""
        entry = self.labels.get(label)
        if not entry:
            return "???"
        kind, number = entry
        word = "рис." if kind == "fig" else "табл."
        text = f"{word} {number}"
        return text[:1].upper() + text[1:] if capitalize else text

    def resolve(self, text: str) -> str:
        """Заменяет ``{{ref:label}}`` на готовый текст ссылки."""
        import re

        def repl(match: "re.Match[str]") -> str:
            cap = match.group(1) == "Ref"
            return self.ref(match.group(2), capitalize=cap)

        return re.sub(r"\{\{(Ref|ref):([A-Za-z0-9_:.-]+)\}\}", repl, text)

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "labels": self.labels,
            "fig_counters": self.fig_counters,
            "tbl_counters": self.tbl_counters,
        }
