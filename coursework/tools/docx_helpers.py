"""Shared Word styles. Explicit fonts override the template's theme fonts."""
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = 'Times New Roman'
SIZE = 14


def font_xml(rpr, bold=None, italic=None, size=SIZE):
    fonts = rpr.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts')
        rpr.insert(0, fonts)
    for key in list(fonts.attrib):
        del fonts.attrib[key]
    for script in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
        fonts.set(qn('w:' + script), FONT)
    fonts.set(qn('w:hint'), 'default')
    for tag, value in (('sz', size), ('szCs', size)):
        el = rpr.find(qn('w:' + tag))
        if el is None:
            el = OxmlElement('w:' + tag)
            rpr.append(el)
        el.set(qn('w:val'), str(int(value * 2)))
    for tag, value in (('b', bold), ('bCs', bold), ('i', italic), ('iCs', italic)):
        if value is not None:
            el = rpr.find(qn('w:' + tag))
            if el is None:
                el = OxmlElement('w:' + tag)
                rpr.append(el)
            el.set(qn('w:val'), '1' if value else '0')
    color = rpr.find(qn('w:color'))
    if color is None:
        color = OxmlElement('w:color')
        rpr.append(color)
    for key in list(color.attrib):
        del color.attrib[key]
    color.set(qn('w:val'), '000000')


def style(doc, name, kind=WD_STYLE_TYPE.PARAGRAPH):
    try:
        return doc.styles[name]
    except KeyError:
        return doc.styles.add_style(name, kind)


def set_style(doc, name, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
              indent=1.25, before=0, after=0, keep=False, outline=None, size=SIZE):
    s = style(doc, name)
    font_xml(s.element.get_or_add_rPr(), bold, italic, size)
    pf = s.paragraph_format
    pf.alignment = align
    pf.left_indent = Cm(0)
    pf.right_indent = Cm(0)
    pf.first_line_indent = Cm(indent)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.keep_with_next = keep
    pf.keep_together = False
    pf.widow_control = True
    pf.page_break_before = False
    if outline is not None:
        ppr = s.element.get_or_add_pPr()
        el = ppr.find(qn('w:outlineLvl'))
        if el is None:
            el = OxmlElement('w:outlineLvl')
            ppr.append(el)
        el.set(qn('w:val'), str(outline))
    return s


def run_font(run, bold=None, italic=None, size=SIZE):
    font_xml(run._r.get_or_add_rPr(), bold, italic, size)
    return run


def configure_styles(doc):
    set_style(doc, 'Normal')
    set_style(doc, 'Body Text')
    set_style(doc, 'Heading 1', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
              indent=0, before=0, after=14, keep=True, outline=0)
    set_style(doc, 'Heading 2', bold=True, align=WD_ALIGN_PARAGRAPH.LEFT,
              indent=0, before=12, after=8, keep=True, outline=1)
    set_style(doc, 'Heading 3', bold=True, indent=0, before=10, after=6, keep=True, outline=2)
    for level, outline in ((1, 0), (2, 1), (3, 2)):
        s = style(doc, f'TOC {level}')
        # Keep the built-in style name 'TOC 1' / 'TOC 2' / 'TOC 3' — renaming it
        # makes python-docx look it up by the new name on the next call and adds
        # a duplicate styleId (breaks LibreOffice's TOC update).
        set_style(doc, f'TOC {level}', bold=(level == 1), align=WD_ALIGN_PARAGRAPH.LEFT,
                  indent=0, before=0, after=0, outline=outline)
        pf = s.paragraph_format
        pf.left_indent = Cm(0.5 * (level - 1))
        pf.tab_stops.add_tab_stop(Cm(16.4), 2, 1)  # right align, dot leader
    set_style(doc, 'TOC Heading', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
              indent=0, after=14, keep=True)
    set_style(doc, 'Caption', align=WD_ALIGN_PARAGRAPH.CENTER, indent=0,
              before=6, after=6, keep=True)
    set_style(doc, 'Table Text', align=WD_ALIGN_PARAGRAPH.LEFT, indent=0)
    set_style(doc, 'Source Note', align=WD_ALIGN_PARAGRAPH.LEFT, indent=0, after=6)
    set_style(doc, 'Formula', align=WD_ALIGN_PARAGRAPH.CENTER, indent=0, before=4, after=4)
    set_style(doc, 'Reference Entry', align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0)
    set_style(doc, 'Title', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=0)
    set_style(doc, 'Subtitle', align=WD_ALIGN_PARAGRAPH.CENTER, indent=0)
    set_style(doc, 'Header', align=WD_ALIGN_PARAGRAPH.CENTER, indent=0)
    set_style(doc, 'Footer', align=WD_ALIGN_PARAGRAPH.CENTER, indent=0)
    for name in ('Strong', 'Emphasis', 'Default Paragraph Font', 'Index Link',
                 'Heading 1 Char', 'Heading 2 Char', 'Heading 3 Char',
                 'Hyperlink', 'Title Char', 'Subtitle Char'):
        s = style(doc, name, WD_STYLE_TYPE.CHARACTER)
        font_xml(s.element.get_or_add_rPr(), True if name == 'Strong' else None,
                 True if name == 'Emphasis' else None)
    defaults = doc.styles.element.find(qn('w:docDefaults'))
    if defaults is not None:
        rpd = defaults.find(qn('w:rPrDefault'))
        if rpd is not None:
            rp = rpd.find(qn('w:rPr'))
            if rp is None:
                rp = OxmlElement('w:rPr')
                rpd.append(rp)
            font_xml(rp)
    settings = doc.settings.element
    uf = settings.find(qn('w:updateFields'))
    if uf is None:
        uf = OxmlElement('w:updateFields')
        settings.append(uf)
    uf.set(qn('w:val'), 'true')
    lang = settings.find(qn('w:themeFontLang'))
    if lang is None:
        lang = OxmlElement('w:themeFontLang')
        settings.append(lang)
    lang.set(qn('w:val'), 'tg-Cyrl-TJ')
    return doc


def configure_theme(doc):
    for part in doc.part.package.parts:
        if part.partname.startswith('/word/theme/'):
            from lxml import etree
            root = etree.fromstring(part.blob)
            ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
            for node in root.xpath('//a:majorFont | //a:minorFont', namespaces=ns):
                for child in node:
                    tag = etree.QName(child).localname
                    if tag in ('latin', 'ea', 'cs') or child.get('script'):
                        child.set('typeface', FONT if tag in ('latin', 'ea', 'cs') else '')
            part._blob = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def page_setup(section):
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.header_distance = Cm(1)
    section.footer_distance = Cm(1)
    section.different_first_page_header_footer = True


def add_field(paragraph, instruction, cached='1'):
    r = paragraph.add_run()
    el = OxmlElement('w:fldChar')
    el.set(qn('w:fldCharType'), 'begin')
    r._r.append(el)
    r = paragraph.add_run()
    el = OxmlElement('w:instrText')
    el.set(qn('xml:space'), 'preserve')
    el.text = ' ' + instruction + ' '
    r._r.append(el)
    r = paragraph.add_run()
    el = OxmlElement('w:fldChar')
    el.set(qn('w:fldCharType'), 'separate')
    r._r.append(el)
    run_font(paragraph.add_run(cached))
    r = paragraph.add_run()
    el = OxmlElement('w:fldChar')
    el.set(qn('w:fldCharType'), 'end')
    r._r.append(el)
