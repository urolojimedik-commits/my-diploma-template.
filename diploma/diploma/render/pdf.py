"""PDF: рендерер AST Pandoc → ReportLab с оформлением по ГОСТ.

Используется, когда в системе нет LaTeX (в том числе в песочнице CI). Если
доступен XeLaTeX/PDFLaTeX/Tectonic, :mod:`engine` предпочитает связку
Pandoc → LaTeX → PDF; этот модуль при этом остаётся доступным по флагу
``--pdf-engine builtin``.

Поддерживаются: иерархические заголовки с автоматическим содержанием
(номера страниц), абзацы с отступом первой строки, списки, цитаты, блоки кода,
таблицы с подписями, рисунки с подписями, сноски, формулы (в виде текста),
колонтитулы и ГОСТ-овский титульный лист.
"""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table as RLTable,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from .pandoc_utils import to_ast

# --------------------------------------------------------------------------- #
# Шрифты: DejaVu поставляется с matplotlib и покрывает кириллицу
# --------------------------------------------------------------------------- #

_FONTS_READY = False
BODY_FONT = "DejaVuSerif"
HEAD_FONT = "DejaVuSans"
MONO_FONT = "DejaVuSansMono"


def register_fonts() -> None:
    global _FONTS_READY
    if _FONTS_READY:
        return
    import matplotlib

    font_dir = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
    candidates = [
        ("DejaVuSerif", "DejaVuSerif.ttf"),
        ("DejaVuSerif-Bold", "DejaVuSerif-Bold.ttf"),
        ("DejaVuSerif-Italic", "DejaVuSerif-Italic.ttf"),
        ("DejaVuSans", "DejaVuSans.ttf"),
        ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"),
        ("DejaVuSans-Oblique", "DejaVuSans-Oblique.ttf"),
        ("DejaVuSansMono", "DejaVuSansMono.ttf"),
    ]
    for name, file in candidates:
        path = font_dir / file
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(name, str(path)))
            except Exception:
                pass
    from reportlab.pdfbase.pdfmetrics import registerFontFamily

    try:
        registerFontFamily(
            "DejaVuSerif", normal="DejaVuSerif", bold="DejaVuSerif-Bold",
            italic="DejaVuSerif-Italic", boldItalic="DejaVuSerif-Bold",
        )
        registerFontFamily(
            "DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold",
            italic="DejaVuSans-Oblique", boldItalic="DejaVuSans-Bold",
        )
        registerFontFamily("DejaVuSansMono", normal="DejaVuSansMono", bold="DejaVuSansMono",
                           italic="DejaVuSansMono", boldItalic="DejaVuSansMono")
    except Exception:
        pass
    _FONTS_READY = True


# --------------------------------------------------------------------------- #
# Стили
# --------------------------------------------------------------------------- #


def build_styles(font_size: int = 14, line_spacing: float = 1.5) -> StyleSheet1:
    register_fonts()
    ss = StyleSheet1()
    base = ParagraphStyle(
        "Body",
        fontName=BODY_FONT,
        fontSize=font_size,
        leading=font_size * line_spacing,
        alignment=TA_JUSTIFY,
        firstLineIndent=1.25 * cm,
        spaceAfter=4,
    )
    ss.add(base)
    ss.add(
        ParagraphStyle(
            "Heading1",
            parent=base,
            fontName=HEAD_FONT + "-Bold",
            fontSize=font_size + 2,
            leading=(font_size + 2) * 1.3,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceBefore=14,
            spaceAfter=10,
            textColor=colors.HexColor("#10233a"),
        )
    )
    ss.add(
        ParagraphStyle(
            "Heading2",
            parent=base,
            fontName=HEAD_FONT + "-Bold",
            fontSize=font_size,
            leading=font_size * 1.3,
            alignment=TA_LEFT,
            firstLineIndent=0,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#10233a"),
        )
    )
    ss.add(
        ParagraphStyle(
            "Heading3",
            parent=base,
            fontName=HEAD_FONT + "-Bold",
            fontSize=font_size,
            leading=font_size * 1.25,
            alignment=TA_LEFT,
            firstLineIndent=0,
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    ss.add(
        ParagraphStyle(
            "Caption",
            parent=base,
            fontName=BODY_FONT,
            fontSize=font_size - 2,
            leading=(font_size - 2) * 1.25,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceBefore=2,
            spaceAfter=8,
        )
    )
    ss.add(
        ParagraphStyle(
            "Code",
            parent=base,
            fontName=MONO_FONT,
            fontSize=font_size - 3,
            leading=(font_size - 3) * 1.3,
            alignment=TA_LEFT,
            firstLineIndent=0,
            backColor=colors.HexColor("#f4f4f4"),
            borderPadding=4,
            spaceBefore=6,
            spaceAfter=6,
        )
    )
    ss.add(
        ParagraphStyle(
            "Quote",
            parent=base,
            fontName=BODY_FONT + "-Italic",
            fontSize=font_size - 1,
            leftIndent=1.2 * cm,
            rightIndent=0.8 * cm,
            firstLineIndent=0,
            spaceBefore=4,
            spaceAfter=6,
        )
    )
    ss.add(
        ParagraphStyle(
            "TableCell",
            parent=base,
            fontSize=font_size - 3,
            leading=(font_size - 3) * 1.25,
            alignment=TA_LEFT,
            firstLineIndent=0,
            spaceAfter=0,
        )
    )
    ss.add(
        ParagraphStyle(
            "TitlePage",
            parent=base,
            fontName=HEAD_FONT,
            fontSize=font_size,
            leading=font_size * 1.4,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceAfter=6,
        )
    )
    ss.add(
        ParagraphStyle(
            "TitlePageBig",
            parent=base,
            fontName=HEAD_FONT + "-Bold",
            fontSize=font_size + 2,
            leading=(font_size + 2) * 1.35,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceAfter=10,
        )
    )
    ss.add(
        ParagraphStyle(
            "Note",
            parent=base,
            fontSize=font_size - 4,
            leading=(font_size - 4) * 1.2,
            firstLineIndent=0,
            spaceAfter=2,
        )
    )
    return ss


# --------------------------------------------------------------------------- #
# Преобразование AST → flowables
# --------------------------------------------------------------------------- #

ALIGN_MAP = {
    "AlignLeft": "LEFT",
    "AlignRight": "RIGHT",
    "AlignCenter": "CENTER",
    "AlignDefault": "LEFT",
}


def _align_name(value) -> str:
    """Pandoc >= 2.10 кодирует выравнивание как {"t": "AlignLeft"}."""
    if isinstance(value, dict):
        return ALIGN_MAP.get(value.get("t"), "LEFT")
    return ALIGN_MAP.get(value, "LEFT")


class ASTRenderer:
    def __init__(self, styles: StyleSheet1, base_dir: Path, max_image_width: float = 15.5 * cm):
        self.styles = styles
        self.base_dir = Path(base_dir)
        self.max_image_width = max_image_width
        self.notes: list[str] = []
        self._heading_count = 0

    # ---------------------------------------------------------------- inline
    def inline(self, nodes: list[dict]) -> str:
        parts: list[str] = []
        for node in nodes or []:
            t = node.get("t")
            c = node.get("c")
            if t == "Str":
                parts.append(self.escape(c))
            elif t == "Space":
                parts.append(" ")
            elif t == "SoftBreak":
                parts.append(" ")
            elif t == "LineBreak":
                parts.append("<br/>")
            elif t == "Emph":
                parts.append(f"<i>{self.inline(c)}</i>")
            elif t == "Strong":
                parts.append(f"<b>{self.inline(c)}</b>")
            elif t == "Strikeout":
                parts.append(f"<strike>{self.inline(c)}</strike>")
            elif t == "Superscript":
                parts.append(f"<super>{self.inline(c)}</super>")
            elif t == "Subscript":
                parts.append(f"<sub>{self.inline(c)}</sub>")
            elif t == "Code":
                parts.append(f'<font face="{MONO_FONT}">{self.escape(c[1] if isinstance(c, list) else c)}</font>')
            elif t == "Quoted":
                parts.append(self.inline(c[1]))
            elif t == "Span":
                parts.append(self.inline(c[1]))
            elif t == "Link":
                text = self.inline(c[2])
                url = c[1][0] if isinstance(c[1], list) else ""
                parts.append(
                    f'<a href="{self.escape(url)}" color="blue">{text}</a>' if url else text
                )
            elif t == "Image":
                parts.append(self.inline(c[2]))  # подпись как текст: рисунок ставим отдельно
            elif t == "Math":
                parts.append(f"<i>{self.escape(c[1])}</i>")
            elif t == "Note":
                self.notes.append(self.blocks_text(c))
                parts.append(f"<super>{len(self.notes)})</super>")
            elif t == "Cite":
                parts.append(self.inline(c[1]))
            elif t == "Underline":
                parts.append(f"<u>{self.inline(c)}</u>")
            elif t == "SmallCaps":
                parts.append(self.inline(c).upper())
            elif isinstance(c, str):
                parts.append(self.escape(c))
        return "".join(parts)

    @staticmethod
    def escape(text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def blocks_text(self, blocks: list[dict]) -> str:
        out = []
        for b in blocks:
            if b.get("t") == "Para":
                out.append(self.inline(b["c"]))
            elif b.get("t") == "Plain":
                out.append(self.inline(b["c"]))
        return " ".join(out)

    # ---------------------------------------------------------------- blocks
    def blocks(self, blocks: list[dict], story: list) -> None:
        i = 0
        while i < len(blocks):
            b = blocks[i]
            t = b.get("t")
            c = b.get("c")
            if t == "Para" and self._is_image_only(c):
                img = self._make_image(c[0])
                flowables = []
                if img:
                    flowables.append(img)
                # следующая подпись (если это наш формат «Рисунок N — …»)
                if i + 1 < len(blocks) and blocks[i + 1].get("t") == "Para":
                    nxt = self.inline(blocks[i + 1]["c"])
                    if re.match(r"^(Рисунок|Таблица|Figure|Table)\b", nxt):
                        flowables.append(Paragraph(nxt, self.styles["Caption"]))
                        i += 1
                if flowables:
                    story.append(KeepTogether(flowables))
                i += 1
                continue
            if t == "Para":
                text = self.inline(c)
                if text.strip():
                    style = "Caption" if re.match(r"^(Рисунок|Таблица)\s", text.strip()) else "Body"
                    story.append(Paragraph(text, self.styles[style]))
            elif t == "Plain":
                text = self.inline(c)
                if text.strip():
                    story.append(Paragraph(text, self.styles["Body"]))
            elif t == "Header":
                level = c[0]
                text = self.inline(c[2])
                style = {1: "Heading1", 2: "Heading2"}.get(level, "Heading3")
                # каждая глава (кроме первой) начинается с новой страницы
                if level == 1 and self._heading_count:
                    story.append(PageBreak())
                self._heading_count += 1
                story.append(Paragraph(text, self.styles[style]))
            elif t == "BulletList":
                items = []
                for item in c:
                    items.append(ListItem(Paragraph(self.blocks_text(item), self.styles["Body"]), leftIndent=12))
                story.append(
                    ListFlowable(items, bulletType="bullet", bulletFontSize=8, leftIndent=18)
                )
            elif t == "OrderedList":
                items = []
                for item in c[1]:
                    items.append(ListItem(Paragraph(self.blocks_text(item), self.styles["Body"]), leftIndent=12))
                story.append(ListFlowable(items, bulletType="1", leftIndent=18))
            elif t == "BlockQuote":
                for sub in c:
                    if sub.get("t") == "Para":
                        story.append(Paragraph(self.inline(sub["c"]), self.styles["Quote"]))
            elif t == "CodeBlock":
                code = c[1]
                story.append(Preformatted(code, self.styles["Code"]))
            elif t == "HorizontalRule":
                story.append(Spacer(1, 4))
                story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))
            elif t == "Table":
                story.extend(self._make_table(c))
            elif t == "Div":
                self.blocks(c[1], story)
            elif t == "Null":
                pass
            elif t == "RawBlock":
                pass
            i += 1

    def _is_image_only(self, inlines: list[dict]) -> bool:
        return len(inlines) == 1 and inlines[0].get("t") == "Image"

    def _make_image(self, image_node: dict):
        c = image_node["c"]
        url = c[2][0] if isinstance(c[2], list) else ""
        path = (self.base_dir / url) if not url.startswith(("http", "/")) else Path(url)
        if not path.exists():
            return None
        try:
            from PIL import Image as PILImage

            with PILImage.open(path) as im:
                w, h = im.size
            ratio = h / w
        except Exception:
            ratio = 0.62
        width = self.max_image_width
        height = width * ratio
        if height > 12 * cm:
            height = 12 * cm
            width = height / ratio
        return RLImage(str(path), width=width, height=height, hAlign="CENTER")

    def _make_table(self, c: list):
        attr, caption, colspecs, thead, tbodies, tfoot = c
        aligns = [_align_name(spec[0]) for spec in (colspecs or [])]
        rows: list[list] = []

        def cell_blocks(cell: dict) -> str:
            return self.blocks_text(cell[4] if len(cell) > 4 else cell[-1])

        head_rows = thead[1] if thead else []
        for row in head_rows:
            rows.append([Paragraph(f"<b>{cell_blocks(cell)}</b>", self.styles["TableCell"]) for cell in row[1]])
        body_rows = []
        for tbody in tbodies or []:
            for row in tbody[3]:
                body_rows.append([Paragraph(cell_blocks(cell), self.styles["TableCell"]) for cell in row[1]])
        if not body_rows:
            return []
        n_cols = len(body_rows[0])
        if head_rows and len(rows[0]) != n_cols:
            n_cols = max(len(rows[0]), n_cols)
        aligns = (aligns + ["LEFT"] * n_cols)[:n_cols]

        data = rows + body_rows
        table = RLTable(data, colWidths=None, hAlign="CENTER", repeatRows=len(rows))
        style = [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
            ("BACKGROUND", (0, 0), (-1, len(rows) - 1), colors.HexColor("#eaf1f8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        for i, a in enumerate(aligns):
            style.append(("ALIGN", (i, 0), (i, -1), a))
        table.setStyle(TableStyle(style))
        out = [table, Spacer(1, 4)]
        # подпись таблицы (pandoc >= 2.10: caption = [short, [blocks]])
        cap_text = ""
        try:
            cap_blocks = caption[1] if isinstance(caption, list) and len(caption) > 1 else []
            cap_text = self.blocks_text(cap_blocks)
        except Exception:
            cap_text = ""
        if cap_text:
            out.append(Paragraph(cap_text, self.styles["Caption"]))
        return out


# --------------------------------------------------------------------------- #
# Документ
# --------------------------------------------------------------------------- #


class ThesisDocTemplate(BaseDocTemplate):
    """Шаблон с титульным листом и колонтитулом-номером страницы."""

    def __init__(self, filename, title_page: list, styles: StyleSheet1, **kwargs):
        self.title_page = title_page
        self.styles = styles
        self._seen_title = False
        super().__init__(filename, pagesize=A4, **kwargs)
        frame_cover = Frame(
            2.0 * cm, 2.0 * cm, A4[0] - 4.0 * cm, A4[1] - 4.0 * cm, id="cover"
        )
        frame_body = Frame(
            3.0 * cm, 2.0 * cm, A4[0] - 5.0 * cm, A4[1] - 4.5 * cm, id="body",
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        self.addPageTemplates(
            [
                PageTemplate(id="Cover", frames=[frame_cover], onPage=self._cover_page),
                PageTemplate(id="Body", frames=[frame_body], onPage=self._body_page),
            ]
        )

    def _cover_page(self, canv, doc):
        canv.saveState()
        canv.restoreState()

    def _body_page(self, canv, doc):
        canv.saveState()
        canv.setFont(HEAD_FONT, 10)
        canv.setFillColor(colors.HexColor("#333333"))
        canv.drawCentredString(A4[0] / 2.0, 1.2 * cm, str(canv.getPageNumber() - 1))
        canv.restoreState()

    # «Содержание» не ссылается само на себя, примечания — служебный раздел
    SKIP_TOC = {"Содержание", "Примечания"}

    def afterFlowable(self, flowable):
        """Регистрирует заголовки в автоматическом содержании."""
        if not isinstance(flowable, Paragraph):
            return
        name = getattr(flowable.style, "name", "")
        if not name.startswith("Heading"):
            return
        level = int(name[-1]) if name[-1].isdigit() else 3
        text = re.sub(r"<[^>]+>", "", flowable.text or "").strip()
        if not text or text in self.SKIP_TOC:
            return
        # нумерация в колонтитуле начинается после титульного листа
        self.notify("TOCEntry", (level, text, self.page - 1))


def build_title_page(meta: dict, styles: StyleSheet1, work_type_ru: str) -> list:
    s = styles["TitlePage"]
    big = styles["TitlePageBig"]
    items: list = [
        Spacer(1, 1.2 * cm),
        Paragraph(meta.get("institution", ""), s),
        Spacer(1, 0.3 * cm),
        Paragraph(meta.get("faculty", ""), s),
        Paragraph(meta.get("chair", ""), s),
        Spacer(1, 1.6 * cm),
        Paragraph(work_type_ru.upper(), big),
        Spacer(1, 0.6 * cm),
        Paragraph(f"Тема: «{meta.get('title', '')}»", big),
        Spacer(1, 2.2 * cm),
    ]
    rows = [
        ("Выполнил", f"{meta.get('author', '')}" + (f", {meta.get('group', '')}" if meta.get("group") else "")),
        ("Научный руководитель", meta.get("supervisor", "")),
        ("Город", meta.get("city", "")),
        ("Год", str(meta.get("year", ""))),
    ]
    data = [[Paragraph(f"<b>{k}</b>", s), Paragraph(v or "—", s)] for k, v in rows]
    table = RLTable(data, colWidths=[6.0 * cm, 8.5 * cm], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#999999")),
                ("LINEBELOW", (0, 1), (-1, 1), 0.5, colors.HexColor("#999999")),
            ]
        )
    )
    items.append(table)
    return items


def render_pdf(
    markdown: str,
    output: Path,
    meta: dict,
    base_dir: Path,
    font_size: int = 14,
    line_spacing: float = 1.5,
    build_toc: bool = True,
    work_type_ru: str = "выпускная квалификационная работа",
) -> Path:
    """Собирает PDF из markdown."""
    register_fonts()
    styles = build_styles(font_size=font_size, line_spacing=line_spacing)
    ast = to_ast(markdown)
    meta_ast = ast.get("meta", {})
    blocks = ast.get("blocks", [])

    renderer = ASTRenderer(styles, base_dir=Path(base_dir))
    story: list = []
    renderer.blocks(blocks, story)

    if renderer.notes:
        story.append(PageBreak())
        story.append(Paragraph("Примечания", styles["Heading2"]))
        for i, note in enumerate(renderer.notes, start=1):
            story.append(Paragraph(f"{i}) {note}", styles["Note"]))

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    doc = ThesisDocTemplate(
        str(output),
        title_page=[],
        styles=styles,
        title=str(meta.get("title", "")),
        author=str(meta.get("author", "")),
        subject=str(meta.get("subject", "")),
        leftMargin=3.0 * cm,
        rightMargin=1.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    title_page = build_title_page(meta, styles, work_type_ru)
    full_story: list = list(title_page) + [NextPageTemplate("Body"), PageBreak()]
    if build_toc:
        toc = TableOfContents()
        toc.levelStyles = [
            ParagraphStyle(
                "TOCH1", fontName=HEAD_FONT + "-Bold", fontSize=font_size - 2,
                leading=(font_size - 2) * 1.5, leftIndent=0, firstLineIndent=0,
                spaceBefore=6,
            ),
            ParagraphStyle(
                "TOCH2", fontName=BODY_FONT, fontSize=font_size - 3,
                leading=(font_size - 3) * 1.4, leftIndent=1.0 * cm, firstLineIndent=0,
            ),
        ]
        full_story.append(Paragraph("Содержание", styles["Heading1"]))
        full_story.append(toc)
        full_story.append(PageBreak())
    full_story += story

    def _page(canv, d):
        canv.saveState()
        canv.restoreState()

    doc.multiBuild(full_story)
    return output
