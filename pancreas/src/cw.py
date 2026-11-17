# -*- coding: utf-8 -*-
"""Асбобҳои сохтани ҳуҷҷати Word: ченкунии матн, симулятсияи саҳифаҳо, тавлиди DOCX."""
import os
from PIL import Image, ImageFont

# ---------------------------------------------------------------- параметрҳо
CM = 72 / 2.54
PAGE_W, PAGE_H = 21.0, 29.7          # см
ML, MR, MT, MB = 3.0, 1.5, 2.0, 2.0  # см
TEXT_W = (PAGE_W - ML - MR) * CM     # pt
TEXT_H = (PAGE_H - MT - MB) * CM     # pt

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

_EM = 2048.0
_LINE_RATIO = 1.1504          # (1825+443+87)/2048 барои Times New Roman
def line_h(size=14, spacing=1.5):
    return size * _LINE_RATIO * spacing

LH = line_h(14, 1.5)          # 24.16 pt
TLH = line_h(12, 1.0)         # 13.80 pt — барои ҷадвалҳо

_cache = {}


def _font(size_pt, bold=False, italic=False):
    name = {(False, False): "Tinos-Regular.ttf", (True, False): "Tinos-Bold.ttf",
            (False, True): "Tinos-Italic.ttf", (True, True): "Tinos-BoldItalic.ttf"}[(bold, italic)]
    key = (name, round(size_pt * 8))
    if key not in _cache:
        _cache[key] = ImageFont.truetype(os.path.join(FONT_DIR, name), int(round(size_pt * 8)))
    return _cache[key], 8.0


def text_width(s, size_pt=14, bold=False, italic=False):
    f, k = _font(size_pt, bold, italic)
    return f.getlength(s) / k


def count_lines(s, width_pt, size_pt=14, bold=False, italic=False):
    """Шумораи сатрҳо ҳангоми ба таври автоматикӣ шикастани матн."""
    if not s:
        return 1
    words = s.split(" ")
    lines, cur = 1, 0.0
    space = text_width(" ", size_pt, bold, italic)
    for w in words:
        ww = text_width(w, size_pt, bold, italic)
        if cur == 0:
            cur = ww
        elif cur + space + ww <= width_pt + 0.01:
            cur += space + ww
        else:
            lines += 1
            cur = ww
        while cur > width_pt:          # калимаи хеле дароз
            lines += 1
            cur -= width_pt
    return lines


# ---------------------------------------------------------------- блокҳо
def h1(t):
    return {"t": "h1", "x": t}


def h2(t):
    return {"t": "h2", "x": t}


def p(t):
    return {"t": "p", "x": t}


def pc(t):
    return {"t": "pc", "x": t}


def pb():
    return {"t": "pb"}


def fig(path, caption, width_cm=15.5, source=None):
    return {"t": "fig", "path": path, "cap": caption, "w": width_cm, "src": source}


def tbl(caption, head, rows, widths, source=None, size=11):
    return {"t": "tbl", "cap": caption, "head": head, "rows": rows,
            "widths": widths, "src": source, "size": size}


def formula(text, num=""):
    return {"t": "formula", "x": text, "n": num}


def bullet(t):
    return {"t": "li", "x": t}


# ---------------------------------------------------------------- андозаҳо
def fig_size(block):
    img = Image.open(os.path.join(BASE, block["path"]))
    w_pt = block["w"] * CM
    h_pt = w_pt * img.size[1] / img.size[0]
    return w_pt, h_pt


def block_height(b):
    kind = b["t"]
    if kind == "h1":
        n = count_lines(b["x"], TEXT_W, 14, bold=True)
        return n * LH + 6
    if kind == "h2":
        n = count_lines(b["x"], TEXT_W - 1.25 * CM, 14, bold=True)
        return n * LH + 14
    if kind == "p":
        n = count_lines(b["x"], TEXT_W - 1.25 * CM, 14)
        # сатри аввал 1.25 см кам ҷойгир аст, дурусткунии дақиқ:
        n = count_lines(b["x"], TEXT_W, 14) if n <= 1 else n
        return n * LH
    if kind == "pc":
        n = count_lines(b["x"], TEXT_W, 14)
        return n * LH
    if kind == "li":
        n = count_lines(b["x"], TEXT_W - 0.75 * CM, 14)
        return n * LH
    if kind == "formula":
        return LH + 6
    if kind == "fig":
        _, h = fig_size(b)
        cap_lines = count_lines(b["cap"], TEXT_W, 12, bold=True)
        extra = 6 + 6 + (4 if b.get("src") else 0)
        return h + cap_lines * TLH + extra
    if kind == "tbl":
        cap_lines = count_lines(b["cap"], TEXT_W, 12, bold=True)
        h = cap_lines * TLH + 6
        colw = [w * CM for w in b["widths"]]
        for row in [b["head"]] + b["rows"]:
            rlines = 1
            for cell, w in zip(row, colw):
                rlines = max(rlines, count_lines(str(cell), w - 0.4 * CM, b["size"],
                                                 bold=(row is b["head"])))
            h += rlines * line_h(b["size"], 1.0) + 2.0
        if b.get("src"):
            h += TLH + 4
        return h + 6
    if kind == "pb":
        return 0
    raise ValueError(kind)


# ---------------------------------------------------------------- саҳифабандӣ
class Layout:
    def __init__(self):
        self.page = 1
        self.y = 0.0
        self.entries = []       # (level, матн, саҳифа)

    def new_page(self):
        self.page += 1
        self.y = 0.0

    def place(self, b):
        kind = b["t"]
        if kind == "pb":
            self.new_page()
            return
        if kind == "h1":
            if self.y > 0:
                self.new_page()
            self.entries.append((1, b["x"], self.page))
            self.y += block_height(b)
            return
        h = block_height(b)
        if kind == "h2":
            self.entries.append((2, b["x"], self.page))
            # сарлавҳа аз матн ҷудо нашавад
            if self.y + h + 2 * LH > TEXT_H:
                self.new_page()
        if kind in ("p", "pc", "li"):
            # матн байни сатрҳо шикаста мешавад
            lines = max(1, int(round(h / LH)))
            while lines > 0:
                avail = max(0, int((TEXT_H - self.y + 0.5) / LH))
                if lines <= avail:
                    self.y += lines * LH
                    return
                lines -= avail
                self.new_page()
            return
        if self.y + h > TEXT_H:
            self.new_page()
        self.y += h

    def run(self, blocks):
        for b in blocks:
            self.place(b)
        return self.page, self.entries


def simulate(blocks):
    lay = Layout()
    total, entries = lay.run(blocks)
    return total, entries
