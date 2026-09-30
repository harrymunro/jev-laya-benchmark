"""Latency / throughput sweeps for hosted System One backends (Jev vs Kev on OpenRouter), no Laya needed.

Same workloads and question pool as run_speed.py. Backends alternate call by call within each
measurement, so both see the same network conditions.

Workloads
  single   one 6-option Choice on a ~45-token support message
  multiq   same state, {1,5,10,25,50} questions per request
  statelen one Choice, state of ~{100..6400} tokens (chars/4 estimate; each backend's own count is recorded)
  tput     64 distinct states x 1 question, concurrency sweep
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.backends import make_backend  # noqa: E402
from bench.run_speed import Q_INTENT, SHORT_STATE, long_state, questions_n, summarize  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "jev-vs-kev" / "speed.json"


def approx_tokens(state):
    return len(json.dumps(state, ensure_ascii=False)) // 4


def measure_interleaved(backends, state, questions, iterations, warmup):
    """Alternate backends call by call; returns {name: summary}."""
    for _ in range(warmup):
        for b in backends.values():
            b.predict(state, questions)
    samples = {n: [] for n in backends}
    last = {}
    for _ in range(iterations):
        for n, b in backends.items():
            r = b.predict(state, questions)
            samples[n].append(r["elapsed_ms"])
            last[n] = r
    out = {}
    for n in backends:
        s = summarize(samples[n])
        s.update(questions=len(questions), input_tokens=last[n]["input_tokens"], output_tokens=last[n].get("output_tokens"), cost_usd=last[n].get("cost_usd"))
        out[n] = s
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backends", nargs="+", default=["jev-openrouter", "kev"])
    ap.add_argument("--workloads", nargs="+", default=["single", "multiq", "statelen", "tput"])
    ap.add_argument("--iterations", type=int, default=50)
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    backends = {n: make_backend(n) for n in args.backends}
    results = {n: {"model": b.model} for n, b in backends.items()}

    def save():
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=1))

    def line(tag, res):
        print(f"  {tag}: " + "  ".join(f"{n} p50={s['p50_ms']:.0f} p95={s['p95_ms']:.0f} ms" for n, s in res.items()), flush=True)

    if "single" in args.workloads:
        res = measure_interleaved(backends, SHORT_STATE, Q_INTENT, args.iterations, args.warmup)
        for n, s in res.items():
            results[n]["single"] = s
        line("single", res)
        save()

    if "multiq" in args.workloads:
        for n in backends:
            results[n]["multiq"] = []
        for k in (1, 5, 10, 25, 50):
            res = measure_interleaved(backends, SHORT_STATE, questions_n(k), 10, 1)
            for n, s in res.items():
                s["per_question_ms"] = s["p50_ms"] / k
                results[n]["multiq"].append(s)
            line(f"multiq n={k}", res)
        save()

    if "statelen" in args.workloads:
        for n in backends:
            results[n]["statelen"] = []
        for target in (100, 400, 1600, 6400):
            st = long_state(target, approx_tokens)
            res = measure_interleaved(backends, st, Q_INTENT, 10, 1)
            for n, s in res.items():
                s["target_tokens"] = target
                s["approx_state_tokens"] = approx_tokens(st)
                results[n]["statelen"].append(s)
            line(f"statelen ~{target}", res)
        save()

    if "tput" in args.workloads:
        jobs = [({"message": f"{SHORT_STATE['message']} Reference {1000 + i}."}, Q_INTENT) for i in range(64)]
        for n in backends:
            results[n]["tput_64states"] = []
        for w in (1, 8, 32):
            for n, b in backends.items():
                t0 = time.perf_counter()
                res = b.predict_many(jobs, workers=w)
                wall = time.perf_counter() - t0
                row = {"workers": w, "wall_s": wall, "items_per_s": len(jobs) / wall, "per_call_p50_ms": statistics.median(r["elapsed_ms"] for r in res)}
                results[n]["tput_64states"].append(row)
                print(f"  tput workers={w} {n}: {row['items_per_s']:.1f} items/s (per-call p50 {row['per_call_p50_ms']:.0f} ms)", flush=True)
        save()

    for b in backends.values():
        b.close()


if __name__ == "__main__":
    main()
