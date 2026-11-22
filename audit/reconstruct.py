# -*- coding: utf-8 -*-
"""v4: clean line-grid segmentation of the coursework PDF.

Rules
-----
* merge same-baseline fragments first (Word justification splits lines)
* a new block starts when the PREVIOUS line ended a sentence and the next line
  is not a justified continuation of a full-width line, or the line starts
  with a list marker, or the previous line is a short (paragraph-final) line
* continuation lines are appended with a single space
"""
import pymupdf, json, re

PDF = "/tmp/arena-coding-uploads/УЛТРАСАДОИ ГУРДАҲО.pdf"
d = pymupdf.open(PDF)

TABLE_RANGES = {
 16: [(244, 505)], 21: [(468, 745)], 25: [(50, 300)], 29: [(515, 780)],
 34: [(58, 240), (600, 800)], 35: [(50, 215)], 38: [(200, 470)],
 41: [(695, 800)], 42: [(45, 335), (388, 645)], 49: [(505, 800)],
 50: [(45, 145), (170, 515)],
}
BULLETS = "•▪➢❖✓→"
MARK_RE = re.compile(r"^([•▪➢❖✓→]|\d{1,2}\.\s?|[a-e][.)]\s?|o(?=[А-ЯЁӢҚҒҲҶӮ]))")
TERM = (".", "!", "?", ":", ";", "»")
FULL = 495.0          # a line ending beyond this x is "full width" (wrapped)
INDENT_MIN = 112.0     # lines starting at/after this x are indented paragraph starts

def in_table(pno, y):
    return any(a - 1 <= y <= b for a, b in TABLE_RANGES.get(pno, []))

def lines_of(pg):
    raw = []
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            spans = [s for s in l["spans"] if s["text"].strip()]
            if not spans:
                continue
            raw.append({"x0": round(l["bbox"][0], 1), "x1": round(l["bbox"][2], 1),
                        "y": round(l["bbox"][1], 1),
                        "text": "".join(s["text"] for s in spans),
                        "allbold": all("Bold" in s["font"] for s in spans)})
    raw.sort(key=lambda l: (l["y"], l["x0"]))
    out = []
    for l in raw:
        if out and abs(out[-1]["y"] - l["y"]) < 3.0 and l["x0"] > out[-1]["x0"]:
            m = out[-1]
            a, b = m["text"], l["text"]
            if a and b and not a.endswith(" ") and not b.startswith(" "):
                a += " "
            m["text"] = (a + b).strip()
            m["x1"] = max(m["x1"], l["x1"])
            m["allbold"] = m["allbold"] and l["allbold"]
        else:
            out.append(dict(l))
    return out

def heading_kind(t, x0):
    if re.match(r"^(БОБИ|МУҚАДДИМА|ХУЛОСА|РӮЙХАТИ|НАҚША|ЗАМИМА)", t):
        return "h1"
    if re.match(r"^\d\.\d\.\s", t):
        return "h2"
    if x0 > 135:
        return "h3c"
    return "h3l"

def build():
    """Single pass over all lines in reading order.

    State
    -----
    items : finished blocks (the last one may still receive a continuation
            when a page break split a sentence)
    open_ : the block currently receiving lines (None between paragraphs)
    prev  : the last physical line consumed, used for the wrap test
    """
    items = []
    cur = None          # block being extended, None when the next line starts one
    prev = None         # last line consumed on the CURRENT page

    for pno in range(1, d.page_count + 1):
        L = [l for l in lines_of(d[pno - 1]) if not in_table(pno, l["y"])]
        first_on_page = True
        for l in L:
            t = l["text"].strip()
            if not t:
                continue
            x0, x1 = l["x0"], l["x1"]

            # ---------------- TOC page ----------------
            if pno == 1:
                if cur and cur["kind"] == "toc" and cur["b"] == l["allbold"]:
                    cur["text"] += "\n" + t
                else:
                    if cur:
                        items.append(cur)
                    cur = {"kind": "toc", "text": t, "page": 1, "b": l["allbold"]}
                prev = l
                continue

            # ---------------- bold line = heading ----------------
            if l["allbold"]:
                if (cur and cur["kind"].startswith("h") and cur["page"] == pno
                        and (l["y"] - cur["y"]) < 22 and x0 >= cur.get("x0", 0) - 5
                        # only a heading that WRAPPED continues on the next line;
                        # a short heading line followed by another heading is not
                        # a continuation ("РӮЙХАТИ АДАБИЁТ" / "Китобҳо ва …")
                        and cur.get("x1", 0) > 480):
                    cur["text"] += " " + t
                    cur["y"] = l["y"]
                    prev = l
                    continue
                if cur:
                    items.append(cur)
                cur = {"kind": heading_kind(t, x0), "text": t, "page": pno,
                       "x0": x0, "x1": x1, "y": l["y"]}
                prev = l
                first_on_page = False
                continue

            marker = bool(MARK_RE.match(t))
            starts_new = True

            if items and items[-1]["page"] == pno - 1 and not marker:
                # a sentence cut by the page break: glue it back to the last block
                last = items[-1]
                if (last["kind"] in ("p", "li") and last["page"] == pno - 1
                        and last["text"].rstrip()[-1:] not in TERM
                        and not t[:1].isupper()):
                    last["text"] = last["text"].rstrip() + " " + t
                    last["last_x1"] = x1
                    last["y"] = l["y"]
                    prev = l
                    first_on_page = False
                    cur = None
                    continue

            if marker:
                starts_new = True
            elif cur is not None and cur["kind"] in ("p", "li") and prev is not None:
                # a line that does not end a sentence continues in the next one,
                # no matter where that next line starts (justified wrapping)
                ptxt = prev["text"].rstrip()
                if ptxt.endswith(")") and not t[:1].isupper():
                    starts_new = False      # "(Papilla renalis) ном дорад."
                else:
                    starts_new = ptxt.endswith(TERM) or ptxt.endswith(")")
                # bibliographic wrap lines: a reference item ends with a year
                # ("… Elsevier, 2018.") and the item number is on the previous
                # line, so a following x0≈121 line is a continuation
                if (starts_new and cur["kind"] == "li" and 115 <= x0 <= 128
                        and prev["x0"] < 110):
                    starts_new = False

            if starts_new:
                if cur:
                    items.append(cur)
                kind = "li" if marker else "p"
                if kind == "li" and t.startswith("o") and t[1:2].isupper():
                    t = "•" + t[1:]
                cur = {"kind": kind, "text": t, "page": pno, "x0": x0,
                       "x1": x1, "last_x1": x1, "y": l["y"]}
            else:
                cur["text"] = cur["text"].rstrip() + " " + t
                cur["last_x1"] = x1
                cur["y"] = l["y"]
            prev = l
            first_on_page = False
        if cur:
            items.append(cur)
        cur = None
        prev = None
    return items


items = build()
json.dump(items, open("blocks.json", "w"), ensure_ascii=False, indent=1)
open("blocks_readable.txt", "w").write(
    "\n\n".join("[p%d %s x0=%.0f] %s" % (b["page"], b["kind"], b.get("x0", 0), b["text"])
                 for b in items))
print("blocks:", len(items), "chars:", sum(len(b["text"]) for b in items))
