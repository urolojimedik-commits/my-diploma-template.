"""Экспорт и импорт BibTeX.

Экспорт нужен и для Pandoc/Quarto (формирование списка литературы средствами
CSL), и для того, чтобы пользователь мог открыть список в JabRef/Zotero.
Импорт позволяет подключить собственную библиографию: пользовательские записи
проходят ту же проверку, что и найденные автоматически.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..model import Author, Source

_ENTRY_RE = re.compile(r"@(?P<type>\w+)\s*[\{\(]\s*(?P<key>[^,]+)\s*,", re.I)
_FIELD_RE = re.compile(
    r"(?P<name>\w+)\s*=\s*(?P<val>\{[^{}]*((?:\{[^{}]*\}[^{}]*)*)\}|\"[^\"]*\"|[^\s,]+)\s*,?",
    re.S,
)

TYPE_MAP = {
    "article": "article-journal",
    "articlejournal": "article-journal",
    "journalarticle": "article-journal",
    "book": "book",
    "incollection": "chapter",
    "inbook": "chapter",
    "inproceedings": "paper-conference",
    "conference": "paper-conference",
    "proceedings": "paper-conference",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "thesis": "thesis",
    "misc": "webpage",
    "online": "webpage",
    "preprint": "preprint",
}


# --------------------------------------------------------------------------- #
# Экспорт
# --------------------------------------------------------------------------- #


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("_", "\\_")
        .replace("#", "\\#")
    )


def _protect(value: str) -> str:
    """Сохраняет капитализацию значимых слов (требование BibTeX)."""
    parts = re.split(r"(\b[A-Z][A-Za-z]*\b|\b[A-ZА-ЯЁ]{2,}\b|\d+[A-Za-z]*)", value)
    out: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1 and part:
            out.append("{" + part + "}")
        else:
            out.append(part)
    return "".join(out)


def to_bibtex(source: Source) -> str:
    lines = [f"@{bib_type(source)}" + "{" + source.key + ","]
    authors = " and ".join(
        f"{a.family}, {a.given}".strip() for a in source.authors
    )
    if authors:
        lines.append(f"  author = {{{_escape(authors)}}},")
    lines.append(f"  title = {{{_escape(_protect(source.title))}}},")
    if source.venue:
        field = "booktitle" if source.type in {"chapter", "paper-conference"} else "journal"
        lines.append(f"  {field} = {{{_escape(_protect(source.venue))}}},")
    if source.year:
        lines.append(f"  year = {{{source.year}}},")
    if source.volume:
        lines.append(f"  volume = {{{_escape(source.volume)}}},")
    if source.number:
        lines.append(f"  number = {{{_escape(source.number)}}},")
    if source.pages:
        lines.append(f"  pages = {{{_escape(source.pages.replace('–', '--'))}}},")
    if source.publisher:
        lines.append(f"  publisher = {{{_escape(source.publisher)}}},")
    if source.doi:
        lines.append(f"  doi = {{{_escape(source.doi)}}},")
    if source.url:
        lines.append(f"  url = {{{_escape(source.url)}}},")
    if source.abstract:
        lines.append(f"  abstract = {{{_escape(source.abstract[:2000])}}},")
    if source.language:
        lines.append(f"  language = {{{_escape(source.language)}}},")
    lines.append(
        f"  note = {{{_escape('Проверен: ' + source.verified_via + ' ' + source.verified_at) if source.verified else _escape('НЕ ПРОВЕРЕН')}}},"
    )
    lines.append("}")
    return "\n".join(lines)


def bib_type(source: Source) -> str:
    inverse = {v: k for k, v in TYPE_MAP.items()}
    return inverse.get(source.type, "misc")


def write_bibtex(sources: list[Source], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "% Библиография сформирована системой автоматизации подготовки "
        "курсовых и дипломных работ.\n"
        "% Все записи проходят проверку DOI (см. поле note).\n\n"
    )
    path.write_text(
        header + "\n\n".join(to_bibtex(s) for s in sources) + "\n", encoding="utf-8"
    )
    return path


# --------------------------------------------------------------------------- #
# Импорт
# --------------------------------------------------------------------------- #


def _strip_value(raw: str) -> str:
    raw = raw.strip()
    if (raw.startswith("{") and raw.endswith("}")) or (raw.startswith('"') and raw.endswith('"')):
        raw = raw[1:-1]
    raw = raw.replace("\\&", "&").replace("\\%", "%").replace("\\$", "$")
    raw = raw.replace("\\_", "_").replace("\\#", "#").replace("\\{", "{").replace("\\}", "}")
    raw = raw.replace("--", "–")
    return re.sub(r"\s+", " ", raw).strip()


def parse_authors(raw: str) -> list[Author]:
    out: list[Author] = []
    for part in re.split(r"\band\b", raw):
        part = part.strip()
        if not part:
            continue
        if "," in part:
            family, given = part.split(",", 1)
        else:
            pieces = part.split()
            family, given = (pieces[-1], " ".join(pieces[:-1]))
        out.append(Author(family=_strip_value(family), given=_strip_value(given)))
    return out


def parse_bibtex(text: str) -> list[Source]:
    """Минималистичный разбор BibTeX (достаточен для типичных записей)."""
    sources: list[Source] = []
    for match in _ENTRY_RE.finditer(text):
        start = match.end()
        depth = 1
        i = start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start : i - 1]
        fields = {m.group("name").lower(): _strip_value(m.group("val")) for m in _FIELD_RE.finditer(body)}
        key = match.group("key").strip()
        title = fields.get("title", "")
        if not title:
            continue
        authors = parse_authors(fields.get("author", ""))
        year = None
        if fields.get("year") and re.search(r"\d{4}", fields["year"]):
            year = int(re.search(r"\d{4}", fields["year"]).group(0))
        doi = fields.get("doi") or ""
        if doi.lower().startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/") :]
        sources.append(
            Source(
                key=key,
                title=title,
                authors=authors,
                year=year,
                venue=fields.get("journal") or fields.get("booktitle") or "",
                volume=fields.get("volume", ""),
                number=fields.get("number", ""),
                pages=fields.get("pages", ""),
                publisher=fields.get("publisher", ""),
                doi=doi or None,
                url=fields.get("url", ""),
                type=TYPE_MAP.get(match.group("type").lower(), "article-journal"),
                provider="user-bibtex",
                abstract=fields.get("abstract", ""),
            )
        )
    return sources


def read_bibtex(path: Path) -> list[Source]:
    return parse_bibtex(Path(path).read_text(encoding="utf-8", errors="replace"))
