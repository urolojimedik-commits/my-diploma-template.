# -*- coding: utf-8 -*-
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
from content_a import INTRO_BLOCKS, CHAPTER1
from content_b import CHAPTER2
from content_c import CHAPTER3, CONCLUSION, APPENDIX
from content_extra import EXTRA, EXTRA_INTRO, EXTRA_CONCLUSION
from tables import TABLES, BIBLIOGRAPHY

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "images")
os.makedirs(IMG, exist_ok=True)
OUT = os.path.join(ROOT, "Кори_курсӣ_Воситаҳои_аёнӣ_ва_мултимедиявӣ.docx")
TOC_JSON = os.path.join(ROOT, "src", "toc.json")

plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10, "axes.titlesize": 11})
BLUE, TEAL, ORANGE, GREY = "#2E5987", "#3E8E7E", "#D98E4A", "#8A8D93"

def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, name), dpi=300, bbox_inches="tight")
    plt.close(fig)

def make_charts():
    # fig_vocab - grouped bar (sample)
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    cats = ["Санҷиши фаврӣ", "Пас аз 1 ҳафта", "Пас аз 2 ҳафта"]
    trad = [74, 55, 46]; mult = [83, 71, 64]
    x = range(len(cats)); w = 0.36
    ax.bar([i-w/2 for i in x], trad, w, label="Усули анъанавӣ", color=GREY)
    ax.bar([i+w/2 for i in x], mult, w, label="Бо мултимедия", color=BLUE)
    ax.set_xticks(list(x)); ax.set_xticklabels(cats)
    ax.set_ylabel("Азхудкунӣ, %"); ax.set_ylim(0, 100); ax.legend(frameon=False)
    ax.grid(axis="y", alpha=.25)
    for bars in ax.containers:
        ax.bar_label(bars, padding=2, fontsize=9)
    save(fig, "fig_vocab.png")

    # fig_types - pie
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    vals = [30, 20, 15, 20, 15]
    labels = ["Видео", "Аудио / подкаст", "Презентасия", "Бозӣ ва викторина", "Кори лоиҳавӣ"]
    ax.pie(vals, labels=labels, autopct="%1.0f%%", startangle=90,
           colors=[BLUE, TEAL, ORANGE, "#6A9AB0", "#B56576"], textprops={"fontsize": 9},
           wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    save(fig, "fig_types.png")

    # fig_dyn - line
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    weeks = [0, 2, 4, 6]
    ax.plot(weeks, [50, 56, 62, 66], "o-", color=GREY, label="Гурӯҳи назоратӣ")
    ax.plot(weeks, [51, 62, 70, 78], "s-", color=BLUE, label="Гурӯҳи озмоишӣ")
    ax.set_xlabel("Ҳафтаҳои омӯзиш"); ax.set_ylabel("Нишондиҳандаи миёна, %")
    ax.set_xticks(weeks); ax.set_ylim(40, 90); ax.grid(alpha=.25); ax.legend(frameon=False)
    save(fig, "fig_dyn.png")

    # fig_paivio - scheme
    fig, ax = plt.subplots(figsize=(6.4, 2.9)); ax.set_xlim(0, 10); ax.set_ylim(0, 4.2); ax.axis("off")
    def box(x, y, w, h, text, color):
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
                                            fc=color, ec="#33475B", lw=1.1))
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=8.5, color="white" if color != "#D9E6F2" else "#1F3550")
    box(0.2, 1.7, 1.9, 1.1, "Калима\n(шунидан / хондан)", BLUE)
    box(3.0, 1.7, 1.9, 1.1, "Ҳофизаи\nшифоҳӣ", TEAL)
    box(5.6, 1.7, 1.9, 1.1, "Пайвасти\nшифоҳӣ–тасвирӣ", ORANGE)
    box(8.0, 1.7, 1.8, 1.1, "Ёддошти\nустувор", "#6A4C93")
    box(3.0, 0.2, 1.9, 1.1, "Ҳофизаи\nтасвирӣ", "#6A9AB0")
    box(0.2, 0.2, 1.9, 1.1, "Тасвир / видео", "#6A9AB0")
    for (x1, y1, x2, y2) in [(2.1, 2.25, 3.0, 2.25), (4.9, 2.25, 5.6, 2.25), (7.5, 2.25, 8.0, 2.25),
                            (2.1, .75, 3.0, .75), (4.4, 1.3, 6.2, 1.7)]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color="#33475B", lw=1.2))
    save(fig, "fig_paivio.png")

    # fig_tpack - Venn
    fig, ax = plt.subplots(figsize=(5.2, 4.2)); ax.set_xlim(0, 10); ax.set_ylim(0, 8); ax.axis("off")
    for (x, y, c, t) in [(3.8, 4.6, BLUE, "Дониши\nфаннӣ (CK)"), (6.2, 4.6, TEAL, "Дониши\nтехнологӣ (TK)"), (5.0, 2.6, ORANGE, "Дониши\nпедагогӣ (PK)")]:
        ax.add_patch(patches.Circle((x, y), 2.1, fc=c, ec="white", alpha=.55, lw=1.5))
        ax.text(x, y + (1.25 if y > 4 else -1.25), t, ha="center", va="center", fontsize=9, weight="bold")
    ax.text(5.0, 4.0, "TPACK", ha="center", va="center", fontsize=11, weight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#33475B"))
    save(fig, "fig_tpack.png")

FIGURES = {
 "fig_paivio": ("Расми 1.1", "Модели рамзгузории дугона дар омӯзиши мултимедиявӣ", "fig_paivio.png", "Сарчашма: таҳияи муаллиф дар асоси [20]."),
 "fig_vocab": ("Расми 2.1", "Муқоисаи намунавии (шартии) азхудкунии луғат аз рӯи усули таълим, %", "fig_vocab.png", "Сарчашма: маълумоти намунавӣ (шартӣ), барои тасвири самти таъсир."),
 "fig_types": ("Расми 2.2", "Тақсимоти намунавии вақти истифодаи намудҳои мултимедия дар дарси омехта, %", "fig_types.png", "Сарчашма: таҳияи муаллиф (намуна)."),
 "fig_tpack": ("Расми 3.1", "Модели салоҳияти TPACK-и омӯзгор", "fig_tpack.png", "Сарчашма: таҳияи муаллиф дар асоси [18]."),
 "fig_dyn": ("Расми 3.2", "Динамикаи намунавии (шартии) нишондиҳандаҳо дар тӯли озмоиш, %", "fig_dyn.png", "Сарчашма: маълумоти намунавӣ (шартӣ)."),
}

def set_cell_shading(cell, color="D9E2EC"):
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>'))

def add_page_field(par):
    run = par.add_run()
    fld1 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>')
    instr = parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> PAGE </w:instrText>')
    fld2 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>')
    run._r.append(fld1); run._r.append(instr); run._r.append(fld2)
    run.font.name = "Times New Roman"; run.font.size = Pt(12)

def style_doc(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3.0), Cm(1.5)
    sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
    sec.different_first_page_header_footer = True
    footer = sec.footer
    p = footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_field(p)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"; st.font.size = Pt(14)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    pf = st.paragraph_format
    pf.line_spacing = 1.5; pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.first_line_indent = Cm(1.25); pf.space_after = Pt(0); pf.space_before = Pt(0)
    for name, size in [("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 14)]:
        s = doc.styles[name]
        s.font.name = "Times New Roman"; s.font.size = Pt(size); s.font.bold = True
        s.font.color.rgb = RGBColor(0, 0, 0)
        s.paragraph_format.line_spacing = 1.5
        s.paragraph_format.space_before = Pt(12); s.paragraph_format.space_after = Pt(6)
        s.paragraph_format.first_line_indent = Cm(0)

def body(doc, text):
    p = doc.add_paragraph(text)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p

def h1(doc, text, pagebreak=True):
    if pagebreak:
        doc.add_page_break()
    p = doc.add_paragraph(style="Heading 1")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(text)
    return p

def h2(doc, text):
    p = doc.add_paragraph(style="Heading 2")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.add_run(text)
    return p

def h3(doc, text):
    p = doc.add_paragraph(style="Heading 3")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.add_run(text)
    return p

def add_table(doc, key):
    num, title, headers, rows, src = TABLES[key]
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run(f"{num} — {title}"); r.bold = True; r.font.size = Pt(12)
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, htxt in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        pp = c.paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER; pp.paragraph_format.first_line_indent = Cm(0)
        rr = pp.add_run(htxt); rr.bold = True; rr.font.size = Pt(11); rr.font.name = "Times New Roman"
        set_cell_shading(c)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            pp = cells[i].paragraphs[0]; pp.paragraph_format.first_line_indent = Cm(0)
            pp.alignment = WD_ALIGN_PARAGRAPH.LEFT if i else WD_ALIGN_PARAGRAPH.LEFT
            rr = pp.add_run(val); rr.font.size = Pt(11); rr.font.name = "Times New Roman"
    p2 = doc.add_paragraph(); p2.paragraph_format.first_line_indent = Cm(0)
    r2 = p2.add_run(src); r2.italic = True; r2.font.size = Pt(11)

def add_figure(doc, key):
    num, title, fname, src = FIGURES[key]
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.first_line_indent = Cm(0)
    p.add_run().add_picture(os.path.join(IMG, fname), width=Cm(12.5))
    p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER; p2.paragraph_format.first_line_indent = Cm(0)
    r = p2.add_run(f"{num} — {title}"); r.font.size = Pt(12); r.bold = True
    p3 = doc.add_paragraph(); p3.alignment = WD_ALIGN_PARAGRAPH.CENTER; p3.paragraph_format.first_line_indent = Cm(0)
    r3 = p3.add_run(src); r3.italic = True; r3.font.size = Pt(11)

def render_blocks(doc, blocks):
    for kind, val in blocks:
        if kind == "p":
            body(doc, val)
        elif kind == "h3":
            h3(doc, val)
        elif kind == "table":
            add_table(doc, val)
        elif kind == "figure":
            add_figure(doc, val)

def title_page(doc):
    for txt, size, bold, after in [
        ("ВАЗОРАТИ МАОРИФ ВА ИЛМИ ҶУМҲУРИИ ТОҶИКИСТОН", 14, True, 6),
        ("________________________________________", 14, False, 6),
        ("(номи пурраи муассисаи таҳсилоти олии касбӣ)", 11, False, 12),
        ("Факултет: ________________________________", 14, False, 6),
        ("Кафедра: _________________________________", 14, False, 24),
    ]:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.first_line_indent = Cm(0)
        r = p.add_run(txt); r.font.size = Pt(size); r.bold = bold
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(72)
    r = p.add_run("КОРИ КУРСӢ"); r.bold = True; r.font.size = Pt(20)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("аз фанни методикаи таълими забони англисӣ"); r.font.size = Pt(14); r.italic = True
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(24)
    r = p.add_run("Мавзӯъ:\nНАҚШИ ВОСИТАҲОИ АЁНӢ ВА МУЛТИМЕДИЯВӢ\nДАР ТАЪЛИМИ ЗАБОНИ АНГЛИСӢ"); r.bold = True; r.font.size = Pt(16)
    for _ in range(4):
        doc.add_paragraph()
    for txt in ["Иҷро кард: донишҷӯи курси ______ гурӯҳи __________",
                "________________________________ (имзо, насаб, ном)",
                "Роҳбари илмӣ: ______________________________________",
                "________________________________ (унвон, имзо, насаб)"]:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT; p.paragraph_format.first_line_indent = Cm(0)
        r = p.add_run(txt); r.font.size = Pt(14)
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("________________ — 20____"); r.font.size = Pt(14)

def toc_page(doc, toc):
    h1(doc, "МУНДАРИҶА")
    entries = [
        ("Муқаддима", toc.get("Муқаддима", 3)),
        ("БОБИ 1. АСОСҲОИ НАЗАРИЯВИИ ИСТИФОДАИ ВОСИТАҲОИ АЁНӢ ВА МУЛТИМЕДИЯВӢ ДАР ТАЪЛИМИ ЗАБОНИ ХОРИҶӢ", toc.get("БОБИ 1", 6)),
        ("1.1. Мафҳум, моҳият ва таснифоти воситаҳои аёнӣ ва мултимедиявӣ", toc.get("1.1", 6)),
        ("1.2. Асосҳои психологӣ-педагогии истифодаи воситаҳои аёнӣ ва мултимедиявӣ дар омӯзиши забон", toc.get("1.2", 9)),
        ("1.3. Инкишофи таърихӣ ва тамоюлҳои муосири истифодаи воситаҳои аёнӣ дар таълими забонҳои хориҷӣ", toc.get("1.3", 12)),
        ("БОБИ 2. ИМКОНИЯТҲОИ МЕТОДИИ ВОСИТАҲОИ АЁНӢ ВА МУЛТИМЕДИЯВӢ ДАР ТАШАККУЛИ САЛОҲИЯТИ КОММУНИКАТИВӢ ЗАБОНӢ".replace("КОММУНИКАТИВӢ", "КОММУНИКАТИВИИ"), toc.get("БОБИ 2", 15)),
        ("2.1. Нақши воситаҳои аёнӣ ва мултимедиявӣ дар таълими луғат ва грамматика", toc.get("2.1", 15)),
        ("2.2. Истифодаи воситаҳои мултимедиявӣ дар рушди малакаҳои шунавоӣ, гуфтор, хониш ва навишт", toc.get("2.2", 18)),
        ("2.3. Технологияҳои интерактивӣ ва захираҳои рақамӣ дар таълими муосири забони англисӣ", toc.get("2.3", 21)),
        ("БОБИ 3. ҶАНБАҲОИ АМАЛИИ ИСТИФОДАИ ВОСИТАҲОИ АЁНӢ ВА МУЛТИМЕДИЯВӢ ВА РОҲҲОИ БАЛАНД БАРДОШТАНИ САМАРАНОКИИ ОНҲО", toc.get("БОБИ 3", 24)),
        ("3.1. Шартҳои педагогӣ ва талаботи ташкилӣ-методӣ ба истифодаи воситаҳои аёнӣ ва мултимедиявӣ", toc.get("3.1", 24)),
        ("3.2. Таҳлили таҷрибаи амалӣ ва самаранокии истифодаи воситаҳои мултимедиявӣ (дар мисоли мушоҳидаи озмоишии намунавӣ)", toc.get("3.2", 27)),
        ("3.3. Мушкилот, хатарҳо ва тавсияҳои методӣ оид ба такмили истифодаи воситаҳои аёнӣ ва мултимедиявӣ", toc.get("3.3", 30)),
        ("Хулоса", toc.get("Хулоса", 33)),
        ("Рӯйхати адабиёти истифодашуда", toc.get("АДАБИЁТ", 35)),
        ("Замима", toc.get("Замима", 37)),
    ]
    for title, pg in entries:
        p = doc.add_paragraph(); p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16.5))
        bold = title.startswith("БОБИ") or title in ("Муқаддима", "Хулоса", "Рӯйхати адабиёти истифодашуда")
        r = p.add_run(f"{title}\t{pg}"); r.font.size = Pt(12); r.bold = bold

def main():
    make_charts()
    toc = {}
    if os.path.exists(TOC_JSON):
        toc = json.load(open(TOC_JSON, encoding="utf-8"))
    doc = Document()
    style_doc(doc)
    title_page(doc)
    toc_page(doc, toc)
    h1(doc, "МУҚАДДИМА")
    render_blocks(doc, INTRO_BLOCKS + EXTRA_INTRO)
    for ch in (CHAPTER1, CHAPTER2, CHAPTER3):
        h1(doc, ch["title"])
        render_blocks(doc, ch["intro"])
        for sec in ch["sections"]:
            h2(doc, sec["title"])
            key = sec["title"][:3]
            blocks = sec["blocks"]
            extra = EXTRA.get(key, [])[:1]
            if extra and blocks:
                render_blocks(doc, blocks[:-1])
                render_blocks(doc, extra)
                render_blocks(doc, blocks[-1:])
            else:
                render_blocks(doc, blocks)
    h1(doc, "ХУЛОСА")
    render_blocks(doc, CONCLUSION + EXTRA_CONCLUSION)
    h1(doc, "РӮЙХАТИ АДАБИЁТИ ИСТИФОДАШУДА")
    for i, ref in enumerate(BIBLIOGRAPHY, 1):
        p = doc.add_paragraph(); p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(1.0); p.paragraph_format.first_line_indent = Cm(-1.0)
        r = p.add_run(f"{i}. {ref}"); r.font.size = Pt(13)
    h1(doc, "ЗАМИМА")
    h2(doc, "Замима 1. Намунаи нақшаи дарси мултимедиявӣ ва варақаи худбаҳодиҳӣ")
    render_blocks(doc, APPENDIX)
    doc.save(OUT)
    words = sum(len(v.split()) for _, v in INTRO_BLOCKS + CONCLUSION if _ == "p")
    for ch in (CHAPTER1, CHAPTER2, CHAPTER3):
        words += sum(len(v.split()) for _, v in ch["intro"] if _ == "p")
        for s in ch["sections"]:
            words += sum(len(v.split()) for _, v in s["blocks"] if _ == "p")
    print("Saved:", OUT)
    print("Body words approx:", words)
    print("File size:", os.path.getsize(OUT))

if __name__ == "__main__":
    main()
