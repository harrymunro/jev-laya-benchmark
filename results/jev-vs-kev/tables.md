Predictions: `/Users/harry/Workspace/jev-laya-benchmark/results/jev-vs-kev/predictions`. Baseline for paired differences: **jev-openrouter**.

## Headline

| | jev-openrouter | kev |
|---|---:|---:|
| Mean accuracy, 19 questions | 93.0% (3,386 judgments) | 88.0% (3,386 judgments) |
| Choice mean accuracy | 99.4% | 97.6% |
| Noul mean accuracy | 98.6% | 93.4% |
| Score mean accuracy | 76.5% | 68.5% |
| Questions where baseline is significantly better / worse |  | 9 / 0 of 19 |
| Per-item latency p50 / p95 (accuracy run) | 223 / 306 ms | 730 / 1242 ms |
| Tokens in / out per item | 937 / 70 | 600 / 170 |
| Est. cost per 1,000 items (list price x input tokens) | $0.039 | $0.025 |

## Accuracy by question

| Task | Question | Type | n | jev-openrouter | kev | jev-openrouter − kev (95% CI) |
|---|---|---|---:|---:|---:|---:|
| triage | intent | choice | 167 | 99.4 | 97.6 | +1.8 (+0.0, +4.2) |
| triage | is_urgent | noul | 167 | 100.0 | 97.6 | **+2.4 (+0.6, +4.8)** |
| triage | frustration | score | 167 | 70.1 | 62.9 | **+7.2 (+2.4, +12.0)** |
| moderation | toxic | noul | 142 | 97.9 | 92.3 | **+5.6 (+1.4, +10.6)** |
| moderation | harassment | noul | 142 | 100.0 | 99.3 | +0.7 (+0.0, +2.1) |
| moderation | severity | score | 142 | 79.6 | 73.2 | **+6.3 (+0.7, +12.0)** |
| routing | domain | choice | 137 | 97.8 | 97.8 | +0.0 (-2.9, +2.9) |
| routing | difficulty | score | 137 | 69.3 | 44.5 | **+24.8 (+14.6, +35.0)** |
| routing | needs_tools | noul | 137 | 98.5 | 92.7 | **+5.8 (+2.2, +10.2)** |
| claims | verdict | choice | 150 | 100.0 | 99.3 | +0.7 (+0.0, +2.0) |
| claims | supported | noul | 150 | 100.0 | 98.7 | +1.3 (+0.0, +3.3) |
| reviews | stars | score | 150 | 74.7 | 70.0 | +4.7 (+0.0, +10.0) |
| reviews | recommends | noul | 150 | 100.0 | 100.0 | +0.0 (+0.0, +0.0) |
| guard | injection | noul | 146 | 100.0 | 87.0 | **+13.0 (+7.5, +18.5)** |
| guard | harm | score | 146 | 89.0 | 91.8 | -2.7 (-7.5, +1.4) |
| multilingual | intent | choice | 128 | 100.0 | 97.7 | +2.3 (+0.0, +5.5) |
| multilingual | is_urgent | noul | 128 | 100.0 | 100.0 | +0.0 (+0.0, +0.0) |
| needle | wants | choice | 450 | 100.0 | 95.8 | **+4.2 (+2.4, +6.2)** |
| needle | mentions_damage | noul | 450 | 90.9 | 73.1 | **+17.8 (+14.2, +21.3)** |

Bold: the paired 95% bootstrap CI excludes zero.

## Yes/no questions: ranking and calibration

| Task | Question | jev-openrouter AUROC / Brier / ECE | kev AUROC / Brier / ECE |
|---|---|---:|---:|
| triage | is_urgent | 1.000 / 0.006 / 0.052 | 0.999 / 0.047 / 0.149 |
| moderation | toxic | 1.000 / 0.025 / 0.115 | 0.999 / 0.077 / 0.218 |
| moderation | harassment | 1.000 / 0.002 / 0.034 | 1.000 / 0.023 / 0.110 |
| routing | needs_tools | 0.997 / 0.019 / 0.065 | 0.971 / 0.070 / 0.092 |
| claims | supported | 1.000 / 0.002 / 0.027 | 0.999 / 0.010 / 0.025 |
| reviews | recommends | 1.000 / 0.004 / 0.042 | 1.000 / 0.000 / 0.008 |
| guard | injection | 1.000 / 0.003 / 0.031 | 0.997 / 0.077 / 0.182 |
| multilingual | is_urgent | 1.000 / 0.004 / 0.041 | 1.000 / 0.023 / 0.127 |
| needle | mentions_damage | 1.000 / 0.052 / 0.123 | 0.998 / 0.178 / 0.243 |

## Ordinal scores

| Task | Question | jev-openrouter within-1 / MAE / Spearman | kev within-1 / MAE / Spearman |
|---|---|---:|---:|
| triage | frustration | 98.8% / 0.33 / 0.836 | 98.2% / 0.45 / 0.804 |
| moderation | severity | 100.0% / 0.23 / 0.929 | 97.9% / 0.42 / 0.929 |
| routing | difficulty | 97.8% / 0.36 / 0.889 | 99.3% / 0.59 / 0.857 |
| reviews | stars | 99.3% / 0.24 / 0.976 | 98.7% / 0.30 / 0.971 |
| guard | harm | 96.6% / 0.19 / 0.925 | 100.0% / 0.33 / 0.914 |

## Long-context needle by state length (tokens)

Share of items with every question right (n).

| length_target | jev-openrouter | kev |
|---|---:|---:|
| 100 | 94.7% (75) | 69.3% (75) |
| 250 | 90.7% (75) | 62.7% (75) |
| 500 | 89.3% (75) | 69.3% (75) |
| 1000 | 88.0% (75) | 72.0% (75) |
| 2000 | 92.0% (75) | 70.7% (75) |
| 4000 | 90.7% (75) | 69.3% (75) |

## Multilingual triage by language

Share of items with every question right (n).

| language | jev-openrouter | kev |
|---|---:|---:|
| Chinese (Simplified) | 100.0% (16) | 100.0% (16) |
| French | 100.0% (19) | 100.0% (19) |
| German | 100.0% (19) | 100.0% (19) |
| Italian | 100.0% (20) | 95.0% (20) |
| Japanese | 100.0% (18) | 94.4% (18) |
| Portuguese | 100.0% (19) | 100.0% (19) |
| Spanish | 100.0% (17) | 94.1% (17) |

## Controlled latency (interleaved calls)

| Workload | jev-openrouter p50 / p95 ms | kev p50 / p95 ms |
|---|---:|---:|
| 1 question, short state | 203 / 329 | 405 / 503 |
| 1 question, one request | 203 / 236 | 409 / 740 |
| 5 questions, one request | 191 / 283 | 471 / 546 |
| 10 questions, one request | 209 / 342 | 478 / 1161 |
| 25 questions, one request | 221 / 273 | 488 / 620 |
| 50 questions, one request | 240 / 285 | 641 / 747 |
| 1 question, ~119-token state | 194 / 236 | 404 / 414 |
| 1 question, ~403-token state | 209 / 324 | 405 / 453 |
| 1 question, ~1606-token state | 231 / 388 | 425 / 451 |
| 1 question, ~6411-token state | 226 / 451 | 534 / 612 |
| 64 items, 1 in flight (items/s) | 4.4 | 2.0 |
| 64 items, 8 in flight (items/s) | 28.0 | 12.3 |
| 64 items, 32 in flight (items/s) | 40.8 | 25.8 |
