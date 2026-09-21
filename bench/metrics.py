"""Accuracy / calibration metrics with bootstrap confidence intervals."""

import math
import random
from collections import Counter, defaultdict


def bootstrap_ci(values, stat=None, n=2000, seed=0):
    """95% CI of the mean of `values` (or of stat(sample))."""
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    stat = stat or (lambda xs: sum(xs) / len(xs))
    m = len(values)
    boots = []
    for _ in range(n):
        sample = [values[rng.randrange(m)] for _ in range(m)]
        boots.append(stat(sample))
    boots.sort()
    return (boots[int(0.025 * n)], boots[int(0.975 * n) - 1])


def macro_f1(golds, preds, labels):
    f1s = []
    for lab in labels:
        tp = sum(1 for g, p in zip(golds, preds) if g == lab and p == lab)
        fp = sum(1 for g, p in zip(golds, preds) if g != lab and p == lab)
        fn = sum(1 for g, p in zip(golds, preds) if g == lab and p != lab)
        if tp + fp + fn == 0:
            continue
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / len(f1s) if f1s else float("nan")


def auroc(golds, scores):
    pos = [s for g, s in zip(golds, scores) if g]
    neg = [s for g, s in zip(golds, scores) if not g]
    if not pos or not neg:
        return float("nan")
    # rank-based (handles ties as 0.5)
    wins = 0.0
    for p in pos:
        for q in neg:
            wins += 1.0 if p > q else 0.5 if p == q else 0.0
    return wins / (len(pos) * len(neg))


def ece(golds, probs, bins=10):
    total, n = 0.0, len(golds)
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(probs) if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if not idx:
            continue
        conf = sum(probs[i] for i in idx) / len(idx)
        acc = sum(1 for i in idx if golds[i]) / len(idx)
        total += len(idx) / n * abs(acc - conf)
    return total


def logloss(p):
    return -math.log(max(min(p, 1 - 1e-6), 1e-6))


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def score_choice(rows):
    """rows: list of (gold_label, answer_dict)."""
    golds = [g for g, _ in rows]
    preds = [a["choice"] for _, a in rows]
    labels = sorted(set(golds) | set(preds))
    correct = [1.0 if g == p else 0.0 for g, p in zip(golds, preds)]
    p_gold = [a["probabilities"].get(g, 0.0) for g, a in rows]
    conf = [a.get("confidence", 0.0) for _, a in rows]
    cm = defaultdict(Counter)
    for g, p in zip(golds, preds):
        cm[g][p] += 1
    return {
        "n": len(rows),
        "accuracy": sum(correct) / len(rows),
        "accuracy_ci": bootstrap_ci(correct),
        "macro_f1": macro_f1(golds, preds, labels),
        "logloss": sum(logloss(p) for p in p_gold) / len(rows),
        "mean_p_gold": sum(p_gold) / len(rows),
        "mean_confidence": sum(conf) / len(rows),
        "accuracy_when_confident": _acc_when(correct, conf, 0.8),
        "coverage_when_confident": sum(1 for c in conf if c >= 0.8) / len(rows),
        "confusion": {g: dict(c) for g, c in cm.items()},
        "correct": correct,
    }


def _acc_when(correct, conf, thr):
    idx = [i for i, c in enumerate(conf) if c >= thr]
    return sum(correct[i] for i in idx) / len(idx) if idx else float("nan")


def score_noul(rows):
    golds = [bool(g) for g, _ in rows]
    probs = [a["noul"] for _, a in rows]
    preds = [p >= 0.5 for p in probs]
    correct = [1.0 if g == p else 0.0 for g, p in zip(golds, preds)]
    return {
        "n": len(rows),
        "accuracy": sum(correct) / len(rows),
        "accuracy_ci": bootstrap_ci(correct),
        "auroc": auroc(golds, probs),
        "brier": sum((p - float(g)) ** 2 for g, p in zip(golds, probs)) / len(rows),
        "ece": ece(golds, probs),
        "logloss": sum(logloss(p if g else 1 - p) for g, p in zip(golds, probs)) / len(rows),
        "macro_f1": macro_f1(golds, preds, [True, False]),
        "pos_rate_gold": sum(golds) / len(rows),
        "pos_rate_pred": sum(preds) / len(rows),
        "correct": correct,
    }


def score_score(rows):
    golds = [int(g) for g, _ in rows]
    probs = [a["probabilities"] for _, a in rows]
    argmax = [int(max(p, key=lambda k: p[k])) for p in probs]
    expected = [a["score"] for _, a in rows]
    exact = [1.0 if g == p else 0.0 for g, p in zip(golds, argmax)]
    within1 = [1.0 if abs(g - p) <= 1 else 0.0 for g, p in zip(golds, argmax)]
    conf = [a.get("confidence", 0.0) for _, a in rows]
    return {
        "n": len(rows),
        "accuracy": sum(exact) / len(rows),
        "accuracy_ci": bootstrap_ci(exact),
        "within_1": sum(within1) / len(rows),
        "mae_expected": sum(abs(g - e) for g, e in zip(golds, expected)) / len(rows),
        "mae_argmax": sum(abs(g - p) for g, p in zip(golds, argmax)) / len(rows),
        "spearman": spearman(golds, expected),
        "logloss": sum(logloss(p.get(str(g), 0.0)) for g, p in zip(golds, probs)) / len(rows),
        "mean_confidence": sum(conf) / len(rows),
        "correct": exact,
    }


SCORERS = {"choice": score_choice, "noul": score_noul, "score": score_score}


def paired_diff_ci(correct_a, correct_b, n=2000, seed=0):
    """Bootstrap CI on accuracy(A) - accuracy(B) over the same items."""
    diffs = [a - b for a, b in zip(correct_a, correct_b)]
    mean = sum(diffs) / len(diffs)
    return mean, bootstrap_ci(diffs, n=n, seed=seed)
