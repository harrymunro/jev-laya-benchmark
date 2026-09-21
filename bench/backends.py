"""Uniform backend interface for Jev (TypeSafe API) and Laya (local MLX).

predict(state, questions) -> dict with keys:
    answers: {qid: {"type", "choice"/"score"/"noul", "probabilities", "confidence"}}
    elapsed_ms: wall-clock for the call, measured around the call only
    input_tokens: as reported by the backend
    model: model id string reported by the backend
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor


def _norm_answer(qid, qdef, raw):
    """Normalise both backends to the same answer dict."""
    t = qdef["type"]
    out = {"type": t}
    if t == "choice":
        out["choice"] = raw["choice"]
        out["probabilities"] = {k: float(v) for k, v in raw["probabilities"].items()}
        out["confidence"] = float(raw.get("confidence", 0.0))
    elif t == "score":
        out["score"] = float(raw["score"])
        out["probabilities"] = {str(k): float(v) for k, v in raw["probabilities"].items()}
        out["confidence"] = float(raw.get("confidence", 0.0))
    else:
        out["noul"] = float(raw["noul"])
    return out


class JevBackend:
    name = "jev"

    def __init__(self, model="jev-latest", timeout=120.0, max_retries=8):
        from typesafe_sdk import Choice, Noul, RetryPolicy, Score, TypeSafeClient

        self._Choice, self._Noul, self._Score = Choice, Noul, Score
        self.model = model
        self.client = TypeSafeClient(
            model=model, timeout=timeout, retry=RetryPolicy(max_retries=max_retries)
        )
        self.reported_model = None
        self.retries_seen = 0

    def _to_sdk(self, questions):
        out = {}
        for qid, q in questions.items():
            if q["type"] == "choice":
                out[qid] = self._Choice(instructions=q["instructions"], criteria=q["criteria"])
            elif q["type"] == "score":
                out[qid] = self._Score(instructions=q["instructions"], criteria=q["criteria"])
            else:
                kw = {"instructions": q["instructions"]}
                if q.get("criteria"):
                    kw["criteria"] = q["criteria"]
                out[qid] = self._Noul(**kw)
        return out

    def predict(self, state, questions):
        sdk_q = self._to_sdk(questions)
        t0 = time.perf_counter()
        resp = self.client.system_one(state=state, questions=sdk_q)
        elapsed = (time.perf_counter() - t0) * 1000
        self.reported_model = resp.model
        answers = {}
        for qid, q in questions.items():
            if q["type"] == "choice":
                a = resp.choices[qid]
                raw = {"choice": a.choice, "probabilities": dict(a.probabilities), "confidence": a.confidence}
            elif q["type"] == "score":
                a = resp.scores[qid]
                raw = {"score": a.score, "probabilities": dict(a.probabilities), "confidence": a.confidence}
            else:
                raw = {"noul": resp.nouls[qid].noul}
            answers[qid] = _norm_answer(qid, q, raw)
        return {
            "answers": answers,
            "elapsed_ms": elapsed,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "model": resp.model,
            "request_id": getattr(resp, "request_id", None),
        }

    def predict_many(self, jobs, workers=6):
        """jobs: list of (state, questions). Returns results in order. Parallel over HTTP."""
        with ThreadPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(lambda j: self.predict(*j), jobs))

    def close(self):
        self.client.close()


class LayaBackend:
    def __init__(self, repo="aac6fef/laya-mlx", name="laya", dtype="float16", batch_size=16, **kw):
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        import mlx.core as mx
        import laya_mlx as laya

        self.mx = mx
        self.name = name
        self.repo = repo
        t0 = time.perf_counter()
        self.agent = laya.load(repo, dtype=dtype, batch_size=batch_size, **kw)
        self.load_seconds = time.perf_counter() - t0
        self.model = repo
        self.max_len = self.agent.cfg.get("max_len", 512)
        self.head_max_len = self.agent.cfg.get("head_max_len", 192)

    def count_state_tokens(self, state):
        from laya_mlx.common import serialize_state

        return len(self.agent.tok(serialize_state(state))["input_ids"])

    def state_truncated(self, state, questions):
        """True if any question's sequence hit max_len (state was cut)."""
        items, _ = self.agent.prepare(state, questions)
        return any(len(it["ids"]) >= self.max_len for it in items)

    def predict(self, state, questions):
        mx = self.mx
        mx.synchronize()
        t0 = time.perf_counter()
        r = self.agent.predict(state, questions)
        mx.synchronize()
        elapsed = (time.perf_counter() - t0) * 1000
        answers = {qid: _norm_answer(qid, q, r["answers"][qid]) for qid, q in questions.items()}
        return {
            "answers": answers,
            "elapsed_ms": elapsed,
            "input_tokens": r["usage"]["input_tokens"],
            "output_tokens": 0,
            "model": self.repo,
            "truncated": self.state_truncated(state, questions),
        }

    def predict_many(self, jobs, workers=None):
        return [self.predict(*j) for j in jobs]

    def close(self):
        pass


LAYA_CHECKPOINTS = {
    "laya": "aac6fef/laya-mlx",
    "laya-multilingual": "aac6fef/laya-multilingual-mlx",
    "laya-typed-decisions": "aac6fef/laya-typed-decisions-mlx",
}


def make_backend(name, **kw):
    if name == "jev":
        return JevBackend(**kw)
    if name in LAYA_CHECKPOINTS:
        return LayaBackend(repo=LAYA_CHECKPOINTS[name], name=name, **kw)
    raise ValueError(name)
