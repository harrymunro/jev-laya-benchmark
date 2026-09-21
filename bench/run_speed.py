"""Controlled latency / throughput benchmark for Jev (API) and Laya (local MLX).

Workloads
  single   one 6-option Choice on a ~45-token support message, sequential, N iterations
  multiq   same state, {1,3,5,10,25,50} distinct questions per request
  statelen one Choice, state of {50..6400} Laya-tokenizer tokens
  tput     64 distinct states x 1 question (Jev: concurrency sweep; Laya: sequential),
           and 1 state x 64 questions in one request
All timings are wall-clock around the call only (SDK/HTTP for Jev, synchronized MLX for Laya).
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.backends import LAYA_CHECKPOINTS, make_backend  # noqa: E402
from bench.tasks import TASKS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "speed.json"

SHORT_STATE = {
    "message": "Hi, I was charged twice for my March subscription and I need the duplicate refunded before our finance close on Friday. Order #A8841."
}

Q_INTENT = {"intent": TASKS["triage"]["questions"]["intent"]}

# A pool of 50 distinct, sensible questions about a support message.
NOULS = [
    "Does the customer mention an order or ticket number?", "Does the customer ask for a phone call?",
    "Does the customer mention a specific deadline or date?", "Is the customer asking about a duplicate charge?",
    "Does the customer threaten to leave or cancel?", "Does the customer thank the support team?",
    "Is the message written in English?", "Does the customer mention a previous contact with support?",
    "Does the customer describe an error message?", "Does the customer mention a mobile app?",
    "Does the customer ask a question?", "Does the message contain profanity?",
    "Does the customer mention their company or employer?", "Is the customer asking for a discount?",
    "Does the customer mention a payment method such as a card or bank account?", "Does the customer mention money or an amount?",
    "Does the customer ask for an explanation of a charge?", "Does the customer apologise?",
    "Does the customer say they are a long-time user?", "Does the customer mention a subscription or plan?",
    "Does the customer report data loss?", "Does the customer ask for a manager or escalation?",
    "Does the customer mention a legal or regulatory issue?", "Is the customer reporting a security concern?",
    "Does the customer mention a physical product or shipment?", "Does the customer request written confirmation?",
    "Does the customer mention a website or web browser?", "Is the customer asking how to do something?",
    "Does the customer mention a specific month?", "Does the message end with a sign-off or name?",
    "Does the customer mention being charged more than once?", "Does the customer mention a refund?",
    "Does the customer use exclamation marks?", "Does the customer express confusion?",
    "Does the customer mention a colleague or team?",
]
CHOICES = [
    ("channel", "Which channel does the customer most likely prefer for the reply?", {"email": None, "phone": None, "chat": None, "no_preference": None}),
    ("tone", "What is the customer's tone?", {"polite": None, "neutral": None, "annoyed": None, "angry": None}),
    ("product_area", "Which product area is the message about?", {"billing": None, "account": None, "app": None, "shipping": None, "unclear": None}),
    ("customer_type", "What kind of customer is writing?", {"individual": None, "business": None, "unclear": None}),
    ("resolution", "What resolution would satisfy the customer?", {"refund": None, "fix": None, "information": None, "apology": None, "other": None}),
    ("language", "What language is the message written in?", {"english": None, "spanish": None, "french": None, "german": None, "other": None}),
    ("time_ref", "What time reference does the customer give?", {"none": None, "specific_date": None, "relative_day": None, "immediate": None}),
    ("next_step", "What should the agent do first?", {"check_billing": None, "ask_details": None, "escalate": None, "send_docs": None}),
    ("sentiment", "What is the overall sentiment?", {"positive": None, "neutral": None, "negative": None}),
    ("length", "How detailed is the message?", {"minimal": None, "adequate": None, "very_detailed": None}),
]
SCORES = [
    ("urgency", "How urgent is the request?", ["not urgent", "soon", "today", "immediately"]),
    ("frustration", "How frustrated is the customer?", ["calm", "concerned", "annoyed", "angry"]),
    ("clarity", "How clear is the request?", ["unclear", "somewhat clear", "very clear"]),
    ("complexity", "How complex is resolving this likely to be?", ["trivial", "simple", "moderate", "complex"]),
    ("churn_risk", "How likely is the customer to leave?", ["unlikely", "possible", "likely", "certain"]),
]


def question_pool():
    pool = {}
    pool["intent"] = Q_INTENT["intent"]
    for i, ins in enumerate(NOULS):
        pool[f"n{i}"] = {"type": "noul", "instructions": ins}
    for qid, ins, crit in CHOICES:
        pool[f"c_{qid}"] = {"type": "choice", "instructions": ins, "criteria": crit}
    for qid, ins, crit in SCORES:
        pool[f"s_{qid}"] = {"type": "score", "instructions": ins, "criteria": crit}
    return pool


POOL = question_pool()
POOL_IDS = list(POOL)


def questions_n(n):
    # interleave types so every size has a mix
    ids = ["intent"] + [i for i in POOL_IDS if i != "intent"]
    return {i: POOL[i] for i in ids[:n]}


SENTENCES = [
    "The customer first contacted us on the third of the month about a charge they did not recognise on their statement.",
    "Our records show two invoices were issued for the same billing period because the plan change was processed twice.",
    "The agent explained that the duplicate would be reversed within five to seven working days depending on the bank.",
    "The customer replied that they had already spoken to their bank and were told the merchant must initiate the refund.",
    "A follow-up note records that the finance team approved the reversal and queued it for the next payment run.",
    "The customer also asked whether the annual plan could be moved to monthly billing without losing the discount.",
    "The agent confirmed that the discount applies only to annual billing and offered a prorated credit instead.",
    "The customer said they would think about it and asked for the conversation to be sent to them by email.",
    "The transcript was exported and attached to the ticket, along with screenshots of both invoices.",
    "The customer wrote again the following week to say the credit had not yet appeared on the account.",
    "The agent checked the payment run and found the credit was held because the card on file had expired.",
    "The customer updated the card and the credit was released the same afternoon, which they confirmed by email.",
    "A separate note mentions the customer's account is linked to a business workspace with four other seats.",
    "The workspace owner later asked for a consolidated invoice covering all seats for the quarter.",
    "The billing team produced the consolidated invoice and sent it to the address on the account.",
    "The ticket was marked resolved after the customer replied with thanks and no further questions.",
]


def long_state(target_tokens, count_tokens):
    parts, i = [], 0
    text = ""
    while True:
        parts.append(SENTENCES[i % len(SENTENCES)].replace("the customer", f"the customer (case {i // len(SENTENCES) + 1})", 1) if i >= len(SENTENCES) else SENTENCES[i])
        i += 1
        text = " ".join(parts)
        n = count_tokens({"transcript": text})
        if n >= target_tokens:
            break
    return {"transcript": text}


def pct(xs, p):
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def summarize(samples):
    return {
        "n": len(samples),
        "p50_ms": statistics.median(samples),
        "p90_ms": pct(samples, 90),
        "p95_ms": pct(samples, 95),
        "p99_ms": pct(samples, 99),
        "mean_ms": statistics.fmean(samples),
        "min_ms": min(samples),
        "max_ms": max(samples),
        "samples_ms": samples,
    }


def measure(backend, state, questions, iterations, warmup):
    for _ in range(warmup):
        backend.predict(state, questions)
    samples, tokens = [], None
    for _ in range(iterations):
        r = backend.predict(state, questions)
        samples.append(r["elapsed_ms"])
        tokens = r["input_tokens"]
    s = summarize(samples)
    s["input_tokens"] = tokens
    s["questions"] = len(questions)
    return s


def run_tput(backend, name, states, workers_list, repeats):
    """64 distinct states x 1 question; Jev with a concurrency sweep."""
    out = []
    jobs = [(s, Q_INTENT) for s in states]
    for w in workers_list:
        runs = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            res = backend.predict_many(jobs, workers=w) if name == "jev" else backend.predict_many(jobs)
            wall = time.perf_counter() - t0
            runs.append({"wall_s": wall, "items_per_s": len(jobs) / wall, "per_call_p50_ms": statistics.median(r["elapsed_ms"] for r in res)})
        out.append({"workers": w, "runs": runs, "items_per_s_best": max(r["items_per_s"] for r in runs), "items_per_s_mean": statistics.fmean(r["items_per_s"] for r in runs)})
        print(f"  [{name}] tput 64 states, workers={w}: {out[-1]['items_per_s_mean']:.1f} items/s (per-call p50 {runs[-1]['per_call_p50_ms']:.0f} ms)", flush=True)
        if name != "jev":
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backends", nargs="+", default=["jev", "laya", "laya-multilingual", "laya-typed-decisions"])
    ap.add_argument("--workloads", nargs="+", default=["single", "multiq", "statelen", "tput"])
    ap.add_argument("--iterations", type=int, default=100)
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    results = json.loads(args.out.read_text()) if args.out.exists() else {}
    # token counter from the Laya tokenizer (the binding constraint); load once
    counter_backend = make_backend("laya")
    count_tokens = counter_backend.count_state_tokens

    for name in args.backends:
        backend = counter_backend if name == "laya" else make_backend(name)
        res = results.setdefault(name, {})
        res["model"] = backend.model
        if hasattr(backend, "load_seconds"):
            res["load_seconds"] = backend.load_seconds
        print(f"=== {name} ({backend.model}) ===", flush=True)

        if "single" in args.workloads:
            s = measure(backend, SHORT_STATE, Q_INTENT, args.iterations, args.warmup)
            res["single"] = s
            print(f"  single: p50={s['p50_ms']:.1f} p95={s['p95_ms']:.1f} p99={s['p99_ms']:.1f} ms  tokens={s['input_tokens']}", flush=True)

        if "multiq" in args.workloads and name in ("jev", "laya"):
            res["multiq"] = []
            for n in (1, 3, 5, 10, 25, 50):
                s = measure(backend, SHORT_STATE, questions_n(n), 30, 3)
                s["per_question_ms"] = s["p50_ms"] / n
                res["multiq"].append(s)
                print(f"  multiq n={n}: p50={s['p50_ms']:.1f} ms ({s['per_question_ms']:.1f} ms/q) tokens={s['input_tokens']}", flush=True)

        if "statelen" in args.workloads and name in ("jev", "laya"):
            res["statelen"] = []
            for target in (50, 100, 200, 400, 800, 1600, 3200, 6400):
                st = long_state(target, count_tokens)
                s = measure(backend, st, Q_INTENT, 20, 3)
                s["target_tokens"] = target
                s["laya_state_tokens"] = count_tokens(st)
                if hasattr(backend, "state_truncated"):
                    s["truncated"] = backend.state_truncated(st, Q_INTENT)
                res["statelen"].append(s)
                print(f"  statelen {target}: p50={s['p50_ms']:.1f} ms tokens={s['input_tokens']} trunc={s.get('truncated')}", flush=True)

        if "tput" in args.workloads and name in ("jev", "laya"):
            states = [{"message": f"{SHORT_STATE['message']} Reference {1000 + i}."} for i in range(64)]
            res["tput_64states"] = run_tput(backend, name, states, [1, 4, 8, 16, 32], repeats=2)
            s = measure(backend, SHORT_STATE, questions_n(50), 10, 2)
            s["questions_per_s"] = 50 / (s["p50_ms"] / 1000)
            res["tput_1state_50q"] = s
            print(f"  tput 1 state x 50 q: p50={s['p50_ms']:.1f} ms -> {s['questions_per_s']:.0f} q/s", flush=True)
            if name == "laya":
                big = make_backend("laya", batch_size=64)
                s = measure(big, SHORT_STATE, questions_n(50), 10, 2)
                s["questions_per_s"] = 50 / (s["p50_ms"] / 1000)
                res["tput_1state_50q_batch64"] = s
                print(f"  tput 1 state x 50 q (batch_size=64): p50={s['p50_ms']:.1f} ms -> {s['questions_per_s']:.0f} q/s", flush=True)
                opt = make_backend("laya", compile=True, cache_prompts=True, pad_to_multiple=16)
                s = measure(opt, SHORT_STATE, Q_INTENT, args.iterations, args.warmup)
                res["single_optimized"] = s
                print(f"  single (compile+cache+pad16): p50={s['p50_ms']:.1f} p95={s['p95_ms']:.1f} ms", flush=True)

        args.out.parent.mkdir(exist_ok=True)
        args.out.write_text(json.dumps(results, indent=1))
        if name != "laya":
            backend.close()


if __name__ == "__main__":
    main()
