#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_docx.py — Санҷиши техникии файли .docx пеш аз додан ба корбар.

Месанҷад он хатоҳое, ки Word файлро «вайрон» ҳисобида кушода наметавонад:

  1. ZIP ва XML-и солим
  2. Тартиби дурусти унсурҳо дар settings.xml (w:updateFields бояд пеш аз
     w:compat / w:rsids / w:themeFontLang / w:clrSchemeMapping бошад)
  3. Майдонҳо (fldChar / instrText): ҳар қисм дар run-и алоҳида
  4. Навбати дурусти фарзандони rPr (rFonts → b → i → sz → szCs …)
  5. Навбати дурусти фарзандони pPr
  6. newline-и хом дар дохили <w:t>
  7. Ҳамаи r:id дар document.xml бояд дар _rels муайян шуда бошанд
  8. Ҳамаи унсурҳои <w:tbl> бояд <w:tblGrid> дошта бошанд
  9. Мавҷудияти қисмҳои ҳатмӣ ([Content_Types].xml, _rels/.rels)

Истифода:
    python coursework/scripts/validate_docx.py файл.docx
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W, "r": R}

# Тартиби дурусти фарзандони <w:rPr> тибқи ECMA-376
RPR_ORDER = [
    "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike",
    "dstrike", "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid",
    "vanish", "webHidden", "color", "spacing", "w", "kern", "position", "sz",
    "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign",
    "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath",
]

# Тартиби дурусти фарзандони <w:pPr>
PPR_ORDER = [
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
    "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs",
    "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
    "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
    "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
    "suppressOverlap", "jc", "textDirection", "textAlignment",
    "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr",
    "pPrChange",
]

# Тартиби дурусти фарзандони <w:settings>
SETTINGS_ORDER = [
    "writeProtection", "view", "zoom", "removePersonalInformation",
    "removeDateAndTime", "doNotDisplayPageBoundaries", "displayBackgroundShape",
    "printPostScriptOverText", "printFractionalCharacterWidth",
    "printFormsData", "embedTrueTypeFonts", "embedSystemFonts",
    "saveSubsetFonts", "saveFormsData", "mirrorMargins", "alignBordersAndEdges",
    "bordersDoNotSurroundHeader", "bordersDoNotSurroundFooter",
    "gutterAtTop", "hideSpellingErrors", "hideGrammaticalErrors",
    "activeWritingStyle", "proofState", "formsDesign", "attachedTemplate",
    "linkStyles", "stylePaneFormatFilter", "stylePaneSortMethod",
    "documentType", "mailMerge", "revisionView", "trackChanges",
    "doNotTrackMoves", "doNotTrackFormatting", "documentProtection",
    "autoFormatOverride", "styleLockTheme", "styleLockQFSet", "defaultTabStop",
    "autoHyphenation", "consecutiveHyphenLimit", "hyphenationZone",
    "doNotHyphenateCaps", "showEnvelope", "summaryLength", "clickAndTypeStyle",
    "defaultTableStyle", "evenAndOddHeaders", "bookFoldRevPrinting",
    "bookFoldPrinting", "bookFoldPrintingSheets", "drawingGridHorizontalSpacing",
    "drawingGridVerticalSpacing", "displayHorizontalDrawingGridEvery",
    "displayVerticalDrawingGridEvery", "doNotUseMarginsForDrawingGridOrigin",
    "drawingGridHorizontalOrigin", "drawingGridVerticalOrigin",
    "doNotShadeFormData", "noPunctuationKerning", "characterSpacingControl",
    "printTwoOnOne", "strictFirstAndLastChars", "noLineBreaksAfter",
    "noLineBreaksBefore", "savePreviewPicture", "doNotValidateAgainstSchema",
    "saveInvalidXml", "ignoreMixedContent", "alwaysShowPlaceholderText",
    "doNotDemarcateInvalidXml", "saveXmlDataOnly", "useXSLTWhenSaving",
    "saveThroughXslt", "showXMLTags", "alwaysMergeEmptyNamespace",
    "updateFields", "hdrShapeDefaults", "footnotePr", "endnotePr", "compat",
    "docVars", "rsids", "mathPr", "attachedSchema", "themeFontLang",
    "clrSchemeMapping", "doNotIncludeSubdocsInStats",
    "doNotAutoCompressPictures", "forceUpgrade", "captions", "readModeInkLockDown",
    "smartTagType", "schemaLibrary", "shapeDefaults", "doNotEmbedSmartTags",
    "decimalSymbol", "listSeparator",
]


class Report:
    def __init__(self, path: Path):
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.ok: list[str] = []

    def err(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def good(self, msg: str):
        self.ok.append(msg)

    def print(self) -> int:
        print(f"\n📄 {self.path.name}")
        print("=" * 70)
        for m in self.ok:
            print(f"  ✅ {m}")
        for m in self.warnings:
            print(f"  ⚠️  {m}")
        for m in self.errors:
            print(f"  ❌ {m}")
        print("=" * 70)
        if self.errors:
            print(f"❌ {len(self.errors)} хато — файл ба Word дода нашавад!")
            return 1
        print("✅ Файл солим аст — Word онро мекушояд." +
              (f" ({len(self.warnings)} огоҳӣ)" if self.warnings else ""))
        return 0


def check_zip(z: zipfile.ZipFile, rep: Report):
    names = z.namelist()
    for must in ("[Content_Types].xml", "_rels/.rels", "word/document.xml"):
        if must in names:
            rep.good(f"қисми ҳатмӣ ҳаст: {must}")
        else:
            rep.err(f"қисми ҳатмӣ НЕСТ: {must}")

    bad = z.testzip()
    if bad:
        rep.err(f"ZIP вайрон: {bad}")
    else:
        rep.good(f"ZIP солим ({len(names)} файл)")

    for name in names:
        if name.endswith((".xml", ".rels")):
            try:
                ET.fromstring(z.read(name))
            except ET.ParseError as e:
                rep.err(f"XML-и вайрон: {name} — {e}")


def check_settings(z: zipfile.ZipFile, rep: Report):
    if "word/settings.xml" not in z.namelist():
        rep.warn("word/settings.xml нест (Word онро худ месозад)")
        return
    root = ET.fromstring(z.read("word/settings.xml"))
    order = {qn: i for i, qn in enumerate(SETTINGS_ORDER)}

    prev_idx = -1
    prev_tag = ""
    for child in root:
        tag = child.tag.split("}")[-1]
        idx = order.get(tag)
        if idx is None:
            continue  # унсурҳои w14:*, m:* ва монанди он
        if idx < prev_idx:
            rep.err(
                f"settings.xml: <w:{tag}> бояд ПЕШ аз <w:{prev_tag}> бошад "
                f"(схемаи OOXML вайрон шудааст → Word файлро кушода наметавонад)"
            )
            return
        prev_idx, prev_tag = idx, tag
    rep.good("settings.xml: тартиби унсурҳо дуруст аст")

    uf = root.find(f"{{{W}}}updateFields")
    if uf is not None:
        rep.good("settings.xml: w:updateFields дар ҷои дуруст (мундариҷа худкор нав мешавад)")


def check_fields(z: zipfile.ZipFile, rep: Report):
    """Ҳар қисми майдон бояд дар run-и алоҳида бошад."""
    for part in ("word/document.xml", "word/footer1.xml", "word/footer2.xml",
                 "word/header1.xml", "word/header2.xml"):
        if part not in z.namelist():
            continue
        xml = z.read(part).decode("utf-8")
        bad = 0
        for run in re.findall(r"<w:r>(.*?)</w:r>", xml, re.S):
            marks = len(re.findall(r"<w:fldChar", run)) + len(re.findall(r"<w:instrText", run))
            if marks > 1:
                bad += 1
        if bad:
            rep.err(f"{part}: {bad} run дорои зиёда аз як қисми майдон (бояд ҳар як дар run-и алоҳида)")
        else:
            rep.good(f"{part}: майдонҳо дуруст ҷудо шудаанд")


def check_ppr_rpr(z: zipfile.ZipFile, rep: Report):
    for part in ("word/document.xml", "word/styles.xml",
                 "word/footer1.xml", "word/footer2.xml"):
        if part not in z.namelist():
            continue
        xml = z.read(part).decode("utf-8")
        for tag, order_list, label in (
            ("rPr", RPR_ORDER, "rPr"),
            ("pPr", PPR_ORDER, "pPr"),
        ):
            order = {n: i for i, n in enumerate(order_list)}
            bad = 0
            example = ""
            for block in re.findall(rf"<w:{tag}>(.*?)</w:{tag}>", xml, re.S):
                seq = []
                for m in re.finditer(r"<w:([a-zA-Z]+)[ />]", block):
                    t = m.group(1)
                    if t in order:
                        seq.append((order[t], t))
                if not seq:
                    continue
                max_seen = -1
                max_tag = ""
                for val, t in seq:
                    if val < max_seen and t != max_tag:
                        bad += 1
                        example = f"<w:{t}> пас аз <w:{max_tag}>"
                        break
                    max_seen, max_tag = val, t
            if bad:
                rep.warn(f"{part}: {bad} {label} бо тартиби нодуруст (мисол: {example})")
            else:
                rep.good(f"{part}: тартиби фарзандони {label} дуруст")


def check_text_newlines(z: zipfile.ZipFile, rep: Report):
    xml = z.read("word/document.xml").decode("utf-8")
    bad = 0
    for m in re.finditer(r"<w:t[^>]*>(.*?)</w:t>", xml, re.S):
        if "\n" in m.group(1) or "\r" in m.group(1):
            bad += 1
    if bad:
        rep.err(f"document.xml: {bad} <w:t> newline-и хом дорад (бояд <w:br/> бошад)")
    else:
        rep.good("document.xml: newline-и хом нест")


def check_rels(z: zipfile.ZipFile, rep: Report):
    names = z.namelist()
    for part in ("word/document.xml", "word/footer1.xml", "word/footer2.xml"):
        if part not in names:
            continue
        rels = part.rsplit("/", 1)[0] + "/_rels/" + part.rsplit("/", 1)[1] + ".rels"
        if rels not in names:
            continue
        xml = z.read(part).decode("utf-8")
        ids = set(re.findall(r'r:(?:id|embed)="([^"]+)"', xml))
        rel_xml = z.read(rels).decode("utf-8")
        defined = set(re.findall(r'Id="([^"]+)"', rel_xml))
        missing = ids - defined
        if missing:
            rep.err(f"{part}: r:id берун аз {rels} — {sorted(missing)}")
        else:
            rep.good(f"{part}: ҳамаи r:id муайян шудаанд")


def check_tables(z: zipfile.ZipFile, rep: Report):
    xml = z.read("word/document.xml").decode("utf-8")
    n_tbl = xml.count("<w:tbl>")
    n_grid = xml.count("<w:tblGrid")
    if n_tbl == 0:
        rep.warn("ҷадвал нест")
        return
    if n_grid < n_tbl:
        rep.err(f"{n_tbl} ҷадвал, вале танҳо {n_grid} <w:tblGrid> — Word ҷадвалро кушода наметавонад")
    else:
        rep.good(f"ҷадвалҳо: {n_tbl}, tblGrid: {n_grid}")

    # ҳар сатр бояд ҳамон шумораи ҳуҷайра дошта бошад, ки tblGrid мегӯяд
    for num, tbl in enumerate(re.findall(r"<w:tbl>.*?</w:tbl>", xml, re.S), 1):
        cols = len(re.findall(r"<w:gridCol[ /]", tbl))
        if cols == 0:
            continue
        for row in re.findall(r"<w:tr[ >].*?</w:tr>", tbl, re.S):
            cells = len(re.findall(r"<w:tc>", row))
            if cells != cols:
                rep.warn(f"ҷадвали {num}: {cells} ҳуҷайра, вале {cols} сутун дар tblGrid")
                break


def main(path: Path) -> int:
    rep = Report(path)
    if not path.exists():
        print(f"Файл ёфт нашуд: {path}")
        return 2
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        rep.err(f"файл ZIP нест: {e}")
        return rep.print()
    check_zip(z, rep)
    check_settings(z, rep)
    check_fields(z, rep)
    check_ppr_rpr(z, rep)
    check_text_newlines(z, rep)
    check_rels(z, rep)
    check_tables(z, rep)
    return rep.print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    code = 0
    for p in sys.argv[1:]:
        code |= main(Path(p))
    sys.exit(code)
