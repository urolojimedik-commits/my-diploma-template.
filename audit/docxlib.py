# -*- coding: utf-8 -*-
"""Helpers: shading, borders, comments-free docx utilities."""
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HIGHLIGHT_COLORS = {
    "yellow": "FFFF00",
    "red": "FF0000",
    "green": "00B050",
    "lightred": "FFC7CE",
    "lightgreen": "C6EFCE",
    "lightyellow": "FFF2CC",
}

def set_run_highlight(run, color):
    rPr = run._element.get_or_add_rPr()
    hl = rPr.find(qn('w:highlight'))
    if hl is None:
        hl = OxmlElement('w:highlight')
        rPr.append(hl)
    hl.set(qn('w:val'), color)

def set_run_shading(run, hexfill):
    rPr = run._element.get_or_add_rPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hexfill)
    rPr.append(shd)

def set_run_color(run, hexcolor):
    rPr = run._element.get_or_add_rPr()
    c = OxmlElement('w:color'); c.set(qn('w:val'), hexcolor); rPr.append(c)

def set_run_underline(run, val="single", color=None):
    u = OxmlElement('w:u'); u.set(qn('w:val'), val)
    if color: u.set(qn('w:color'), color)
    run._element.get_or_add_rPr().append(u)

def set_run_bold(run, on=True):
    run.bold = on

def cell_shading(cell, hexfill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), hexfill)
    tcPr.append(shd)

def table_borders(table, sz=4, color="808080"):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'),'single'); el.set(qn('w:sz'),str(sz))
        el.set(qn('w:space'),'0'); el.set(qn('w:color'),color)
        borders.append(el)
    tblPr.append(borders)

def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement('w:tblHeader'); el.set(qn('w:val'),'true')
    trPr.append(el)

def keep_with_next(par, on=True):
    pPr = par._p.get_or_add_pPr()
    el = OxmlElement('w:keepNext'); el.set(qn('w:val'),'1' if on else '0')
    pPr.append(el)

def add_field(par, instr):
    """Insert a complex field (e.g. PAGE) into paragraph."""
    r = par.add_run()
    fld = OxmlElement('w:fldChar'); fld.set(qn('w:fldCharType'),'begin'); r._r.append(fld)
    r2 = par.add_run()
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'),'preserve'); it.text = instr; r2._r.append(it)
    r3 = par.add_run()
    fld2 = OxmlElement('w:fldChar'); fld2.set(qn('w:fldCharType'),'separate'); r3._r.append(fld2)
    r4 = par.add_run("1")
    r5 = par.add_run()
    fld3 = OxmlElement('w:fldChar'); fld3.set(qn('w:fldCharType'),'end'); r5._r.append(fld3)
    return r4

def set_cell_margins(table, top=50, bottom=50, left=80, right=80):
    tblPr = table._tbl.tblPr
    mar = OxmlElement('w:tblCellMar')
    for k,v in (('top',top),('left',left),('bottom',bottom),('right',right)):
        el = OxmlElement(f'w:{k}'); el.set(qn('w:w'),str(v)); el.set(qn('w:type'),'dxa'); mar.append(el)
    tblPr.append(mar)
