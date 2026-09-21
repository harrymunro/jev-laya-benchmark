## Single-question latency
| Backend | p50 ms | p90 ms | p95 ms | p99 ms | mean ms | min ms | network floor ms | input tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Jev 1.13 (API) | 135.6 | 203.1 | 255.6 | 342.8 | 147.6 | 89.7 | 53 | 500 |
| Jev 1.13 (API), later run, degraded network | 359.7 | 396.7 | 409.4 | 458.2 | 367.5 | 328.6 | 295 | 500 |
| Laya 421M (local) | 41.9 | 42.8 | 43.0 | 43.4 | 42.1 | 41.2 | 0 (local) | 183 |
| Laya multilingual 322M (local) | 18.3 | 19.2 | 19.6 | 20.0 | 18.4 | 17.0 | 0 (local) | 179 |
| Laya typed-decisions 421M (local) | 42.6 | 46.2 | 46.6 | 47.2 | 43.5 | 41.5 | 0 (local) | 183 |
| Laya 421M, compile+cache+pad16 | 39.1 | 40.2 | 40.4 | 41.3 | 39.3 | 39.0 | 0 (local) | 183 |

## Questions per request
| Questions per request | Jev p50 ms | Jev ms/question | Jev tokens | Laya p50 ms | Laya ms/question | Laya tokens |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 142.1 | 142.1 | 500 | 42.2 | 42.2 | 183 |
| 3 | 151.7 | 50.6 | 533 | 111.1 | 37.0 | 324 |
| 5 | 142.9 | 28.6 | 566 | 179.7 | 35.9 | 465 |
| 10 | 135.4 | 13.5 | 643 | 349.1 | 34.9 | 812 |
| 25 | 139.0 | 5.6 | 882 | 664.6 | 26.6 | 1864 |
| 50 | 170.1 | 3.4 | 1696 | 1001.8 | 20.0 | 3501 |

## State length
| State tokens (Laya tokenizer) | Jev p50 ms | Jev tokens billed | Laya p50 ms | Laya truncated? |
|---:|---:|---:|---:|:---|
| 68 | 137.9 | 533 | 49.6 | no |
| 112 | 145.7 | 575 | 61.8 | no |
| 210 | 187.6 | 670 | 77.5 | no |
| 402 | 157.3 | 861 | 104.2 | yes |
| 806 | 147.6 | 1258 | 104.9 | yes |
| 1602 | 165.3 | 2046 | 107.9 | yes |
| 3207 | 156.1 | 3633 | 111.2 | yes |
| 6417 | 183.2 | 6823 | 111.9 | yes |

## Throughput
| Scenario | Jev | Laya 421M |
|---|---:|---:|
| 64 distinct states x 1 question, Jev concurrency 1 | 6.1 items/s | 24.1 items/s (sequential) |
| 64 distinct states x 1 question, Jev concurrency 4 | 23.5 items/s | 24.1 items/s (sequential) |
| 64 distinct states x 1 question, Jev concurrency 8 | 44.4 items/s | 24.1 items/s (sequential) |
| 64 distinct states x 1 question, Jev concurrency 16 | 42.3 items/s | 24.1 items/s (sequential) |
| 64 distinct states x 1 question, Jev concurrency 32 | 71.5 items/s | 24.1 items/s (sequential) |
| 1 state x 50 questions, one request (Laya batch_size=16) | 301 q/s (166 ms) | 50 q/s (1001 ms) |
| 1 state x 50 questions, one request (Laya batch_size=64) | 301 q/s (166 ms) | 30 q/s (1658 ms) |

## Accuracy master
| Task | Question | Type | n | Jev 1.13 | Laya 421M | Laya multilingual 322M | Laya typed-decisions 421M |
|---|---|---|---:|---:|---:|---:|---:|
| triage | intent | choice | 167 | **99.4** | 78.4 | 64.7 | 79.0 |
| triage | is_urgent | noul | 167 | **100.0** | 63.5 | 60.5 | 81.4 |
| triage | frustration | score | 167 | **70.7** | 44.9 | 42.5 | 45.5 |
| moderation | toxic | noul | 142 | **98.6** | 68.3 | 64.8 | 72.5 |
| moderation | harassment | noul | 142 | **100.0** | 71.1 | 60.6 | 78.9 |
| moderation | severity | score | 142 | **77.5** | 65.5 | 19.0 | 73.2 |
| routing | domain | choice | 137 | **97.1** | 80.3 | 60.6 | 80.3 |
| routing | difficulty | score | 137 | **69.3** | 43.1 | 40.9 | 45.3 |
| routing | needs_tools | noul | 137 | **97.8** | 68.6 | 53.3 | 68.6 |
| claims | verdict | choice | 150 | **100.0** | 90.0 | 78.7 | 90.7 |
| claims | supported | noul | 150 | **100.0** | 90.0 | 80.7 | 92.0 |
| reviews | stars | score | 150 | **74.7** | 46.7 | 26.7 | 68.7 |
| reviews | recommends | noul | 150 | **100.0** | 95.3 | 58.0 | 94.7 |
| guard | injection | noul | 146 | **100.0** | 63.0 | 41.8 | 87.7 |
| guard | harm | score | 146 | **88.4** | 57.5 | 24.7 | 63.0 |
| multilingual | intent | choice | 128 | **100.0** | 48.4 | 64.1 | 59.4 |
| multilingual | is_urgent | noul | 128 | **100.0** | 65.6 | 61.7 | 76.6 |
| needle | wants | choice | 450 | **100.0** | 44.4 | 42.9 | 41.3 |
| needle | mentions_damage | noul | 450 | **90.9** | 56.4 | 49.3 | 52.7 |
| | | | |  |  |  |  |
| **mean** | **choice** | | | 99.3 | 68.3 | 62.2 | 70.1 |
| **mean** | **noul** | | | 98.6 | 71.3 | 59.0 | 78.3 |
| **mean** | **score** | | | 76.1 | 51.5 | 30.7 | 59.1 |
| **mean** | **all** | | | 92.9 | 65.3 | 52.4 | 71.1 |

## Paired Jev - Laya
| Task | Question | jev - laya (pp) | 95% CI | n |
|---|---|---:|---|---:|
| triage | intent | +21.0 | [+15.0, +26.9] | 167 |
| triage | is_urgent | +36.5 | [+29.3, +44.3] | 167 |
| triage | frustration | +25.7 | [+18.0, +33.5] | 167 |
| moderation | toxic | +30.3 | [+22.5, +38.0] | 142 |
| moderation | harassment | +28.9 | [+21.8, +36.6] | 142 |
| moderation | severity | +12.0 | [+2.8, +21.1] | 142 |
| routing | domain | +16.8 | [+10.2, +24.1] | 137 |
| routing | difficulty | +26.3 | [+16.1, +36.5] | 137 |
| routing | needs_tools | +29.2 | [+21.2, +37.2] | 137 |
| claims | verdict | +10.0 | [+5.3, +15.3] | 150 |
| claims | supported | +10.0 | [+5.3, +15.3] | 150 |
| reviews | stars | +28.0 | [+18.7, +36.7] | 150 |
| reviews | recommends | +4.7 | [+1.3, +8.0] | 150 |
| guard | injection | +37.0 | [+28.8, +45.2] | 146 |
| guard | harm | +30.8 | [+21.9, +40.4] | 146 |
| multilingual | intent | +51.6 | [+43.0, +59.4] | 128 |
| multilingual | is_urgent | +34.4 | [+26.6, +43.0] | 128 |
| needle | wants | +55.6 | [+50.9, +60.2] | 450 |
| needle | mentions_damage | +34.4 | [+29.8, +38.9] | 450 |

## Choice detail
| Task | Question | Backend | Acc | macro-F1 | log-loss | mean P(gold) | mean conf | acc @conf>=0.8 (coverage) |
|---|---|---|---:|---:|---:|---:|---:|---|
| triage | intent | jev | 99.4 | 0.994 | 0.02 | 0.99 | 0.99 | 100.0 (98%) |
| triage | intent | laya | 78.4 | 0.756 | 0.62 | 0.67 | 0.60 | 98.2 (34%) |
| triage | intent | laya-multilingual | 64.7 | 0.576 | 1.27 | 0.63 | 0.75 | 86.0 (56%) |
| triage | intent | laya-typed-decisions | 79.0 | 0.773 | 0.62 | 0.62 | 0.48 | 100.0 (8%) |
| routing | domain | jev | 97.1 | 0.967 | 0.05 | 0.97 | 0.98 | 98.5 (98%) |
| routing | domain | laya | 80.3 | 0.784 | 0.63 | 0.67 | 0.59 | 98.1 (39%) |
| routing | domain | laya-multilingual | 60.6 | 0.598 | 1.01 | 0.57 | 0.61 | 93.5 (34%) |
| routing | domain | laya-typed-decisions | 80.3 | 0.792 | 0.60 | 0.62 | 0.46 | 100.0 (5%) |
| claims | verdict | jev | 100.0 | 1.000 | 0.01 | 0.99 | 0.98 | 100.0 (97%) |
| claims | verdict | laya | 90.0 | 0.897 | 0.33 | 0.82 | 0.63 | 100.0 (21%) |
| claims | verdict | laya-multilingual | 78.7 | 0.785 | 0.63 | 0.74 | 0.69 | 93.7 (53%) |
| claims | verdict | laya-typed-decisions | 90.7 | 0.903 | 0.44 | 0.69 | 0.33 | nan (0%) |
| multilingual | intent | jev | 100.0 | 1.000 | 0.01 | 0.99 | 0.99 | 100.0 (98%) |
| multilingual | intent | laya | 48.4 | 0.455 | 1.51 | 0.42 | 0.47 | 70.8 (19%) |
| multilingual | intent | laya-multilingual | 64.1 | 0.539 | 1.26 | 0.62 | 0.77 | 83.1 (55%) |
| multilingual | intent | laya-typed-decisions | 59.4 | 0.570 | 1.22 | 0.39 | 0.26 | nan (0%) |
| needle | wants | jev | 100.0 | 1.000 | 0.00 | 1.00 | 1.00 | 100.0 (100%) |
| needle | wants | laya | 44.4 | 0.437 | 1.39 | 0.35 | 0.28 | 100.0 (0%) |
| needle | wants | laya-multilingual | 42.9 | 0.413 | 2.30 | 0.42 | 0.74 | 49.2 (53%) |
| needle | wants | laya-typed-decisions | 41.3 | 0.380 | 1.35 | 0.30 | 0.13 | nan (0%) |

## Noul detail
| Task | Question | Backend | Acc | AUROC | Brier | ECE | log-loss | pred. positive rate (gold) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| triage | is_urgent | jev | 100.0 | 1.000 | 0.006 | 0.053 | 0.06 | 0.44 (0.44) |
| triage | is_urgent | laya | 63.5 | 0.827 | 0.237 | 0.215 | 0.67 | 0.13 (0.44) |
| triage | is_urgent | laya-multilingual | 60.5 | 0.676 | 0.296 | 0.266 | 0.94 | 0.28 (0.44) |
| triage | is_urgent | laya-typed-decisions | 81.4 | 0.893 | 0.152 | 0.151 | 0.48 | 0.42 (0.44) |
| moderation | toxic | jev | 98.6 | 1.000 | 0.024 | 0.115 | 0.13 | 0.55 (0.56) |
| moderation | toxic | laya | 68.3 | 0.905 | 0.199 | 0.248 | 0.57 | 0.27 (0.56) |
| moderation | toxic | laya-multilingual | 64.8 | 0.918 | 0.269 | 0.335 | 0.82 | 0.23 (0.56) |
| moderation | toxic | laya-typed-decisions | 72.5 | 0.923 | 0.179 | 0.277 | 0.54 | 0.33 (0.56) |
| moderation | harassment | jev | 100.0 | 1.000 | 0.002 | 0.034 | 0.03 | 0.35 (0.35) |
| moderation | harassment | laya | 71.1 | 0.904 | 0.171 | 0.173 | 0.49 | 0.08 (0.35) |
| moderation | harassment | laya-multilingual | 60.6 | 0.721 | 0.275 | 0.275 | 0.81 | 0.28 (0.35) |
| moderation | harassment | laya-typed-decisions | 78.9 | 0.915 | 0.150 | 0.187 | 0.47 | 0.18 (0.35) |
| routing | needs_tools | jev | 97.8 | 0.997 | 0.020 | 0.066 | 0.10 | 0.31 (0.31) |
| routing | needs_tools | laya | 68.6 | 0.662 | 0.210 | 0.110 | 0.61 | 0.04 (0.31) |
| routing | needs_tools | laya-multilingual | 53.3 | 0.562 | 0.274 | 0.228 | 0.76 | 0.53 (0.31) |
| routing | needs_tools | laya-typed-decisions | 68.6 | 0.679 | 0.197 | 0.057 | 0.58 | 0.08 (0.31) |
| claims | supported | jev | 100.0 | 1.000 | 0.002 | 0.026 | 0.03 | 0.33 (0.33) |
| claims | supported | laya | 90.0 | 0.969 | 0.072 | 0.077 | 0.24 | 0.39 (0.33) |
| claims | supported | laya-multilingual | 80.7 | 0.878 | 0.159 | 0.145 | 0.57 | 0.31 (0.33) |
| claims | supported | laya-typed-decisions | 92.0 | 0.985 | 0.068 | 0.151 | 0.27 | 0.40 (0.33) |
| reviews | recommends | jev | 100.0 | 1.000 | 0.004 | 0.042 | 0.04 | 0.50 (0.50) |
| reviews | recommends | laya | 95.3 | 0.992 | 0.045 | 0.113 | 0.20 | 0.48 (0.50) |
| reviews | recommends | laya-multilingual | 58.0 | 0.656 | 0.310 | 0.281 | 0.99 | 0.15 (0.50) |
| reviews | recommends | laya-typed-decisions | 94.7 | 0.994 | 0.070 | 0.202 | 0.29 | 0.47 (0.50) |
| guard | injection | jev | 100.0 | 1.000 | 0.003 | 0.031 | 0.03 | 0.38 (0.38) |
| guard | injection | laya | 63.0 | 0.925 | 0.233 | 0.308 | 0.65 | 0.75 (0.38) |
| guard | injection | laya-multilingual | 41.8 | 0.719 | 0.546 | 0.567 | 2.76 | 0.97 (0.38) |
| guard | injection | laya-typed-decisions | 87.7 | 0.940 | 0.144 | 0.218 | 0.47 | 0.44 (0.38) |
| multilingual | is_urgent | jev | 100.0 | 1.000 | 0.003 | 0.041 | 0.04 | 0.44 (0.44) |
| multilingual | is_urgent | laya | 65.6 | 0.792 | 0.209 | 0.172 | 0.61 | 0.20 (0.44) |
| multilingual | is_urgent | laya-multilingual | 61.7 | 0.691 | 0.265 | 0.210 | 0.84 | 0.41 (0.44) |
| multilingual | is_urgent | laya-typed-decisions | 76.6 | 0.847 | 0.177 | 0.122 | 0.54 | 0.44 (0.44) |
| needle | mentions_damage | jev | 90.9 | 1.000 | 0.052 | 0.123 | 0.17 | 0.43 (0.52) |
| needle | mentions_damage | laya | 56.4 | 0.681 | 0.313 | 0.303 | 0.96 | 0.10 (0.52) |
| needle | mentions_damage | laya-multilingual | 49.3 | 0.620 | 0.461 | 0.476 | 2.61 | 0.01 (0.52) |
| needle | mentions_damage | laya-typed-decisions | 52.7 | 0.724 | 0.260 | 0.211 | 0.72 | 0.06 (0.52) |

## Score detail
| Task | Question | Backend | exact | within 1 | MAE (expected) | Spearman | log-loss | mean conf |
|---|---|---|---:|---:|---:|---:|---:|---:|
| triage | frustration | jev | 70.7 | 98.8 | 0.34 | 0.836 | 1.48 | 0.89 |
| triage | frustration | laya | 44.9 | 84.4 | 0.70 | 0.632 | 1.34 | 0.40 |
| triage | frustration | laya-multilingual | 42.5 | 91.6 | 0.83 | 0.387 | 1.67 | 0.29 |
| triage | frustration | laya-typed-decisions | 45.5 | 85.0 | 0.74 | 0.593 | 1.24 | 0.26 |
| moderation | severity | jev | 77.5 | 100.0 | 0.23 | 0.929 | 0.59 | 0.88 |
| moderation | severity | laya | 65.5 | 93.0 | 0.65 | 0.791 | 0.99 | 0.30 |
| moderation | severity | laya-multilingual | 19.0 | 52.8 | 1.19 | -0.397 | 2.06 | 0.14 |
| moderation | severity | laya-typed-decisions | 73.2 | 97.2 | 0.63 | 0.859 | 0.84 | 0.19 |
| routing | difficulty | jev | 69.3 | 97.8 | 0.36 | 0.888 | 0.68 | 0.76 |
| routing | difficulty | laya | 43.1 | 95.6 | 0.69 | 0.812 | 1.17 | 0.28 |
| routing | difficulty | laya-multilingual | 40.9 | 81.0 | 0.73 | 0.711 | 1.33 | 0.34 |
| routing | difficulty | laya-typed-decisions | 45.3 | 97.8 | 0.65 | 0.848 | 1.06 | 0.17 |
| reviews | stars | jev | 74.7 | 99.3 | 0.24 | 0.976 | 0.72 | 0.93 |
| reviews | stars | laya | 46.7 | 74.7 | 0.93 | 0.869 | 1.88 | 0.59 |
| reviews | stars | laya-multilingual | 26.7 | 58.7 | 1.53 | 0.509 | 4.79 | 0.74 |
| reviews | stars | laya-typed-decisions | 68.7 | 99.3 | 0.44 | 0.950 | 1.06 | 0.45 |
| guard | harm | jev | 88.4 | 96.6 | 0.19 | 0.924 | 0.36 | 0.88 |
| guard | harm | laya | 57.5 | 93.8 | 0.73 | 0.725 | 0.98 | 0.25 |
| guard | harm | laya-multilingual | 24.7 | 84.9 | 1.04 | 0.065 | 2.07 | 0.30 |
| guard | harm | laya-typed-decisions | 63.0 | 95.2 | 0.70 | 0.741 | 0.97 | 0.16 |

## Needle by length
| State tokens | Jev 1.13 wants / damage | Laya 421M wants / damage | Laya multilingual 322M wants / damage | Laya typed-decisions 421M wants / damage |
|---:|---:|---:|---:|---:|
| 100 | 100 / 95 | 61 / 61 | 64 / 51 | 61 / 57 |
| 250 | 100 / 91 | 43 / 55 | 47 / 49 | 45 / 53 |
| 500 | 100 / 91 | 40 / 56 | 43 / 48 | 39 / 52 |
| 1000 | 100 / 89 | 44 / 57 | 41 / 49 | 35 / 55 |
| 2000 | 100 / 91 | 39 / 53 | 32 / 49 | 35 / 49 |
| 4000 | 100 / 89 | 40 / 56 | 31 / 49 | 33 / 49 |

## Needle by position
| Backend | Needle position | 100 | 250 | 500 | 1000 | 2000 | 4000 |
|---|---|---:|---:|---:|---:|---:|---:|
| jev | start | 100 | 100 | 100 | 100 | 100 | 100 |
| jev | middle | 100 | 100 | 100 | 100 | 100 | 100 |
| jev | end | 100 | 100 | 100 | 100 | 100 | 100 |
| laya | start | 64 | 56 | 84 | 72 | 68 | 84 |
| laya | middle | 64 | 24 | 20 | 40 | 24 | 20 |
| laya | end | 56 | 48 | 16 | 20 | 24 | 16 |

## Multilingual
| Language | n | Jev 1.13 intent / urgent | Laya 421M intent / urgent | Laya multilingual 322M intent / urgent | Laya typed-decisions 421M intent / urgent |
|---|---:|---:|---:|---:|---:|
| Chinese (Simplified) | 16 | 100 / 100 | 56 / 31 | 69 / 56 | 75 / 62 |
| French | 19 | 100 / 100 | 74 / 58 | 74 / 53 | 74 / 79 |
| German | 19 | 100 / 100 | 21 / 63 | 47 / 79 | 37 / 84 |
| Italian | 20 | 100 / 100 | 45 / 60 | 55 / 55 | 60 / 65 |
| Japanese | 18 | 100 / 100 | 22 / 72 | 61 / 61 | 33 / 78 |
| Portuguese | 19 | 100 / 100 | 58 / 89 | 74 / 84 | 74 / 79 |
| Spanish | 17 | 100 / 100 | 65 / 82 | 71 / 41 | 65 / 88 |
| ALL | 128 | 100 / 100 | 48 / 66 | 64 / 62 | 59 / 77 |

## Accuracy-run timing
| Task | n | Jev 1.13 s (items/s) | Laya 421M s (items/s) | Laya multilingual 322M s (items/s) | Laya typed-decisions 421M s (items/s) | Jev tokens/item | Laya tokens/item | Laya truncated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| triage | 167 | 4.8 (34.9) | 25.6 (6.5) | 28.1 (5.9) | 28.7 (5.8) | 687 | 468 | 0% |
| moderation | 142 | 3.8 (37.8) | 17.7 (8.0) | 7.5 (19.0) | 21.1 (6.7) | 572 | 390 | 0% |
| routing | 137 | 3.6 (38.5) | 28.9 (4.7) | 54.9 (2.5) | 20.1 (6.8) | 713 | 495 | 1% |
| claims | 150 | 4.4 (34.1) | 15.7 (9.6) | 6.2 (24.2) | 17.8 (8.4) | 553 | 368 | 0% |
| reviews | 150 | 4.4 (34.0) | 16.4 (9.2) | 5.7 (26.2) | 187.7 (0.8) | 523 | 319 | 0% |
| guard | 146 | 4.4 (33.0) | 63.5 (2.3) | 4.6 (32.0) | 129.5 (1.1) | 523 | 284 | 0% |
| multilingual | 128 | 3.8 (33.7) | 16.1 (7.9) | 8.1 (15.9) | 16.7 (7.6) | 619 | 408 | 0% |
| needle | 450 | 12.2 (36.8) | 80.2 (5.6) | 80.9 (5.6) | 135.4 (3.3) | 1705 | 839 | 67% |