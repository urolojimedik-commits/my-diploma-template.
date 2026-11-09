"""
web/app.py — Flask веб-приложение для приёма темы и скачивания DOCX/PDF.

Маршруты:
  GET  /          — форма
  POST /build     — запуск pipeline
  GET  /download/<fmt> — скачивание
  GET  /preview   — предпросмотр
"""

from __future__ import annotations

import pathlib
import threading
import uuid
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_file, flash, jsonify, session

from ..pipeline import create_project_from_topic, DiplomaPipeline
from ..search import SourceSearcher

# Хранилище задач (в памяти)
JOBS: dict = {}


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = "diploma_builder_secret_2026"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/build", methods=["POST"])
    def build():
        topic = request.form.get("topic", "").strip()
        work_type = request.form.get("work_type", "диплом")
        discipline = request.form.get("discipline", "Информационные системы")
        author = request.form.get("author", "Иванов И.И.")
        verify = request.form.get("verify") == "on"

        if not topic:
            flash("Укажите тему работы", "error")
            return redirect(url_for("index"))

        if len(topic) < 10:
            flash("Тема слишком короткая (минимум 10 символов)", "error")
            return redirect(url_for("index"))

        job_id = str(uuid.uuid4())[:8]
        output_dir = pathlib.Path("output") / f"job_{job_id}"
        output_dir.mkdir(parents=True, exist_ok=True)

        JOBS[job_id] = {"status": "running", "topic": topic, "created": datetime.now().isoformat(), "output_dir": str(output_dir), "log": []}

        # Запуск в потоке
        def run_pipeline():
            try:
                cfg = create_project_from_topic(topic=topic, work_type=work_type, discipline=discipline, author_fio=author, output_dir=str(output_dir))
                pipeline = DiplomaPipeline(cfg)
                results = pipeline.run(with_search=True, with_figures=True, with_docx=True, with_pdf=True, with_quarto=True, search_rows=15, verify_sources=verify)
                JOBS[job_id]["status"] = "done"
                JOBS[job_id]["results"] = {k: str(v) for k, v in results.items()}
                JOBS[job_id]["log"].append("✅ Готово")
            except Exception as e:
                import traceback

                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["error"] = str(e)
                JOBS[job_id]["traceback"] = traceback.format_exc()
                print(f"[web] job {job_id} error: {e}")

        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()

        return render_template("building.html", job_id=job_id, topic=topic)

    @app.route("/status/<job_id>")
    def status(job_id):
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "not found"}), 404
        return jsonify(job)

    @app.route("/result/<job_id>")
    def result(job_id):
        job = JOBS.get(job_id)
        if not job:
            flash("Задача не найдена", "error")
            return redirect(url_for("index"))
        if job["status"] == "running":
            return render_template("building.html", job_id=job_id, topic=job["topic"])
        if job["status"] == "error":
            return render_template("error.html", job=job)

        # done
        output_dir = pathlib.Path(job["output_dir"])
        # список файлов
        files = {}
        for fmt in ["docx", "pdf"]:
            p = output_dir / f"thesis.{fmt}"
            if p.exists():
                files[fmt] = {"path": str(p), "size_kb": round(p.stat().st_size / 1024, 1)}

        # план
        plan_text = ""
        plan_path = output_dir / "plan.md"
        if plan_path.exists():
            plan_text = plan_path.read_text(encoding="utf-8")

        # источники
        sources = []
        src_json = output_dir / "sources.json"
        if src_json.exists():
            import json

            try:
                sources = json.loads(src_json.read_text(encoding="utf-8"))
            except Exception:
                pass

        # изображения
        images = list((output_dir / "images").glob("*.png")) if (output_dir / "images").exists() else []

        return render_template("result.html", job_id=job_id, job=job, files=files, plan_text=plan_text, sources=sources, images=[i.name for i in images])

    @app.route("/download/<job_id>/<fmt>")
    def download(job_id, fmt):
        job = JOBS.get(job_id)
        if not job or job["status"] != "done":
            return "Файл не готов", 404
        output_dir = pathlib.Path(job["output_dir"])
        file_map = {"docx": "thesis.docx", "pdf": "thesis.pdf", "bib": "references.bib", "plan": "plan.md", "gost": "bibliography_gost.txt"}
        fname = file_map.get(fmt)
        if not fname:
            return "Неизвестный формат", 404
        fpath = output_dir / fname
        if not fpath.exists():
            return f"Файл {fname} не найден", 404
        return send_file(str(fpath), as_attachment=True, download_name=f"diploma_{job_id}.{fmt}" if fmt in ("docx", "pdf") else fname)

    @app.route("/preview/<job_id>")
    def preview(job_id):
        job = JOBS.get(job_id)
        if not job:
            return "Not found", 404
        # отдаём список изображений
        output_dir = pathlib.Path(job["output_dir"])
        images_dir = output_dir / "images"
        if not images_dir.exists():
            return jsonify([])
        imgs = [f.name for f in images_dir.glob("*.png")]
        return jsonify(imgs)

    @app.route("/image/<job_id>/<name>")
    def image(job_id, name):
        job = JOBS.get(job_id)
        if not job:
            return "Not found", 404
        p = pathlib.Path(job["output_dir"]) / "images" / name
        if not p.exists():
            return "Not found", 404
        return send_file(str(p), mimetype="image/png")

    @app.route("/search", methods=["GET", "POST"])
    def search_page():
        results = None
        query = ""
        if request.method == "POST":
            query = request.form.get("query", "").strip()
            if query:
                searcher = SourceSearcher()
                results = searcher.search(query, rows=10, verify=False)
        return render_template("search.html", results=results, query=query)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "jobs": len(JOBS)})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)

