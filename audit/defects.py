# -*- coding: utf-8 -*-
"""Rule-based inline defect detection for the marked copy.
Each finder returns list of (start, end, colour, code, note)."""
import re

Y, R, G = "yellow", "red", "green"

RULES = [
    # (regex, colour, code, message-template)
    # --- no space after sentence punctuation (Tajik orthography) ---
    (re.compile(r"(?<=[а-яёӣқғҳҷӯА-ЯЁӢҚҒҲҶӮ])\.(?=[А-ЯЁӢҚҒҲҶӮа-яёӣқғҳҷӯ])"),
     Y, "Л1", "Нуқтаи баъди ҷумла бояд бо фосила ҷудо шавад: «{ctx}». Баъди нуқта фосила гузоред."),
    (re.compile(r"(?<=[а-яёӣқғҳҷӯ])\.(?=[А-ЯЁӢҚҒҲҶӮ])"),
     Y, "Л1", "Баъди нуқта фосила нест: «{ctx}». Дурусташ: «{fix}»."),
    # --- glued bullet / numbering markers ---
    (re.compile(r"(?m)^([•▪➢❖✓→])(?=[А-ЯЁӢҚҒҲҶӮа-яёӣқғҳҷӯA-Za-z])"),
     Y, "Л2", "Аломати рӯйхат ба матн часпидааст: «{ctx}». Баъди аломат фосила лозим аст."),
    (re.compile(r"(?m)^(\d{1,2}\.)(?=[А-ЯЁӢҚҒҲҶӮ])"),
     Y, "Л2", "Рақами рӯйхат ба калима часпидааст: «{ctx}». Баъди рақам фосила лозим аст."),
    (re.compile(r"(?m)^([a-eа-е])\)(?=[А-ЯЁӢҚҒҲҶӮ])"),
     Y, "Л2", "Ҳарфи рӯйхат ба калима часпидааст: «{ctx}». Баъди «)» фосила лозим аст."),
    # --- latin o used as bullet
    (re.compile(r"(?m)^(o)(?=[А-ЯЁӢҚҒҲҶӮ])"),
     Y, "Л3", "Ба ҷои аломати рӯйхат ҳарфи лотинии «o» истифода шудааст: «{ctx}». Низоми аломатҳоро якхела кунед (масалан «•»)."),
    # --- space before punctuation ---
    (re.compile(r"(?<=[^\s])\s+(?=[,;:!?])"),
     Y, "Л4", "Пеш аз аломати пунктуатсия фосилаи зиёдатӣ: «{ctx}». Фосиларо нест кунед."),
    # --- double space ---
    (re.compile(r"[^\s]  +[^\s]"),
     Y, "Л5", "Фосилаи дучанда: «{ctx}». Як фосила гузоред."),
    # --- stray comma after bracket / dangling punctuation ---
    (re.compile(r"(?<![A-ZА-ЯЁӮӢҚҒҲҶ])\.\s*,(?=\s|$)"),
     Y, "Л6", "Нуқта ва вергул пайиҳам: «{ctx}». Аломати зиёдатиро нест кунед."),
    # --- hyphen with space inside compound term ---
    (re.compile(r"(?<=[а-яёӣқғҳҷӯ])\s+-\s*(?=[а-яёӣқғҳҷӯ])|(?<=[а-яёӣқғҳҷӯ])-\s+(?=[а-яёӣқғҳҷӯ])"),
     Y, "Л7", "Дар атрофи дефис фосилаи зиёдатӣ: «{ctx}». Дар калимаҳои якҷоя дефис бе фосила навишта мешавад."),
]

WORD_FIX = {  # spelling: wrong -> correct
    "пешгири": "пешгирӣ",
    "Эхогеннокӣ": "Эхогения",
    "эхогеннокии": "эхогенияи",
    "эхогеннокӣ": "эхогения",
    "ҳавзакҳои": "ҳавзаҳои",
    "ҳавзакҳо": "ҳавзаҳо",
    "Ташхиси ултрасадоии": None,
}

DOC_ISSUES = []  # filled by builders

def find_all(text):
    hits = []
    for rx, colour, code, msg in RULES:
        for m in rx.finditer(text):
            s, e = m.start(), m.end()
            if s >= e:
                # zero-width: expand to following word
                e = s + 1
            ctx = text[max(0, s - 25):min(len(text), e + 25)].replace("\n", " ")
            hits.append((s, e, colour, code, msg.format(ctx=ctx, fix=ctx.replace(".", ". ", 1))))
    # drop overlapping duplicates, keep first
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    out = []
    for h in hits:
        if out and h[0] < out[-1][1]:
            continue
        out.append(h)
    return out
