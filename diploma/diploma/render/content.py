"""Модель содержания медицинской работы на таджикском.

Это «черновик» документа до попадания в Word: список блоков
(заголовок, абзац, рисунок, таблица, список литературы…). Такой вид удобен
тем, что номера рисунков, таблиц, глав и ссылок вычисляются один раз
(``assign_numbers``) и попадают в документ как **поля Word** — то есть
Word сам перенумерует их, если вы вставите новый рисунок или главу.

Встроенная разметка абзаца
--------------------------
* ``{fig:ключ}`` — ссылка на рисунок (расми 2.1);
* ``{tbl:ключ}`` — ссылка на таблицу (ҷадвали 2.2);
* ``{src:ключ}`` — ссылка на источник из списка литературы: [3].

Если ключ неизвестен, подставляется «Маълумот нокифоя»/«[?]», но **не**
выдуманный номер.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

APPENDIX_LETTERS = ["А", "Б", "В", "Г", "Д", "Е", "Ж", "З"]

INLINE_REF = re.compile(r"\{(FIG|TBL|fig|tbl|src):([A-Za-z0-9_\-\.]+)\}")


# --------------------------------------------------------------------------- #
# Блоки
# --------------------------------------------------------------------------- #


class Block:
    """Общий предок блоков (не dataclass: чтобы наследники задавали свои поля)."""

    kind: str = "block"


@dataclass
class TitlePage(Block):
    """Титульный лист (реквизиты берутся из профиля университета)."""

    work_type: str = "diploma"
    topic: str = ""
    topic_ru: str = ""
    author: str = ""
    group: str = ""
    supervisor: str = ""
    reviewer: str = ""
    consultant: str = ""
    head_of_chair: str = ""
    chair: str = ""
    city: str = ""
    year: int = 2026
    frame: bool = False  # рамка по ГОСТ 7.32-2017

    def __post_init__(self):
        self.kind = "title"


@dataclass
class TOC(Block):
    levels: str = "1-2"
    title: str = "Мундариҷа"

    def __post_init__(self):
        self.kind = "toc"


@dataclass
class Heading(Block):
    text: str
    level: int = 1  # 1 — глава (Боб), 2 — параграф
    numbered: bool = True
    chapter: bool = True  # нумеровать как главу (SEQ Chapter)

    def __post_init__(self):
        self.kind = "heading"


@dataclass
class Para(Block):
    text: str
    style: str = "body"  # body | annotation | note | centered | source

    def __post_init__(self):
        self.kind = "para"


@dataclass
class Bullets(Block):
    items: list[str]
    style: str = "list"

    def __post_init__(self):
        self.kind = "bullets"


@dataclass
class FigureBlock(Block):
    key: str
    path: str
    caption: str
    source_note: str = ""
    provenance: str = "diagram"  # real | synthetic | diagram | own_data
    width_cm: float = 14.0

    def __post_init__(self):
        self.kind = "figure"


@dataclass
class TableBlock(Block):
    key: str
    header: list[str]
    rows: list[list[Any]]
    caption: str = ""
    source_note: str = ""
    note: str = ""
    provenance: str = "own_data"
    widths_cm: list[float] = field(default_factory=list)

    def __post_init__(self):
        self.kind = "table"


@dataclass
class AbbrevBlock(Block):
    pairs: list[tuple[str, str]]
    title: str = "Рӯйхати ихтисораҳо"

    def __post_init__(self):
        self.kind = "abbrev"


@dataclass
class RefList(Block):
    entries: list[str]
    title: str = "Рӯйхати адабиёт"

    def __post_init__(self):
        self.kind = "refs"


@dataclass
class Appendix(Block):
    title: str
    letter: str = ""  # вычисляется автоматически: А, Б, В…
    blocks: list[Block] = field(default_factory=list)

    def __post_init__(self):
        self.kind = "appendix"


@dataclass
class PageBreak(Block):
    def __post_init__(self):
        self.kind = "pagebreak"


@dataclass
class MedicalDocument:
    """Готовый «черновик» работы: метаданные + последовательность блоков."""

    blocks: list[Block] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    numbering: str = "per_chapter"  # per_chapter | continuous

    def add(self, block: Block) -> Block:
        self.blocks.append(block)
        return block

    def walk(self):
        for b in self.blocks:
            yield b
            if isinstance(b, Appendix):
                for sub in b.blocks:
                    yield sub


# --------------------------------------------------------------------------- #
# Нумерация
# --------------------------------------------------------------------------- #


def assign_numbers(doc: MedicalDocument, citation_map: dict[str, int] | None = None) -> dict[str, str]:
    """Рассчитывает кэшированные номера: они же дублируются в полях Word.

    Логика повторяет правила полей ``SEQ``: счётчики рисунков и таблиц
    сбрасываются в начале каждой главы (и каждого приложения), главы
    нумеруются подряд, приложения — буквами А, Б, В…
    """
    numbers: dict[str, str] = {}
    chapter = 0
    fig = 0
    tbl = 0
    continuous = doc.numbering == "continuous"
    appendix_idx = 0
    appendix_letter = ""
    appendix_fig = 0
    appendix_tbl = 0

    for block in doc.walk():
        if isinstance(block, Appendix):
            appendix_idx += 1
            appendix_letter = APPENDIX_LETTERS[(appendix_idx - 1) % len(APPENDIX_LETTERS)]
            if not block.letter:
                block.letter = appendix_letter  # чтобы сборщик печатал ту же букву
            appendix_fig = 0
            appendix_tbl = 0
            continue
        if isinstance(block, Heading) and block.numbered and block.level == 1 and block.chapter:
            chapter += 1
            fig = 0
            tbl = 0
        elif isinstance(block, FigureBlock):
            fig += 1
            if appendix_letter:
                appendix_fig += 1
                numbers[f"fig:{block.key}"] = f"{appendix_letter}.{appendix_fig}"
            elif continuous:
                numbers[f"fig:{block.key}"] = str(fig)
            else:
                numbers[f"fig:{block.key}"] = f"{max(chapter, 1)}.{fig}"
        elif isinstance(block, TableBlock):
            tbl += 1
            if appendix_letter:
                appendix_tbl += 1
                numbers[f"tbl:{block.key}"] = f"{appendix_letter}.{appendix_tbl}"
            elif continuous:
                numbers[f"tbl:{block.key}"] = str(tbl)
            else:
                numbers[f"tbl:{block.key}"] = f"{max(chapter, 1)}.{tbl}"

    for key, num_value in (citation_map or {}).items():
        numbers[f"src:{key}"] = str(num_value)
    return numbers


def split_inline(text: str) -> list[tuple[str, str, str]]:
    """Разбирает абзац на обычный текст и встроенные ссылки.

    Возвращает список ``(тип, ключ или текст, обычный текст)``;
    ``тип`` — ``text`` | ``fig`` | ``tbl`` | ``src``.
    """
    out: list[tuple[str, str, str]] = []
    pos = 0
    for m in INLINE_REF.finditer(text):
        if m.start() > pos:
            out.append(("text", text[pos : m.start()], text[pos : m.start()]))
        out.append((m.group(1), m.group(2), m.group(0)))
        pos = m.end()
    if pos < len(text):
        out.append(("text", text[pos:], text[pos:]))
    return out
