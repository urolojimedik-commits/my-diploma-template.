"""Формирование списка литературы.

Основной стиль — **ГОСТ Р 7.0.5-2008** (в России он обязателен для курсовых и
ВКР). Дополнительно поддерживаются APA, IEEE и Vancouver: они нужны, если
работа готовится по требованиям конкретного вуза или журнала.

Важно: форматирование ничего не придумывает — если у источника нет года или
страниц, соответствующий элемент описания просто отсутствует.
"""

from __future__ import annotations

import re

from ..model import Source

CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def _is_ru(text: str) -> bool:
    return bool(CYRILLIC.search(text or ""))


def authors_gost(source: Source) -> str:
    """«Фамилия И. О., Фамилия2 И. О.» (не более 4, иначе — первые 3 и «и др.»)."""
    names = [str(a) for a in source.authors]
    if not names:
        return ""
    if len(names) > 4:
        names = names[:3] + ["и др."]
    return ", ".join(names)


def _vol(source: Source) -> str:
    if not source.volume:
        return ""
    ru = _is_ru(source.venue or "")
    return f"Т. {source.volume}" if ru else f"Vol. {source.volume}"


def _pages(source: Source) -> str:
    if not source.pages:
        return ""
    ru = _is_ru(source.venue or "")
    return f"С. {source.pages}" if ru else f"P. {source.pages}"


def format_gost(source: Source, access_date: str = "") -> str:
    """Библиографическое описание по ГОСТ Р 7.0.5-2008."""
    head = authors_gost(source).rstrip(".")
    title = source.title or "б. з."
    parts: list[str] = []
    if head:
        parts.append(head)
    parts.append(title.rstrip("."))

    sep = ". — "
    text = ". ".join(parts)

    if source.type in {"chapter", "paper-conference"}:
        text += " // " + (source.venue.rstrip(".") if source.venue else "б. и.")
        bits = []
        if source.publisher:
            bits.append(source.publisher)
        if source.year:
            bits.append(str(source.year))
        if bits:
            text += sep + ", ".join(bits)
        if _pages(source):
            text += sep + _pages(source)
    elif source.type == "book":
        text += "."
        text += sep + (source.publisher or "б. и.")
        if source.year:
            text += ", " + str(source.year)
        if source.pages:
            text += sep + f"{source.pages} с."
    else:
        # статья из журнала / сборника
        text += " // " + (source.venue.rstrip(".") if source.venue else "б. и.")
        if source.year:
            text += sep + str(source.year)
        num_parts = [p for p in (_vol(source), f"№ {source.number}" if source.number else "", _pages(source)) if p]
        if num_parts:
            text += sep + ". — ".join(num_parts)

    if source.doi:
        text += sep + f"DOI: {source.doi}"
    if source.url and not source.doi:
        text += sep + f"URL: {source.url}"
        if access_date:
            text += f" (дата обращения: {access_date})"
    return text.strip().rstrip(".") + "."


def authors_apa(source: Source) -> str:
    names: list[str] = []
    for a in source.authors:
        ini = "".join(p[0].upper() + "." for p in a.given.split())
        names.append(f"{a.family}, {ini}".strip().rstrip(","))
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    if len(names) <= 20:
        return ", ".join(names[:-1]) + f", & {names[-1]}"
    return ", ".join(names[:19]) + f", … {names[-1]}"


def format_apa(source: Source) -> str:
    a = authors_apa(source)
    year = f"({source.year})" if source.year else "(б. г.)"
    title = (source.title or "").rstrip(".")
    venue = source.venue or ""
    vol = f"{source.volume}" + (f"({source.number})" if source.number else "")
    pages = source.pages or ""
    if source.type in {"chapter", "paper-conference"}:
        text = f"{a} {year}. {title}. In {venue} (pp. {pages})."
    elif source.type == "book":
        text = f"{a} {year}. {title}. {source.publisher or ''}."
    else:
        text = f"{a} {year}. {title}. {venue}"
        if vol:
            text += f", {vol}"
        if pages:
            text += f", {pages}"
        text += "."
    if source.doi:
        text += f" https://doi.org/{source.doi}"
    return re.sub(r"\s+", " ", text).strip()


def authors_ieee(source: Source) -> str:
    names = []
    for a in source.authors:
        ini = ". ".join(p[0].upper() for p in a.given.split())
        names.append(f"{ini}. {a.family}".strip())
    if not names:
        return ""
    if len(names) <= 3:
        return ", ".join(names[:-1] or names) + (f", and {names[-1]}" if len(names) > 1 else "")
    return f"{names[0]} et al."


def format_ieee(source: Source) -> str:
    a = authors_ieee(source)
    title = f"“{(source.title or '').rstrip('.')},”"
    venue = source.venue or ""
    text = f"{a}, {title} {venue}"
    if source.volume:
        text += f", vol. {source.volume}"
    if source.number:
        text += f", no. {source.number}"
    if source.pages:
        text += f", pp. {source.pages}"
    if source.year:
        text += f", {source.year}"
    text += "."
    if source.doi:
        text += f" doi: {source.doi}."
    return re.sub(r"\s+", " ", text).strip()


def format_vancouver(source: Source) -> str:
    names = [f"{a.family} {''.join(p[0].upper() for p in a.given.split())}" for a in source.authors]
    if len(names) > 6:
        names = names[:6] + ["et al."]
    a = ", ".join(names) if names else ""
    title = (source.title or "").rstrip(".")
    text = f"{a}. {title}. {source.venue or ''}"
    if source.year:
        text += f". {source.year}"
    if source.volume:
        text += f";{source.volume}"
        if source.number:
            text += f"({source.number})"
    if source.pages:
        text += f":{source.pages}"
    text += "."
    if source.doi:
        text += f" doi:{source.doi}"
    return re.sub(r"\s+", " ", text).strip()


FORMATTERS = {
    "gost": format_gost,
    "apa": format_apa,
    "ieee": format_ieee,
    "vancouver": format_vancouver,
}

STYLE_NAMES = {
    "gost": "ГОСТ Р 7.0.5-2008",
    "apa": "APA (7th)",
    "ieee": "IEEE",
    "vancouver": "Vancouver",
}


def format_reference(source: Source, style: str = "gost", access_date: str = "") -> str:
    fn = FORMATTERS.get(style, format_gost)
    try:
        return fn(source, access_date=access_date)  # type: ignore[call-arg]
    except TypeError:
        return fn(source)


def sort_key(source: Source) -> tuple:
    """Порядок по умолчанию для ГОСТ: сначала кириллица, затем латиница, по алфавиту."""
    first = ""
    if source.language == "ru" or _is_ru(source.title or ""):
        first = "0" + (source.authors[0].family if source.authors else source.title or "")
    else:
        first = "1" + (source.authors[0].family if source.authors else source.title or "")
    return (first.lower(), source.year or 0)


def format_bibliography(
    sources: list[Source], style: str = "gost", access_date: str = "", ordered: bool = True
) -> list[str]:
    """Готовый список литературы: нумерация в порядке цитирования или по алфавиту."""
    items = list(sources) if ordered else sorted(sources, key=sort_key)
    out = []
    for i, s in enumerate(items, start=1):
        out.append(f"{i}. {format_reference(s, style=style, access_date=access_date)}")
    return out
