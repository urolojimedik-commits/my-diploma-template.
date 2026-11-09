"""Сборка Word-документа медицинской работы на таджикском по ГОСТ.

Отличия от прежнего конвейера (``render/docx.py``, работающего через Pandoc
и эталонный документ): документ строится напрямую через python-docx, потому что

1. нужны **поля Word** (``SEQ``, ``TOC``, ``PAGE``) — автоматическая нумерация
   глав, рисунков, таблиц и перекрёстных ссылок; Pandoc их не создаёт;
2. титульный лист оформляется по реквизитам конкретного университета из
   ``config/university.yml``;
3. текст таджикский, а параметры шрифта, интервалов и отступов берутся из
   того же файла конфигурации, а не «зашиты» в код.

Правило системы сохранено и здесь: **никаких выдуманных данных.** Рисунок с
происхождением ``synthetic`` получает пометку «учебный пример», ``unknown`` —
«Маълумот нокифоя», ссылка на неизвестный источник — «[?]».
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document as DocxDocument
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from ..lang import get_language
from ..lang.ortho import get_orthography
from ..structure.medical import get_profile
from . import numbering as num
from .content import (
    AbbrevBlock,
    Appendix,
    Bullets,
    FigureBlock,
    Heading,
    MedicalDocument,
    PageBreak,
    Para,
    RefList,
    TableBlock,
    TitlePage,
    TOC,
    assign_numbers,
    split_inline,
)

# Названия стилей, создаваемых в документе
STYLE = {
    "body": "TgBody",
    "annotation": "TgAnnotation",
    "note": "TgNote",
    "centered": "TgCentered",
    "list": "TgList",
    "caption": "TgCaption",
    "table": "TgTable",
    "title": "TgTitle",
    "abbrev": "TgAbbrev",
    "ref": "TgRef",
    "front": "TgFrontTitle",  # ненумеруемый раздел (входит в содержание)
}

WORK_TYPE_KEYS = {
    "course": "work_type_course",
    "diploma": "work_type_diploma",
    "master": "work_type_master",
}


# --------------------------------------------------------------------------- #
# Низкоуровневые помощники OOXML
# --------------------------------------------------------------------------- #


def _set_font(element, font: str, size: Pt, bold: bool = False, italic: bool = False):
    rPr = element.element.get_or_add_rPr()
    for tag, value in (("w:b", bold), ("w:i", italic)):
        el = rPr.find(qn(tag))
        if value and el is None:
            rPr.append(OxmlElement(tag))
        elif not value and el is not None:
            rPr.remove(el)
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), font)
    sz = rPr.find(qn("w:sz"))
    if sz is None:
        sz = OxmlElement("w:sz")
        rPr.append(sz)
    sz.set(qn("w:val"), str(int(size.pt * 2)))


def _set_lang(style, code: str = "tg-Cyrl-TJ") -> None:
    rPr = style.element.get_or_add_rPr()
    for tag in ("w:lang", "w:langCS", "w:langBidi"):
        el = rPr.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            rPr.append(el)
        el.set(qn("w:val"), code)


def _set_outline_level(style, level: int = 0) -> None:
    """Уровень структуры: чтобы раздел попадал в поле TOC.

    ``level``: 0 — уровень 1 (как Heading 1), 1 — уровень 2, 9 — не включать.
    """
    pPr = style.element.get_or_add_pPr()
    el = pPr.find(qn("w:outlineLvl"))
    if el is None:
        el = OxmlElement("w:outlineLvl")
        pPr.append(el)
    el.set(qn("w:val"), str(level))


def _para_spacing(style, line_spacing: float, before: float = 0, after: float = 0,
                  first_line_cm: float | None = None, left_cm: float | None = None,
                  align=None):
    pf = style.paragraph_format
    pf.line_spacing = line_spacing
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if first_line_cm is not None:
        pf.first_line_indent = Cm(first_line_cm)
    if left_cm is not None:
        pf.left_indent = Cm(left_cm)
    if align is not None:
        pf.alignment = align


def _cell_borders(cell, top: str = "nil", bottom: str = "nil",
                  left: str = "nil", right: str = "nil", size: int = 4) -> None:
    """Границы ячейки: по ГОСТ 7.32-2017 таблицы — только по горизонтали."""
    tcPr = cell._tc.get_or_add_tcPr()
    old = tcPr.find(qn("w:tcBorders"))
    if old is not None:
        tcPr.remove(old)
    borders = OxmlElement("w:tcBorders")
    for side, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), val)
        if val != "nil":
            el.set(qn("w:sz"), str(size))
            el.set(qn("w:color"), "000000")
        borders.append(el)
    tcPr.append(borders)


# --------------------------------------------------------------------------- #
# Сборщик документа
# --------------------------------------------------------------------------- #


class MedicalDocxBuilder:
    """Собирает .docx из модели ``MedicalDocument``."""

    def __init__(
        self,
        doc: MedicalDocument,
        profile=None,
        lang_code: str | None = None,
        citation_map: dict[str, int] | None = None,
        normalize_orthography: bool = True,
    ) -> None:
        self.doc = doc
        self.profile = profile or get_profile()
        self.lang = get_language(lang_code or self.profile.main_language)
        self.ortho = get_orthography() if normalize_orthography else None
        self.citation_map = citation_map or {}
        self.numbers = assign_numbers(doc, self.citation_map)
        self.layout = self.profile.layout or {}
        font_cfg = self.layout.get("font") or {}
        self.font = font_cfg.get("name", "Times New Roman")
        self.size = Pt(int(font_cfg.get("size_pt", 14)))
        self.caption_size = Pt(int(font_cfg.get("caption_size_pt", 12)))
        self.table_size = Pt(int(font_cfg.get("table_size_pt", 11)))
        self.spacing = float(font_cfg.get("line_spacing", 1.5))
        self.indent = float(self.layout.get("first_line_indent_cm", 1.25))
        # режим нумерации: из модели документа, иначе из config/university.yml
        self.numbering_mode = getattr(doc, "numbering", None) or (
            (self.profile.gost or {}).get("numbering", "per_chapter")
        )
        # «курсор» нумерации: текущий номер главы, параграфа и буква приложения
        self._chapter = 0
        self._section = 0
        self._appendix_letter = ""

    # ------------------------------------------------------------------ текст
    def _t(self, text: str) -> str:
        if not text:
            return text
        return self.ortho.normalize(text) if self.ortho else text

    def _style_run(self, paragraph, size: Pt | None = None, bold: bool = False,
                   italic: bool = False):
        for run in paragraph.runs:
            run.font.name = self.font
            run.font.size = size or self.size
            run.font.bold = bold
            run.font.italic = italic

    # --------------------------------------------------------------- создание
    def build(self, out_path: Path | str) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        document = DocxDocument()
        self._setup_page(document)
        self._setup_styles(document)

        for block in self.doc.blocks:
            self._render(document, block)

        document.save(str(out_path))
        return out_path

    # ------------------------------------------------------------- оформление
    def _margins(self) -> dict:
        return self.layout.get("margins_mm") or {"left": 30, "right": 15, "top": 20, "bottom": 20}

    def _apply_margins(self, section) -> None:
        m = self._margins()
        section.left_margin = Cm(float(m.get("left", 30)) / 10)
        section.right_margin = Cm(float(m.get("right", 15)) / 10)
        section.top_margin = Cm(float(m.get("top", 20)) / 10)
        section.bottom_margin = Cm(float(m.get("bottom", 20)) / 10)

    def _setup_page(self, document) -> None:
        for section in document.sections:
            if str(self.layout.get("page", "A4")).upper() == "A4":
                section.page_width = Cm(21)
                section.page_height = Cm(29.7)
            self._apply_margins(section)

    def _setup_styles(self, document) -> None:
        styles = document.styles
        normal = styles["Normal"]
        _set_font(normal, self.font, self.size)
        _set_lang(normal)
        _para_spacing(normal, self.spacing, first_line_cm=self.indent,
                      align=WD_ALIGN_PARAGRAPH.JUSTIFY)

        def add(name: str, size: Pt = None, bold: bool = False, italic: bool = False,
                spacing: float = None, first_line_cm: float | None = 0.0,
                left_cm: float | None = None, align=None, before: float = 0, after: float = 0,
                outline: int = 9):
            try:
                style = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            except Exception:  # стиль уже есть (повторная сборка одного документа)
                style = styles[name]
            style.base_style = normal
            _set_font(style, self.font, size or self.size, bold=bold, italic=italic)
            _set_lang(style)
            _set_outline_level(style, outline)
            _para_spacing(style, spacing or self.spacing, before=before, after=after,
                          first_line_cm=first_line_cm, left_cm=left_cm, align=align)
            return style

        add(STYLE["body"], first_line_cm=self.indent, after=0)
        add(STYLE["annotation"], first_line_cm=self.indent, after=6, size=Pt(12))
        add(STYLE["note"], size=self.caption_size, first_line_cm=0.0, after=6,
            align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        add(STYLE["centered"], first_line_cm=0.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        add(STYLE["list"], first_line_cm=0.0, left_cm=self.indent)
        add(STYLE["caption"], size=self.caption_size, first_line_cm=0.0,
            align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=6)
        add(STYLE["table"], size=self.table_size, first_line_cm=0.0,
            align=WD_ALIGN_PARAGRAPH.CENTER)
        add(STYLE["title"], first_line_cm=0.0, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
        add(STYLE["abbrev"], first_line_cm=0.0, after=0)
        add(STYLE["ref"], first_line_cm=0.0, left_cm=1.25, spacing=1.0, after=0)
        # ненумеруемые разделы: как заголовок 1-го уровня, но без номера
        add(STYLE["front"], first_line_cm=0.0, align=WD_ALIGN_PARAGRAPH.CENTER,
            before=0, after=12, bold=True, outline=0)

        h1 = styles["Heading 1"]
        h1.base_style = normal
        _set_font(h1, self.font, self.size, bold=True)
        _set_lang(h1)
        _para_spacing(h1, self.spacing, first_line_cm=0.0,
                      align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=12)
        h1.paragraph_format.page_break_before = bool(self.layout.get("chapter_new_page", True))
        h1.paragraph_format.keep_with_next = True

        h2 = styles["Heading 2"]
        h2.base_style = normal
        _set_font(h2, self.font, self.size, bold=True)
        _set_lang(h2)
        _para_spacing(h2, self.spacing, first_line_cm=self.indent,
                      align=WD_ALIGN_PARAGRAPH.LEFT, before=12, after=6)
        h2.paragraph_format.keep_with_next = True

    # ------------------------------------------------------------------ блоки
    def _render(self, document, block) -> None:
        if isinstance(block, TitlePage):
            self._title_page(document, block)
        elif isinstance(block, TOC):
            self._toc(document, block)
        elif isinstance(block, Heading):
            self._heading(document, block)
        elif isinstance(block, Para):
            self._para(document, block)
        elif isinstance(block, Bullets):
            self._bullets(document, block)
        elif isinstance(block, FigureBlock):
            self._figure(document, block)
        elif isinstance(block, TableBlock):
            self._table(document, block)
        elif isinstance(block, AbbrevBlock):
            self._abbrev(document, block)
        elif isinstance(block, RefList):
            self._refs(document, block)
        elif isinstance(block, Appendix):
            self._appendix(document, block)
        elif isinstance(block, PageBreak):
            document.add_page_break()

    # -------------------------------------------------------------- титульный
    def _title_page(self, document, block: TitlePage) -> None:
        uni = self.profile.university or {}
        tg = self.lang

        def line(text: str, bold: bool = False, italic: bool = False, after: int = 6):
            p = document.add_paragraph(style=STYLE["title"])
            p.paragraph_format.space_after = Pt(after)
            run = p.add_run(self._t(text))
            self._style_run(p, bold=bold, italic=italic)
            return run

        if block.frame:
            num.set_page_borders(document.sections[0])

        line(str(uni.get("ministry", "")))
        line(str(uni.get("name", "")), bold=True)
        if uni.get("faculty"):
            line(str(uni["faculty"]))
        line(str(block.chair or uni.get("chair", "")))
        document.add_paragraph()

        line(tg.t(WORK_TYPE_KEYS.get(block.work_type, "work_type_diploma")), bold=True)
        if block.topic:
            document.add_paragraph()
            p = document.add_paragraph(style=STYLE["title"])
            run = p.add_run(f"{tg.t('topic')}: ")
            run2 = p.add_run(self._t(block.topic))
            self._style_run(p, bold=True)
        if block.topic_ru:
            p = document.add_paragraph(style=STYLE["title"])
            p.add_run(self._t(block.topic_ru))
            self._style_run(p, italic=True)

        document.add_paragraph()
        document.add_paragraph()

        def role(label: str, value: str) -> None:
            p = document.add_paragraph(style=STYLE["abbrev"])
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.left_indent = Cm(2.0)
            p.add_run(f"{label}: ")
            p.add_run(self._t(value) if value else "_" * 24).underline = True
            self._style_run(p)
            sign = document.add_paragraph(style=STYLE["abbrev"])
            sign.paragraph_format.first_line_indent = Cm(0)
            sign.paragraph_format.left_indent = Cm(2.0)
            sign.paragraph_format.space_after = Pt(12)
            s = sign.add_run("(имзо)" + " " * 20 + "(насаб, ном, номи падар)")
            s.font.size = Pt(10)
            s.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

        role(tg.t("performed_by"), block.author)
        role(tg.t("supervisor"), block.supervisor)
        if block.reviewer:
            role(tg.t("reviewer"), block.reviewer)
        if block.consultant:
            role("Мушовир", block.consultant)
        if block.head_of_chair:
            role(tg.t("head_of_chair"), block.head_of_chair)

        document.add_paragraph()
        document.add_paragraph()
        city = block.city or uni.get("city", "")
        line(f"{city} — {block.year}", bold=True)

        # Титульный лист — отдельная секция: номер на нём не печатается,
        # но страница входит в общую нумерацию (GOST 7.32-2017).
        new_section = document.add_section(WD_SECTION.NEW_PAGE)
        new_section.footer.is_linked_to_previous = False
        self._apply_margins(new_section)
        page_cfg = self.layout.get("page_number") or {}
        if page_cfg.get("enabled", True):
            num.page_number_footer(
                new_section,
                align=page_cfg.get("align", "center"),
                start=2 if page_cfg.get("start_after_title_page", True) else 1,
            )

    # ------------------------------------------------------------- содержание
    def _toc(self, document, block: TOC) -> None:
        p = document.add_paragraph(style=STYLE["centered"])
        run = p.add_run(self._t(block.title))
        self._style_run(p, bold=True)
        toc_p = document.add_paragraph()
        num.add_toc(toc_p, levels=block.levels)
        document.add_page_break()

    # ---------------------------------------------------------------- разделы
    def _heading(self, document, block: Heading) -> None:
        if not block.numbered:
            p = document.add_paragraph(style=STYLE["front"])
            p.add_run(self._t(block.text))
            self._style_run(p, bold=True)
            return

        if block.level == 1:
            self._chapter += 1
            self._section = 0
            p = document.add_paragraph(style="Heading 1")
            run = p.add_run(f"{self.lang.t('chapter_gen')} ")
            run.font.name = self.font
            run.font.size = self.size
            run.font.bold = True
            num.chapter_number(p, cached=str(self._chapter))
            num.set_bookmark(p, f"ch{self._chapter}")
            p.add_run(f". {self._t(block.text)}")
        else:
            self._section += 1
            p = document.add_paragraph(style="Heading 2")
            num.section_number(p, cached=f"{self._chapter}.{self._section}")
            p.add_run(". ")
            p.add_run(self._t(block.text))
        self._style_run(p, bold=True)

    # --------------------------------------------------------------- абзац
    def _para(self, document, block: Para) -> None:
        style = STYLE.get(block.style, STYLE["body"])
        p = document.add_paragraph(style=style)
        self._inline(p, block.text)
        size = self.caption_size if block.style in ("note", "caption") else self.size
        self._style_run(p, size=size)

    def _bullets(self, document, block: Bullets) -> None:
        for item in block.items:
            p = document.add_paragraph(style=STYLE["list"])
            p.add_run("– ")
            self._inline(p, item)
            self._style_run(p)

    def _inline(self, paragraph, text: str) -> None:
        """Печатает абзац, заменяя {fig:…}, {tbl:…}, {src:…} полями и ссылками."""
        for kind, key, raw in split_inline(text or ""):
            if kind == "text":
                paragraph.add_run(self._t(raw))
            elif kind == "src":
                number = self.citation_map.get(key)
                paragraph.add_run(f"[{number if number else '?'}]")
            else:
                cached = self.numbers.get(f"{kind}:{key}")
                if cached is None:
                    run = paragraph.add_run(self.lang.missing_data())
                    run.font.italic = True
                    continue
                # по-таджикски слово стоит перед номером: «расми 2.1»
                noun = self.lang.t("figure_ref" if kind == "fig" else "table_ref")
                if raw[:5].isupper():
                    noun = noun[:1].upper() + noun[1:]
                paragraph.add_run(noun + "\u00a0")
                kind_field = "fig" if kind == "fig" else "tbl"
                if cached[:1].isalpha() and cached[1:2] == ".":
                    num.appendix_object_ref(paragraph, kind_field, cached=cached)
                elif self.numbering_mode == "continuous":
                    num.continuous_number(paragraph, kind_field, cached=cached)
                else:
                    num.object_ref(paragraph, kind_field, cached=cached)

    # --------------------------------------------------------------- рисунок
    def _figure(self, document, block: FigureBlock) -> None:
        p = document.add_paragraph(style=STYLE["centered"])
        path = Path(block.path)
        if path.exists():
            p.add_run().add_picture(str(path), width=Cm(block.width_cm))
        else:
            run = p.add_run(f"[{self.lang.missing_data()}: {path.name}]")
            run.font.size = self.caption_size
            run.font.italic = True

        caption = document.add_paragraph(style=STYLE["caption"])
        run = caption.add_run(f"{self.lang.t('figure')} ")
        run.font.name = self.font
        run.font.size = self.caption_size
        cached = self.numbers.get(f"fig:{block.key}", "1")
        if self._appendix_letter or (cached[:1].isalpha() and cached[1:2] == "."):
            num.appendix_object_number(caption, "fig", cached=cached)
        elif self.numbering_mode == "continuous":
            num.continuous_number(caption, "fig", cached=cached)
        else:
            num.object_number(caption, "fig", cached=cached)
        num.set_bookmark(caption, f"fig_{block.key}")
        dash = caption.add_run(f" — {self._t(block.caption).rstrip('.')}")
        dash.font.name = self.font
        dash.font.size = self.caption_size

        note = self._provenance_note(block.provenance, block.source_note)
        if note:
            p2 = document.add_paragraph(style=STYLE["note"])
            r2 = p2.add_run(note)
            r2.font.name = self.font
            r2.font.size = self.caption_size
            r2.font.italic = True

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
    def _table(self, document, block: TableBlock) -> None:
        if block.caption:
            caption = document.add_paragraph(style=STYLE["note"])
            caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = caption.add_run(f"{self.lang.t('table')} ")
            run.font.name = self.font
            run.font.size = self.caption_size
            cached = self.numbers.get(f"tbl:{block.key}", "1")
            if self._appendix_letter or (cached[:1].isalpha() and cached[1:2] == "."):
                num.appendix_object_number(caption, "tbl", cached=cached)
            elif self.numbering_mode == "continuous":
                num.continuous_number(caption, "tbl", cached=cached)
            else:
                num.object_number(caption, "tbl", cached=cached)
            tail = caption.add_run(f" — {self._t(block.caption).rstrip('.')}")
            tail.font.name = self.font
            tail.font.size = self.caption_size

        rows, cols = len(block.rows) + 1, max(1, len(block.header))
        table = document.add_table(rows=rows, cols=cols)
        table.autofit = True
        try:
            table.style = "Table Grid"
        except KeyError:
            pass

        def fill(row_idx: int, values, bold: bool = False, header: bool = False):
            for c in range(cols):
                cell = table.cell(row_idx, c)
                cell.text = ""
                p = cell.paragraphs[0]
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(0)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run("" if c >= len(values) else str(values[c]))
                run.font.name = self.font
                run.font.size = self.table_size
                run.font.bold = bold
                if header:
                    _cell_borders(cell, top="single", bottom="single")
                else:
                    _cell_borders(cell, top="nil", bottom="single")

        fill(0, block.header, bold=True, header=True)
        for i, row in enumerate(block.rows, start=1):
            fill(i, row)

        document.add_paragraph()
        extra = ". ".join(
            [x for x in (block.note, self._provenance_note(block.provenance, block.source_note)) if x]
        )
        if extra:
            p = document.add_paragraph(style=STYLE["note"])
            r = p.add_run(extra)
            r.font.name = self.font
            r.font.size = self.caption_size
            r.font.italic = True

    # -------------------------------------------------------------- сокращения
    def _abbrev(self, document, block: AbbrevBlock) -> None:
        p = document.add_paragraph(style=STYLE["front"])
        p.add_run(self._t(block.title))
        self._style_run(p, bold=True)
        table = document.add_table(rows=max(1, len(block.pairs)), cols=2)
        table.autofit = True
        for i, (abbr, expansion) in enumerate(block.pairs):
            cells = table.rows[i].cells
            cells[0].text = ""
            cells[1].text = ""
            left = cells[0].paragraphs[0]
            right = cells[1].paragraphs[0]
            left.paragraph_format.space_after = Pt(0)
            right.paragraph_format.space_after = Pt(0)
            left.add_run(self._t(abbr))
            right.add_run(self._t(expansion))
            for cell in cells:
                _cell_borders(cell)
                for par in cell.paragraphs:
                    self._style_run(par)
            cells[0].width = Cm(3.0)
            cells[1].width = Cm(12.0)
        document.add_paragraph()

    # --------------------------------------------------------------- адабиёт
    def _refs(self, document, block: RefList) -> None:
        p = document.add_paragraph(style=STYLE["front"])
        p.paragraph_format.page_break_before = True
        p.add_run(self._t(block.title))
        self._style_run(p, bold=True)
        for i, entry in enumerate(block.entries, start=1):
            p = document.add_paragraph(style=STYLE["ref"])
            p.paragraph_format.left_indent = Cm(1.25)
            p.paragraph_format.first_line_indent = Cm(-0.75)
            text = re.sub(r"^\s*\d+\.\s*", "", self._t(entry))
            run = p.add_run(f"{i}. {text}")
            run.font.name = self.font
            run.font.size = self.size

    # --------------------------------------------------------------- замимаҳо
    def _appendix(self, document, block: Appendix) -> None:
        self._appendix_letter = block.letter or ""
        p = document.add_paragraph(style="Heading 1")
        p.add_run(f"{self.lang.t('appendix_gen')} ")
        num.appendix_letter(p, cached=self._appendix_letter)
        p.add_run(f". {self._t(block.title)}")
        self._style_run(p, bold=True)
        for sub in block.blocks:
            self._render(document, sub)
        self._appendix_letter = ""


def build_docx(
    doc: MedicalDocument,
    out_path: Path | str,
    profile=None,
    citation_map: dict[str, int] | None = None,
    lang_code: str | None = None,
) -> Path:
    """Точка входа: собрать .docx из модели документа."""
    return MedicalDocxBuilder(
        doc, profile=profile, citation_map=citation_map, lang_code=lang_code
    ).build(out_path)
