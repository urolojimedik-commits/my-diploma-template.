"""Тесты этапа 2: титульный лист, ГОСТ-разметка и автонумерация в Word.

Проверяется главное требование: номера глав, параграфов, рисунков и таблиц
вставляются **полями Word** (SEQ/TOC/PAGE), а не вписанными цифрами, —
то есть Word перенумерует их сам при вставке нового материала.

Запуск:  python -m unittest discover -s tests
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm

from diploma.model import Author, Source
from diploma.render.content import (
    AbbrevBlock,
    Appendix,
    Bullets,
    FigureBlock,
    Heading,
    MedicalDocument,
    Para,
    RefList,
    TableBlock,
    TitlePage,
    TOC,
    assign_numbers,
)
from diploma.render.docx_med import build_docx
from diploma.sources.gost_med import citation_map, format_bibliography_med
from diploma.structure.medical import get_profile

SOURCES = [
    Source(
        key="turk2016",
        title="EAU Guidelines on Urolithiasis",
        authors=[Author("Turk", "C")],
        year=2016,
        venue="Eur Urol",
        volume="69",
        pages="468-474",
        doi="10.1016/j.eururo.2015.07.040",
        pmid="26318714",
        verified=True,
    ),
    Source(
        key="yildirim2021",
        title="Deep learning model for automated kidney stone detection",
        authors=[Author("Yildirim", "K")],
        year=2021,
        venue="Comput Biol Med",
        volume="135",
        pages="104569",
        doi="10.1016/j.compbiomed.2021.104569",
        verified=True,
    ),
]

FIG_PATH = Path(__file__).resolve().parent.parent / "build" / "stage2" / "media" / "fig1.png"


def sample_document(path: Path, numbering: str = "per_chapter") -> MedicalDocument:
    doc = MedicalDocument()
    doc.numbering = numbering
    doc.add(TitlePage(work_type="diploma", topic="Санги гурда: ташхис",
                      author="Алиев А. А.", supervisor="Петров П. П.",
                      city="Хуҷанд", year=2026, frame=True))
    doc.add(TOC())
    doc.add(Heading("Аннотатсия", numbered=False))
    doc.add(Para("Матни аннотатсия 12.5 %, ки бо вергул навишта мешавад.", style="annotation"))
    doc.add(AbbrevBlock(pairs=[("КТ", "томографияи компютерӣ")]))
    doc.add(Heading("Муқаддима", numbered=False))
    doc.add(Para("Маълумот аз {src:turk2016} гирифта шуд. Ин ҷо {fig:fig1} нишон дода шудааст."))
    doc.add(Bullets(items=["аввал;", "баъд."]))
    doc.add(Heading("Баррасии адабиёт", level=1))
    doc.add(Heading("Вазъи масъала", level=2))
    doc.add(Para("Матн."))
    doc.add(Heading("Мавод ва усулҳо", level=1))
    doc.add(Heading("Тарҳи таҳқиқот", level=2))
    doc.add(TableBlock(key="tbl1", header=["Нишондиҳанда", "Гурӯҳ"], rows=[["n", "Маълумот нокифоя"]],
                       caption="Хусусияти беморон", provenance="unknown"))
    doc.add(Heading("Натиҷаҳо", level=1))
    doc.add(Para("Натиҷа дар {fig:fig1} ва {tbl:tbl1} оварда шудааст."))
    doc.add(FigureBlock(key="fig1", path=str(path), caption="Муқоисаи усулҳо",
                        provenance="synthetic"))
    doc.add(Heading("Хулоса", numbered=False))
    doc.add(RefList(entries=format_bibliography_med(SOURCES)))
    doc.add(Appendix(title="Протоколи санҷиш",
                     blocks=[TableBlock(key="tblA1", header=["Сарчашма", "DOI"],
                                        rows=[["turk2016", "10.1016/j.eururo.2015.07.040"]],
                                        caption="Санҷиш", provenance="real")]))
    return doc


class DocxCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="docx_med_"))
        self.out = self.tmp / "document.docx"
        self.fig = FIG_PATH
        if not self.fig.exists():  # строим учебный рисунок при первом запуске
            from make_docx_demo import make_figure

            self.fig = make_figure(self.fig)
        self.doc = sample_document(self.fig)
        build_docx(self.doc, self.out, citation_map=citation_map(SOURCES))
        self.document = Document(str(self.out))

    # ------------------------------------------------------------- помощники
    def instructions(self) -> list[str]:
        out: list[str] = []
        for p in self.document.paragraphs:
            out.extend(n.text.strip() for n in p._p.iter(qn("w:instrText")))
        for section in self.document.sections:
            for p in list(section.footer.paragraphs) + list(section.header.paragraphs):
                out.extend(n.text.strip() for n in p._p.iter(qn("w:instrText")))
        return out

    def text_of(self, predicate) -> list[str]:
        return [p.text.strip() for p in self.document.paragraphs if predicate(p)]


class TestPageSetup(DocxCase):
    def test_page_size_a4(self):
        s = self.document.sections[0]
        self.assertAlmostEqual(s.page_width.cm, 21.0, places=1)
        self.assertAlmostEqual(s.page_height.cm, 29.7, places=1)

    def test_margins_from_config(self):
        s = self.document.sections[0]
        self.assertAlmostEqual(s.left_margin.cm, 3.0, places=1)
        self.assertAlmostEqual(s.right_margin.cm, 1.5, places=1)
        self.assertAlmostEqual(s.top_margin.cm, 2.0, places=1)
        self.assertAlmostEqual(s.bottom_margin.cm, 2.0, places=1)

    def test_normal_style_gost(self):
        st = self.document.styles["Normal"]
        self.assertEqual(st.font.name, "Times New Roman")
        self.assertEqual(st.font.size.pt, 14)
        self.assertEqual(st.paragraph_format.line_spacing, 1.5)
        self.assertAlmostEqual(st.paragraph_format.first_line_indent.cm, 1.25, places=2)

    def test_heading_styles(self):
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        h1 = self.document.styles["Heading 1"]
        self.assertTrue(h1.font.bold)
        self.assertEqual(h1.paragraph_format.alignment, WD_ALIGN_PARAGRAPH.CENTER)
        self.assertTrue(h1.paragraph_format.page_break_before)

    def test_language_is_tajik(self):
        rPr = self.document.styles["Normal"].element.get_or_add_rPr()
        lang = rPr.find(qn("w:lang"))
        self.assertIsNotNone(lang)
        self.assertEqual(lang.get(qn("w:val")), "tg-Cyrl-TJ")


class TestTitlePage(DocxCase):
    def setUp(self):
        super().setUp()
        self.texts = [p.text for p in self.document.paragraphs]

    def test_university_requisites(self):
        uni = get_profile().university
        joined = "\n".join(self.texts)
        self.assertIn(uni["ministry"], joined)
        self.assertIn(uni["name"], joined)
        self.assertIn(uni["faculty"], joined)

    def test_work_type_and_topic(self):
        joined = "\n".join(self.texts)
        self.assertIn("КОРИ ХАТМКУНАНДАГОН", joined)
        self.assertIn("Санги гурда", joined)

    def test_supervisor_and_city_year(self):
        joined = "\n".join(self.texts)
        self.assertIn("Петров П. П.", joined)
        self.assertIn("Хуҷанд — 2026", joined)

    def test_tajik_letters_present(self):
        joined = "\n".join(self.texts)
        # специфические буквы таджикского алфавита из реквизитов вуза
        for ch in "ҷӣқҳ":
            self.assertIn(ch, joined.lower())

    def test_frame_drawn(self):
        self.assertIsNotNone(self.document.sections[0]._sectPr.find(qn("w:pgBorders")))

    def test_two_sections(self):
        self.assertEqual(len(self.document.sections), 2)


class TestAutoNumbering(DocxCase):
    def test_toc_field(self):
        self.assertTrue(any(i.startswith("TOC") for i in self.instructions()))

    def test_chapter_seq_without_reset(self):
        chapter_fields = [i for i in self.instructions() if i.startswith("SEQ Chapter")]
        self.assertTrue(chapter_fields)
        self.assertTrue(any(i == r"SEQ Chapter \* ARABIC" for i in chapter_fields))
        # \s 1 в главе сбросил бы счётчик в самой главе — все главы стали бы «Боби 1»
        self.assertFalse(any(r"\s 1" in i for i in chapter_fields if not i.endswith(r"\c")))

    def test_section_seq_restarts_per_chapter(self):
        fields = [i for i in self.instructions() if i.startswith("SEQ Section")]
        self.assertTrue(fields)
        for f in fields:
            self.assertIn(r"\s 1", f)

    def test_figure_and_table_seq(self):
        fields = self.instructions()
        self.assertTrue(any(i.startswith("SEQ Figure") and r"\s 1" in i for i in fields))
        self.assertTrue(any(i.startswith("SEQ Table") and r"\s 1" in i for i in fields))

    def test_cross_reference_uses_seq_c(self):
        fields = [i for i in self.instructions() if i.startswith("SEQ Figure") and r"\c" in i]
        self.assertTrue(fields, "перекрёстная ссылка должна быть полем SEQ ... \\c")

    def test_cross_reference_word_before_number(self):
        joined = "\n".join(p.text for p in self.document.paragraphs)
        self.assertIn("расми\xa03.1", joined)

    def test_captions_have_fields(self):
        caption = [p for p in self.document.paragraphs if p.text.startswith("Расм 3.1")]
        self.assertEqual(len(caption), 1)
        instr = [n.text.strip() for n in caption[0]._p.iter(qn("w:instrText"))]
        self.assertTrue(any("SEQ Figure" in i for i in instr))

    def test_appendix_letter_field(self):
        fields = [i for i in self.instructions() if i.startswith("SEQ Appendix")]
        self.assertTrue(any(r"ALPHABETIC" in i for i in fields))

    def test_appendix_table_number(self):
        joined = "\n".join(p.text for p in self.document.paragraphs)
        self.assertIn("Ҷадвал А.1", joined)

    def test_numbering_matches_assign_numbers(self):
        numbers = assign_numbers(self.doc, citation_map(SOURCES))
        self.assertEqual(numbers["fig:fig1"], "3.1")
        self.assertEqual(numbers["tbl:tbl1"], "2.1")
        self.assertEqual(numbers["tbl:tblA1"], "А.1")

    def test_continuous_mode_has_no_chapter_reset(self):
        out = self.tmp / "continuous.docx"
        doc = sample_document(self.fig, numbering="continuous")
        build_docx(doc, out, citation_map=citation_map(SOURCES))
        document = Document(str(out))
        fields = [
            n.text.strip()
            for p in document.paragraphs
            for n in p._p.iter(qn("w:instrText"))
        ]
        self.assertTrue(any(i.startswith("SEQ Figure") for i in fields))
        self.assertFalse(any(i.startswith("SEQ Figure") and r"\s 1" in i for i in fields))


class TestPageNumbers(DocxCase):
    def test_page_field_in_second_section(self):
        fields = [
            n.text.strip()
            for p in self.document.sections[1].footer.paragraphs
            for n in p._p.iter(qn("w:instrText"))
        ]
        self.assertIn("PAGE", fields)

    def test_title_page_has_no_number(self):
        fields = [
            n.text.strip()
            for p in self.document.sections[0].footer.paragraphs
            for n in p._p.iter(qn("w:instrText"))
        ]
        self.assertEqual(fields, [])

    def test_numbering_starts_at_two(self):
        pg = self.document.sections[1]._sectPr.find(qn("w:pgNumType"))
        self.assertIsNotNone(pg)
        self.assertEqual(pg.get(qn("w:start")), "2")


class TestDataPolicyInDocx(DocxCase):
    def test_synthetic_figure_marked(self):
        joined = "\n".join(p.text for p in self.document.paragraphs)
        self.assertIn("Намунаи таълимӣ", joined)

    def test_unknown_data_marker(self):
        joined = "\n".join(p.text for p in self.document.paragraphs)
        self.assertIn("Маълумот нокифоя", joined)

    def test_unknown_source_is_question_mark(self):
        out = self.tmp / "unknown.docx"
        doc = MedicalDocument()
        doc.add(Heading("Муқаддима", numbered=False))
        doc.add(Para("Иқтибос аз {src:nosuchkey}."))
        build_docx(doc, out)
        joined = "\n".join(p.text for p in Document(str(out)).paragraphs)
        self.assertIn("[?]", joined)
        self.assertNotIn("[src:nosuchkey]", joined)

    def test_unknown_figure_ref_not_invented(self):
        out = self.tmp / "unknown_fig.docx"
        doc = MedicalDocument()
        doc.add(Heading("Муқаддима", numbered=False))
        doc.add(Para("Ниг.: {fig:nosuch}."))
        build_docx(doc, out)
        joined = "\n".join(p.text for p in Document(str(out)).paragraphs)
        self.assertIn("Маълумот нокифоя", joined)

    def test_orthography_applied(self):
        joined = "\n".join(p.text for p in self.document.paragraphs)
        self.assertIn("12,5 %", joined)

    def test_doi_not_corrupted(self):
        joined = "\n".join(p.text for p in self.document.paragraphs)
        self.assertIn("10.1016/j.eururo.2015.07.040", joined)
        self.assertNotIn("10,1016", joined)

    def test_references_numbered_once(self):
        entries = [
            p.text.strip()
            for p in self.document.paragraphs
            if p.text.strip().startswith(("1. Turk", "2. Yildirim"))
        ]
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertNotRegex(entry, r"^\d+\.\s*\d+\.")


class TestRussianBuild(unittest.TestCase):
    def test_russian_captions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "ru.docx"
            doc = MedicalDocument()
            doc.add(TitlePage(work_type="course", topic="Тест", year=2026))
            doc.add(Heading("Обзор литературы", level=1))
            doc.add(FigureBlock(key="f1", path=str(FIG_PATH), caption="Сравнение",
                                provenance="synthetic"))
            build_docx(doc, out, lang_code="ru")
            document = Document(str(out))
            joined = "\n".join(p.text for p in document.paragraphs)
            self.assertIn("Рисунок 1.1", joined)
            self.assertIn("Глава 1", joined)
            self.assertIn("Учебный пример", joined)


if __name__ == "__main__":
    unittest.main()
