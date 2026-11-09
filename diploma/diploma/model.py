"""Модель данных системы подготовки курсовых и дипломных работ.

Все сущности сериализуемы в JSON (см. ``to_dict``), чтобы конвейер можно было
останавливать на любом шаге и продолжать позже (используется веб-интерфейсом).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable


# --------------------------------------------------------------------------- #
# Источники
# --------------------------------------------------------------------------- #


@dataclass
class Author:
    """Автор источника. Имена хранятся в языке оригинала (требование ГОСТ)."""

    family: str
    given: str = ""

    @property
    def initials(self) -> str:
        parts = [p for p in self.given.replace(".", " ").split() if p]
        return "".join(p[0].upper() + "." for p in parts)

    def __str__(self) -> str:
        if self.given:
            return f"{self.family} {self.initials}".strip()
        return self.family


@dataclass
class Source:
    """Библиографическая запись, пригодная для цитирования.

    Ключевое правило системы: в текст попадают только записи с
    ``verified=True``. Поле ``facts`` содержит утверждения, каждое из которых
    восходит к абстракту или к проверенным библиографическим данным; генератор
    текста не имеет права выходить за пределы этих утверждений.
    """

    key: str
    title: str
    authors: list[Author] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    volume: str | None = None
    number: str | None = None
    pages: str | None = None
    publisher: str | None = None
    doi: str | None = None
    url: str | None = None
    type: str = "article-journal"
    language: str = "en"
    provider: str = "manual"
    abstract: str = ""
    summary_ru: str = ""
    facts: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    title_ru: str = ""
    verified: bool = False
    verified_via: str = ""
    verified_at: str = ""
    pmid: str | None = None
    relevance: float = 0.0

    @property
    def authors_ru(self) -> str:
        """Список авторов в форме, принятой в русских научных текстах."""
        if not self.authors:
            return "б. а."
        names = [str(a) for a in self.authors]
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} и {names[1]}"
        return f"{names[0]} и др."

    @property
    def authors_full(self) -> str:
        if not self.authors:
            return ""
        names = [str(a) for a in self.authors]
        if len(names) <= 3:
            return ", ".join(names)
        return ", ".join(names[:3]) + " и др."

    @property
    def cite_inline(self) -> str:
        """Ссылка в тексте: в формате, используемом Pandoc/Quarto."""
        return f"[@{self.key}]"

    @property
    def year_str(self) -> str:
        return str(self.year) if self.year else "б. г."

    @property
    def title_display(self) -> str:
        return self.title_ru or self.title

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}" if self.doi else (self.url or "")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["authors"] = [asdict(a) for a in self.authors]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Source":
        data = dict(data)
        authors = [Author(**a) for a in data.pop("authors", []) or []]
        return cls(authors=authors, **data)


# --------------------------------------------------------------------------- #
# Тема и план
# --------------------------------------------------------------------------- #


@dataclass
class Topic:
    """Разобранная тема работы (шаг 1 конвейера)."""

    raw: str
    title: str = ""
    work_type: str = "diploma"  # diploma | course | bachelor | master
    discipline: str = ""
    object_ru: str = ""  # объект исследования
    subject_ru: str = ""  # предмет исследования
    goal_ru: str = ""  # цель работы
    tasks_ru: list[str] = field(default_factory=list)
    methods_ru: list[str] = field(default_factory=list)
    keywords_ru: list[str] = field(default_factory=list)
    keywords_en: list[str] = field(default_factory=list)
    # части названия, выделенные при разборе темы (используются в плане):
    title_process: str = ""  # «Применение»
    title_method: str = ""  # «методов машинного обучения»
    title_domain: str = ""  # «автоматизированной диагностики …»

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Topic":
        return cls(**data)


@dataclass
class SectionPlan:
    """Узел плана работы (шаг 2 конвейера)."""

    id: str
    title: str
    level: int = 1  # 1 — глава, 2 — параграф, 3 — подпараграф
    goal: str = ""
    source_keys: list[str] = field(default_factory=list)
    children: list["SectionPlan"] = field(default_factory=list)
    kind: str = "body"  # front | body | back
    target_words: int = 400

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SectionPlan":
        children = [cls.from_dict(c) for c in data.pop("children", []) or []]
        return cls(children=children, **data)

    def walk(self) -> Iterable["SectionPlan"]:
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass
class Plan:
    topic: Topic
    sections: list[SectionPlan] = field(default_factory=list)

    def walk(self) -> Iterable[SectionPlan]:
        for s in self.sections:
            yield from s.walk()

    def to_dict(self) -> dict[str, Any]:
        return {"topic": self.topic.to_dict(), "sections": [s.to_dict() for s in self.sections]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        return cls(
            topic=Topic.from_dict(data["topic"]),
            sections=[SectionPlan.from_dict(s) for s in data.get("sections", [])],
        )


# --------------------------------------------------------------------------- #
# Данные, рисунки, таблицы
# --------------------------------------------------------------------------- #


@dataclass
class DataRow:
    values: dict[str, Any]
    source_keys: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class Dataset:
    """Набор данных для построения графиков.

    ``provenance`` обязателен и принимает одно из значений:

    ``real``      — реальные данные, извлечённые из проверенного источника
                    (в каждой строке указаны ключи-источники);
    ``synthetic`` — учебный пример, смоделированные данные; такие рисунки
                    получают явную пометку «учебный пример» в подписи;
    ``diagram``   — схема, построенная автором работы (не содержит данных).
    """

    key: str
    title: str
    columns: list[str]
    rows: list[DataRow]
    provenance: str = "real"
    description: str = ""
    unit: str = ""

    def to_csv(self) -> str:
        header = self.columns + ["_source_keys", "_note"]
        lines = [",".join(f'"{c}"' for c in header)]
        for r in self.rows:
            vals = [str(r.values.get(c, "")) for c in self.columns]
            vals += [";".join(r.source_keys), r.note]
            lines.append(",".join(f'"{v}"' for v in vals))
        return "\n".join(lines) + "\n"


@dataclass
class Figure:
    """Рисунок/workflow-иллюстрация с подписью и номером (шаги 5, 6)."""

    key: str
    path: str
    caption: str
    number: str = ""
    label: str = ""
    section_id: str = ""
    provenance: str = "diagram"
    source_note: str = ""
    dataset_key: str = ""

    def caption_full(self, style: str = "gost") -> str:
        num = f"Рисунок {self.number}" if self.number else "Рисунок"
        if style == "gost":
            head = f"{num} — {self.caption}"
        else:
            head = f"{num}. {self.caption}"
        if self.source_note:
            head = f"{head}. {self.source_note}"
        if not head.endswith("."):
            head += "."
        return head


@dataclass
class Table:
    """Таблица с подписью и номером (шаг 5)."""

    key: str
    headers: list[str]
    rows: list[list[str]]
    caption: str
    number: str = ""
    label: str = ""
    section_id: str = ""
    provenance: str = "real"
    source_note: str = ""
    align: str | None = None

    def caption_full(self, style: str = "gost") -> str:
        num = f"Таблица {self.number}" if self.number else "Таблица"
        head = f"{num} — {self.caption}" if style == "gost" else f"{num}. {self.caption}"
        if self.source_note:
            head = f"{head}. {self.source_note}"
        if not head.endswith("."):
            head += "."
        return head


# --------------------------------------------------------------------------- #
# Документ
# --------------------------------------------------------------------------- #


@dataclass
class Document:
    """Полностью собранный документ перед рендерингом."""

    topic: Topic
    plan: Plan
    sources: list[Source]
    sections_md: dict[str, str] = field(default_factory=dict)
    figures: list[Figure] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def source_by_key(self, key: str) -> Source | None:
        for s in self.sources:
            if s.key == key:
                return s
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic.to_dict(),
            "plan": self.plan.to_dict(),
            "sources": [s.to_dict() for s in self.sources],
            "figures": [asdict(f) for f in self.figures],
            "tables": [asdict(t) for t in self.tables],
            "metadata": self.metadata,
            "warnings": self.warnings,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
