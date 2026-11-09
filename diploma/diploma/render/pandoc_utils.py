"""Обёртка над Pandoc.

Pandoc используется как **парсер** (markdown → AST) и как **сборщик DOCX**.
В песочнице бинарник Pandoc поставляется пакетом ``pypandoc-binary``,
поэтому отдельная установка не требуется; если в системе есть свой Pandoc,
он имеет приоритет.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_PANDOC_PATH: str | None = None


def find_pandoc() -> str | None:
    """Возвращает путь к pandoc или None, если инструмент недоступен."""
    global _PANDOC_PATH
    if _PANDOC_PATH:
        return _PANDOC_PATH
    system = shutil.which("pandoc")
    if system:
        _PANDOC_PATH = system
        return _PANDOC_PATH
    try:
        import pypandoc  # type: ignore

        path = pypandoc.get_pandoc_path()
        if path:
            _PANDOC_PATH = str(path)
            return _PANDOC_PATH
    except Exception:
        pass
    return None


def pandoc_available() -> bool:
    return find_pandoc() is not None


def pandoc_version() -> str:
    path = find_pandoc()
    if not path:
        return ""
    try:
        out = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=30
        ).stdout
        return out.splitlines()[0].replace("pandoc", "").strip() if out else ""
    except Exception:
        return ""


def run_pandoc(args: list[str], input_text: str | None = None, cwd: str | Path | None = None) -> str:
    path = find_pandoc()
    if not path:
        raise RuntimeError("Pandoc не найден. Установите его: pip install pypandoc-binary")
    proc = subprocess.run(
        [path, *args],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Pandoc завершился с ошибкой:\n{proc.stderr[:4000]}")
    return proc.stdout


def to_ast(markdown: str, fmt: str = "markdown") -> dict:
    """Разбирает markdown в AST Pandoc (JSON)."""
    out = run_pandoc(
        [
            "--from",
            fmt,
            "--to",
            "json",
            "--wrap=preserve",
            "--indented-code-classes=python",
        ],
        input_text=markdown,
    )
    return json.loads(out)


def convert(
    markdown: str,
    to: str,
    extra_args: list[str] | None = None,
    cwd: str | Path | None = None,
) -> str:
    return run_pandoc(["--from", "markdown", "--to", to, *(extra_args or [])], markdown, cwd=cwd)


def convert_file(
    src: Path | str,
    to: str,
    output: Path | str,
    extra_args: list[str] | None = None,
    cwd: str | Path | None = None,
) -> Path:
    run_pandoc(
        [
            str(src),
            "--from",
            "markdown",
            "--to",
            to,
            "--output",
            str(output),
            *(extra_args or []),
        ],
        cwd=cwd,
    )
    return Path(output)
