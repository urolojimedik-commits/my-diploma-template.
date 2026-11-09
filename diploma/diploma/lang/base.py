"""Базовый класс языка оформления.

От языка зависит: названия разделов, слова «Расм/Ҷадвал» (рисунок/таблица),
форма чисел (десятичный разделитель), формулировки служебных пометок
(«Маълумот нокифоя» — «данных недостаточно»).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Language:
    code: str
    name: str
    terms: dict[str, str] = field(default_factory=dict)
    months: list[str] = field(default_factory=list)
    decimal_separator: str = ","
    thousands_separator: str = " "

    # ----------------------------------------------------------------- слова
    def t(self, key: str, **kwargs) -> str:
        """Перевод служебного термина; при отсутствии ключа возвращает сам ключ."""
        value = self.terms.get(key, key)
        return value.format(**kwargs) if kwargs else value

    # --------------------------------------------------------------- подписи
    def figure_caption(self, number: str, caption: str, source_note: str = "") -> str:
        text = f"{self.t('figure')} {number} — {caption.rstrip('.')}"
        if source_note:
            text += f". {source_note.rstrip('.')}"
        return text.strip() + "."

    def table_caption(self, number: str, caption: str, source_note: str = "") -> str:
        """Подпись таблицы (по ГОСТ — над таблицей)."""
        text = f"{self.t('table')} {number} — {caption.rstrip('.')}"
        if source_note:
            text += f". {source_note.rstrip('.')}"
        return text.strip() + "."

    def ref(self, kind: str, number: str, capitalize: bool = False) -> str:
        """Перекрёстная ссылка: «расми 2.1», «ҷадвали 2.2»."""
        key = "figure_ref" if kind == "fig" else "table_ref"
        text = f"{self.t(key)} {number}"
        return text[:1].upper() + text[1:] if capitalize else text

    def chapter_title(self, number: str, title: str) -> str:
        return f"{self.t('chapter_gen')} {number}. {title}"

    def section_title(self, number: str, title: str) -> str:
        return f"{number} {title}"

    # ---------------------------------------------------------------- числа
    def number(self, value: float | int, decimals: int | None = None) -> str:
        """Число с десятичной запятой и округлением «по правилам» (не до чётного)."""
        from decimal import Decimal, ROUND_HALF_UP

        if decimals is None:
            text = str(value)
        else:
            q = Decimal(1).scaleb(-decimals)
            text = f"{Decimal(str(float(value))).quantize(q, rounding=ROUND_HALF_UP):f}"
        if self.decimal_separator != ".":
            text = text.replace(".", self.decimal_separator)
        return text

    def percent(self, value: float, decimals: int = 1) -> str:
        return f"{self.number(value, decimals)} %"

    def p_value(self, value: float, threshold: float = 0.05) -> str:
        """«p<0,05» или «p = 0,032» в принятой для языка форме."""
        if value < threshold:
            return f"p<{self.number(threshold, 2)}"
        return f"p = {self.number(value, 3)}"

    def date_str(self, value: date | None = None) -> str:
        value = value or date.today()
        return f"{value.day:02d}.{value.month:02d}.{value.year}"

    def plural(self, n: int, forms: tuple[str, str, str]) -> str:
        """forms: (1, 2-4, 5+) — например («бемор», «бемор», «беморон»)."""
        n = abs(int(n)) % 100
        n1 = n % 10
        if 10 < n < 20:
            return forms[2]
        if 1 < n1 < 5:
            return forms[1]
        if n1 == 1:
            return forms[0]
        return forms[2]

    def count(self, n: int, noun: str) -> str:
        return f"{n} {noun}"  # в таджикском после числительного — единственное число

    # ------------------------------------------------------- служебные метки
    def missing_data(self) -> str:
        return self.t("missing_data")

    def source_label(self) -> str:
        return self.t("source")

    def own_data_label(self) -> str:
        return self.t("own_data")

    def teaching_example(self) -> str:
        return self.t("teaching_example")
