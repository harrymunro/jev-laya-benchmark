"""Print disagreements between Jev and Laya for qualitative review."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.tasks import TASKS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "results" / "predictions"
DATA = ROOT / "bench" / "data"


def main(task, qid, limit=8):
    items = {json.loads(l)["id"]: json.loads(l) for l in (DATA / f"{task}.jsonl").read_text().splitlines() if l.strip()}
    j = {r["id"]: r for r in map(json.loads, (PRED / "jev" / f"{task}.jsonl").read_text().splitlines())}
    l = {r["id"]: r for r in map(json.loads, (PRED / "laya" / f"{task}.jsonl").read_text().splitlines())}
    qtype = TASKS[task]["gold"][qid][1]
    field = TASKS[task]["state_fields"][0]

    def pred(a):
        if qtype == "choice":
            return a["choice"]
        if qtype == "noul":
            return a["noul"] >= 0.5
        return int(max(a["probabilities"], key=a["probabilities"].get))

    def show(a):
        if qtype == "choice":
            top = sorted(a["probabilities"].items(), key=lambda kv: -kv[1])[:3]
            return ", ".join(f"{k}={v:.2f}" for k, v in top)
        if qtype == "noul":
            return f"p={a['noul']:.2f}"
        return f"E={a['score']:.2f} " + " ".join(f"{k}:{v:.2f}" for k, v in a["probabilities"].items())

    buckets = {"jev right, laya wrong": [], "laya right, jev wrong": [], "both wrong": []}
    for id_, jr in j.items():
        lr = l.get(id_)
        if not lr:
            continue
        gold = jr["gold"][qid]
        if qtype == "noul":
            gold = bool(gold)
        jp, lp = pred(jr["answers"][qid]), pred(lr["answers"][qid])
        if jp == gold and lp != gold:
            buckets["jev right, laya wrong"].append((id_, gold, jr, lr))
        elif lp == gold and jp != gold:
            buckets["laya right, jev wrong"].append((id_, gold, jr, lr))
        elif jp != gold and lp != gold:
            buckets["both wrong"].append((id_, gold, jr, lr))
    print(f"### {task}/{qid}: " + ", ".join(f"{k}: {len(v)}" for k, v in buckets.items()))
    for k, rows in buckets.items():
        print(f"\n--- {k} ({len(rows)}) ---")
        for id_, gold, jr, lr in rows[:limit]:
            text = items[id_][field] if field in items[id_] else json.dumps({f: items[id_][f] for f in TASKS[task]["state_fields"]})[:300]
            print(f"[{id_}] gold={gold}\n   jev:  {show(jr['answers'][qid])}\n   laya: {show(lr['answers'][qid])}\n   text: {text[:260].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
