"""Сборка итоговых файлов: DOCX, PDF, HTML, BibTeX, экспорт Quarto (шаг 8)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ..model import Document
from ..sources.bibtex import write_bibtex
from . import pandoc_utils
from .markdown import (
    bibliography_markdown,
    figure_markdown,
    front_matter,
    heading_markdown,
    resolve_citations,
    table_markdown,
    title_page_markdown,
)
from .pdf import render_pdf

WEB_CSS = """
:root { color-scheme: light; }
body {
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  max-width: 46rem; margin: 2rem auto; padding: 0 1.5rem;
  line-height: 1.6; color: #14202e;
}
h1, h2, h3 { color: #10233a; line-height: 1.3; }
h1 { text-align: center; margin-top: 2.5rem; font-size: 1.6rem; }
h2 { font-size: 1.2rem; margin-top: 1.8rem; }
p { text-align: justify; }
img { max-width: 100%; display: block; margin: 1rem auto; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.92rem; }
th, td { border: 1px solid #c8d3e0; padding: 0.4rem 0.6rem; text-align: left; }
th { background: #eaf1f8; }
#TOC { background: #f7f9fc; border: 1px solid #e2e8f0; padding: 1rem 1.5rem; border-radius: 8px; }
code { background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; }
"""


@dataclass
class RenderResult:
    files: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #


def assemble_markdown(doc: Document, registry, st) -> str:
    """Собирает тело документа (без титульного листа — его добавляет рендерер)."""
    md = doc.sections_md
    parts: list[str] = []
    style = st.bib_style
    body_sections = [s for s in doc.plan.sections if s.kind == "body"]

    for sec in doc.plan.sections:
        if sec.kind == "body":
            idx = body_sections.index(sec) + 1
            parts.append(heading_markdown(f"Глава {idx}. {sec.title}", 1))
            label = str(idx)
        else:
            parts.append(heading_markdown(sec.title, 1))
            label = ""
        if sec.id in md and md[sec.id].strip() and md[sec.id] != "{{BIBLIOGRAPHY}}":
            parts.append(md[sec.id].strip() + "\n")
        for j, child in enumerate(sec.children, start=1):
            prefix = f"{label}.{j} " if label else ""
            parts.append(heading_markdown(prefix + child.title, 2))
            if child.id in md and md[child.id].strip():
                parts.append(md[child.id].strip() + "\n")
            # рисунки и таблицы раздела
            for fig in [f for f in doc.figures if f.section_id == child.id]:
                parts.append(figure_markdown(fig, style=style))
            for tbl in [t for t in doc.tables if t.section_id == child.id]:
                parts.append(table_markdown(tbl, style=style))
        if sec.id == "refs":
            parts.append("{{BIBLIOGRAPHY}}\n")
    return "\n".join(parts)


def appendices(doc: Document, st) -> str:
    parts = [heading_markdown("Приложение А. Протокол проверки источников", 1)]
    parts.append(
        "В таблице приведены результаты автоматической проверки всех источников, "
        "найденных по теме. В текст работы включены только источники, прошедшие "
        "проверку (статус «проверен»)."
    )
    if doc.sources:
        rows = ["| Источник | DOI | Проверка | Способ |", "| --- | --- | --- | --- |"]
        for s in doc.sources:
            rows.append(
                f"| {_short(str(s.authors_ru) + ' (' + str(s.year) + ')', 48)} | "
                f"{s.doi or '—'} | проверен | {s.verified_via or '—'} |"
            )
        parts.append("\n".join(rows) + "\n")
    else:
        parts.append("Проверенных источников не найдено.\n")

    parts.append(heading_markdown("Приложение Б. Данные, использованные для построения графиков", 1))
    parts.append(
        "Все графики построены по файлам каталога `data/`. Происхождение каждого "
        "набора данных указано в подписи соответствующего рисунка: реальные данные "
        "сопровождаются ссылками на источники, учебные примеры помечены явно."
    )
    rows = ["| Рисунок | Набор данных | Происхождение |", "| --- | --- | --- |"]
    provenance_ru = {"real": "реальные данные", "synthetic": "учебный пример (модель)", "diagram": "схема (без данных)"}
    for fig in doc.figures:
        rows.append(
            f"| рис. {fig.number} | `{fig.dataset_key or '—'}` | {provenance_ru.get(fig.provenance, fig.provenance)} |"
        )
    parts.append("\n".join(rows) + "\n")
    return "\n".join(parts)


def _short(text: str, n: int) -> str:
    text = str(text).replace("|", "\\|")
    return text if len(text) <= n else text[: n - 1] + "…"


# --------------------------------------------------------------------------- #
# Рендерер
# --------------------------------------------------------------------------- #


def render_all(doc: Document, registry, st, out_dir: Path) -> RenderResult:
    out_dir = Path(out_dir).resolve()
    result = RenderResult()
    access_date = date.today().strftime("%d.%m.%Y")

    body = assemble_markdown(doc, registry, st)
    body = registry.resolve(body)
    body = "\n".join(
        (registry.resolve(line) if "{{ref:" in line or "{{Ref:" in line else line)
        for line in (body + "\n" + appendices(doc, st)).splitlines()
    )
    bib_md = ""
    body_resolved, bibliography, _order = resolve_citations(
        body, doc.sources, style=st.bib_style, access_date=access_date
    )
    bib_md = bibliography_markdown(bibliography, title="")
    body_resolved = body_resolved.replace("{{BIBLIOGRAPHY}}", bib_md)

    # Канонический markdown со ссылками Pandoc (для Quarto)
    canonical = front_matter(doc, st) + body.replace("{{BIBLIOGRAPHY}}", "")
    (out_dir / "document.md").write_text(canonical, encoding="utf-8")
    result.files["Markdown"] = str(out_dir / "document.md")

    rendered_md = body_resolved
    (out_dir / "document.rendered.md").write_text(rendered_md, encoding="utf-8")

    # --- BibTeX ---
    bib_path = write_bibtex(doc.sources, out_dir / "references.bib")
    result.files["BibTeX"] = str(bib_path)

    # --- DOCX ---
    try:
        from .docx import render_docx

        docx_md = title_page_markdown(doc, st) + "\n" + rendered_md
        docx_path = render_docx(
            docx_md,
            out_dir / "document.docx",
            base_dir=out_dir,
            toc=True,
            font_size=st.font_size_pt,
            line_spacing=st.line_spacing,
        )
        result.files["DOCX"] = str(docx_path)
    except Exception as exc:  # DOCX критичен, но сборка не должна падать целиком
        result.warnings.append(f"DOCX не собран: {exc}")

    # --- PDF ---
    pdf_path = out_dir / "document.pdf"
    pdf_engine_used = _choose_pdf_engine(st)
    try:
        if pdf_engine_used == "latex":
            _render_pdf_latex(rendered_md, pdf_path, doc, st, out_dir)
        else:
            render_pdf(
                rendered_md,
                pdf_path,
                meta=doc.metadata,
                base_dir=out_dir,
                font_size=st.font_size_pt,
                line_spacing=st.line_spacing,
                work_type_ru=st.work_type_ru,
            )
        result.files["PDF"] = str(pdf_path)
    except Exception as exc:
        result.warnings.append(f"PDF ({pdf_engine_used}) не собран: {exc}")
        if pdf_engine_used == "latex":
            try:
                render_pdf(
                    rendered_md,
                    pdf_path,
                    meta=doc.metadata,
                    base_dir=out_dir,
                    font_size=st.font_size_pt,
                    line_spacing=st.line_spacing,
                    work_type_ru=st.work_type_ru,
                )
                result.files["PDF"] = str(pdf_path)
                result.warnings.append("PDF собран встроенным рендерером (fallback).")
            except Exception as exc2:
                result.warnings.append(f"PDF не собран и резервным рендерером: {exc2}")

    # --- HTML (предпросмотр) ---
    try:
        html_path = out_dir / "document.html"
        css_path = out_dir / "assets" / "web.css"
        css_path.parent.mkdir(parents=True, exist_ok=True)
        css_path.write_text(WEB_CSS, encoding="utf-8")
        tmp_html_md = out_dir / "document.html.md"
        tmp_html_md.write_text(rendered_md, encoding="utf-8")
        pandoc_utils.convert_file(
            tmp_html_md,
            "html",
            html_path,
            [
                "--standalone",
                "--toc",
                "--toc-depth=2",
                "--embed-resources",
                "--css",
                str(css_path),
                "--metadata",
                f"title={doc.metadata.get('title', '')}",
            ],
            cwd=out_dir,
        )
        tmp_html_md.unlink(missing_ok=True)
        result.files["HTML"] = str(html_path)
    except Exception as exc:
        result.warnings.append(f"HTML-предпросмотр не собран: {exc}")

    # --- JSON с данными документа ---
    (out_dir / "document.json").write_text(doc.to_json(), encoding="utf-8")

    # --- Экспорт Quarto ---
    if st.export_quarto:
        try:
            from .quarto import export_quarto_project

            qdir = export_quarto_project(
                canonical,
                out_dir / "quarto",
                doc.sources,
                media_dir=out_dir / "media",
                title=doc.metadata.get("title", ""),
                csl_source=Path(__file__).resolve().parents[1] / "assets" / "gost.csl",
            )
            for csv in (out_dir / "data").glob("*.csv"):
                shutil.copy(csv, qdir / "data" / csv.name)
            result.files["Quarto"] = str(qdir)
        except Exception as exc:
            result.warnings.append(f"Экспорт Quarto не выполнен: {exc}")

    return result


def _choose_pdf_engine(st) -> str:
    """auto → LaTeX, если он есть; иначе встроенный рендерер."""
    from ..settings import has_latex

    if st.pdf_engine == "builtin":
        return "builtin"
    if st.pdf_engine == "latex":
        return "latex"
    return "latex" if has_latex() else "builtin"


def _render_pdf_latex(markdown: str, output: Path, doc: Document, st, out_dir: Path) -> Path:
    """Pandoc → LaTeX → PDF (используется при наличии XeLaTeX/PDFLaTeX/Tectonic)."""
    from ..settings import has_latex  # локальный импорт избегает циклов
    import shutil

    engine_name = next(
        (x for x in ("xelatex", "lualatex", "tectonic", "pdflatex") if shutil.which(x)),
        "pdflatex",
    )
    args = [
        "--pdf-engine",
        engine_name,
        "--resource-path",
        str(out_dir),
        "-V",
        "lang=ru-RU",
        "-V",
        f"fontsize={st.font_size_pt}pt",
        "-V",
        f"linestretch={st.line_spacing}",
        "-V",
        "geometry:a4paper",
        "-V",
        "geometry:left=30mm",
        "-V",
        "geometry:right=15mm",
        "-V",
        "geometry:top=20mm",
        "-V",
        "geometry:bottom=20mm",
    ]
    if engine_name == "pdflatex":
        args += ["-V", "fontenc=T2A", "-V", "babel-lang=russian"]
    else:
        args += ["-V", "mainfont=DejaVu Serif", "-V", "sansfont=DejaVu Sans", "-V", "monofont=DejaVu Sans Mono"]
    pandoc_utils.convert_file(markdown, "pdf", output, args, cwd=out_dir)
    return output
