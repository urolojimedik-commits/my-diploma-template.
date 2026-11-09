"""Языки оформления работы: таджикский (основной) и русский."""

from __future__ import annotations

from .base import Language
from .ru import Russian
from .tg import Tajik

LANGS: dict[str, type[Language]] = {
    "tg": Tajik,
    "ru": Russian,
}

DEFAULT_LANGUAGE = "tg"


def get_language(code: str = DEFAULT_LANGUAGE) -> Language:
    """Возвращает объект языка; для неизвестного кода — таджикский."""
    cls = LANGS.get((code or DEFAULT_LANGUAGE).lower(), Tajik)
    return cls()


def available() -> list[str]:
    return sorted(LANGS)


__all__ = ["Language", "Tajik", "Russian", "get_language", "available"]
