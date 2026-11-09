"""Сборка исходного текста (Markdown/QMD) и разрешение ссылок.

Результат работы модуля — единый markdown, из которого одинаково
воспроизводимо получаются DOCX и PDF. Ссылки ``[@key]`` превращаются в
номера вида ``[3]`` в порядке первого упоминания, а список литературы
формируется средствами :mod:`diploma.sources.gost` (ГОСТ Р 7.0.5-2008).
"""

from __future__ import annotations

import re
from datetime import date

from ..model import Document, Figure, Table
from ..sources.gost import format_reference

# Ключ цитирования может содержать кириллицу (например, [@иванов2020])
CITE_RE = re.compile(r"\[((?:@[^\s;,\]]+)(?:\s*;\s*@[^\s;,\]]+)*)([^\]]*)\]")


def yaml_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def front_matter(doc: "Document", settings) -> str:
    meta = doc.metadata
    lines = [
        "---",
        f'title: "{yaml_escape(meta.get("title", doc.topic.title))}"',
        f'author: "{yaml_escape(meta.get("author", settings.author))}"',
        f'date: "{meta.get("year", date.today().year)}"',
        f'lang: {settings.language}',
        "lang-ru: true",
        f'bibliography: "{meta.get("bibfile", "references.bib")}"',
        f'csl: "{meta.get("cslfile", "assets/gost.csl")}"',
        "link-citations: true",
        "fontsize: 14pt",
        "geometry:",
        '  - "a4paper"',
        '  - "left=30mm"',
        '  - "right=15mm"',
        '  - "top=20mm"',
        '  - "bottom=20mm"',
        "linestretch: 1.5",
        "toc: true",
        "toc-depth: 2",
        "numbersections: false",
        "---",
        "",
    ]
    return "\n".join(lines)


def title_page_markdown(doc: "Document", settings) -> str:
    meta = doc.metadata
    rows = [
        ("Выполнил", f'{meta.get("author", settings.author)}'
         + (f', {meta.get("group", settings.group)}' if meta.get("group", settings.group) else "")),
        ("Научный руководитель", meta.get("supervisor", settings.supervisor) or "—"),
    ]
    lines = ["```{=openxml}", "<w:p/>", "```", ""]  # страница начинается чистой
    lines.append(f'::: {{.titlepage data-worktype="{settings.work_type_ru}"}}')
    lines.append("")
    for key, value in [
        ("institution", meta.get("institution", settings.institution)),
        ("faculty", meta.get("faculty", "")),
        ("chair", meta.get("chair", settings.chair)),
    ]:
        if value:
            lines.append(f"**{value}**")
            lines.append("")
    lines.append(f'**{settings.work_type_ru.upper()}**')
    lines.append("")
    lines.append(f'**Тема работы:** «{meta.get("title", doc.topic.title)}»')
    lines.append("")
    lines.append("| | |")
    lines.append("| --- | --- |")
    for k, v in rows:
        lines.append(f"| **{k}** | {v} |")
    lines.append("")
    city = meta.get("city", settings.city) or ""
    year = meta.get("year", date.today().year)
    lines.append(f"{city} — {year}" if city else str(year))
    lines.append("")
    lines.append(":::")
    lines.append("")
    return "\n".join(lines)


def figure_markdown(figure: Figure, style: str = "gost") -> str:
    """Рисунок: изображение + подпись с номером (шаг 6)."""
    caption = figure.caption_full(style=style)
    return f"![]({figure.path}){{#fig-{figure.key} width=90%}}\n\n{caption}\n"


def table_markdown(table: Table, style: str = "gost") -> str:
    def cell(value: str) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    header = "| " + " | ".join(cell(h) for h in table.headers) + " |"
    sep = "| " + " | ".join("---" for _ in table.headers) + " |"
    rows = ["| " + " | ".join(cell(c) for c in row) + " |" for row in table.rows]
    caption = table.caption_full(style=style)
    return "\n".join([header, sep, *rows, "", caption, ""])


def heading_markdown(text: str, level: int) -> str:
    return f"{'#' * level} {text}\n"


# --------------------------------------------------------------------------- #
# Разрешение ссылок
# --------------------------------------------------------------------------- #


def resolve_citations(
    markdown: str, sources: list, style: str = "gost", access_date: str = ""
) -> tuple[str, list, dict[str, int]]:
    """Заменяет ``[@key]`` на номера и возвращает порядок цитирования.

    Возвращает ``(текст, список литературы в порядке ссылок, key → номер)``.
    """
    by_key = {s.key: s for s in sources}
    order: dict[str, int] = {}

    def repl(match: "re.Match[str]") -> str:
        keys = [k.strip()[1:] for k in match.group(1).split(";")]
        suffix = match.group(2).strip()
        nums: list[int] = []
        for key in keys:
            if key not in by_key:
                continue
            if key not in order:
                order[key] = len(order) + 1
            nums.append(order[key])
        if not nums:
            return f"[ТРЕБУЕТСЯ ИСТОЧНИК: {match.group(1)}]"
        text = ", ".join(str(n) for n in sorted(set(nums)))
        if suffix:
            text = f"{text}, {suffix.lstrip(',; ')}"
        return f"[{text}]"

    resolved = CITE_RE.sub(repl, markdown)
    cited = [by_key[k] for k, _ in sorted(order.items(), key=lambda kv: kv[1])]
    rest = [s for s in sources if s.key not in order]
    rest.sort(key=lambda s: (s.authors[0].family.lower() if s.authors else "", s.year or 0))
    bibliography = [
        f"{i}. {format_reference(s, style=style, access_date=access_date)}"
        for i, s in enumerate(cited + rest, start=1)
    ]
    return resolved, bibliography, order


def bibliography_markdown(bibliography: list[str], title: str = "Список использованных источников") -> str:
    """Список литературы. Заголовок добавляется, только если раздел не создан планом."""
    lines: list[str] = []
    if title:
        lines += [f"# {title}", ""]
    lines += bibliography
    lines.append("")
    return "\n".join(lines)
