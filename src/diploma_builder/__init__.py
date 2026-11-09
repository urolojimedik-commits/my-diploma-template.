"""
diploma_builder — система автоматизации подготовки курсовых и дипломных работ.

Поддерживает:
- приём темы → план → поиск реальных источников → текст → графики → DOCX/PDF
- русский язык, ГОСТ Р 7.0.5-2018
- проверку DOI, явную маркировку учебных примеров
"""

__version__ = "1.0.0"
__author__ = "diploma_builder"

from .config import ProjectConfig, WorkType, ChapterPlan, FigureSpec, TableSpec

__all__ = ["ProjectConfig", "WorkType", "ChapterPlan", "FigureSpec", "TableSpec"]

