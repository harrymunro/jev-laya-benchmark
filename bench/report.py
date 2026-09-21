"""Build charts (PNG) and markdown tables from results/."""

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.metrics import SCORERS, paired_diff_ci  # noqa: E402
from bench.tasks import TASKS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
PRED = RES / "predictions"
CH = RES / "charts"
CH.mkdir(parents=True, exist_ok=True)

# dataviz reference palette (light mode)
COLORS = {"jev": "#2a78d6", "laya": "#eb6834", "laya-multilingual": "#1baf7a", "laya-typed-decisions": "#eda100"}
LABELS = {"jev": "Jev 1.13 (API)", "laya": "Laya 421M (local)", "laya-multilingual": "Laya multilingual 322M (local)", "laya-typed-decisions": "Laya typed-decisions 421M (local)"}
SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
BACKENDS = ["jev", "laya", "laya-multilingual", "laya-typed-decisions"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID, "axes.labelcolor": TEXT2,
    "xtick.color": TEXT2, "ytick.color": TEXT2, "text.color": TEXT, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
    "axes.titleweight": "semibold", "axes.titlesize": 11, "legend.frameon": False, "figure.dpi": 150,
})


def load_preds(backend, task):
    p = PRED / backend / f"{task}.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def fmt_ci(ci):
    return f"[{ci[0]:.2f}, {ci[1]:.2f}]"


# ---------------------------------------------------------------------------
# Speed
# ---------------------------------------------------------------------------

def speed_tables_and_charts(speed):
    md = []
    rows = []
    EXTRA = {"jev-run2": ("jev", "single_run2", "Jev 1.13 (API), later run, degraded network"), "laya-optimized": ("laya", "single_optimized", "Laya 421M, compile+cache+pad16")}
    for b in ["jev", "jev-run2", "laya", "laya-multilingual", "laya-typed-decisions", "laya-optimized"]:
        key, field, lab = EXTRA.get(b, (b, "single", LABELS.get(b)))
        s = speed.get(key, {}).get(field)
        if s:
            rows.append((b, lab, s))
    md.append("| Backend | p50 ms | p90 ms | p95 ms | p99 ms | mean ms | min ms | network floor ms | input tokens |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for b, lab, s in rows:
        floor = f"{s['network_floor_ms']:.0f}" if s.get("network_floor_ms") else "0 (local)"
        md.append(f"| {lab} | {s['p50_ms']:.1f} | {s['p90_ms']:.1f} | {s['p95_ms']:.1f} | {s['p99_ms']:.1f} | {s['mean_ms']:.1f} | {s['min_ms']:.1f} | {floor} | {s['input_tokens']} |")
    single_md = "\n".join(md)

    # chart: single-question latency
    fig, ax = plt.subplots(figsize=(9.5, 2.2 + 0.45 * len(rows)))
    names = [lab for _, lab, _ in rows]
    p50 = [s["p50_ms"] for _, _, s in rows]
    p95 = [s["p95_ms"] for _, _, s in rows]
    cols = [COLORS.get({"laya-optimized": "laya", "jev-run2": "jev"}.get(b, b)) for b, _, _ in rows]
    y = range(len(rows))
    ax.barh(y, p50, color=cols, height=0.55)
    floors = [s.get("network_floor_ms") or 0 for _, _, s in rows]
    ax.barh(y, floors, color="none", edgecolor=TEXT2, hatch="////", height=0.55, lw=0)
    for i, (v, v95, fl) in enumerate(zip(p50, p95, floors)):
        extra = f", floor {fl:.0f}" if fl else ""
        ax.text(v + max(p95) * 0.015, i, f"p50 {v:.0f} ms  (p95 {v95:.0f}{extra})", va="center", color=TEXT, fontsize=9)
    ax.set_yticks(list(y), names)
    ax.invert_yaxis()
    ax.set_xlim(0, max(p95) * 1.75)
    ax.set_xlabel("p50 latency (ms), one 6-option Choice on a 45-token message. Hatched: measured network round trip.")
    ax.set_title("Single-question end-to-end latency")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(CH / "latency_single.png")
    plt.close(fig)

    # multiq
    md = ["| Questions per request | Jev p50 ms | Jev ms/question | Jev tokens | Laya p50 ms | Laya ms/question | Laya tokens |", "|---:|---:|---:|---:|---:|---:|---:|"]
    jm = {r["questions"]: r for r in speed.get("jev", {}).get("multiq", [])}
    lm = {r["questions"]: r for r in speed.get("laya", {}).get("multiq", [])}
    for n in sorted(set(jm) | set(lm)):
        j, l = jm.get(n), lm.get(n)
        md.append(f"| {n} | {j['p50_ms']:.1f} | {j['per_question_ms']:.1f} | {j['input_tokens']} | {l['p50_ms']:.1f} | {l['per_question_ms']:.1f} | {l['input_tokens']} |" if j and l else f"| {n} | | | | | | |")
    multiq_md = "\n".join(md)
    if jm and lm:
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.3))
        for b, m in (("jev", jm), ("laya", lm)):
            xs = sorted(m)
            axes[0].plot(xs, [m[x]["p50_ms"] for x in xs], marker="o", ms=4, lw=2, color=COLORS[b], label=LABELS[b])
            axes[1].plot(xs, [m[x]["per_question_ms"] for x in xs], marker="o", ms=4, lw=2, color=COLORS[b], label=LABELS[b])
        axes[0].set_xlabel("questions in one request"); axes[0].set_ylabel("p50 latency (ms)"); axes[0].set_title("Request latency vs question count"); axes[0].set_ylim(bottom=0)
        axes[1].set_xlabel("questions in one request"); axes[1].set_ylabel("p50 ms per question"); axes[1].set_title("Effective cost per question"); axes[1].set_yscale("log"); axes[1].set_xscale("log")
        axes[0].legend(loc="upper left")
        fig.tight_layout(); fig.savefig(CH / "latency_multiq.png"); plt.close(fig)

    # statelen
    md = ["| State tokens (Laya tokenizer) | Jev p50 ms | Jev tokens billed | Laya p50 ms | Laya truncated? |", "|---:|---:|---:|---:|:---|"]
    js = {r["target_tokens"]: r for r in speed.get("jev", {}).get("statelen", [])}
    ls = {r["target_tokens"]: r for r in speed.get("laya", {}).get("statelen", [])}
    for t in sorted(set(js) | set(ls)):
        j, l = js.get(t), ls.get(t)
        if j and l:
            md.append(f"| {l['laya_state_tokens']} | {j['p50_ms']:.1f} | {j['input_tokens']} | {l['p50_ms']:.1f} | {'yes' if l.get('truncated') else 'no'} |")
    statelen_md = "\n".join(md)
    if js and ls:
        fig, ax = plt.subplots(figsize=(7, 3.3))
        for b, m in (("jev", js), ("laya", ls)):
            xs = sorted(m)
            ax.plot([m[x]["laya_state_tokens"] for x in xs], [m[x]["p50_ms"] for x in xs], marker="o", ms=4, lw=2, color=COLORS[b], label=LABELS[b])
        first_trunc = next((m["laya_state_tokens"] for t, m in sorted(ls.items()) if m.get("truncated")), None)
        if first_trunc:
            ax.axvspan(first_trunc, max(m["laya_state_tokens"] for m in ls.values()), color=COLORS["laya"], alpha=0.07, lw=0)
            ax.text(first_trunc * 1.05, ax.get_ylim()[1] * 0.92, "Laya truncates state\n(512-token window)", color=COLORS["laya"], fontsize=8, va="top")
        ax.set_xscale("log"); ax.set_xlabel("state length (tokens, Laya tokenizer, log scale)"); ax.set_ylabel("p50 latency (ms)")
        ax.set_title("Latency vs state length, one Choice question"); ax.set_ylim(bottom=0); ax.legend(loc="upper left")
        fig.tight_layout(); fig.savefig(CH / "latency_statelen.png"); plt.close(fig)

    # throughput
    md = ["| Scenario | Jev | Laya 421M |", "|---|---:|---:|"]
    jt = speed.get("jev", {}).get("tput_64states", [])
    lt = speed.get("laya", {}).get("tput_64states", [])
    for row in jt:
        lrow = lt[0] if lt else None
        md.append(f"| 64 distinct states x 1 question, Jev concurrency {row['workers']} | {row['items_per_s_mean']:.1f} items/s | {lrow['items_per_s_mean']:.1f} items/s (sequential) |" if lrow else "")
    j50 = speed.get("jev", {}).get("tput_1state_50q"); l50 = speed.get("laya", {}).get("tput_1state_50q"); l64 = speed.get("laya", {}).get("tput_1state_50q_batch64")
    if j50 and l50:
        md.append(f"| 1 state x 50 questions, one request (Laya batch_size=16) | {j50['questions_per_s']:.0f} q/s ({j50['p50_ms']:.0f} ms) | {l50['questions_per_s']:.0f} q/s ({l50['p50_ms']:.0f} ms) |")
    if j50 and l64:
        md.append(f"| 1 state x 50 questions, one request (Laya batch_size=64) | {j50['questions_per_s']:.0f} q/s ({j50['p50_ms']:.0f} ms) | {l64['questions_per_s']:.0f} q/s ({l64['p50_ms']:.0f} ms) |")
    tput_md = "\n".join(md)
    if jt and lt:
        fig, ax = plt.subplots(figsize=(7, 3.2))
        names = [f"Jev, {r['workers']} concurrent" for r in jt] + ["Laya, sequential"]
        vals = [r["items_per_s_mean"] for r in jt] + [lt[0]["items_per_s_mean"]]
        cols = [COLORS["jev"]] * len(jt) + [COLORS["laya"]]
        ax.barh(range(len(vals)), vals, color=cols, height=0.55)
        for i, v in enumerate(vals):
            ax.text(v + max(vals) * 0.01, i, f"{v:.1f}", va="center", fontsize=9)
        ax.set_yticks(range(len(vals)), names); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
        ax.set_xlabel("items per second (64 distinct states, 1 question each)"); ax.set_title("Throughput on independent items")
        fig.tight_layout(); fig.savefig(CH / "throughput.png"); plt.close(fig)

    return single_md, multiq_md, statelen_md, tput_md


# ---------------------------------------------------------------------------
# Accuracy
# ---------------------------------------------------------------------------

def score_all():
    """Return {task: {qid: {backend: metrics}}} and per-item correctness for pairing."""
    out = defaultdict(lambda: defaultdict(dict))
    for task, tdef in TASKS.items():
        for b in BACKENDS:
            preds = load_preds(b, task)
            if not preds:
                continue
            for qid, (field, qtype) in tdef["gold"].items():
                rows = [(p["gold"][qid], p["answers"][qid]) for p in preds]
                m = SCORERS[qtype](rows)
                m["qtype"] = qtype
                m["ids"] = [p["id"] for p in preds]
                out[task][qid][b] = m
    return out


def accuracy_master_table(scores):
    md = ["| Task | Question | Type | n | " + " | ".join(LABELS[b].split(" (")[0] for b in BACKENDS) + " |", "|---|---|---|---:|" + "---:|" * len(BACKENDS)]
    per_type = defaultdict(lambda: defaultdict(list))
    for task in TASKS:
        for qid, bm in scores.get(task, {}).items():
            n = next(iter(bm.values()))["n"]
            qtype = next(iter(bm.values()))["qtype"]
            cells = []
            best = max(m["accuracy"] for m in bm.values())
            for b in BACKENDS:
                m = bm.get(b)
                if not m:
                    cells.append("")
                    continue
                per_type[qtype][b].append(m["accuracy"])
                per_type["all"][b].append(m["accuracy"])
                v = f"{m['accuracy']*100:.1f}"
                cells.append(f"**{v}**" if m["accuracy"] == best else v)
            md.append(f"| {task} | {qid} | {qtype} | {n} | " + " | ".join(cells) + " |")
    md.append("| | | | | " + " | ".join("" for _ in BACKENDS) + " |")
    for t in ("choice", "noul", "score", "all"):
        cells = [f"{statistics.fmean(per_type[t][b])*100:.1f}" if per_type[t][b] else "" for b in BACKENDS]
        md.append(f"| **mean** | **{t}** | | | " + " | ".join(cells) + " |")
    return "\n".join(md), per_type


def paired_table(scores, a="jev", b="laya"):
    md = [f"| Task | Question | {a} - {b} (pp) | 95% CI | n |", "|---|---|---:|---|---:|"]
    for task in TASKS:
        for qid, bm in scores.get(task, {}).items():
            if a in bm and b in bm and bm[a]["ids"] == bm[b]["ids"]:
                d, ci = paired_diff_ci(bm[a]["correct"], bm[b]["correct"])
                md.append(f"| {task} | {qid} | {d*100:+.1f} | [{ci[0]*100:+.1f}, {ci[1]*100:+.1f}] | {bm[a]['n']} |")
    return "\n".join(md)


def detail_tables(scores):
    noul = ["| Task | Question | Backend | Acc | AUROC | Brier | ECE | log-loss | pred. positive rate (gold) |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    sc = ["| Task | Question | Backend | exact | within 1 | MAE (expected) | Spearman | log-loss | mean conf |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    ch = ["| Task | Question | Backend | Acc | macro-F1 | log-loss | mean P(gold) | mean conf | acc @conf>=0.8 (coverage) |", "|---|---|---|---:|---:|---:|---:|---:|---|"]
    for task in TASKS:
        for qid, bm in scores.get(task, {}).items():
            for b in BACKENDS:
                m = bm.get(b)
                if not m:
                    continue
                if m["qtype"] == "noul":
                    noul.append(f"| {task} | {qid} | {b} | {m['accuracy']*100:.1f} | {m['auroc']:.3f} | {m['brier']:.3f} | {m['ece']:.3f} | {m['logloss']:.2f} | {m['pos_rate_pred']:.2f} ({m['pos_rate_gold']:.2f}) |")
                elif m["qtype"] == "score":
                    sc.append(f"| {task} | {qid} | {b} | {m['accuracy']*100:.1f} | {m['within_1']*100:.1f} | {m['mae_expected']:.2f} | {m['spearman']:.3f} | {m['logloss']:.2f} | {m['mean_confidence']:.2f} |")
                else:
                    ch.append(f"| {task} | {qid} | {b} | {m['accuracy']*100:.1f} | {m['macro_f1']:.3f} | {m['logloss']:.2f} | {m['mean_p_gold']:.2f} | {m['mean_confidence']:.2f} | {m['accuracy_when_confident']*100:.1f} ({m['coverage_when_confident']*100:.0f}%) |")
    return "\n".join(ch), "\n".join(noul), "\n".join(sc)


def accuracy_chart(scores):
    rows = []
    for task in TASKS:
        for qid, bm in scores.get(task, {}).items():
            rows.append((f"{task} / {qid}", bm))
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(8.5, 1.5 + 0.42 * len(rows)))
    h = 0.8 / 2
    for i, (name, bm) in enumerate(rows):
        for k, b in enumerate(("jev", "laya")):
            m = bm.get(b)
            if not m:
                continue
            acc, ci = m["accuracy"] * 100, m["accuracy_ci"]
            y = i - h / 2 + k * h
            ax.barh(y, acc, height=h * 0.9, color=COLORS[b], label=LABELS[b] if i == 0 else None)
            ax.errorbar(acc, y, xerr=[[acc - ci[0] * 100], [ci[1] * 100 - acc]], fmt="none", ecolor=TEXT2, elinewidth=0.8, capsize=2)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows]); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 100); ax.set_xlabel("accuracy (%) with 95% bootstrap CI; score questions use exact level match")
    ax.set_title("Accuracy per question, Jev vs Laya 421M"); ax.legend(loc="lower left")
    fig.tight_layout(); fig.savefig(CH / "accuracy_by_question.png"); plt.close(fig)


def needle_analysis():
    md_len = ["| State tokens | " + " | ".join(f"{LABELS[b].split(' (')[0]} wants / damage" for b in BACKENDS) + " |", "|---:|" + "---:|" * len(BACKENDS)]
    data = {}
    for b in BACKENDS:
        preds = load_preds(b, "needle")
        if preds:
            data[b] = preds
    if not data:
        return "", ""
    lengths = sorted({p["meta"]["length_target"] for p in next(iter(data.values()))})
    series = {b: {"wants": [], "mentions_damage": []} for b in data}
    for L in lengths:
        cells = []
        for b in BACKENDS:
            if b not in data:
                cells.append("")
                continue
            sub = [p for p in data[b] if p["meta"]["length_target"] == L]
            aw = statistics.fmean(1.0 if p["answers"]["wants"]["choice"] == p["gold"]["wants"] else 0.0 for p in sub)
            ad = statistics.fmean(1.0 if (p["answers"]["mentions_damage"]["noul"] >= 0.5) == bool(p["gold"]["mentions_damage"]) else 0.0 for p in sub)
            series[b]["wants"].append(aw); series[b]["mentions_damage"].append(ad)
            cells.append(f"{aw*100:.0f} / {ad*100:.0f}")
        md_len.append(f"| {L} | " + " | ".join(cells) + " |")
    # by position, laya only (truncation) and jev
    md_pos = ["| Backend | Needle position | 100 | 250 | 500 | 1000 | 2000 | 4000 |", "|---|---|" + "---:|" * 6]
    for b in ("jev", "laya"):
        if b not in data:
            continue
        for pos in ("start", "middle", "end"):
            cells = []
            for L in lengths:
                sub = [p for p in data[b] if p["meta"]["length_target"] == L and p["meta"]["position"] == pos]
                cells.append(f"{statistics.fmean(1.0 if p['answers']['wants']['choice'] == p['gold']['wants'] else 0.0 for p in sub)*100:.0f}")
            md_pos.append(f"| {b} | {pos} | " + " | ".join(cells) + " |")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.3), sharey=True)
    for b in data:
        axes[0].plot(lengths, [v * 100 for v in series[b]["wants"]], marker="o", ms=4, lw=2, color=COLORS[b], label=LABELS[b])
        axes[1].plot(lengths, [v * 100 for v in series[b]["mentions_damage"]], marker="o", ms=4, lw=2, color=COLORS[b], label=LABELS[b])
    axes[0].set_title("'What does the customer want?' (5-way Choice)"); axes[1].set_title("'Was a damaged item mentioned?' (Noul)")
    for ax in axes:
        ax.set_xscale("log"); ax.set_xlabel("state length (tokens)"); ax.set_ylim(0, 102)
    axes[0].set_ylabel("accuracy (%)"); axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("Needle-in-notes accuracy vs state length", fontweight="semibold")
    fig.tight_layout(); fig.savefig(CH / "needle_by_length.png"); plt.close(fig)
    return "\n".join(md_len), "\n".join(md_pos)


def multilingual_table():
    data = {b: load_preds(b, "multilingual") for b in BACKENDS}
    data = {b: p for b, p in data.items() if p}
    if not data:
        return ""
    langs = sorted({p["meta"]["language"] for p in next(iter(data.values()))})
    md = ["| Language | n | " + " | ".join(f"{LABELS[b].split(' (')[0]} intent / urgent" for b in data) + " |", "|---|---:|" + "---:|" * len(data)]
    for lang in langs + ["ALL"]:
        cells, n = [], 0
        for b, preds in data.items():
            sub = [p for p in preds if lang == "ALL" or p["meta"]["language"] == lang]
            n = len(sub)
            ai = statistics.fmean(1.0 if p["answers"]["intent"]["choice"] == p["gold"]["intent"] else 0.0 for p in sub)
            au = statistics.fmean(1.0 if (p["answers"]["is_urgent"]["noul"] >= 0.5) == bool(p["gold"]["is_urgent"]) else 0.0 for p in sub)
            cells.append(f"{ai*100:.0f} / {au*100:.0f}")
        md.append(f"| {lang} | {n} | " + " | ".join(cells) + " |")
    return "\n".join(md)


def calibration_chart():
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    for b, ax in zip(("jev", "laya"), axes):
        golds, probs = [], []
        for task, tdef in TASKS.items():
            for p in load_preds(b, task):
                for qid, (field, qtype) in tdef["gold"].items():
                    if qtype == "noul":
                        golds.append(bool(p["gold"][qid])); probs.append(p["answers"][qid]["noul"])
        if not probs:
            continue
        bins = 10
        xs, ys, ns = [], [], []
        for k in range(bins):
            lo, hi = k / bins, (k + 1) / bins
            idx = [i for i, pr in enumerate(probs) if lo <= pr < hi or (k == bins - 1 and pr == 1.0)]
            if idx:
                xs.append(statistics.fmean(probs[i] for i in idx)); ys.append(statistics.fmean(golds[i] for i in idx)); ns.append(len(idx))
        ax.plot([0, 1], [0, 1], color=GRID, lw=1, ls="--")
        ax.plot(xs, ys, marker="o", ms=5, lw=2, color=COLORS[b])
        for x, y, n in zip(xs, ys, ns):
            ax.annotate(str(n), (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7, color=TEXT2)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1.08); ax.set_xlabel("predicted P(yes)"); ax.set_title(f"{LABELS[b].split(' (')[0]}, n={len(probs)}")
    axes[0].set_ylabel("observed frequency of yes")
    fig.suptitle("Reliability of Noul answers, all tasks pooled (labels = items per bin)", fontweight="semibold")
    fig.tight_layout(); fig.savefig(CH / "calibration_noul.png"); plt.close(fig)


def accuracy_run_timing():
    md = ["| Task | n | " + " | ".join(f"{LABELS[b].split(' (')[0]} s (items/s)" for b in BACKENDS) + " | Jev tokens/item | Laya tokens/item | Laya truncated |", "|---|---:|" + "---:|" * len(BACKENDS) + "---:|---:|---:|"]
    for task in TASKS:
        cells, n, jt, lt, tr = [], None, "", "", ""
        for b in BACKENDS:
            p = PRED / b / f"{task}.summary.json"
            if not p.exists():
                cells.append("")
                continue
            s = json.loads(p.read_text())
            n = s["n"]
            if b == "jev":
                cells.append(f"{s['wall_s']:.1f} ({s['items_per_s']:.1f})")
            else:
                # sequential local compute: sum of per-call times (wall clock was shared with other jobs)
                tot = sum(r["elapsed_ms"] for r in load_preds(b, task)) / 1000
                cells.append(f"{tot:.1f} ({n / tot:.1f})")
            if b == "jev":
                jt = f"{s['mean_input_tokens']:.0f}"
            if b == "laya":
                lt = f"{s['mean_input_tokens']:.0f}"; tr = f"{s['truncated_frac']*100:.0f}%"
        if n:
            md.append(f"| {task} | {n} | " + " | ".join(cells) + f" | {jt} | {lt} | {tr} |")
    return "\n".join(md)


def main():
    speed = json.loads((RES / "speed.json").read_text()) if (RES / "speed.json").exists() else {}
    single_md, multiq_md, statelen_md, tput_md = speed_tables_and_charts(speed) if speed else ("", "", "", "")
    scores = score_all()
    master_md, per_type = accuracy_master_table(scores)
    paired_md = paired_table(scores)
    ch_md, noul_md, sc_md = detail_tables(scores)
    accuracy_chart(scores)
    needle_len_md, needle_pos_md = needle_analysis()
    multi_md = multilingual_table()
    calibration_chart()
    timing_md = accuracy_run_timing()
    out = RES / "tables.md"
    out.write_text("\n\n".join([
        "## Single-question latency\n" + single_md, "## Questions per request\n" + multiq_md, "## State length\n" + statelen_md,
        "## Throughput\n" + tput_md, "## Accuracy master\n" + master_md, "## Paired Jev - Laya\n" + paired_md,
        "## Choice detail\n" + ch_md, "## Noul detail\n" + noul_md, "## Score detail\n" + sc_md,
        "## Needle by length\n" + needle_len_md, "## Needle by position\n" + needle_pos_md, "## Multilingual\n" + multi_md,
        "## Accuracy-run timing\n" + timing_md,
    ]))
    # compact JSON summary without per-item arrays
    summary = {t: {q: {b: {k: v for k, v in m.items() if k not in ("correct", "ids", "confusion")} for b, m in bm.items()} for q, bm in tq.items()} for t, tq in scores.items()}
    (RES / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(f"wrote {out} and charts to {CH}")


if __name__ == "__main__":
    main()
