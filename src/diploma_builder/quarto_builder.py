"""
quarto_builder.py — генерация Quarto проекта на русском (ГОСТ) + вызов quarto/pandoc если доступны.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
from typing import Dict, List, Optional

from .config import ProjectConfig
from .bibliography import BibliographyManager


QUARTO_TEMPLATE_METADATA = """# _metadata.yml — ГОСТ
title: "{title}"
subtitle: "{subtitle}"
author:
  - name: "{author}"
    affiliation: "{university}"
date: "{year}"
date-format: "DD MMMM YYYY"
lang: ru
language:
  title-block-author-single: "Автор"
  title-block-published: "Дата"
  crossref-fig-title: "Рисунок"
  crossref-tbl-title: "Таблица"
  crossref-fig-prefix: "Рисунок"
  crossref-tbl-prefix: "Таблица"

bibliography: references.bib
csl: ../../assets/csl/gost-r-7-0-5-2018.csl
link-citations: true
toc: true
toc-depth: 2
toc-title: "Содержание"
lof: true
lofTitle: "Список рисунков"
lot: true
lotTitle: "Список таблиц"
abstract-title: "Аннотация"
keywords: [{keywords}]
abstract: |
  {abstract}
thanks: "Научный руководитель: {supervisor}"

# ГОСТ формат
format:
  html:
    theme: cosmo
    toc: true
    lang: ru
  docx:
    output-file: thesis.docx
    toc: true
  pdf:
    output-file: thesis.pdf
    pdf-engine: xelatex
    toc: true
    keep-tex: false
    documentclass: scrbook
    classoption: [a4paper, 14pt, titlepage, openany, DIV=calc, toc=listof]
    geometry: [a4paper, bindingoffset=0mm, inner=30mm, outer=15mm, top=20mm, bottom=20mm]
    mainfont: "Times New Roman"
    sansfont: "Arial"
    monofont: "Courier New"
    linestretch: 1.5
    toc-depth: 2
    lof: true
    lot: true
    include-in-header:
      text: |
        \\usepackage{{polyglossia}}
        \\setdefaultlanguage{{russian}}
        \\usepackage{{indentfirst}}
        \\setlength{{\\parindent}}{{1.25cm}}
        \\usepackage{{chngcntr}}
        \\counterwithout{{figure}}{{chapter}}
        \\counterwithout{{table}}{{chapter}}
  latex:
    output-file: thesis.tex
"""

QUARTO_PROJECT = """project:
  type: default
  render:
    - index.qmd

execute:
  freeze: false

filters:
  - filters/multibib.lua

lang: ru
syntax-highlighting: pygments
"""


class QuartoBuilder:
    """Генерация Quarto исходников."""

    def __init__(self, config: ProjectConfig, output_dir: pathlib.Path):
        self.config = config
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_target = self.output_dir / "images"
        self.images_target.mkdir(parents=True, exist_ok=True)

    def generate(self, markdown_chapters: Dict[str, str], bibliography_manager: BibliographyManager) -> pathlib.Path:
        """Создаёт полный Quarto проект в output_dir."""
        # _quarto.yml
        (self.output_dir / "_quarto.yml").write_text(QUARTO_PROJECT, encoding="utf-8")

        # _metadata.yml
        keywords_str = ", ".join(f'"{k}"' for k in self.config.keywords) if self.config.keywords else '"исследование"'
        abstract = f"Работа посвящена теме «{self.config.topic}». Цель — {self.config.goal or 'комплексное исследование'}. Практическая значимость — рекомендации для организаций."
        metadata = QUARTO_TEMPLATE_METADATA.format(
            title=self.config.topic,
            subtitle=self._subtitle(),
            author=self.config.author.fio,
            university=self.config.organization.university,
            year=str(self.config.organization.year),
            keywords=keywords_str,
            abstract=abstract,
            supervisor=self.config.author.supervisor,
        )
        (self.output_dir / "_metadata.yml").write_text(metadata, encoding="utf-8")

        # references.bib
        bibliography_manager.to_bibtex(self.output_dir / "references.bib")

        # создаём index.qmd
        includes = []
        chapter_files = []
        # сортировка
        for fname, content in sorted(markdown_chapters.items()):
            # сохраняем каждый файл
            safe_name = fname.replace(" ", "_")
            fpath = self.output_dir / safe_name
            # добавляем front matter для первой?
            fpath.write_text(content, encoding="utf-8")
            chapter_files.append(safe_name)
            includes.append(f'{{{{< include {safe_name} >}}}}')

        # библиография + приложения — отдельные include
        bib_content = "# Список использованных источников {#sec-bibliography}\n\n::: {#refs}\n:::\n"
        (self.output_dir / "99_Библиография.md").write_text(bib_content, encoding="utf-8")
        includes.append("{{< include 99_Библиография.md >}}")

        index_qmd = "\n\n".join(includes)
        # Добавим titlepage через include-before в _metadata, но для простоты — просто includes
        (self.output_dir / "index.qmd").write_text(index_qmd, encoding="utf-8")

        # копируем filters если есть в шаблоне
        src_filters = pathlib.Path("thesis/filters")
        if src_filters.exists():
            dst_filters = self.output_dir / "filters"
            dst_filters.mkdir(exist_ok=True)
            for f in src_filters.glob("*.lua"):
                shutil.copy(f, dst_filters / f.name)

        # копируем csl если нужен ГОСТ
        csl_src = pathlib.Path("assets/csl/chicago-author-date.csl")
        if csl_src.exists():
            # пробуем найти ГОСТ CSL; если нет — используем существующий
            pass

        print(f"[quarto] Quarto проект создан → {self.output_dir}")
        print(f"  файлы: {', '.join(chapter_files)}")
        return self.output_dir

    def _subtitle(self) -> str:
        mapping = {
            "курсовая": "Курсовая работа",
            "диплом": "Выпускная квалификационная работа",
            "вкр_бакалавр": "ВКР бакалавра",
            "магистерская": "Магистерская диссертация",
            "статья": "Научная статья",
        }
        return mapping.get(self.config.work_type.value, "Научная работа")

    def render(self, to: str = "docx") -> Optional[pathlib.Path]:
        """Пытается вызвать quarto render, иначе fallback."""
        cmd = None
        if shutil.which("quarto"):
            cmd = ["quarto", "render", str(self.output_dir), "--to", to]
        elif shutil.which("pandoc"):
            # pandoc fallback: index.qmd -> docx/pdf
            # Собираем единый md
            combined = self.output_dir / "combined.md"
            md_parts = []
            for f in sorted(self.output_dir.glob("*.md")):
                md_parts.append(f.read_text(encoding="utf-8"))
            combined.write_text("\n\n".join(md_parts), encoding="utf-8")
            out_map = {"docx": "thesis.docx", "pdf": "thesis.pdf", "html": "thesis.html"}
            out_file = self.output_dir / out_map.get(to, "thesis.docx")
            cmd = ["pandoc", str(combined), "-o", str(out_file), "--toc", "--citeproc", f"--bibliography={self.output_dir / 'references.bib'}"]
        else:
            print("[quarto] Quarto/Pandoc не найдены — используйте DocxBuilder/PdfBuilder (Python)")
            return None

        print(f"[quarto] Запуск: {' '.join(cmd)}")
        try:
            res = subprocess.run(cmd, cwd=str(self.output_dir), capture_output=True, text=True, timeout=120)
            print(res.stdout[-2000:])
            if res.returncode != 0:
                print(f"[quarto] Ошибка: {res.stderr[-2000:]}")
                return None
            # найдём выходной файл
            candidates = list(self.output_dir.glob(f"*.{to}"))
            if candidates:
                print(f"[quarto] Рендер успешен → {candidates[0]}")
                return candidates[0]
            return None
        except Exception as e:
            print(f"[quarto] Исключение: {e}")
            return None

