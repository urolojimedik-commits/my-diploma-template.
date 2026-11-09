"""Интерфейсы генераторов академического текста (шаг 4).

Ключевой принцип: генератор получает **только проверенные источники** и не
имеет права выходить за пределы их выверенных утверждений. Если по разделу
нет проверенных данных, генератор обязан вернуть явную пометку
``{{ТРЕБУЕТСЯ ИСТОЧНИК}}``, а не «правдоподобный» текст.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import Plan, SectionPlan, Source, Topic

MISSING_SOURCE_MARK = "{{ТРЕБУЕТСЯ ИСТОЧНИК}}"


@dataclass
class SectionContext:
    """Всё, что нужно для написания одного раздела."""

    topic: Topic
    plan: Plan
    section: SectionPlan
    sources: list[Source] = field(default_factory=list)
    media_refs: list[str] = field(default_factory=list)  # метки рисунков/таблиц раздела
    chapter_number: str = ""
    path: str = ""  # «Глава 2», «2.3» и т. п.

    @property
    def label(self) -> str:
        return f"{self.path} {self.section.title}".strip()


class TextBackend:
    """Базовый класс генератора текста."""

    name = "base"

    def write_section(self, ctx: SectionContext) -> str:
        raise NotImplementedError

    def write_introduction(self, topic: Topic, sources: list[Source], plan: Plan) -> str:
        raise NotImplementedError

    def write_conclusion(self, topic: Topic, sources: list[Source], plan: Plan) -> str:
        raise NotImplementedError

    def write_annotation(self, topic: Topic, sources: list[Source]) -> str:
        raise NotImplementedError
