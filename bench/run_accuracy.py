"""Run every backend over every task dataset; save per-item predictions and timings."""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.backends import make_backend  # noqa: E402
from bench.tasks import TASKS, state_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "bench" / "data"
PRED = ROOT / "results" / "predictions"


def load_items(task):
    path = DATA / f"{task}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backends", nargs="+", default=["jev", "laya", "laya-multilingual", "laya-typed-decisions"])
    ap.add_argument("--tasks", nargs="+", default=list(TASKS))
    ap.add_argument("--workers", type=int, default=6, help="Jev HTTP concurrency")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    for name in args.backends:
        backend = make_backend(name)
        print(f"=== {name} ({backend.model}) ===", flush=True)
        for task in args.tasks:
            items = load_items(task)
            if args.limit:
                items = items[: args.limit]
            if not items:
                print(f"  {task}: no data, skipped", flush=True)
                continue
            questions = TASKS[task]["questions"]
            jobs = [(state_for(task, it), questions) for it in items]
            t0 = time.perf_counter()
            results = backend.predict_many(jobs, workers=args.workers)
            wall = time.perf_counter() - t0
            out_dir = PRED / name
            out_dir.mkdir(parents=True, exist_ok=True)
            with (out_dir / f"{task}.jsonl").open("w") as f:
                for it, r in zip(items, results):
                    gold = {qid: it[field] for qid, (field, _) in TASKS[task]["gold"].items()}
                    row = {
                        "id": it["id"],
                        "gold": gold,
                        "answers": r["answers"],
                        "elapsed_ms": r["elapsed_ms"],
                        "input_tokens": r["input_tokens"],
                        "truncated": r.get("truncated"),
                        "meta": {k: it[k] for k in ("length_target", "position", "language", "verifier_exact") if k in it},
                    }
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            lat = [r["elapsed_ms"] for r in results]
            summary = {
                "task": task,
                "n": len(items),
                "wall_s": wall,
                "items_per_s": len(items) / wall,
                "per_call_p50_ms": statistics.median(lat),
                "per_call_p95_ms": sorted(lat)[int(0.95 * len(lat)) - 1],
                "mean_input_tokens": statistics.fmean(r["input_tokens"] for r in results),
                "truncated_frac": (sum(1 for r in results if r.get("truncated")) / len(results)) if name != "jev" else None,
                "model": results[0]["model"],
            }
            (out_dir / f"{task}.summary.json").write_text(json.dumps(summary, indent=1))
            print(f"  {task}: n={len(items)} wall={wall:.1f}s ({summary['items_per_s']:.1f} items/s) p50={summary['per_call_p50_ms']:.0f} ms tokens={summary['mean_input_tokens']:.0f} trunc={summary['truncated_frac']}", flush=True)
        backend.close()


if __name__ == "__main__":
    main()
