"""Accuracy, calibration and latency tables for a set of backends against a baseline (Jev vs Kev).

python bench/report_compare.py                                  # results/jev-vs-kev/predictions -> results/jev-vs-kev/tables.md
python bench/report_compare.py --pred-dir results/predictions --backends jev laya   # reproduces the Laya report
"""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.metrics import SCORERS, paired_diff_ci  # noqa: E402
from bench.tasks import TASKS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# OpenRouter list price, USD per million input tokens (output is free for both); used to estimate cost
PRICE_IN_PER_MTOK = {"jev-openrouter": 0.042, "kev": 0.042}


def load(pred_dir, backend, task):
    p = pred_dir / backend / f"{task}.jsonl"
    return {r["id"]: r for r in map(json.loads, p.read_text().splitlines())} if p.exists() else {}


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", type=Path, default=ROOT / "results" / "jev-vs-kev" / "predictions")
    ap.add_argument("--backends", nargs="+", default=["jev-openrouter", "kev"])
    ap.add_argument("--speed", type=Path, default=ROOT / "results" / "jev-vs-kev" / "speed.json")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "jev-vs-kev" / "tables.md")
    args = ap.parse_args()

    base = args.backends[0]
    preds = {b: {t: load(args.pred_dir, b, t) for t in TASKS} for b in args.backends}
    backends = [b for b in args.backends if any(preds[b].values())]
    others = [b for b in backends if b != base]
    md = [f"Predictions: `{args.pred_dir}`. Baseline for paired differences: **{base}**.", ""]

    # per-question scores on the items every backend answered (paired)
    per_q, per_type, pooled, n_judg, summary = [], defaultdict(lambda: defaultdict(list)), defaultdict(list), defaultdict(int), {}
    for task, spec in TASKS.items():
        ids = sorted(set.intersection(*(set(preds[b][task]) for b in backends))) if backends else []
        if not ids:
            continue
        for qid, (_, qtype) in spec["gold"].items():
            row = {"task": task, "qid": qid, "type": qtype, "n": len(ids), "m": {}}
            for b in backends:
                rows = [(preds[b][task][i]["gold"][qid], preds[b][task][i]["answers"][qid]) for i in ids]
                m = SCORERS[qtype](rows)
                row["m"][b] = m
                per_type[qtype][b].append(m["accuracy"])  # mean over questions, as in report.py
                pooled[b].append(m["accuracy"])
                n_judg[b] += m["n"]
            per_q.append(row)

    # headline
    md += ["## Headline", "", "| | " + " | ".join(backends) + " |", "|---|" + "---:|" * len(backends)]
    md.append(f"| Mean accuracy, {len(per_q)} questions | " + " | ".join(f"{100 * statistics.fmean(pooled[b]):.1f}% ({n_judg[b]:,} judgments)" for b in backends) + " |")
    for t in ("choice", "noul", "score"):
        md.append(f"| {t.capitalize()} mean accuracy | " + " | ".join(f"{100 * statistics.fmean(per_type[t][b]):.1f}%" for b in backends) + " |")
    for b in others:
        cis = [paired_diff_ci(r["m"][base]["correct"], r["m"][b]["correct"])[1] for r in per_q]
        summary[b] = (sum(1 for lo, _ in cis if lo > 0), sum(1 for _, hi in cis if hi < 0))
    md.append("| Questions where baseline is significantly better / worse | " + " | ".join("" if b == base else f"{summary[b][0]} / {summary[b][1]} of {len(per_q)}" for b in backends) + " |")
    lat, cost, tok_in, tok_out, n_items = {}, {}, {}, {}, {}
    for b in backends:
        rows = [r for t in TASKS for r in preds[b][t].values()]
        lat[b] = [r["elapsed_ms"] for r in rows]
        cost[b] = sum(r["input_tokens"] for r in rows) * PRICE_IN_PER_MTOK[b] / 1e6 if b in PRICE_IN_PER_MTOK else None
        tok_in[b] = statistics.fmean(r["input_tokens"] for r in rows)
        tok_out[b] = statistics.fmean(r.get("output_tokens") or 0 for r in rows)
        n_items[b] = len(rows)
    md.append("| Per-item latency p50 / p95 (accuracy run) | " + " | ".join(f"{pct(lat[b], .5):.0f} / {pct(lat[b], .95):.0f} ms" for b in backends) + " |")
    md.append("| Tokens in / out per item | " + " | ".join(f"{tok_in[b]:.0f} / {tok_out[b]:.0f}" for b in backends) + " |")
    md.append("| Est. cost per 1,000 items (list price x input tokens) | " + " | ".join(f"${1000 * cost[b] / n_items[b]:.3f}" if cost[b] else "n/a" for b in backends) + " |")
    md.append("")

    # per question with paired differences
    hdr = "| Task | Question | Type | n | " + " | ".join(backends) + " | " + " | ".join(f"{base} − {b} (95% CI)" for b in others) + " |"
    md += ["## Accuracy by question", "", hdr, "|---|---|---|---:|" + "---:|" * (len(backends) + len(others))]
    for r in per_q:
        cells = [f"{100 * r['m'][b]['accuracy']:.1f}" for b in backends]
        for b in others:
            d, (lo, hi) = paired_diff_ci(r["m"][base]["correct"], r["m"][b]["correct"])
            sig = "**" if lo > 0 or hi < 0 else ""
            cells.append(f"{sig}{100 * d:+.1f} ({100 * lo:+.1f}, {100 * hi:+.1f}){sig}")
        md.append(f"| {r['task']} | {r['qid']} | {r['type']} | {r['n']} | " + " | ".join(cells) + " |")
    md += ["", "Bold: the paired 95% bootstrap CI excludes zero.", ""]

    # calibration / ranking quality
    md += ["## Yes/no questions: ranking and calibration", "", "| Task | Question | " + " | ".join(f"{b} AUROC / Brier / ECE" for b in backends) + " |", "|---|---|" + "---:|" * len(backends)]
    for r in per_q:
        if r["type"] == "noul":
            md.append(f"| {r['task']} | {r['qid']} | " + " | ".join(f"{r['m'][b]['auroc']:.3f} / {r['m'][b]['brier']:.3f} / {r['m'][b]['ece']:.3f}" for b in backends) + " |")
    md += ["", "## Ordinal scores", "", "| Task | Question | " + " | ".join(f"{b} within-1 / MAE / Spearman" for b in backends) + " |", "|---|---|" + "---:|" * len(backends)]
    for r in per_q:
        if r["type"] == "score":
            md.append(f"| {r['task']} | {r['qid']} | " + " | ".join(f"{100 * r['m'][b]['within_1']:.1f}% / {r['m'][b]['mae_expected']:.2f} / {r['m'][b]['spearman']:.3f}" for b in backends) + " |")

    # needle by length, multilingual by language
    for task, key, title in (("needle", "length_target", "Long-context needle by state length (tokens)"), ("multilingual", "language", "Multilingual triage by language")):
        groups = defaultdict(lambda: defaultdict(list))
        for b in backends:
            for r in preds[b][task].values():
                g = r["meta"].get(key)
                groups[g][b].append(all(_correct(r, q, t) for q, (_, t) in TASKS[task]["gold"].items()))
        if groups:
            md += ["", f"## {title}", "", "Share of items with every question right (n).", "", f"| {key} | " + " | ".join(backends) + " |", "|---|" + "---:|" * len(backends)]
            for g in sorted(groups, key=lambda x: (isinstance(x, str), x)):
                md.append(f"| {g} | " + " | ".join(f"{100 * statistics.fmean(groups[g][b]):.1f}% ({len(groups[g][b])})" if groups[g][b] else "" for b in backends) + " |")

    # controlled speed sweeps
    if args.speed.exists():
        sp = json.loads(args.speed.read_text())
        sb = [b for b in backends if b in sp] or list(sp)
        md += ["", "## Controlled latency (interleaved calls)", "", "| Workload | " + " | ".join(f"{b} p50 / p95 ms" for b in sb) + " |", "|---|" + "---:|" * len(sb)]
        if all("single" in sp[b] for b in sb):
            md.append("| 1 question, short state | " + " | ".join(f"{sp[b]['single']['p50_ms']:.0f} / {sp[b]['single']['p95_ms']:.0f}" for b in sb) + " |")
        for i, row in enumerate(sp[sb[0]].get("multiq", [])):
            md.append(f"| {row['questions']} question{'s' if row['questions'] > 1 else ''}, one request | " + " | ".join(f"{sp[b]['multiq'][i]['p50_ms']:.0f} / {sp[b]['multiq'][i]['p95_ms']:.0f}" for b in sb) + " |")
        for i, row in enumerate(sp[sb[0]].get("statelen", [])):
            md.append(f"| 1 question, ~{row['approx_state_tokens']}-token state | " + " | ".join(f"{sp[b]['statelen'][i]['p50_ms']:.0f} / {sp[b]['statelen'][i]['p95_ms']:.0f}" for b in sb) + " |")
        for i, row in enumerate(sp[sb[0]].get("tput_64states", [])):
            md.append(f"| 64 items, {row['workers']} in flight (items/s) | " + " | ".join(f"{sp[b]['tput_64states'][i]['items_per_s']:.1f}" for b in sb) + " |")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(md) + "\n")
    print("\n".join(md[:14]))
    print(f"\nwrote {args.out}")


def _correct(row, qid, qtype):
    g, a = row["gold"][qid], row["answers"][qid]
    if qtype == "choice":
        return a["choice"] == g
    if qtype == "noul":
        return (a["noul"] >= 0.5) == bool(g)
    p = a["probabilities"]
    return int(max(p, key=p.get)) == int(g)


if __name__ == "__main__":
    main()
