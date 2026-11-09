"""
config.py — модели данных и ГОСТ-настройки.
"""

from __future__ import annotations

import enum
import pathlib
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


class WorkType(str, enum.Enum):
    """Тип научной работы."""

    COURSE = "курсовая"
    DIPLOMA = "диплом"
    BACHELOR = "вкр_бакалавр"
    MASTER = "магистерская"
    ARTICLE = "статья"
    PRESENTATION = "презентация"


@dataclass
class AuthorInfo:
    fio: str = "Иванов И.И."
    group: str = "ИВТ-21"
    faculty: str = "Факультет информационных технологий"
    department: str = "Кафедра информационных систем"
    supervisor: str = "Петров П.П., к.т.н., доцент"
    supervisor_degree: str = "к.т.н., доцент"


@dataclass
class OrganizationInfo:
    ministry: str = "Министерство науки и высшего образования Российской Федерации"
    university: str = "Российский государственный университет"
    institute: str = ""
    city: str = "Москва"
    year: int = 2026


@dataclass
class FigureSpec:
    id: str
    caption: str
    filename: str
    source_note: str = ""  # "Источник: ..." или "Учебный пример"
    synthetic: bool = False


@dataclass
class TableSpec:
    id: str
    caption: str
    headers: List[str]
    rows: List[List[str]]
    source_note: str = ""
    synthetic: bool = False


@dataclass
class SourceRecord:
    """Один источник (проверенный)."""

    key: str  # bibtex key, напр. ivanov2023digital
    title: str
    authors: List[str]
    year: int
    doi: Optional[str] = None
    url: Optional[str] = None
    journal: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    verified: bool = False  # DOI проверен через Crossref
    language: str = "ru"
    abstract: Optional[str] = None
    bibtex: Optional[str] = None

    def to_bibtex(self) -> str:
        """Генерация BibTeX записи."""
        if self.bibtex:
            return self.bibtex
        authors_bib = " and ".join(self.authors) if self.authors else "Anon"
        entry_type = "article" if self.journal else "book"
        lines = [f"@{entry_type}{{{self.key},"]
        lines.append(f"  title = {{{self.title}}},")
        lines.append(f"  author = {{{authors_bib}}},")
        lines.append(f"  year = {{{self.year}}},")
        if self.journal:
            lines.append(f"  journal = {{{self.journal}}},")
        if self.publisher:
            lines.append(f"  publisher = {{{self.publisher}}},")
        if self.volume:
            lines.append(f"  volume = {{{self.volume}}},")
        if self.pages:
            lines.append(f"  pages = {{{self.pages}}},")
        if self.doi:
            lines.append(f"  doi = {{{self.doi}}},")
        if self.url:
            lines.append(f"  url = {{{self.url}}},")
        lines.append("}")
        return "\n".join(lines)

    def to_gost(self, number: int) -> str:
        """ГОСТ Р 7.0.5-2018 (упрощённый)."""
        authors_str = ", ".join(self.authors) if self.authors else "Anon"
        base = f"{number}. {authors_str} {self.title}"
        if self.journal:
            base += f" // {self.journal}"
        if self.publisher:
            base += f" : {self.publisher}"
        if self.year:
            base += f". — {self.year}"
        if self.volume:
            base += f". — Т. {self.volume}"
        if self.pages:
            base += f". — С. {self.pages}"
        if self.doi:
            base += f". — DOI: {self.doi}"
        elif self.url:
            base += f". — URL: {self.url}"
        base += "."
        return base


@dataclass
class ChapterPlan:
    """План одной главы/раздела."""

    number: str  # "Введение", "1", "2.1"
    title: str
    description: str = ""
    pages_target: int = 8
    subsections: List["ChapterPlan"] = field(default_factory=list)
    sources_needed: int = 5
    figures: List[FigureSpec] = field(default_factory=list)
    tables: List[TableSpec] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    """Главный конфиг проекта (project.yaml)."""

    topic: str
    work_type: WorkType = WorkType.DIPLOMA
    discipline: str = "Информационные системы"
    language: str = "ru"
    author: AuthorInfo = field(default_factory=AuthorInfo)
    organization: OrganizationInfo = field(default_factory=OrganizationInfo)
    keywords: List[str] = field(default_factory=list)
    goal: str = ""
    tasks: List[str] = field(default_factory=list)
    object_research: str = ""
    subject_research: str = ""
    methods: List[str] = field(default_factory=list)
    plan: List[ChapterPlan] = field(default_factory=list)
    sources: List[SourceRecord] = field(default_factory=list)
    output_dir: pathlib.Path = pathlib.Path("output")
    # ГОСТ настройки
    font_name: str = "Times New Roman"
    font_size: int = 14
    line_spacing: float = 1.5
    margins_mm: Dict[str, int] = field(
        default_factory=lambda: {"left": 30, "right": 15, "top": 20, "bottom": 20}
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "work_type": self.work_type.value,
            "discipline": self.discipline,
            "language": self.language,
            "author": self.author.__dict__,
            "organization": self.organization.__dict__,
            "keywords": self.keywords,
            "goal": self.goal,
            "tasks": self.tasks,
            "object_research": self.object_research,
            "subject_research": self.subject_research,
            "methods": self.methods,
            "output_dir": str(self.output_dir),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        wt = WorkType(data.get("work_type", "диплом"))
        author = AuthorInfo(**data.get("author", {}))
        org = OrganizationInfo(**data.get("organization", {}))
        return cls(
            topic=data["topic"],
            work_type=wt,
            discipline=data.get("discipline", "Информационные системы"),
            language=data.get("language", "ru"),
            author=author,
            organization=org,
            keywords=data.get("keywords", []),
            goal=data.get("goal", ""),
            tasks=data.get("tasks", []),
            object_research=data.get("object_research", ""),
            subject_research=data.get("subject_research", ""),
            methods=data.get("methods", []),
            output_dir=pathlib.Path(data.get("output_dir", "output")),
        )


# ГОСТ-константы
GOST = {
    "margins_mm": {"left": 30, "right": 15, "top": 20, "bottom": 20},
    "font": {"name": "Times New Roman", "size_pt": 14, "heading_size": 16},
    "line_spacing": 1.5,
    "paragraph_indent_cm": 1.25,
    "caption": {"font_size": 12, "prefix_figure": "Рисунок", "prefix_table": "Таблица"},
    "page_numbering": "bottom_center",
}

