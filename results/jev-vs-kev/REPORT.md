# Jev vs Kev on OpenRouter

Run on 2026-09-30. Both models called through OpenRouter's `/v1/systemone` route with the TypeSafe Python SDK, on the same 1,470 synthetic items (3,386 judgments) used in the [Jev vs Laya report](../../REPORT.md), plus controlled latency sweeps with the two backends' calls interleaved.

| | Jev | Kev |
|---|---|---|
| OpenRouter slug | `~typesafe/jev-latest` | `jaredpalmer/kev-4b` |
| Model that answered | `typesafe/jev-1.13-20260917` | `jaredpalmer/kev-4b-20260924` |
| What it is | TypeSafe's hosted System One model | Open-weight LoRA adapter and pointer head on Qwen3.5-4B-Base |
| Provider | TypeSafe | SiliconFlow |
| Price | $0.042 / M input tokens, output free | $0.042 / M input tokens, output free |
| Context | 32k | 8k |

## Result

| | Jev | Kev |
|---|---:|---:|
| Mean accuracy over 19 questions | **93.0%** | 88.0% |
| Choice / Noul / Score | 99.4 / 98.6 / 76.5 | 97.6 / 93.4 / 68.5 |
| Questions with a significant difference (paired 95% CI) | better on 9 | better on 0 |
| 1 question, p50 / p95 | **203 / 329 ms** | 405 / 503 ms |
| 50 questions in one request, p50 | **240 ms** | 641 ms |
| Throughput, 32 in flight | **40.8 items/s** | 25.8 items/s |
| Est. cost per 1,000 items | $0.039 | **$0.025** |

Jev is more accurate and about twice as fast. Kev is about a third cheaper per item because its tokenizer produces fewer input tokens at the same per-token price. Kev was never significantly better than Jev on any question; its best result, `guard/harm`, is +2.7 points with a CI spanning zero.

Jev's figures match the earlier direct-API run (92.9% then, 93.0% now), so calling Jev through OpenRouter does not change its answers in any measurable way.

## Where Kev falls behind

The largest gaps, Jev minus Kev, with paired 95% CIs:

| Question | Jev | Kev | Difference |
|---|---:|---:|---:|
| routing / difficulty (4-level score) | 69.3 | 44.5 | +24.8 (+14.6, +35.0) |
| needle / mentions_damage (yes/no) | 90.9 | 73.1 | +17.8 (+14.2, +21.3) |
| guard / injection (yes/no) | 100.0 | 87.0 | +13.0 (+7.5, +18.5) |
| triage / frustration (4-level score) | 70.1 | 62.9 | +7.2 (+2.4, +12.0) |
| moderation / severity (4-level score) | 79.6 | 73.2 | +6.3 (+0.7, +12.0) |
| routing / needs_tools (yes/no) | 98.5 | 92.7 | +5.8 (+2.2, +10.2) |
| moderation / toxic (yes/no) | 97.9 | 92.3 | +5.6 (+1.4, +10.6) |
| needle / wants (choice) | 100.0 | 95.8 | +4.2 (+2.4, +6.2) |
| triage / is_urgent (yes/no) | 100.0 | 97.6 | +2.4 (+0.6, +4.8) |

On Choice questions the two are close (99.4 vs 97.6), and on multilingual triage Kev is 94 to 100% per language against Jev's 100%.

**Kev's yes/no errors are mostly calibration, not ranking.** Its AUROC is 0.97 to 1.00 on every yes/no question, so it orders items almost as well as Jev, but its 0.5 threshold sits in the wrong place, and in different directions on different questions:

| Question | Kev errors at 0.5 | In-sample best threshold |
|---|---|---|
| needle / mentions_damage | 121 false negatives, 0 false positives | 96.7% at 0.07 |
| guard / injection | 0 false negatives, 19 false positives | 97.9% at 0.73 |
| moderation / toxic | 11 false negatives, 0 false positives | 98.6% at 0.39 |
| routing / needs_tools | 5 false negatives, 5 false positives | no better than 0.5 |

The best-threshold numbers are chosen on the test items themselves, so they overstate what a tuned threshold would achieve on new data. They do show that most of Kev's yes/no gap could be recovered by per-question thresholds, which Jev does not need. Jev has the same under-calling pattern on `mentions_damage` (41 false negatives, as in the earlier run), which a 0.19 threshold would fix.

**On Score questions** both models are within one level of gold 96 to 100% of the time, but Kev's expected-value error is larger (MAE 0.30 to 0.59 of a level against Jev's 0.19 to 0.36). As in the earlier report, exact-level Score accuracy has a ceiling well below 100% because the ordinal labels are fuzzy.

**Long context.** On the needle task Kev gets both questions right on 63 to 72% of items at every length from 100 to 4,000 tokens, against Jev's 88 to 95%. Its shortfall does not grow with length, so this is the `mentions_damage` threshold effect rather than a context problem. Kev's 8k window covered every state in this benchmark; longer states were not tested.

## Speed

Controlled runs from this Mac, the two backends' calls alternating so both saw the same network. Timings include the round trip to OpenRouter.

| Workload | Jev p50 / p95 ms | Kev p50 / p95 ms |
|---|---:|---:|
| 1 question, short state | 203 / 329 | 405 / 503 |
| 10 questions, one request | 209 / 342 | 478 / 1,161 |
| 50 questions, one request | 240 / 285 | 641 / 747 |
| 1 question, ~6,400-token state | 226 / 451 | 534 / 612 |
| 64 items, 1 / 8 / 32 in flight | 4.4 / 28.0 / 40.8 items/s | 2.0 / 12.3 / 25.8 items/s |

Both scale well with more questions per request and longer states. Kev's fixed cost per call is about twice Jev's.

## Caveats

- The data are synthetic, with gold labels from label-conditioned generation filtered by a blind re-label; see section 2 of the [Jev vs Laya report](../../REPORT.md) for the label-noise estimates.
- Costs are estimates: list price times the input tokens each provider reported. OpenRouter did not return a per-request cost on this route.
- Kev had a single provider (SiliconFlow) at the time of the run; its latency reflects that deployment. Kev is open-weight and could be self-hosted, which was not tested.
- Each figure comes from one run. The speed sweeps used 50 iterations for the single-question case and 10 for the others.

## Files

```
results/jev-vs-kev/tables.md          every table (per question, calibration, scores, needle, languages, speed)
results/jev-vs-kev/predictions/       every answer with probabilities and timings
results/jev-vs-kev/speed.json         every latency sample
```

## Reproduce

```
./scripts/set-openrouter-key.sh      # stores OPENROUTER_API_KEY in .env (gitignored)
python bench/run_accuracy.py --backends jev-openrouter kev --workers 8 --out-dir results/jev-vs-kev/predictions
python bench/run_speed_api.py
python bench/report_compare.py
```
