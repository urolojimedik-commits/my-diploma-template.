# -*- coding: utf-8 -*-
"""Insert table objects into the block stream at their physical position (page, y)."""
import json
blocks = json.load(open("blocks.json"))

TABLES = [  # (key, page, y_start)
    ("T1", 16, 244), ("T2", 21, 468), ("T3", 25, 50), ("T4", 29, 515),
    ("T5", 34, 58), ("T6", 34, 600), ("T7", 38, 200), ("T8", 41, 695),
    ("T9", 49, 505), ("T10", 50, 40),
]

def insert_point(page, y):
    for i, b in enumerate(blocks):
        if b["page"] > page: return i
        if b["page"] == page and b.get("y", 1e9) >= y: return i
    return len(blocks)

ins = {}
for key, page, y in TABLES:
    i = insert_point(page, y)
    ins.setdefault(i, []).append((key, page, y))

paras = []
for i in range(len(blocks) + 1):
    for key, page, y in ins.get(i, []):
        paras.append({"kind": "table", "key": key, "page": page})
    if i < len(blocks):
        b = blocks[i]
        paras.append({"kind": b["kind"], "text": b["text"], "page": b["page"]})

json.dump(paras, open("paras.json", "w"), ensure_ascii=False, indent=1)
print("paras:", len(paras), "tables:", sum(1 for p in paras if p["kind"] == "table"))
for i, v in sorted(ins.items()):
    nxt = blocks[i]["text"][:45] if i < len(blocks) else "EOF"
    print(f"  after p{blocks[i-1]['page']}: {[k for k, _, _ in v]}  ->  {nxt}")
