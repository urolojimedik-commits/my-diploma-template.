"""Орфография и типографика таджикского текста.

Правила лежат в ``data/orthography.tg.yml``; модуль только применяет их:

* ``normalize(text)`` — приводит тире, кавычки, десятичную запятую, пробел
  перед «%» и неразрывные пробелы к принятому виду;
* ``check(text)`` — находит нарушения и возвращает понятные сообщения
  (код, фрагмент, что исправить);
* ``check_heading(text)`` — отдельная проверка заголовка: регистр, отсутствие
  точки в конце.

Модуль ничего не «улучшает» по смыслу: правила механические и обратимые.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..settings import DATA_DIR

ORTHO_PATH = DATA_DIR / "orthography.tg.yml"

# Заимствования, в которых ъ/ы/ь допустимы
BORROWED = {
    "объект", "объектив", "объём", "субъект", "субъектив", "адъювант",
    "инъексия", "инъекция", "конъюнктива", "разъезд", "подъём", "объяснение",
    "ы", "ь", "ъ", "алгоритм", "биология", "физиология",
}

DECIMAL_POINT = re.compile(r"(?<![\d.,])(\d+)\.(\d{1,3})(?![\d.,])")
# Идентификаторы (DOI, URL, десятичные дроби вроде 10.1155/2018) не трогаем
PROTECTED = re.compile(r"https?://|doi:|10\.\d{4,9}/|/", re.IGNORECASE)
PERCENT = re.compile(r"(?<=[\d,.])%")
NO_SPACE_AFTER_COMMA = re.compile(r",(?=[^\s\d])")
MULTISPACE = re.compile(r"[ \t]{2,}")
RUSSIAN_ONLY_LETTERS = re.compile(r"[ыъь]")
WORD_RE = re.compile(r"[А-Яа-яЁёҒӢҚӮҲҶғӣқӯҳҷ]+")
HEADING_DOT = re.compile(r"[.!?]$")


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return {}
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class Problem:
    code: str
    fragment: str
    message: str
    suggestion: str = ""

    def __str__(self) -> str:
        tail = f" → {self.suggestion}" if self.suggestion else ""
        return f"[{self.code}] «{self.fragment}»: {self.message}{tail}"


class Orthography:
    """Правила таджикской орфографии и типографики."""

    def __init__(self, data: dict | None = None) -> None:
        self.data = data if data is not None else _load_yaml(ORTHO_PATH)
        p = (self.data.get("punctuation") or {})
        self.dash: str = p.get("dash", "—")
        self.decimal_separator: str = p.get("decimal_separator", ",")
        self.percent_space: str = p.get("percent_space", " ")
        q = (self.data.get("punctuation") or {}).get("quotes_primary") or ["«", "»"]
        self.quote_open, self.quote_close = q[0], q[1]
        rules = self.data.get("rules") or {}
        self.heading_case: str = rules.get("heading_case", "sentence")
        self.no_dot_at_heading_end: bool = bool(rules.get("no_dot_at_heading_end", True))
        self.specific_letters: list[str] = list(
            (self.data.get("alphabet") or {}).get("specific_letters", [])
        )

    # ------------------------------------------------------------ нормализация
    def normalize(self, text: str) -> str:
        # тире только там, где оно стоит отдельно: « - » → « — »;
        # дефисы внутри слов («12,5 %-ро», «магнитӣ-резонансӣ») не трогаем
        text = re.sub(r"\s+-\s+", f" {self.dash} ", text)
        text = MULTISPACE.sub(" ", text)
        if self.decimal_separator == ",":
            text = re.sub(r"\S+", lambda m: self._decimal_token(m.group(0)), text)
        if self.percent_space:
            text = PERCENT.sub(f"{self.percent_space}%", text)
        text = NO_SPACE_AFTER_COMMA.sub(", ", text)
        return text

    @staticmethod
    def _needs_comma(integer: str, fraction: str) -> bool:
        """Нужно ли заменять точку на запятую.

        «12.5» → да; «0.05» → да; «1.1» → нет: в таджикском (и русском) тексте
        одинарные цифры через точку чаще означают номер раздела или рисунка.
        """
        return len(integer) >= 2 or len(fraction) >= 2

    @classmethod
    def _decimal_token(cls, token: str) -> str:
        """Десятичная точка → запятая внутри «простых» чисел одного токена."""
        if PROTECTED.search(token):
            return token

        def repl(m: re.Match) -> str:
            prev = token[: m.start()]
            nxt = token[m.end() :]
            if prev and (prev[-1].isdigit() or prev[-1] in ".,"):
                return m.group(0)
            if nxt[:1].isdigit() or nxt[:1] == ".":
                return m.group(0)
            if not cls._needs_comma(m.group(1), m.group(2)):
                return m.group(0)
            return f"{m.group(1)},{m.group(2)}"

        return re.sub(r"(\d+)\.(\d{1,3})", repl, token)

    # ---------------------------------------------------------------- проверки
    def check(self, text: str) -> list[Problem]:
        problems: list[Problem] = []
        if self.decimal_separator == ",":
            for m in re.finditer(r"(\d+)\.(\d{1,3})", text):
                context = text[max(0, m.start() - 40) : m.end() + 40]
                if PROTECTED.search(context):
                    continue
                if not self._needs_comma(m.group(1), m.group(2)):
                    continue
                frag = text[max(0, m.start() - 3) : m.end() + 3]
                problems.append(
                    Problem(
                        "decimal_comma",
                        frag.strip(),
                        "даҳӣ бо вергул навишта мешавад",
                        frag.strip().replace(".", ","),
                    )
                )
        for m in PERCENT.finditer(text):
            frag = text[max(0, m.start() - 5) : m.end()]
            problems.append(
                Problem("percent_space", frag.strip(),
                        "пеши % фосила лозим аст",
                        frag.strip().replace("%", " %"))
            )
        for m in NO_SPACE_AFTER_COMMA.finditer(text):
            frag = text[max(0, m.start() - 6) : m.end() + 6]
            problems.append(
                Problem("space_after_comma", frag.strip(),
                        "баъди вергул фосила лозим аст")
            )
        for word in WORD_RE.findall(text):
            low = word.lower()
            if low in BORROWED:
                continue
            if RUSSIAN_ONLY_LETTERS.search(low):
                problems.append(
                    Problem("russian_letter", word,
                            "ҳарфи ъ/ы/ь танҳо дар калимаҳои иқтибосӣ иҷозат аст")
                )
        return problems

    def check_heading(self, text: str) -> list[Problem]:
        problems: list[Problem] = []
        head = text.strip()
        if self.no_dot_at_heading_end and HEADING_DOT.search(head):
            problems.append(
                Problem("heading_dot", head[-20:],
                        "дар охири сарлавҳа нуқта гузошта намешавад",
                        head.rstrip(".!?"))
            )
        if head and head[0].islower():
            problems.append(
                Problem("heading_case", head[:20],
                        "сарлавҳа бо ҳарфи калон оғоз мешавад",
                        head[0].upper() + head[1:])
            )
        return problems

    def fix_heading(self, text: str) -> str:
        head = text.strip().rstrip(".!?")
        return head[0].upper() + head[1:] if head else head

    # ------------------------------------------------------------------ шрифты
    def fonts(self) -> dict:
        return dict(self.data.get("fonts") or {})


def get_orthography() -> Orthography:
    return Orthography()
