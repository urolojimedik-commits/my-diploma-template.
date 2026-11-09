"""Тесты системы (запуск: ``python -m unittest discover -s tests`` или ``pytest``).

Главное, что проверяется — **честность данных**: ни один DOI не выдуман,
непроверенные источники не попадают в текст, учебные примеры помечены явно.
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diploma.model import Source  # noqa: E402
from diploma.pipeline import run_pipeline  # noqa: E402
from diploma.settings import Settings  # noqa: E402
from diploma.sources.providers import SeedProvider  # noqa: E402
from diploma.sources.gost import format_reference  # noqa: E402
from diploma.sources.verify import verify_source  # noqa: E402
from diploma.figures.data import extract_metrics, synthetic_roc_dataset  # noqa: E402
from diploma.render.markdown import resolve_citations  # noqa: E402
from diploma.topic import build_topic  # noqa: E402

TOPIC = (
    "Применение методов машинного обучения для автоматизированной диагностики "
    "мочекаменной болезни по данным компьютерной томографии"
)
DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


class TestSeedCorpus(unittest.TestCase):
    """Проверенный корпус: только настоящие DOI, все со штампом проверки."""

    @classmethod
    def setUpClass(cls):
        cls.sources = SeedProvider().load()

    def test_corpus_not_empty(self):
        self.assertGreaterEqual(len(self.sources), 10)

    def test_all_doi_wellformed(self):
        for s in self.sources:
            self.assertTrue(s.doi, f"нет DOI: {s.title}")
            self.assertRegex(s.doi, DOI_RE, f"битый DOI: {s.doi}")

    def test_all_verified(self):
        unverified = [s.key for s in self.sources if not (s.verified and s.verified_via)]
        self.assertEqual(unverified, [], f"непроверенные записи: {unverified}")

    def test_every_record_has_year_and_venue(self):
        for s in self.sources:
            self.assertIsInstance(s.year, int, f"нет года: {s.key}")
            self.assertTrue(s.venue or s.publisher, f"нет издания: {s.key}")


class TestVerification(unittest.TestCase):
    """Непроверенные источники не должны проходить в текст."""

    def test_fake_doi_is_rejected_offline(self):
        fake = Source(key="fake2026", title="Выдуманная статья", doi="10.9999/fake.2026.01", year=2026)
        result = verify_source(fake, allow_network=False)
        self.assertFalse(result.verified)
        self.assertFalse(fake.verified)

    def test_verified_stamp_is_accepted_offline(self):
        stamped = Source(
            key="ok2024",
            title="Проверенная статья",
            doi="10.1016/j.euf.2024.07.003",
            year=2024,
            verified=True,
            verified_via="crossref-api",
        )
        result = verify_source(stamped, allow_network=False)
        self.assertTrue(result.verified)


class TestTopicAndPlan(unittest.TestCase):
    def test_title_normalized_and_parts(self):
        topic = build_topic("тема: " + TOPIC.lower(), work_type="diploma")
        self.assertTrue(topic.title[0].isupper())
        self.assertEqual(topic.title_process, "Применение")
        self.assertIn("машинного обучения", topic.title_method)
        self.assertIn("мочекаменной болезни", topic.title_domain)
        self.assertTrue(topic.keywords_en)

    def test_goal_is_grammatical_phrase(self):
        topic = build_topic(TOPIC)
        self.assertIn(topic.title, topic.goal_ru)
        self.assertIn("«" + topic.title + "»", topic.object_ru)


class TestCitations(unittest.TestCase):
    def setUp(self):
        self.sources = [
            Source(key="a2020", title="A", year=2020, doi="10.1000/a", verified=True),
            Source(key="b2021", title="B", year=2021, doi="10.1000/b", verified=True),
        ]

    def test_citation_numbers_in_order_of_first_use(self):
        text, bibliography, order = resolve_citations("Текст [@b2021] и снова [@a2020; @b2021].", self.sources)
        self.assertEqual(order, {"b2021": 1, "a2020": 2})
        self.assertIn("[1] и снова [1, 2]", text)
        self.assertEqual(len(bibliography), 2)

    def test_unknown_key_is_marked_not_invented(self):
        text, bibliography, order = resolve_citations("Утверждение [@нет2026].", self.sources)
        self.assertIn("ТРЕБУЕТСЯ ИСТОЧНИК", text)
        self.assertEqual(order, {})


class TestMetrics(unittest.TestCase):
    def test_metrics_come_from_verified_sources_only(self):
        sources = SeedProvider().load()
        metrics = extract_metrics(sources)
        self.assertTrue(metrics)
        keys = {s.key for s in sources if s.verified}
        for m in metrics:
            for k in m.source_keys:
                self.assertIn(k, keys)
            self.assertIsInstance(m.value, float)

    def test_synthetic_dataset_is_marked(self):
        ds = synthetic_roc_dataset()
        self.assertEqual(ds.provenance, "synthetic")
        self.assertIn("УЧЕБНЫЙ ПРИМЕР", ds.description.upper())


class TestGost(unittest.TestCase):
    def test_reference_contains_doi_and_no_double_dot(self):
        s = next(x for x in SeedProvider().load() if x.key == "kim2024")
        ref = format_reference(s, style="gost")
        self.assertIn("DOI: 10.1016/j.euf.2024.07.003", ref)
        self.assertNotIn("..", ref)
        self.assertTrue(ref.endswith("."))


class TestFullPipeline(unittest.TestCase):
    """Сквозной прогон: DOCX и PDF должны собираться без выдуманных данных."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="diploma-test-")
        st = Settings(
            topic=TOPIC,
            out_dir=Path(cls.tmp) / "build",
            search_offline=True,
            make_zip=False,
            export_quarto=True,
        )
        cls.result = run_pipeline(st)

    def test_documents_built(self):
        for label in ("DOCX", "PDF", "Markdown", "BibTeX"):
            self.assertIn(label, self.result.files, f"не собран {label}")
            self.assertTrue(Path(self.result.files[label]).is_file())

    def test_no_fabricated_doi(self):
        md = Path(self.result.files["Markdown"]).read_text(encoding="utf-8")
        for doi in re.findall(r"10\.\d{4,9}/[^\s\"'\)]+", md):
            self.assertRegex(doi.rstrip(".,;"), DOI_RE)
            self.assertIn(doi.rstrip(".,;"), {s.doi for s in self.result.document.sources})

    def test_figures_and_tables_numbered(self):
        doc = self.result.document
        self.assertGreaterEqual(len(doc.figures), 3)
        self.assertGreaterEqual(len(doc.tables), 2)
        for fig in doc.figures:
            self.assertRegex(fig.number, r"^\d+\.\d+$")
        for table in doc.tables:
            self.assertRegex(table.number, r"^\d+\.\d+$")

    def test_synthetic_figure_marked_in_caption(self):
        synthetic = [f for f in self.result.document.figures if f.provenance == "synthetic"]
        self.assertTrue(synthetic)
        for fig in synthetic:
            self.assertIn("учебный пример", fig.caption_full().lower())

    def test_pdf_has_cyrillic_and_toc(self):
        try:
            import pymupdf
        except ImportError:  # pragma: no cover — опциональная проверка
            self.skipTest("pymupdf не установлен")
        doc = pymupdf.open(self.result.files["PDF"])
        text = "".join(doc.load_page(i).get_text() for i in range(min(3, doc.page_count)))
        self.assertIn("Содержание", text)
        self.assertIn("Введение", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
