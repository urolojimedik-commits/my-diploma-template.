"""Структура медицинской работы: разделы, план IMRAD, сокращения."""

from __future__ import annotations

from .sections import SectionSpec, build_outline, outline_to_plan, next_figure_number
from .medical import MedicalProfile, get_profile, build_medical_plan
from .abbreviations import Abbreviation, AbbreviationList

__all__ = [
    "SectionSpec",
    "build_outline",
    "outline_to_plan",
    "next_figure_number",
    "MedicalProfile",
    "get_profile",
    "build_medical_plan",
    "Abbreviation",
    "AbbreviationList",
]
