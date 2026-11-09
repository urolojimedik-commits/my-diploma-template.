"""Веб-интерфейс и выдача готовых документов (шаг 10).

Сервер написан на стандартной библиотеке (http.server), поэтому для запуска
не нужны Flask/Django: ``python -m diploma web --port 8000``.

Маршруты:

* ``GET  /``                       — интерфейс;
* ``POST /api/generate``           — запуск конвейера (в отдельном потоке);
* ``GET  /api/jobs/<id>``          — состояние и прогресс задания;
* ``GET  /api/jobs/<id>/files``    — список файлов для скачивания;
* ``GET  /files/<id>/<path>``      — файл на диске;
* ``GET  /api/jobs/<id>/download/<label>`` — скачиваниеDOCX/PDF/ZIP.
"""

from __future__ import annotations

import copy
import html
import json
import mimetypes
import re
import threading
import traceback
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..pipeline import TOTAL_STEPS, BuildResult, run_pipeline
from ..settings import Settings

STATIC_DIR = Path(__file__).resolve().parent / "static"

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()

DEFAULT_TOPIC = (
    "Применение методов машинного обучения для автоматизированной диагностики "
    "мочекаменной болезни по данным компьютерной томографии"
)

MIME_BY_LABEL = {
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "PDF": "application/pdf",
    "ZIP": "application/zip",
    "HTML": "text/html; charset=utf-8",
    "BibTeX": "application/x-bibtex; charset=utf-8",
    "Markdown": "text/markdown; charset=utf-8",
}


# --------------------------------------------------------------------------- #
# Задания
# --------------------------------------------------------------------------- #


def _new_job(out_root: Path) -> str:
    job_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    out_dir = Path(out_root) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "status": "queued",
            "step": 0,
            "total": TOTAL_STEPS,
            "message": "В очереди",
            "out_dir": str(out_dir),
            "files": {},
            "warnings": [],
            "stats": {},
            "topic": "",
            "created": datetime.now().isoformat(timespec="seconds"),
        }
    return job_id


def _update(job_id: str, **fields) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(fields)


def _run_job(job_id: str, payload: dict) -> None:
    try:
        out_dir = Path(JOBS[job_id]["out_dir"])
        st = Settings(
            topic=payload.get("topic") or DEFAULT_TOPIC,
            work_type=payload.get("work_type", "diploma"),
            out_dir=out_dir,
            bib_style=payload.get("bib_style", "gost"),
            max_sources=int(payload.get("max_sources", 20) or 20),
            search_offline=bool(payload.get("offline", False)),
            verify_doi=not bool(payload.get("no_verify", False)),
            pdf_engine=payload.get("pdf_engine", "auto"),
            author=payload.get("author", "Иванов И. И.") or "Иванов И. И.",
            group=payload.get("group", ""),
            chair=payload.get("chair", ""),
            supervisor=payload.get("supervisor", ""),
            institution=payload.get("institution", ""),
            city=payload.get("city", ""),
            year=int(payload["year"]) if payload.get("year") else None,
            export_quarto=bool(payload.get("export_quarto", True)),
            make_zip=bool(payload.get("make_zip", True)),
        )

        def progress(step: int, total: int, message: str) -> None:
            _update(job_id, status="running", step=step, total=total, message=message)

        _update(job_id, status="running", topic=st.topic, message="Запуск конвейера")
        result: BuildResult = run_pipeline(st, progress=progress)
        _update(
            job_id,
            status="done",
            step=TOTAL_STEPS,
            message="Готово",
            files=result.files,
            warnings=result.warnings,
            stats={
                "sources": len(result.document.sources) if result.document else 0,
                "verified": sum(1 for s in result.document.sources if s.verified) if result.document else 0,
                "figures": len(result.document.figures) if result.document else 0,
                "tables": len(result.document.tables) if result.document else 0,
                "sections": len(list(result.document.plan.walk())) if result.document else 0,
                "search": result.search_report.summary() if result.search_report else "",
            },
        )
    except Exception as exc:  # сбой не должен ронять сервер
        tb = traceback.format_exc(limit=6)
        _update(job_id, status="error", message=f"{exc}", warnings=[tb])


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #


class Handler(BaseHTTPRequestHandler):
    server_version = "DiplomaAutomation/1.0"

    # --------------------------------------------------------------- helpers
    def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8",
              extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: dict, code: int = 200) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _html(self, text: str, code: int = 200) -> None:
        self._send(code, text.encode("utf-8"), "text/html; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:  # тише в консоли
        pass

    # ------------------------------------------------------------------- GET
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._html((STATIC_DIR / "index.html").read_text(encoding="utf-8"))
            return
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            file = (STATIC_DIR / rel).resolve()
            if str(file).startswith(str(STATIC_DIR)) and file.exists():
                ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                if ctype.startswith("text/") or ctype in {"application/javascript"}:
                    ctype += "; charset=utf-8"
                self._send(200, file.read_bytes(), ctype)
                return
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        m = re.match(r"^/api/jobs/([A-Za-z0-9._-]+)$", path)
        if m:
            job = JOBS.get(m.group(1))
            if not job:
                self._json({"error": "job not found"}, 404)
                return
            self._json(job)
            return
        m = re.match(r"^/api/jobs/([A-Za-z0-9._-]+)/files$", path)
        if m:
            job = JOBS.get(m.group(1))
            if not job:
                self._json({"error": "job not found"}, 404)
                return
            files = []
            for label, p in job.get("files", {}).items():
                path_obj = Path(p)
                files.append(
                    {
                        "label": label,
                        "name": path_obj.name,
                        "size": path_obj.stat().st_size if path_obj.is_file() else 0,
                        "url": f"/api/jobs/{job['id']}/download/{label}",
                    }
                )
            self._json({"files": files})
            return
        m = re.match(r"^/api/jobs/([A-Za-z0-9._-]+)/download/(.+)$", path)
        if m:
            self._download(m.group(1), unquote(m.group(2)))
            return
        m = re.match(r"^/files/([A-Za-z0-9._-]+)/(.*)$", path)
        if m:
            job = JOBS.get(m.group(1))
            if not job:
                self._send(404, b"job not found", "text/plain; charset=utf-8")
                return
            base = Path(job["out_dir"]).resolve()
            target = (base / unquote(m.group(2))).resolve()
            if str(target).startswith(str(base)) and target.is_file():
                ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                self._send(
                    200,
                    target.read_bytes(),
                    ctype,
                    {"Content-Disposition": f'inline; filename="{target.name}"'},
                )
                return
            self._send(404, b"file not found", "text/plain; charset=utf-8")
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def _download(self, job_id: str, label: str) -> None:
        job = JOBS.get(job_id)
        if not job:
            self._send(404, b"job not found", "text/plain; charset=utf-8")
            return
        target = job.get("files", {}).get(label)
        if not target:
            self._send(404, f"файл «{label}» не найден".encode("utf-8"), "text/plain; charset=utf-8")
            return
        path = Path(target)
        if path.is_dir():  # Quarto-проект отдаём архивом
            import io
            import zipfile

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(path.rglob("*")):
                    if f.is_file():
                        zf.write(f, f.relative_to(path))
            self._send(
                200,
                buf.getvalue(),
                "application/zip",
                {"Content-Disposition": f'attachment; filename="{path.name}.zip"'},
            )
            return
        if not path.exists():
            self._send(404, b"file missing", "text/plain; charset=utf-8")
            return
        ctype = MIME_BY_LABEL.get(label) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self._send(
            200,
            path.read_bytes(),
            ctype,
            {"Content-Disposition": f'attachment; filename="{_safe_name(path.name)}"'},
        )

    # ------------------------------------------------------------------ POST
    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/generate":
            self._json({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json({"error": "invalid json"}, 400)
            return
        out_root = Path(self.server.out_root)  # type: ignore[attr-defined]
        job_id = _new_job(out_root)
        thread = threading.Thread(target=_run_job, args=(job_id, payload), daemon=True)
        thread.start()
        self._json({"id": job_id, "status": "queued"})


def _safe_name(name: str) -> str:
    name = re.sub(r"[^\w.\-() ]+", "_", name, flags=re.UNICODE)
    return name or "file"


def serve(host: str = "0.0.0.0", port: int = 8000, out_root: Path | str | None = None) -> None:
    out_root = Path(out_root or (Path(__file__).resolve().parents[2] / "build" / "jobs"))
    out_root.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    server.out_root = str(out_root)  # type: ignore[attr-defined]
    print(f"Веб-интерфейс: http://{host}:{port}/")
    print(f"Каталог сборок: {out_root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
