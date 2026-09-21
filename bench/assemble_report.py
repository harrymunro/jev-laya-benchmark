"""Stitch REPORT.md from the narrative drafts and the generated tables."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"

tables = {}
current = None
for line in (RES / "tables.md").read_text().splitlines():
    m = re.match(r"^## (.+)$", line)
    if m:
        current = m.group(1)
        tables[current] = []
    elif current:
        tables[current].append(line)
tables = {k: "\n".join(v).strip() for k, v in tables.items()}

MAP = {
    "SINGLE_TABLE": "Single-question latency", "MULTIQ_TABLE": "Questions per request", "STATELEN_TABLE": "State length",
    "TPUT_TABLE": "Throughput", "TIMING_TABLE": "Accuracy-run timing", "MASTER_TABLE": "Accuracy master",
    "PAIRED_TABLE": "Paired Jev - Laya", "CHOICE_TABLE": "Choice detail", "NOUL_TABLE": "Noul detail",
    "SCORE_TABLE": "Score detail", "NEEDLE_LEN_TABLE": "Needle by length", "NEEDLE_POS_TABLE": "Needle by position",
    "MULTI_TABLE": "Multilingual",
}


def fill(text):
    for key, name in MAP.items():
        text = text.replace(key, tables.get(name, f"_({name} table missing)_"))
    return text


parts = [
    (RES / "report_header.md").read_text(),
    (RES / "report_static.md").read_text(),
    fill((RES / "report_speed.md").read_text()),
    fill((RES / "report_accuracy.md").read_text()),
    (RES / "report_qualitative.md").read_text(),
    (RES / "report_tail.md").read_text(),
]
out = ROOT / "REPORT.md"
out.write_text("\n\n".join(p.strip() for p in parts) + "\n")
print(f"wrote {out} ({len(out.read_text().split())} words)")
