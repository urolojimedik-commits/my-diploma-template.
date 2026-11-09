"""Экспорт медицинской работы в PDF (встроенный движок на ReportLab).

Почему не LaTeX/Quarto: в песочнице нет TeX Live, Quarto и LibreOffice
(проверено: `pdflatex`, `xelatex`, `tectonic`, `quarto` отсутствуют, системные
шрифты и Pango/Cairo недоступны). Поэтому PDF строится напрямую:

* движок — ReportLab (platypus);
* шрифт — DejaVu Serif из комплекта matplotlib: **единственный** доступный
  TTF, покрывающий специфические буквы таджикского алфавита
  (Ғ Ӣ Қ Ӯ Ҳ Ҷ ғ ӣ қ ӯ ҳ ҷ) — проверено, пропущенных глифов нет;
* параметры страницы, шрифта, интервалов и полей берутся из
  ``config/university.yml`` — те же, что и для Word.

Номера глав, рисунков и таблиц в PDF вычисляются и печатаются как текст:
в PDF полей Word нет, но они совпадают с номерами в DOCX, потому что считаются
одной и той же функцией ``content.assign_numbers()``.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from ..lang import get_language
from ..structure.medical import get_profile
from .content import (
    AbbrevBlock,
    Appendix,
    Bullets,
    FigureBlock,
    Heading,
    MedicalDocument,
    PageBreak as PageBreakBlock,
    Para,
    RefList,
    TableBlock,
    TitlePage,
    TOC,
    assign_numbers,
    split_inline,
)

# --------------------------------------------------------------------------- #
# Шрифты
# --------------------------------------------------------------------------- #

_FONT_DIRS = [
    Path(os.path.dirname(__import__("matplotlib").__file__)) / "mpl-data" / "fonts" / "ttf",
    Path("/usr/share/fonts/truetype/dejavu"),
]

FONTS = {
    "DejaVuSerif": "DejaVuSerif.ttf",
    "DejaVuSerif-Bold": "DejaVuSerif-Bold.ttf",
    "DejaVuSerif-Italic": "DejaVuSerif-Italic.ttf",
    "DejaVuSans": "DejaVuSans.ttf",
}
_REGISTERED = False


def register_fonts() -> bool:
    """Регистрирует DejaVu в ReportLab. Возвращает False, если шрифтов нет."""
    global _REGISTERED
    if _REGISTERED:
        return True
    ok = False
    for directory in _FONT_DIRS:
        if not directory.exists():
            continue
        found = True
        for name, filename in FONTS.items():
            path = directory / filename
            if not path.exists():
                found = False
                break
        if not found:
            continue
        for name, filename in FONTS.items():
            pdfmetrics.registerFont(TTFont(name, str(directory / filename)))
        from reportlab.lib.fonts import addMapping

        for family, bold, italic, name in (
            ("DejaVuSerif", 0, 0, "DejaVuSerif"),
            ("DejaVuSerif", 1, 0, "DejaVuSerif-Bold"),
            ("DejaVuSerif", 0, 1, "DejaVuSerif-Italic"),
        ):
            addMapping(family, bold, italic, name)
        ok = True
        break
    _REGISTERED = ok
    return ok


# --------------------------------------------------------------------------- #
# Сборщик
# --------------------------------------------------------------------------- #


class MedicalPdfBuilder:
    """Собирает PDF из модели ``MedicalDocument``."""

    def __init__(
        self,
        doc: MedicalDocument,
        profile=None,
        lang_code: str | None = None,
        citation_map: dict[str, int] | None = None,
    ) -> None:
        self.doc = doc
        self.profile = profile or get_profile()
        self.lang = get_language(lang_code or self.profile.main_language)
        self.citation_map = citation_map or {}
        self.numbers = assign_numbers(doc, self.citation_map)
        self.layout = self.profile.layout or {}
        font_cfg = self.layout.get("font") or {}
        self.size = float(font_cfg.get("size_pt", 14))
        self.caption_size = float(font_cfg.get("caption_size_pt", 12))
        self.table_size = float(font_cfg.get("table_size_pt", 11))
        self.spacing = float(font_cfg.get("line_spacing", 1.5))
        self.indent = float(self.layout.get("first_line_indent_cm", 1.25)) * cm
        self.numbering_mode = getattr(doc, "numbering", None) or (
            (self.profile.gost or {}).get("numbering", "per_chapter")
        )
        m = self.layout.get("margins_mm") or {"left": 30, "right": 15, "top": 20, "bottom": 20}
        self.margins = {k: float(v) / 10 * cm for k, v in m.items()}
        self.family = "DejaVuSerif" if register_fonts() else "Times-Roman"
        self._chapter = 0
        self._section = 0
        self._styles = self._make_styles()

    # ----------------------------------------------------------------- стили
    def _make_styles(self) -> dict:
        family = self.family
        body = ParagraphStyle(
            "Body", fontName=family, fontSize=self.size, leading=self.size * self.spacing,
            alignment=TA_JUSTIFY, firstLineIndent=self.indent, spaceAfter=0,
        )
        return {
            "body": body,
            "annotation": ParagraphStyle(
                "Annotation", parent=body, fontSize=self.size, spaceAfter=6),
            "note": ParagraphStyle(
                "Note", parent=body, fontSize=self.caption_size,
                firstLineIndent=0, alignment=TA_JUSTIFY, spaceAfter=6),
            "centered": ParagraphStyle(
                "Centered", parent=body, firstLineIndent=0, alignment=TA_CENTER),
            "list": ParagraphStyle(
                "List", parent=body, firstLineIndent=0, leftIndent=self.indent,
                alignment=TA_LEFT),
            "caption": ParagraphStyle(
                "Caption", parent=body, fontSize=self.caption_size,
                firstLineIndent=0, alignment=TA_CENTER, spaceBefore=6, spaceAfter=6),
            "title": ParagraphStyle(
                "Title", parent=body, firstLineIndent=0, alignment=TA_CENTER, spaceAfter=6),
            "h1": ParagraphStyle(
                "H1", parent=body, fontName=f"{family}-Bold", firstLineIndent=0,
                alignment=TA_CENTER, spaceBefore=0, spaceAfter=12),
            "h2": ParagraphStyle(
                "H2", parent=body, fontName=f"{family}-Bold", alignment=TA_LEFT,
                spaceBefore=12, spaceAfter=6),
            "front": ParagraphStyle(
                "Front", parent=body, fontName=f"{family}-Bold", firstLineIndent=0,
                alignment=TA_CENTER, spaceBefore=0, spaceAfter=12),
            "ref": ParagraphStyle(
                "Ref", parent=body, firstLineIndent=-0.75 * cm, leftIndent=1.25 * cm,
                alignment=TA_JUSTIFY, leading=self.size * 1.2, spaceAfter=4),
        }

    # ------------------------------------------------------------------ сборка
    def build(self, out_path: Path | str) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        document = BaseDocTemplate(
            str(out_path),
            pagesize=A4,
            leftMargin=self.margins["left"],
            rightMargin=self.margins["right"],
            topMargin=self.margins["top"],
            bottomMargin=self.margins["bottom"],
            title=self.doc.meta.get("topic", "Кори курсӣ"),
            author=self.doc.meta.get("author", ""),
        )
        frame = Frame(
            document.leftMargin, document.bottomMargin, document.width, document.height, id="main"
        )
        page_cfg = self.layout.get("page_number") or {}
        start = 2 if page_cfg.get("start_after_title_page", True) else 1
        document.addPageTemplates(
            [
                PageTemplate(
                    id="main",
                    frames=[frame],
                    onPage=lambda canvas, doc: self._decorate(canvas, doc, start),
                )
            ]
        )

        story: list = []
        for block in self.doc.blocks:
            self._render(story, block)
        document.build(story)
        return out_path

    def _decorate(self, canvas, document, start: int) -> None:
        """Номер страницы внизу по центру; на титульном листе не печатается."""
        page = document.page
        if (self.layout.get("page_number") or {}).get("enabled", True) and page >= start:
            canvas.saveState()
            canvas.setFont(self.family, self.size)
            canvas.drawCentredString(
                A4[0] / 2, self.margins["bottom"] / 2, str(page)
            )
            canvas.restoreState()

    # ------------------------------------------------------------------ блоки
    def _render(self, story: list, block) -> None:
        if isinstance(block, TitlePage):
            self._title_page(story, block)
        elif isinstance(block, TOC):
            self._toc(story, block)
        elif isinstance(block, Heading):
            self._heading(story, block)
        elif isinstance(block, Para):
            style = {"annotation": "annotation", "note": "note"}.get(block.style, "body")
            story.append(self._para(block.text, style))
        elif isinstance(block, Bullets):
            for item in block.items:
                story.append(self._para("– " + item, "list"))
        elif isinstance(block, FigureBlock):
            self._figure(story, block)
        elif isinstance(block, TableBlock):
            self._table(story, block)
        elif isinstance(block, AbbrevBlock):
            self._abbrev(story, block)
        elif isinstance(block, RefList):
            self._refs(story, block)
        elif isinstance(block, Appendix):
            self._appendix(story, block)
        elif isinstance(block, PageBreakBlock):
            story.append(PageBreak())

    def _para(self, text: str, style: str = "body") -> Paragraph:
        return Paragraph(self._inline(text), self._styles[style])

    def _inline(self, text: str) -> str:
        out = []
        for kind, key, raw in split_inline(text or ""):
            if kind == "text":
                out.append(self._esc(raw))
            elif kind == "src":
                num = self.citation_map.get(key)
                out.append(f"[{num if num else '?'}]")
            else:
                cached = self.numbers.get(f"{kind}:{key}")
                if cached is None:
                    out.append(f"<i>{self.lang.missing_data()}</i>")
                    continue
                noun = self.lang.t("figure_ref" if kind == "fig" else "table_ref")
                out.append(f"{noun}&nbsp;{cached}")
        return "".join(out)

    @staticmethod
    def _esc(text: str) -> str:
        return (
            (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    # -------------------------------------------------------------- титульный
    def _title_page(self, story: list, block: TitlePage) -> None:
        uni = self.profile.university or {}
        tg = self.lang

        def line(text: str, bold: bool = False, italic: bool = False, size: float | None = None):
            style = ParagraphStyle(
                "T", parent=self._styles["title"], fontSize=size or self.size,
                fontName=self.family + ("-Bold" if bold else ""),
                alignment=TA_CENTER, spaceAfter=6,
            )
            tag = ""
            if italic:
                tag = "<i>"
            story.append(Paragraph(f"{tag}{self._esc(text)}{'</i>' if italic else ''}", style))

        line(str(uni.get("ministry", "")))
        line(str(uni.get("name", "")), bold=True)
        if uni.get("faculty"):
            line(str(uni["faculty"]))
        line(str(block.chair or uni.get("chair", "")))
        story.append(Spacer(1, 1.2 * cm))
        line(tg.t("work_type_diploma") if block.work_type == "diploma"
             else tg.t("work_type_course"), bold=True)
        story.append(Spacer(1, 0.6 * cm))
        if block.topic:
            line(f"{tg.t('topic')}: {block.topic}", bold=True)
        if block.topic_ru:
            line(block.topic_ru, italic=True, size=self.size - 1)
        story.append(Spacer(1, 2 * cm))

        role_style = ParagraphStyle(
            "Role", parent=self._styles["body"], firstLineIndent=0, leftIndent=2 * cm,
            spaceAfter=2)
        sign_style = ParagraphStyle(
            "Sign", parent=role_style, fontSize=9, textColor=colors.HexColor("#444444"),
            spaceAfter=12)

        def role(label: str, value: str) -> None:
            story.append(Paragraph(f"{self._esc(label)}: {self._esc(value or '_' * 24)}", role_style))
            story.append(Paragraph("(имзо)" + " " * 12 + "(насаб, ном, номи падар)", sign_style))

        role(tg.t("performed_by"), block.author)
        role(tg.t("supervisor"), block.supervisor)
        if block.reviewer:
            role(tg.t("reviewer"), block.reviewer)
        if block.head_of_chair:
            role(tg.t("head_of_chair"), block.head_of_chair)
        story.append(Spacer(1, 2 * cm))
        line(f"{block.city or uni.get('city', '')} — {block.year}", bold=True)
        story.append(PageBreak())

    # ------------------------------------------------------------- содержание
    def _toc(self, story: list, block: TOC) -> None:
        story.append(Paragraph(self._esc(block.title), self._styles["front"]))
        lines = []
        for b in self.doc.blocks:
            if isinstance(b, Heading) and b.numbered:
                lines.append(("     " if b.level == 2 else "") + b.text)
        body = "<br/>".join(self._esc(t) for t in lines)
        story.append(Paragraph(body, self._styles["body"]))
        story.append(PageBreak())

    # ---------------------------------------------------------------- разделы
    def _heading(self, story: list, block: Heading) -> None:
        if not block.numbered:
            story.append(Paragraph(self._esc(block.text), self._styles["front"]))
            return
        if block.level == 1:
            self._chapter += 1
            self._section = 0
            text = f"{self.lang.t('chapter_gen')} {self._chapter}. {block.text}"
            story.append(Paragraph(self._esc(text), self._styles["h1"]))
        else:
            self._section += 1
            text = f"{self._chapter}.{self._section}. {block.text}"
            story.append(Paragraph(self._esc(text), self._styles["h2"]))

    # --------------------------------------------------------------- рисунок
    def _figure(self, story: list, block: FigureBlock) -> None:
        path = Path(block.path)
        if path.exists():
            try:
                img = Image(str(path))
                max_width = A4[0] - self.margins["left"] - self.margins["right"]
                if img.imageWidth > max_width:
                    ratio = max_width / img.imageWidth
                    img.drawWidth = max_width
                    img.drawHeight = img.imageHeight * ratio
                story.append(img)
                story.append(Spacer(1, 0.2 * cm))
            except Exception:
                story.append(self._para(f"[{self.lang.missing_data()}: {path.name}]", "note"))
        else:
            story.append(self._para(f"[{self.lang.missing_data()}: {path.name}]", "note"))

        cached = self.numbers.get(f"fig:{block.key}", "1")
        caption = f"{self.lang.t('figure')} {cached} — {block.caption.rstrip('.')}"
        story.append(Paragraph(self._esc(caption), self._styles["caption"]))
        note = self._provenance_note(block.provenance, block.source_note)
        if note:
            story.append(Paragraph(f"<i>{self._esc(note)}</i>", self._styles["note"]))

    def _provenance_note(self, provenance: str, source_note: str) -> str:
        bits = []
        if provenance == "synthetic":
            bits.append(self.lang.teaching_example())
        elif provenance == "unknown":
            bits.append(self.lang.missing_data())
        elif provenance == "own_data":
            bits.append(f"{self.lang.t('source')}: {self.lang.own_data_label()}")
        if source_note and provenance != "synthetic":
            bits.append(f"{self.lang.t('source')}: {source_note}")
        return ". ".join(bits)

    # ---------------------------------------------------------------- таблица
    def _table(self, story: list, block: TableBlock) -> None:
        def cell(text: str, bold: bool = False) -> Paragraph:
            style = ParagraphStyle(
                "Cell", fontName=self.family + ("-Bold" if bold else ""),
                fontSize=self.table_size, leading=self.table_size * 1.2,
                alignment=TA_CENTER, spaceAfter=0)
            return Paragraph(self._esc(str(text)), style)

        data = [[cell(c, bold=True) for c in block.header]]
        data += [[cell(v) for v in row] for row in block.rows]
        table = Table(data, hAlign="CENTER", repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.black),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        block_elements = []
        if block.caption:
            cached = self.numbers.get(f"tbl:{block.key}", "1")
            caption = f"{self.lang.t('table')} {cached} — {block.caption.rstrip('.')}"
            block_elements.append(
                Paragraph(self._esc(caption),
                          ParagraphStyle("Cap2", parent=self._styles["note"],
                                         alignment=TA_LEFT, spaceBefore=6))
            )
        block_elements.append(table)
        extra = ". ".join(
            [x for x in (block.note, self._provenance_note(block.provenance, block.source_note)) if x]
        )
        if extra:
            block_elements.append(Paragraph(f"<i>{self._esc(extra)}</i>", self._styles["note"]))
        block_elements.append(Spacer(1, 0.3 * cm))
        story.append(KeepTogether(block_elements))

    # -------------------------------------------------------------- сокращения
    def _abbrev(self, story: list, block: AbbrevBlock) -> None:
        story.append(Paragraph(self._esc(block.title), self._styles["front"]))
        style = ParagraphStyle("Ab", parent=self._styles["body"], firstLineIndent=0, spaceAfter=2)
        for abbr, expansion in block.pairs:
            story.append(Paragraph(f"{self._esc(abbr)} — {self._esc(expansion)}", style))
        story.append(Spacer(1, 0.4 * cm))

    # --------------------------------------------------------------- адабиёт
    def _refs(self, story: list, block: RefList) -> None:
        import re

        story.append(Paragraph(self._esc(block.title), self._styles["front"]))
        for i, entry in enumerate(block.entries, start=1):
            text = re.sub(r"^\s*\d+\.\s*", "", entry)
            story.append(Paragraph(f"{i}. {self._esc(text)}", self._styles["ref"]))

    # --------------------------------------------------------------- замимаҳо
    def _appendix(self, story: list, block: Appendix) -> None:
        story.append(Paragraph(
            f"{self._esc(self.lang.t('appendix_gen'))} {self._esc(block.letter or 'А')}. "
            f"{self._esc(block.title)}",
            self._styles["front"],
        ))
        for sub in block.blocks:
            self._render(story, sub)


def build_pdf(
    doc: MedicalDocument,
    out_path: Path | str,
    profile=None,
    citation_map: dict[str, int] | None = None,
    lang_code: str | None = None,
) -> Path:
    """Точка входа: собрать PDF из модели документа."""
    return MedicalPdfBuilder(doc, profile=profile, citation_map=citation_map,
                             lang_code=lang_code).build(out_path)
