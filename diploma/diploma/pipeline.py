"""Конвейер подготовки работы: шаги 1-10.

Порядок шагов:

1. разбор темы (:mod:`topic`);
2. план и структура (:mod:`outline`);
3. поиск и проверка источников (:mod:`sources`);
4. написание текста (:mod:`textgen`);
5. данные, таблицы, графики, иллюстрации (:mod:`figures`);
6. нумерация и подписи (:mod:`figures.registry`);
7. список литературы (:mod:`sources.gost`);
8. DOCX и PDF (:mod:`render`);
9. русский язык (все тексты, стили и подписи — русские);
10. выдача и скачивание (:mod:`web`, ZIP-архив).
"""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .figures.charts import ChartSpec, render_chart
from .figures.data import extract_metrics, metrics_dataset, studies_dataset, synthetic_roc_dataset, write_datasets
from .figures.diagrams import pipeline_diagram
from .figures.registry import Registry
from .model import Document, Figure, Plan, Source, Table, Topic
from .outline import allocate_sources, build_plan, plan_to_markdown
from .render import engine
from .settings import Settings
from .sources.bibtex import write_bibtex
from .sources.search import SearchReport, search_sources
from .sources.verify import verification_report
from .textgen.base import SectionContext
from .textgen.deterministic import DeterministicComposer
from .topic import build_topic

TOTAL_STEPS = 9


@dataclass
class BuildResult:
    out_dir: Path
    files: dict[str, str] = field(default_factory=dict)
    document: Document | None = None
    search_report: SearchReport | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def downloads(self) -> list[dict[str, str]]:
        order = ["DOCX", "PDF", "HTML", "Markdown", "BibTeX", "ZIP", "Quarto"]
        out = []
        for key in order:
            if key in self.files:
                out.append({"label": key, "path": self.files[key]})
        for key, value in self.files.items():
            if key not in order:
                out.append({"label": key, "path": value})
        return out


def _progress(cb, step: int, message: str):
    if cb:
        cb(step, TOTAL_STEPS, message)


# --------------------------------------------------------------------------- #
# Шаг 5: данные, рисунки, таблицы
# --------------------------------------------------------------------------- #


def build_media(doc: Document, registry: Registry, st: Settings, out_dir: Path) -> None:
    media_dir = out_dir / "media"
    data_dir = out_dir / "data"
    media_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    sources = doc.sources

    # --- 1. Схема этапов исследования (иллюстрация, данных не содержит) ---
    chapter_titles = [s.title for s in doc.plan.sections if s.kind == "body"]
    stages = ["Постановка цели и задач", "Поиск и проверка источников"]
    stages += [t[:64] for t in chapter_titles]
    stages += ["Обобщение результатов", "Формулирование выводов"]
    path = pipeline_diagram(
        stages,
        media_dir / "fig-pipeline.png",
        title="Этапы проведения исследования",
        dpi=st.figure_dpi,
    )
    doc.figures.append(
        Figure(
            key="pipeline",
            path=f"media/{Path(path).name}",
            caption="Этапы проведения исследования",
            section_id="ch2-1",
            provenance="diagram",
            source_note="Схема составлена автором работы",
        )
    )

    # --- 2. Реальные количественные показатели ---
    metrics = extract_metrics(sources)
    pct = metrics_dataset([m for m in metrics if m.unit == "%"], "%", key="metrics_percent")
    counts = metrics_dataset([m for m in metrics if m.unit == "ед."], "ед.", key="metrics_counts")
    auc = metrics_dataset([m for m in metrics if m.unit == "AUC"], "AUC", key="metrics_auc")

    if pct.rows:
        pct.rows.sort(key=lambda r: -float(r.values.get("Значение", 0)))
        p = render_chart(
            ChartSpec(
                kind="bar",
                dataset=pct,
                output=media_dir / "fig-metrics.png",
                title="Значения показателей, приведённые в рассмотренных работах",
                x="Исследование",
                y="Значение",
                ylabel="Значение показателя, %",
                rotate_xticks=25,
                figsize=(9, 4.8),
                dpi=st.figure_dpi,
            )
        )
        keys = sorted({k for r in pct.rows for k in r.source_keys})
        doc.figures.append(
            Figure(
                key="metrics",
                path=f"media/{Path(p).name}",
                caption="Сравнение значений показателей, опубликованных в рассмотренных исследованиях",
                section_id="ch2-2",
                provenance="real",
                source_note="По данным: " + ", ".join(f"[{k}]" for k in keys),
                dataset_key="metrics_percent",
            )
        )
        doc.tables.append(
            _metrics_table(pct, keys, number="", caption="Количественные показатели, извлечённые из проверенных источников")
        )

    if counts.rows:
        counts.rows.sort(key=lambda r: -float(r.values.get("Значение", 0)))
        p = render_chart(
            ChartSpec(
                kind="barh",
                dataset=counts,
                output=media_dir / "fig-samples.png",
                title="Объём выборок в рассмотренных исследованиях",
                x="Исследование",
                y="Значение",
                xlabel="Объём выборки (число наблюдений, изображений, случаев)",
                log_scale=True,
                figsize=(9, 4.6),
                dpi=st.figure_dpi,
            )
        )
        keys = sorted({k for r in counts.rows for k in r.source_keys})
        doc.figures.append(
            Figure(
                key="samples",
                path=f"media/{Path(p).name}",
                caption="Объём выборок, использованных в рассмотренных исследованиях (логарифмическая шкала)",
                section_id="ch2-2",
                provenance="real",
                source_note="По данным: " + ", ".join(f"[{k}]" for k in keys),
                dataset_key="metrics_counts",
            )
        )

    # --- 3. Учебный пример: явно помеченные смоделированные данные ---
    roc = synthetic_roc_dataset()
    p = render_chart(
        ChartSpec(
            kind="line",
            dataset=roc,
            output=media_dir / "fig-roc.png",
            title="ROC-кривые (учебный пример)",
            x="FPR",
            y="TPR",
            group="Модель",
            xlabel="Доля ложноположительных результатов (FPR)",
            ylabel="Чувствительность (TPR)",
            figsize=(7.4, 5.2),
            dpi=st.figure_dpi,
        )
    )
    doc.figures.append(
        Figure(
            key="roc",
            path=f"media/{Path(p).name}",
            caption="ROC-кривые гипотетических моделей (учебный пример)",
            section_id="ch2-3",
            provenance="synthetic",
            source_note="Учебный пример: данные смоделированы и не являются результатом реального исследования",
            dataset_key="roc_demo",
        )
    )

    # --- 4. Таблица источников ---
    studies = studies_dataset(sources)
    doc.tables.append(
        Table(
            key="studies",
            headers=["Источник", "Год", "Название", "Издание", "DOI"],
            rows=[
                [
                    r.values.get("Источник", ""),
                    str(r.values.get("Год", "")),
                    _short(r.values.get("Название", ""), 70),
                    _short(r.values.get("Издание", ""), 34),
                    r.values.get("DOI", ""),
                ]
                for r in studies.rows
            ],
            caption="Характеристика отобранных источников",
            section_id="ch2-1",
            provenance="real",
            source_note="Все записи проверены через Crossref API",
        )
    )

    # --- 5. CSV с данными (прозрачность) ---
    write_datasets([pct, counts, auc, studies, roc], data_dir)


def _short(text: str, n: int) -> str:
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def _metrics_table(dataset, source_keys: list[str], caption: str, number: str = "") -> Table:
    rows = []
    for r in dataset.rows:
        rows.append(
            [
                r.values.get("Исследование", ""),
                _short(r.values.get("Контекст", ""), 90),
                _fmt(r.values.get("Значение")),
                ", ".join(r.source_keys),
            ]
        )
    return Table(
        key=dataset.key,
        headers=["Исследование", "Контекст показателя", "Значение", "Ключ источника"],
        rows=rows,
        caption=caption,
        number=number,
        section_id="ch2-2",
        provenance="real",
        source_note="Значения извлечены из проверенных источников в неизменном виде",
    )


def _fmt(value) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(v)) if abs(v - round(v)) < 1e-9 else f"{v:.2f}"


# --------------------------------------------------------------------------- #
# Шаг 6: нумерация
# --------------------------------------------------------------------------- #


def number_media(doc: Document, registry: Registry) -> None:
    """Нумерует рисунки и таблицы в порядке их появления в тексте."""
    chapter_number: dict[str, str] = {}
    for i, sec in enumerate([s for s in doc.plan.sections if s.kind == "body"], start=1):
        chapter_number[sec.id] = str(i)
        for child in sec.children:
            chapter_number[child.id] = str(i)

    def order_key(section_id: str) -> tuple:
        ids = [s.id for s in doc.plan.walk()]
        return (ids.index(section_id) if section_id in ids else len(ids), section_id)

    for fig in sorted(doc.figures, key=lambda f: order_key(f.section_id)):
        registry.number_figure(fig, chapter_number.get(fig.section_id))
    for tbl in sorted(doc.tables, key=lambda t: order_key(t.section_id)):
        registry.number_table(tbl, chapter_number.get(tbl.section_id))


# --------------------------------------------------------------------------- #
# Шаг 4: текст
# --------------------------------------------------------------------------- #


def _backend(st: Settings):
    if st.text_backend == "llm":
        from .textgen.llm import LLMBackend

        backend = LLMBackend(model=st.llm_model, base_url=st.llm_base_url)
        if backend.available():
            return backend
    return DeterministicComposer()


def compose_text(doc: Document, st: Settings, backend) -> None:
    plan = doc.plan
    allocation = allocate_sources(plan, doc.sources)

    def media_for(section_id: str) -> list[str]:
        labels = [f.label for f in doc.figures if f.section_id == section_id]
        labels += [t.label for t in doc.tables if t.section_id == section_id]
        return labels

    for sec in plan.sections:
        if sec.id == "intro":
            doc.sections_md["intro"] = backend.write_introduction(plan.topic, doc.sources, plan)
            continue
        if sec.id == "concl":
            doc.sections_md["concl"] = backend.write_conclusion(plan.topic, doc.sources, plan)
            continue
        if sec.id == "refs":
            doc.sections_md["refs"] = "{{BIBLIOGRAPHY}}"
            continue
        # главы и параграфы
        if sec.children:
            chapter_idx = [s.id for s in plan.sections if s.kind == "body"].index(sec.id) + 1
            ctx = SectionContext(
                topic=plan.topic,
                plan=plan,
                section=sec,
                sources=[],
                media_refs=media_for(sec.id),
                chapter_number=str(chapter_idx),
                path=f"Глава {chapter_idx}",
            )
            # вступительный абзац главы (без повторения заголовка главы)
            doc.sections_md[sec.id] = backend.write_section(ctx).split("\n\n")[0]
            for j, child in enumerate(sec.children, start=1):
                cctx = SectionContext(
                    topic=plan.topic,
                    plan=plan,
                    section=child,
                    sources=allocation.get(child.id, []),
                    media_refs=media_for(child.id),
                    chapter_number=str(chapter_idx),
                    path=f"{chapter_idx}.{j}",
                )
                doc.sections_md[child.id] = backend.write_section(cctx)
        else:
            ctx = SectionContext(
                topic=plan.topic,
                plan=plan,
                section=sec,
                sources=allocation.get(sec.id, []),
                media_refs=media_for(sec.id),
            )
            doc.sections_md[sec.id] = backend.write_section(ctx)


# --------------------------------------------------------------------------- #
# Основная функция
# --------------------------------------------------------------------------- #


def run_pipeline(st: Settings, progress=None) -> BuildResult:
    st.ensure_dirs()
    out_dir = Path(st.out_dir)
    result = BuildResult(out_dir=out_dir)

    # 1. Тема ----------------------------------------------------------------
    _progress(progress, 1, f"Разбор темы: {st.topic}")
    topic = build_topic(st.topic, st.work_type)

    # 2. План ----------------------------------------------------------------
    _progress(progress, 2, "Построение плана и структуры глав")
    plan = build_plan(topic, st.work_type)
    (out_dir / "plan.md").write_text(plan_to_markdown(plan), encoding="utf-8")

    # 3. Поиск и проверка источников -----------------------------------------
    _progress(progress, 3, "Поиск и проверка научных источников")
    report = search_sources(
        topic,
        max_sources=st.max_sources,
        offline=st.search_offline,
        verify=st.verify_doi,
    )
    sources = report.sources
    result.warnings += report.warnings
    if report.verification:
        (out_dir / "verification.md").write_text(verification_report(report.verification), encoding="utf-8")

    doc = Document(topic=topic, plan=plan, sources=sources, warnings=list(report.warnings))
    doc.metadata = {
        "title": topic.title,
        "author": st.author,
        "group": st.group,
        "chair": st.chair,
        "supervisor": st.supervisor,
        "institution": st.institution,
        "city": st.city,
        "year": st.year or date.today().year,
        "work_type": st.work_type,
        "bibfile": "references.bib",
        "cslfile": "assets/gost.csl",
        "bib_style": st.bib_style,
    }

    # 4-6. Данные, рисунки, таблицы, нумерация -------------------------------
    _progress(progress, 4, "Подготовка данных, графиков и иллюстраций")
    registry = Registry(mode="chapter")
    build_media(doc, registry, st, out_dir)
    _progress(progress, 5, "Нумерация рисунков и таблиц")
    number_media(doc, registry)

    # 4. Текст ---------------------------------------------------------------
    _progress(progress, 6, "Написание текста по проверенным источникам")
    backend = _backend(st)
    compose_text(doc, st, backend)
    doc.metadata["annotation"] = backend.write_annotation(topic, sources)

    # 7. Сборка markdown, список литературы ----------------------------------
    _progress(progress, 7, "Формирование списка литературы и исходного текста")
    rendered = engine.render_all(doc, registry, st, out_dir)
    result.files.update(rendered.files)
    result.warnings += rendered.warnings

    # 10. Архив --------------------------------------------------------------
    _progress(progress, 8, "Упаковка результатов")
    if st.make_zip:
        zip_path = out_dir / "diploma-build.zip"
        _make_zip(out_dir, zip_path)
        result.files["ZIP"] = str(zip_path)

    result.document = doc
    result.search_report = report
    result.files["План"] = str(out_dir / "plan.md")
    result.files["Протокол проверки"] = str(out_dir / "verification.md")
    if (out_dir / "document.json").exists():
        result.files["Данные (JSON)"] = str(out_dir / "document.json")
    _progress(progress, 9, "Готово")
    return result


def _make_zip(out_dir: Path, zip_path: Path) -> Path:
    zip_path = Path(zip_path)
    skip = {zip_path.name, "document.rendered.md", "_reference.docx"}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(Path(out_dir).rglob("*")):
            if not path.is_file() or path.name in skip or path.suffix == ".zip":
                continue
            zf.write(path, path.relative_to(out_dir))
    return zip_path
