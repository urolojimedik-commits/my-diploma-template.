"""Список сокращений медицинской работы (рӯйхати ихтисораҳо).

Правила ГОСТ 7.32-2017 и ГОСТ Р 7.0.11-2011:

* сокращение вводится при первом употреблении в тексте, дальше без расшифровки:
  «томографияи компютерӣ (ТК)» → далее «ТК»;
* в список сокращений попадают только те, что реально встретились в тексте;
* список упорядочивается по алфавиту (латиница, затем кириллица).

Модуль ничего не придумывает: расшифровка либо задана автором/словарём
``data/terms.med.tg.json``, либо сокращение помечается как нерасшифрованное
и система просит автора дописать его (см. ``undefined()``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..settings import DATA_DIR

DICT_PATH = DATA_DIR / "terms.med.tg.json"

# Латинские аббревиатуры (2–8 символов, хотя бы одна заглавная), не внутри слова
LAT_RE = re.compile(r"(?<![А-Яа-яЁёA-Za-z0-9_])([A-Z][A-Za-z0-9]{1,7})\b")
# Кириллические (все заглавные, 2–6 символов)
CYR_RE = re.compile(r"(?<![А-Яа-яЁёA-Za-z0-9_])([А-ЯЁҒӢҚӮҲҶ]{2,6})\b")

# Слова, которые не являются сокращениями
STOP_ABBR = {
    "AND", "OR", "OF", "THE", "FOR", "WITH", "AND/OR", "IN", "ON", "TO", "AT",
    "US", "IS", "IT", "AS", "BE", "BY", "DO", "GO", "NO", "SO", "WE",
    "ВА", "ВАҚТ", "ДАР", "ИН", "ОН", "ҲАМ",
}


@dataclass
class Abbreviation:
    abbr: str
    expansion_tg: str = ""
    expansion_ru: str = ""
    expansion_en: str = ""
    note: str = ""  # «бо забони англисӣ», «аз луғати истилоҳот»
    first_seen_section: str = ""
    occurrences: int = 0

    @property
    def defined(self) -> bool:
        return bool(self.expansion_tg or self.expansion_ru)

    def expansion(self, lang: str = "tg") -> str:
        return {
            "tg": self.expansion_tg or self.expansion_ru,
            "ru": self.expansion_ru or self.expansion_tg,
            "en": self.expansion_en,
        }.get(lang, self.expansion_tg)

    def to_dict(self) -> dict:
        return {
            "abbr": self.abbr,
            "expansion_tg": self.expansion_tg,
            "expansion_ru": self.expansion_ru,
            "expansion_en": self.expansion_en,
            "note": self.note,
            "first_seen_section": self.first_seen_section,
            "occurrences": self.occurrences,
        }


class AbbreviationList:
    """Упорядоченный список сокращений с расшифровками."""

    def __init__(self, items: list[Abbreviation] | None = None) -> None:
        self._items: dict[str, Abbreviation] = {}
        for i in items or []:
            self.add_obj(i)

    # ------------------------------------------------------------------ мутаторы
    def add(
        self,
        abbr: str,
        expansion: str = "",
        lang: str = "tg",
        expansion_ru: str = "",
        expansion_en: str = "",
        note: str = "",
        section: str = "",
    ) -> Abbreviation:
        key = abbr.strip()
        if not key or key in STOP_ABBR:
            raise ValueError(f"Недопустимое сокращение: {abbr!r}")
        obj = self._items.get(key)
        if obj is None:
            obj = Abbreviation(abbr=key)
            self._items[key] = obj
        if lang == "tg":
            obj.expansion_tg = obj.expansion_tg or expansion
        elif lang == "ru":
            obj.expansion_ru = obj.expansion_ru or expansion
        elif lang == "en":
            obj.expansion_en = obj.expansion_en or expansion
        obj.expansion_ru = obj.expansion_ru or expansion_ru
        obj.expansion_en = obj.expansion_en or expansion_en
        obj.note = obj.note or note
        if section and not obj.first_seen_section:
            obj.first_seen_section = section
        return obj

    def add_obj(self, item: Abbreviation) -> Abbreviation:
        self._items[item.abbr] = item
        return item

    def get(self, abbr: str) -> Abbreviation | None:
        return self._items.get(abbr.strip())

    def __contains__(self, abbr: str) -> bool:
        return abbr.strip() in self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self.entries())

    # -------------------------------------------------------------------- вывод
    def entries(self) -> list[Abbreviation]:
        """Сортировка: латиница, затем кириллица; внутри — по алфавиту."""

        def key(a: Abbreviation) -> tuple[int, str]:
            first = a.abbr[0]
            group = 0 if first.isascii() else 1
            return (group, a.abbr.lower())

        return sorted(self._items.values(), key=key)

    def defined_entries(self) -> list[Abbreviation]:
        return [a for a in self.entries() if a.defined]

    def undefined(self) -> list[Abbreviation]:
        """Сокращения без расшифровки — их нужно показать автору."""
        return [a for a in self.entries() if not a.defined]

    def render_lines(self, lang: str = "tg", width: int = 0) -> list[str]:
        """Строки вида «КТ — томографияи компютерӣ»."""
        lines = []
        for a in self.defined_entries():
            exp = a.expansion(lang)
            extra = []
            if lang == "tg" and a.expansion_en and a.expansion_en.lower() != a.abbr.lower():
                extra.append(a.expansion_en)
            if extra:
                exp = f"{exp} ({'; '.join(extra)})"
            lines.append(f"{a.abbr} — {exp}".rstrip())
        return lines

    def to_dict(self) -> dict:
        return {"items": [a.to_dict() for a in self.entries()]}

    # ------------------------------------------------------------- разбор текста
    def scan_text(self, text: str, section: str = "") -> list[str]:
        """Находит сокращения в тексте; возвращает новые, ещё не описанные."""
        found: list[str] = []
        for match in list(LAT_RE.finditer(text)) + list(CYR_RE.finditer(text)):
            token = match.group(1)
            if token in STOP_ABBR:
                continue
            obj = self._items.get(token)
            if obj is None:
                self._items[token] = Abbreviation(abbr=token, first_seen_section=section)
                found.append(token)
            else:
                obj.occurrences += 1
        return found

    def expand_first_use(self, text: str, lang: str = "tg") -> str:
        """Расшифровывает сокращение при первом употреблении: «КТ (ТК)»."""
        seen: set[str] = set()

        def repl(match: re.Match) -> str:
            token = match.group(1)
            if token in seen or token in STOP_ABBR:
                return token
            obj = self._items.get(token)
            if obj is None or not obj.defined:
                return token
            seen.add(token)
            return f"{obj.expansion(lang)} ({token})"

        text = LAT_RE.sub(repl, text)
        text = CYR_RE.sub(repl, text)
        return text

    def check_undefined(self) -> list[str]:
        """Сообщения для автора о сокращениях без расшифровки."""
        return [
            f"{a.abbr}: расшифровка на таджикском/русском не задана"
            for a in self.undefined()
        ]


# --------------------------------------------------------------------------- #
# Словарь сокращений из терминологического файла
# --------------------------------------------------------------------------- #


def load_from_dictionary(path: Path | None = None, lang: str = "tg") -> AbbreviationList:
    """Заполняет список сокращениями из ``data/terms.med.tg.json``."""
    path = path or DICT_PATH
    lst = AbbreviationList()
    if not path.exists():
        return lst
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    for term, info in (data.get("terms", {}) or {}).items():
        src = str(info.get("source", ""))
        ru = src.split(" / ")[0]
        en = src.split(" / ")[-1] if " / " in src else ""
        # расшифровка: если сам термин — сокращение (УЗИ), берём явное поле
        # expansion_tg, иначе — название статьи словаря
        expansion = info.get("expansion_tg") or (
            term if not (LAT_RE.fullmatch(term) or CYR_RE.fullmatch(term)) else ""
        )
        if not expansion:
            non_abbr = [
                v
                for v in (info.get("variants", []) or [])
                if not (LAT_RE.fullmatch(v) or CYR_RE.fullmatch(v))
            ]
            expansion = non_abbr[0] if non_abbr else term
        for variant in info.get("variants", []) or []:
            is_abbr = bool(LAT_RE.fullmatch(variant) or CYR_RE.fullmatch(variant))
            if not is_abbr or variant in STOP_ABBR or variant == expansion:
                continue
            lst.add(
                variant,
                expansion=expansion,
                lang=lang,
                expansion_ru=ru,
                expansion_en=en,
                note="аз луғати истилоҳот",
            )
    return lst
