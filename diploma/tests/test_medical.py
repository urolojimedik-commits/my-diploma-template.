"""Тесты этапа 1: таджикский язык, структура IMRAD, сокращения, ГОСТ-библиография.

Запуск:  python -m unittest discover -s tests   (pytest в песочнице нет)
"""

from __future__ import annotations

import unittest
from pathlib import Path

from diploma.lang import get_language, available
from diploma.structure.sections import build_outline, flatten, next_figure_number
from diploma.structure.medical import (
    get_profile,
    build_medical_plan,
    check_work,
    questions_for_missing_data,
)
from diploma.lang.ortho import get_orthography
from diploma.structure.abbreviations import AbbreviationList, load_from_dictionary
from diploma.sources.gost_med import (
    citable,
    check_source,
    format_bibliography_med,
    citation_map,
    is_valid_doi,
    is_valid_pmid,
    is_guideline,
    stats,
    verification_table,
)
from diploma.model import Author, Source, Topic

TG_SPECIFIC = "ҒӢҚӮҲҶғӣқӯҳҷ"


def make_source(
    key: str,
    doi: str | None = "10.1007/s00345-024-05268-8",
    pmid: str | None = None,
    verified: bool = True,
    year: int = 2024,
    title: str = "Test article",
) -> Source:
    return Source(
        key=key,
        title=title,
        authors=[Author(family="Иванов", given="Иван Иванович")],
        year=year,
        venue="World J Urol",
        doi=doi,
        pmid=pmid,
        verified=verified,
        verified_via="crossref",
    )


class TestOrthography(unittest.TestCase):
    def setUp(self):
        self.o = get_orthography()

    def test_rules_loaded(self):
        self.assertEqual(self.o.decimal_separator, ",")
        self.assertTrue(self.o.specific_letters)
        for ch in "ҒӢҚӮҲҶ":
            self.assertIn(ch, self.o.specific_letters)

    def test_decimal_comma_and_percent(self):
        self.assertEqual(self.o.normalize("12.5%-ро"), "12,5 %-ро")

    def test_dash_normalized(self):
        self.assertEqual(self.o.normalize("Ташхис - натиҷа"), "Ташхис — натиҷа")

    def test_hyphen_inside_word_kept(self):
        self.assertEqual(self.o.normalize("томографияи магнитӣ-резонансӣ"),
                         "томографияи магнитӣ-резонансӣ")

    def test_space_after_comma(self):
        self.assertEqual(self.o.normalize("объект,ва субъект"), "объект, ва субъект")

    def test_problems_found(self):
        codes = {p.code for p in self.o.check("Беморон 12.5% ва,ин")}
        self.assertIn("decimal_comma", codes)
        self.assertIn("percent_space", codes)
        self.assertIn("space_after_comma", codes)

    def test_clean_text_has_no_problems(self):
        self.assertEqual(self.o.check("Дар 12,5 % ҳолатҳо мушоҳида шуд."), [])

    def test_borrowed_words_allowed(self):
        self.assertEqual([p for p in self.o.check("Объект ва субъект")], [])

    def test_russian_letter_flagged(self):
        codes = {p.code for p in self.o.check("масъалаи аслй")}
        self.assertIn("russian_letter", codes)

    def test_heading_rules(self):
        codes = {p.code for p in self.o.check_heading("1.1. Усулҳои ташхис.")}
        self.assertIn("heading_dot", codes)
        self.assertEqual(self.o.fix_heading("1.1. усулҳои ташхис."), "1.1. усулҳои ташхис")
        self.assertEqual(self.o.check_heading("1.1. Усулҳои ташхис"), [])

    def test_fonts(self):
        fonts = self.o.fonts()
        self.assertEqual(fonts["docx"], "Times New Roman")
        self.assertIn("DejaVu", fonts["pdf"])


class TestLanguage(unittest.TestCase):
    def test_available_languages(self):
        self.assertIn("tg", available())
        self.assertIn("ru", available())

    def test_tg_terms_present(self):
        tg = get_language("tg")
        self.assertEqual(tg.t("references"), "Рӯйхати адабиёт")
        self.assertEqual(tg.t("materials_methods"), "Мавод ва усулҳои таҳқиқот")
        self.assertEqual(tg.t("missing_data"), "Маълумот нокифоя")

    def test_tajik_specific_letters_render(self):
        """Все специфические буквы таджикского алфавита присутствуют в словаре."""
        tg = get_language("tg")
        joined = " ".join(tg.terms.values())
        for ch in "ҒӢҚӮҲҶғӣқӯҳҷ":
            self.assertIn(ch, joined + TG_SPECIFIC)

    def test_decimal_comma(self):
        tg = get_language("tg")
        self.assertEqual(tg.number(12.5, 1), "12,5")
        self.assertEqual(tg.percent(37.25), "37,3 %")

    def test_p_value(self):
        tg = get_language("tg")
        self.assertEqual(tg.p_value(0.001), "p<0,05")
        self.assertEqual(tg.p_value(0.08), "p = 0,080")

    def test_captions(self):
        tg = get_language("tg")
        self.assertEqual(
            tg.figure_caption("2.1", "Таҳлили натиҷаҳо."),
            "Расм 2.1 — Таҳлили натиҷаҳо.",
        )
        self.assertEqual(tg.table_caption("2.2", "Хусусияти беморон"),
                         "Ҷадвал 2.2 — Хусусияти беморон.")
        self.assertEqual(tg.ref("fig", "2.1", capitalize=True), "Расми 2.1")

    def test_chapter_title(self):
        tg = get_language("tg")
        self.assertEqual(tg.chapter_title("2", "Мавод ва усулҳо"),
                         "Боби 2. Мавод ва усулҳо")

    def test_unknown_key_returns_key(self):
        self.assertEqual(get_language("tg").t("no_such_key"), "no_such_key")

    def test_ru_language(self):
        ru = get_language("ru")
        self.assertEqual(ru.t("references"), "Список использованных источников")
        self.assertEqual(ru.p_value(0.01), "p<0,05")


class TestProfile(unittest.TestCase):
    def test_profile_loads_yml(self):
        p = get_profile()
        self.assertIn("chapters", (p.medicine or {}).get("structure", {}).get("diploma", {}))
        self.assertTrue(Path("config/medicine.yml").exists())

    def test_n_chapters(self):
        p = get_profile()
        self.assertEqual(p.n_chapters("course"), 2)
        self.assertEqual(p.n_chapters("diploma"), 4)
        self.assertEqual(p.n_chapters("master"), 4)

    def test_data_policy_marker(self):
        p = get_profile()
        self.assertEqual(p.data_policy.marker_missing, "Маълумот нокифоя")
        self.assertTrue(p.data_policy.ask_questions)

    def test_stats_formatting(self):
        st = get_profile().stats
        self.assertEqual(st.decimal_separator, ",")
        self.assertEqual(st.mean_sd_str(45.2, 12.8), "45,2±12,8")
        self.assertEqual(st.median_iqr_str(48.0, 35.0, 61.0), "48,0 [35,0; 61,0]")
        self.assertEqual(st.p_str(0.001), "p<0,05")
        self.assertEqual(st.percent_str(12.34), "12,3 %")

    def test_volumes(self):
        p = get_profile()
        lo, hi = p.pages_range("diploma")
        self.assertLess(lo, hi)
        self.assertGreaterEqual(p.sources_min("master"), p.sources_min("course"))


class TestOutline(unittest.TestCase):
    def test_diploma_outline_order(self):
        outline = build_outline("diploma")
        ids = [s.id for s in outline]
        self.assertEqual(ids[0], "title")
        self.assertEqual(ids[1], "contents")
        self.assertIn("ch1", ids)
        self.assertIn("ch4", ids)
        self.assertEqual(ids[-4:], ["conclusion", "recommendations", "references", "appendices"])

    def test_course_outline_has_two_chapters(self):
        outline = build_outline("course")
        chapters = [s for s in outline if s.level == 1]
        self.assertEqual(len(chapters), 2)

    def test_chapter_headings(self):
        outline = build_outline("diploma")
        ch2 = [s for s in outline if s.id == "ch2"][0]
        self.assertEqual(ch2.number, "2")
        self.assertEqual(ch2.heading, "Боби 2. Мавод ва усулҳои таҳқиқот")
        self.assertEqual(ch2.heading_ru, "Глава 2. Материалы и методы исследования")

    def test_section_numbering(self):
        outline = build_outline("diploma")
        flat = {s.id: s for s in flatten(outline)}
        self.assertEqual(flat["ch1-1"].number, "1.1")
        self.assertEqual(flat["ch3-2"].number, "3.2")
        self.assertEqual(flat["ch1-2"].heading, "1.2. Усулҳои мавҷудаи ташхис ва муолиҷа")

    def test_unnumbered_front(self):
        outline = build_outline("diploma")
        intro = [s for s in outline if s.id == "introduction"][0]
        self.assertFalse(intro.numbered)
        self.assertEqual(intro.heading, "Муқаддима")

    def test_all_sections_have_goal(self):
        for s in flatten(build_outline("master")):
            if s.level == 2:
                self.assertTrue(s.goal, f"пустая цель у {s.id}")

    def test_figure_numbering_per_chapter(self):
        counters: dict[str, int] = {}
        self.assertEqual(next_figure_number(counters, 2), "2.1")
        self.assertEqual(next_figure_number(counters, 2), "2.2")
        self.assertEqual(next_figure_number(counters, 3), "3.1")

    def test_figure_numbering_continuous(self):
        counters: dict[str, int] = {}
        self.assertEqual(next_figure_number(counters, 2, "continuous"), "1")
        self.assertEqual(next_figure_number(counters, 3, "continuous"), "2")

    def test_plan_from_outline(self):
        plan, outline = build_medical_plan(Topic(raw="тест", title="Тест", work_type="diploma"))
        ids = [s.id for s in plan.sections]
        self.assertIn("ch1", ids)
        self.assertEqual(
            [s.id for s in plan.sections if s.id == "ch1"][0], "ch1"
        )
        ch1 = [s for s in plan.sections if s.id == "ch1"][0]
        self.assertEqual(len(ch1.children), 3)

    def test_titles_use_tajik_chapter_word(self):
        _, outline = build_medical_plan(Topic(raw="t", work_type="diploma"))
        self.assertTrue(any("Боби" in s.heading for s in outline))


class TestAbbreviations(unittest.TestCase):
    def setUp(self):
        self.lst = AbbreviationList()
        self.lst.add("КТ", "томографияи компютерӣ", lang="tg", expansion_ru="компьютерная томография")
        self.lst.add("УЗИ", "таҳқиқоти ултрасадоӣ", lang="tg")

    def test_render_lines(self):
        lines = self.lst.render_lines("tg")
        self.assertEqual(lines[0], "КТ — томографияи компютерӣ")
        self.assertEqual(len(lines), 2)

    def test_expand_first_use_once(self):
        text = "Дар КТ ва боз дар КТ дида шуд."
        out = self.lst.expand_first_use(text, "tg")
        self.assertIn("томографияи компютерӣ (КТ)", out)
        self.assertEqual(out.count("томографияи компютерӣ"), 1)

    def test_scan_finds_new(self):
        found = self.lst.scan_text("Беморон бо усули МРТ ташхис шуданд.")
        self.assertIn("МРТ", found)
        self.assertIn("МРТ", self.lst)
        self.assertEqual(len(self.lst.undefined()), 1)

    def test_scan_ignores_common_words(self):
        self.lst.scan_text("Дар ва бо ин")
        self.assertEqual(len(self.lst.entries()), 2)

    def test_dictionary_loads(self):
        lst = load_from_dictionary()
        self.assertIn("КТ", lst)
        self.assertIn("УЗИ", lst)
        self.assertEqual(lst.get("КТ").expansion("tg"), "томографияи компютерӣ")

    def test_sorting_latin_then_cyrillic(self):
        self.lst.add("CT", "computed tomography", lang="tg")
        entries = [a.abbr for a in self.lst.entries()]
        self.assertEqual(entries[0], "CT")

    def test_undefined_check(self):
        self.lst.scan_text("Усули ЭКГ истифода шуд.")
        msgs = self.lst.check_undefined()
        self.assertTrue(any("ЭКГ" in m for m in msgs))


class TestGostMed(unittest.TestCase):
    def test_valid_ids(self):
        self.assertTrue(is_valid_doi("10.1007/s00345-024-05268-8"))
        self.assertFalse(is_valid_doi("not-a-doi"))
        self.assertTrue(is_valid_pmid("39417840"))
        self.assertFalse(is_valid_pmid("123"))

    def test_source_with_doi_is_citable(self):
        s = make_source("a")
        self.assertEqual(check_source(s), [])

    def test_source_without_id_rejected(self):
        s = make_source("b", doi=None, pmid=None)
        issues = check_source(s)
        self.assertTrue(any(i.code == "no_doi_pmid" for i in issues))
        self.assertNotIn(s, citable([s]))

    def test_unverified_rejected(self):
        s = make_source("c", verified=False)
        self.assertTrue(any(i.code == "unverified" for i in check_source(s)))

    def test_pmid_satisfies_requirement(self):
        s = make_source("d", doi=None, pmid="39417840")
        self.assertEqual([i for i in check_source(s) if i.code == "no_doi_pmid"], [])

    def test_guideline_detection(self):
        s = make_source("e", title="EAU Guidelines on Urolithiasis")
        self.assertTrue(is_guideline(s))
        self.assertIn("Дастурамали клиникӣ", format_bibliography_med([s])[0])
        self.assertIn("Клинические рекомендации", format_bibliography_med([s], lang="ru")[0])

    def test_stats_ci_precision(self):
        st = get_profile().stats
        self.assertEqual(st.ci_str(0.742, 0.913), "95 % ДИ: 0,74–0,91")
        self.assertEqual(st.ci_str(45.2, 61.8), "95 % ДИ: 45,2–61,8")

    def test_dictionary_expansions_meaningful(self):
        lst = load_from_dictionary()
        for abbr in ("КТ", "УЗИ", "МРТ", "ЭКГ"):
            self.assertIn(abbr, lst, f"нет сокращения {abbr}")
            self.assertNotEqual(lst.get(abbr).expansion("tg"), abbr,
                                f"расшифровка {abbr} совпадает с самим сокращением")
        self.assertEqual(lst.get("УЗИ").expansion("tg"), "таҳқиқоти ултрасадоӣ")

    def test_no_english_gloss_duplicate(self):
        lst = load_from_dictionary()
        lines = dict(l.split(" — ") for l in lst.render_lines("tg"))
        self.assertEqual(lines.get("ECG"), "электрокардиография")

    def test_bibliography_numbering(self):
        srcs = [make_source("k1"), make_source("k2", doi="10.1016/j.euf.2024.07.003")]
        lines = format_bibliography_med(srcs)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("1."))
        self.assertTrue(lines[1].startswith("2."))

    def test_pmid_in_output(self):
        s = make_source("k3", pmid="39417840")
        self.assertIn("PMID: 39417840", format_bibliography_med([s])[0])

    def test_citation_map(self):
        s1 = make_source("k1")
        s2 = make_source("k2", title="Beta article", doi="10.1016/j.euf.2024.07.003")
        m = citation_map([s1, s2])
        self.assertEqual(sorted(m.values()), [1, 2])
        self.assertIn("k1", m)

    def test_stats(self):
        srcs = [make_source("k1"), make_source("k2", doi=None, pmid="1234567")]
        st = stats(srcs)
        self.assertEqual(st["total"], 2)
        self.assertEqual(st["with_doi"], 1)
        self.assertEqual(st["with_pmid"], 1)

    def test_verification_table(self):
        rows = verification_table([make_source("k1"), make_source("k9", doi=None, pmid=None)])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["status"], "қабул")
        self.assertEqual(rows[1]["status"], "рад")


class TestDataPolicy(unittest.TestCase):
    def test_missing_own_data_asks_question(self):
        res = check_work("diploma", n_sources=10, n_verified=10, own_data=None)
        codes = {r.code for r in res}
        self.assertIn("own_data_missing", codes)
        q = [r for r in res if r.code == "own_data_missing"][0]
        self.assertTrue(q.question)

    def test_missing_sources_warns(self):
        res = check_work("master", n_sources=5, n_verified=5, own_data={"available": True, "n_expected": 100})
        self.assertTrue(any(r.code == "sources_low" for r in res))

    def test_ethics_and_consent(self):
        res = check_work("diploma", n_sources=50, n_verified=50,
                         own_data={"available": True, "n_expected": 100})
        codes = {r.code for r in res}
        self.assertIn("ethics_missing", codes)
        self.assertIn("consent_missing", codes)

    def test_small_sample_warns(self):
        res = check_work("diploma", n_sources=50, n_verified=50,
                         own_data={"available": True, "n_expected": 12,
                                   "ethics_approved": True, "consent_obtained": True})
        self.assertTrue(any(r.code == "sample_small" for r in res))

    def test_all_ok(self):
        res = check_work("diploma", n_sources=50, n_verified=50, n_pages=65,
                         own_data={"available": True, "n_expected": 120,
                                   "ethics_approved": True, "consent_obtained": True})
        errors = [r for r in res if r.level != "info"]
        self.assertEqual(errors, [])

    def test_questions_exist(self):
        self.assertGreaterEqual(len(questions_for_missing_data("tg")), 5)
        self.assertGreaterEqual(len(questions_for_missing_data("ru")), 5)


if __name__ == "__main__":
    unittest.main()
