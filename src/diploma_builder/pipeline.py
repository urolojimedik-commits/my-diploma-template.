"""
pipeline.py — оркестрация: тема → план → источники → текст → графики → DOCX/PDF.
"""

from __future__ import annotations

import pathlib
import shutil
from typing import Dict, Optional

from .config import ProjectConfig, WorkType
from .planner import Planner
from .search import SourceSearcher
from .writer import AcademicWriter
from .figures import FigureFactory
from .bibliography import BibliographyManager
from .docx_builder import DocxBuilder
from .pdf_builder import PdfBuilder
from .quarto_builder import QuartoBuilder


class DiplomaPipeline:
    """Главный pipeline."""

    def __init__(self, config: ProjectConfig):
        self.config = config
        self.output_dir = pathlib.Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        with_search: bool = True,
        with_figures: bool = True,
        with_docx: bool = True,
        with_pdf: bool = True,
        with_quarto: bool = True,
        search_rows: int = 15,
        verify_sources: bool = False,
    ) -> Dict[str, pathlib.Path]:
        """Запускает все этапы, возвращает пути к артефактам."""
        results: Dict[str, pathlib.Path] = {}

        # 1. План
        print("\n[1/7] 📋 Генерация плана...")
        planner = Planner(self.config)
        planner.generate()
        plan_md = planner.to_markdown()
        plan_path = self.output_dir / "plan.md"
        plan_path.write_text(plan_md, encoding="utf-8")
        (self.output_dir / "project.yaml").write_text(self._config_to_yaml(), encoding="utf-8")
        results["plan"] = plan_path
        print(plan_md[:800] + "\n...")

        # 2. Поиск источников
        if with_search:
            print("\n[2/7] 🔍 Поиск реальных источников (Crossref + OpenAlex)...")
            searcher = SourceSearcher()
            sources = searcher.ensure_min_sources(self.config.topic, min_count=search_rows, verify=verify_sources)
            self.config.sources = sources
            results["sources"] = self.output_dir / "sources.json"
            # сохраним для отладки
            import json

            with open(results["sources"], "w", encoding="utf-8") as f:
                json.dump([s.__dict__ for s in sources], f, ensure_ascii=False, indent=2)
            print(f"  Найдено {len(sources)} источников:")
            for i, s in enumerate(sources[:5], 1):
                v = "✓ verified" if s.verified else "○"
                print(f"   {i}. {v} {s.authors[0][:40] if s.authors else ''} ({s.year}) — {s.title[:70]}...")
            if len(sources) > 5:
                print(f"   ... и ещё {len(sources)-5}")
            bib_mgr = BibliographyManager(sources)
            bib_mgr.verify_all()
        else:
            bib_mgr = BibliographyManager(self.config.sources)

        # 3. Библиография
        print("\n[3/7] 📚 Формирование библиографии (ГОСТ + BibTeX)...")
        bib_path = bib_mgr.to_bibtex(self.output_dir / "references.bib")
        gost_path = self.output_dir / "bibliography_gost.txt"
        gost_lines = bib_mgr.to_gost_list(gost_path)
        results["bibtex"] = bib_path
        results["gost"] = gost_path

        # 4. Графики / иллюстрации
        figure_paths = {}
        if with_figures:
            print("\n[4/7] 📊 Генерация таблиц, графиков, диаграмм...")
            factory = FigureFactory(self.images_dir)
            # соберём все фигуры из плана
            all_specs = []
            for ch in self.config.plan:
                for sub in ch.subsections:
                    all_specs.extend(sub.figures)
            if all_specs:
                generated = factory.generate_for_plan(self.config.topic, all_specs)
            else:
                generated = []
            # Всегда добавляем полный демо-набор для демонстрации возможностей
            demo = factory.create_demo_set(self.config.topic)
            for k, p in demo.items():
                if p not in generated:
                    generated.append(p)
            results["images_dir"] = self.images_dir
            print(f"  Создано {len(generated)} изображений в {self.images_dir}")

            # копируем в thesis/images для совместимости?
            # уже в output_dir/images
        else:
            print("\n[4/7] 📊 Пропуск графиков (with_figures=False)")

        # 5. Академический текст
        print("\n[5/7] ✍️ Написание академического текста...")
        writer = AcademicWriter(self.config)
        chapters = writer.write_full_thesis()

        # --- Добавляем приложение со всеми иллюстрациями (если есть демо-набор) ---
        # Собираем все PNG в images_dir
        all_images = sorted(self.images_dir.glob("*.png")) if self.images_dir.exists() else []
        if len(all_images) >= 2:
            extra_lines = ["# Приложения. Иллюстрации\n", ""]
            extra_lines.append("В данном приложении представлены все иллюстрации работы с подписями по ГОСТ.\n")
            fig_idx = 1
            for img_path in all_images:
                # Пропускаем те, что уже встроены в главы (по имени)
                # Но для полноты покажем все
                caption_map = {
                    "fig_01_dynamics.png": "Динамика цифровизации процессов (2020–2024)",
                    "fig_02_comparison.png": "Сравнение показателей до и после внедрения цифрового решения",
                    "fig_03_structure.png": "Структура процессов по степени автоматизации (2024)",
                    "fig_04_barriers.png": "Оценка барьеров цифровизации (экспертный опрос, 10-балльная шкала)",
                    "fig_05_scheme.png": "Модель цифрового взаимодействия «гражданин — государство»",
                    "fig_06_forecast.png": "Прогноз экономического эффекта от внедрения (базовый год 2024 = 100%)",
                    "fig_2_2_dynamics.png": "Динамика ключевых показателей объекта исследования",
                    "fig_3_2_forecast.png": "Прогноз эффективности предлагаемых мероприятий",
                }
                caption = caption_map.get(img_path.name, f"Иллюстрация {fig_idx}")
                extra_lines.append(f"![{caption}](images/{img_path.name}){{#fig-app-{fig_idx}}}")
                extra_lines.append("")
                extra_lines.append(f"Рисунок {fig_idx} — {caption}. Источник: см. подпись на графике.")
                extra_lines.append("")
                fig_idx += 1
            chapters["60_Приложения_Иллюстрации.md"] = "\n".join(extra_lines)

        # сохраняем каждую главу как .md в output
        for fname, content in chapters.items():
            fpath = self.output_dir / fname
            fpath.write_text(content, encoding="utf-8")
        # статья
        article_md = writer.write_article()
        (self.output_dir / "article.md").write_text(article_md, encoding="utf-8")
        results["chapters"] = self.output_dir
        print(f"  Сохранено {len(chapters)} глав + статья")

        # 6. Сборка DOCX
        if with_docx:
            print("\n[6/7] 📄 Сборка DOCX (ГОСТ)...")
            docx_builder = DocxBuilder(self.config, self.output_dir, self.images_dir)
            docx_path = docx_builder.build(chapters, gost_lines)
            results["docx"] = docx_path
        else:
            print("\n[6/7] 📄 Пропуск DOCX")

        # 7. Сборка PDF
        if with_pdf:
            print("\n[7/7] 📕 Сборка PDF (ГОСТ)...")
            pdf_builder = PdfBuilder(self.config, self.output_dir, self.images_dir)
            pdf_path = pdf_builder.build(chapters, gost_lines)
            results["pdf"] = pdf_path
        else:
            print("\n[7/7] 📕 Пропуск PDF")

        # 8. Quarto проект (опционально)
        if with_quarto:
            print("\n[8/7] 📦 Генерация Quarto проекта (опционально)...")
            quarto_dir = self.output_dir / "quarto"
            quarto_builder = QuartoBuilder(self.config, quarto_dir)
            quarto_builder.generate(chapters, bib_mgr)
            # копируем картинки
            for img in self.images_dir.glob("*.png"):
                shutil.copy(img, quarto_dir / "images" / img.name) if (quarto_dir / "images").exists() else None
                # ensure
                (quarto_dir / "images").mkdir(parents=True, exist_ok=True)
                shutil.copy(img, quarto_dir / "images" / img.name)
            results["quarto"] = quarto_dir
            # попытка рендера если есть quarto/pandoc
            quarto_builder.render("docx")
            quarto_builder.render("pdf")

        print("\n✅ Pipeline завершён. Артефакты:")
        for k, v in results.items():
            print(f"  {k}: {v}")
        return results

    def _config_to_yaml(self) -> str:
        import yaml

        try:
            data = self.config.to_dict()
            return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        except Exception:
            # fallback без yaml
            return f"topic: {self.config.topic}\nwork_type: {self.config.work_type.value}\n"


# Удобный хелпер для CLI / Web

def create_project_from_topic(
    topic: str,
    work_type: str = "диплом",
    discipline: str = "Информационные системы",
    author_fio: str = "Иванов И.И.",
    output_dir: str = "output",
) -> ProjectConfig:
    from .config import AuthorInfo, OrganizationInfo

    wt = WorkType(work_type) if work_type in WorkType._value2member_map_ else WorkType.DIPLOMA
    cfg = ProjectConfig(
        topic=topic,
        work_type=wt,
        discipline=discipline,
        author=AuthorInfo(fio=author_fio),
        organization=OrganizationInfo(),
        output_dir=pathlib.Path(output_dir),
    )
    return cfg

