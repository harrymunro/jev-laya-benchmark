## 1. What was compared

| | Jev (TypeSafe) | Laya (laya-mlx port) |
|---|---|---|
| Model | `jev-1.13.0` via `jev-latest` alias, hosted API (`POST /v1/systemone`) | `aac6fef/laya-mlx` (ModernBERT-large, 421M, FP16), run locally with MLX. Also `laya-multilingual-mlx` (mmBERT-base, 322M) and `laya-typed-decisions-mlx` (421M) |
| Client | `typesafe-sdk` 0.7.1, default retry policy | `laya-mlx` 0.1.0 at commit `fc1df62`, MLX 0.32.2, default `batch_size=16` |
| Context | 64k tokens per request, 32k for state plus longest question | 512 tokens total per question row, of which up to 192 are the question prefix; state is cut from the end when it does not fit (multilingual checkpoint: 1,024) |
| Question types | Choice, Score, Noul | Choice, Score, Noul (same vocabulary and answer shapes) |
| Hardware for local runs | n/a (network: ~50 ms warm round trip to `api.typesafe.ai` from this machine) | Apple M3 Pro, 14 CPU cores, 18 GB, macOS 14.4, Python 3.12.3 |

Both backends received byte-identical `state` objects and question maps (same instructions, same criteria text, same option order). Laya's own README quotes 13.4 ms on an M3 Max with 40 GPU cores and 128 GB; this machine is an M3 Pro, so Laya's absolute latencies here are roughly 3x its published figure, and that is a hardware difference, not a port issue.

## 2. Synthetic data

All data was generated for this benchmark on 2026-09-21. No public dataset was used, so neither model has seen the items.

**Seven natural-language tasks** were generated with `gpt-5.5` via the OpenAI API, using label-conditioned prompts: every item was written *for* a target label tuple (for example, intent = billing_question, urgent = true, frustration = 2), with randomised company, register, and length hints for diversity. A second, blind `gpt-5.5` call then re-labelled each item without seeing the target. Items whose categorical labels disagreed were dropped; ordinal (Score) labels had to be within one level. The drop rate and the blind exact-agreement rate are recorded per task as a label-noise estimate.

**One programmatic task** (`needle`) was built in code with gold labels known by construction: 25 hand-written support-note sentences (each with a known customer ask and a known damaged-item flag) inserted at the start, middle, or end of neutral filler paragraphs (40 unique paragraphs, also generated, with a hard rule against mentioning customers, damage, refunds, or requests), sized to 100, 250, 500, 1,000, 2,000, and 4,000 tokens using Laya's tokenizer.

| Task | State | Questions (type) | Items kept / generated | Blind exact agreement before filtering |
|---|---|---|---:|---:|
| triage | support message | intent (Choice, 6), is_urgent (Noul), frustration (Score, 4) | 167 / 180 | 64% |
| moderation | forum post | toxic (Noul), harassment (Noul), severity (Score, 4) | 142 / 155 | 79% |
| routing | request to an AI assistant | domain (Choice, 6), difficulty (Score, 4), needs_tools (Noul) | 137 / 150 | 51% |
| claims | passage + claim (two fields) | verdict (Choice, 3), supported (Noul) | 150 / 150 | 100% |
| reviews | product review | stars (Score, 5), recommends (Noul) | 150 / 150 | 75% |
| guard | prompt to an AI assistant | injection (Noul), harm (Score, 4) | 146 / 150 | 92% |
| multilingual | support message in es/fr/de/pt/it/ja/zh | intent (Choice, 6), is_urgent (Noul) | 128 / 140 | 91% |
| needle | long notes with one buried fact | wants (Choice, 5), mentions_damage (Noul) | 450 (programmatic) | n/a |

Total: 1,470 items and 3,386 judgments per backend. Classes are balanced or near-balanced (see `bench/data/*.jsonl`). Score levels are inherently fuzzier than categorical labels; the blind exact-agreement column shows that even the generating model only reproduces its own ordinal labels 51 to 79% of the time, so Score "exact level" accuracy has a ceiling well below 100 and within-one-level accuracy and MAE are the fairer Score metrics.

## 3. Method

**Accuracy.** Each item is one request carrying all of the task's questions. Choice is scored by argmax accuracy and macro-F1. Noul is thresholded at 0.5 for accuracy and also scored by AUROC, Brier score, expected calibration error (ECE, 10 bins), and log-loss. Score is scored by exact level (argmax of the returned distribution), within-one-level accuracy, mean absolute error of the returned expected value, and Spearman correlation. 95% confidence intervals are 2,000-sample bootstraps; paired differences are bootstrapped over the same items.

**Speed.** Separate controlled runs, sequential, wall-clock around the call only (SDK call for Jev; `mx.synchronize()` bracketed `predict` for Laya), 5 warmup calls then 100 iterations for the single-question workload, 30 for question-count sweeps, 20 for state-length sweeps. Model loading is excluded. Jev timings include network transit from this machine; the warm round trip for a no-inference `GET /v1/models` was 49 to 60 ms.

**Fairness notes.** Laya was given `dtype="float16"` (its default and the published validation configuration). Its `batch_size=64` was also tried and was slower on this machine. Its documented `compile=True, cache_prompts=True, pad_to_multiple=16` path was measured separately. Jev was called with the SDK defaults and 6-way HTTP concurrency for the accuracy runs (well under the published 1,200 requests/minute limit; the slowest of the 1,470 calls took 700 ms, so no retry-with-backoff occurred).

**Cost, for reference only.** Jev bills input tokens at $0.042 per million. The entire accuracy suite (1.38M input tokens across all eight tasks) cost about $0.06. Laya is free to run once downloaded.
