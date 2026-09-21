# Jev vs Laya benchmark

Speed and accuracy of [Jev](https://docs.typesafe.ai) (TypeSafe's hosted System One model, `jev-1.13.0`) against [Laya](https://github.com/mizorewww/laya-mlx) (open-weight typed-decision models, run locally with MLX on Apple silicon), on 1,470 synthetic items across eight typed-decision tasks, plus controlled latency and throughput sweeps.

**Read the full report: [REPORT.md](REPORT.md).**

| | Jev 1.13 (API) | Laya 421M (local, M3 Pro) |
|---|---:|---:|
| Judgments correct (3,386 per backend) | 92.9% | 65.3% |
| Choice / Noul / Score accuracy | 99.3 / 98.6 / 76.1 | 68.3 / 71.3 / 51.5 |
| Single question, p50 latency | 136 ms (about 50 ms network) | 42 ms |
| 50 questions on one state, one request | 170 ms | 1,002 ms |
| Independent items, throughput | 72 items/s at 32 in flight | 24 items/s sequential |

Jev won all 19 questions with paired confidence intervals excluding zero. Laya is about 3x faster on a single short question; Jev is faster above 3 to 4 questions per request and on states longer than Laya's 512-token window. Details, calibration analysis, the long-context and multilingual results, and qualitative observations are in the report.

## Layout

```
bench/tasks.py              the exact questions sent to both models
bench/gen_data.py           synthetic data generation (gpt-5.5, label-conditioned + blind re-label)
bench/gen_needle.py         programmatic long-context task
bench/backends.py           uniform Jev / Laya wrappers
bench/run_speed.py          latency and throughput sweeps
bench/run_accuracy.py       accuracy runs, per-item predictions
bench/metrics.py            accuracy, calibration, bootstrap CIs
bench/report.py             tables and charts
bench/disagreements.py      per-item Jev vs Laya diffs for qualitative review
bench/data/*.jsonl          the datasets, with gold labels and the blind re-label
results/predictions/        every answer from every backend, with probabilities and timings
results/speed.json          every latency sample
results/charts/             figures used in the report
results/tables.md           all generated tables
```

## Reproduce

Apple silicon Mac (for Laya), a TypeSafe API key, and an OpenAI key (only for regenerating the data; the generated data is committed).

```
uv venv --python 3.12 .venv && source .venv/bin/activate
git clone https://github.com/mizorewww/laya-mlx && git -C laya-mlx checkout fc1df62828a3fedf4d8229fdac1cbd85f1cdf337
uv pip install ./laya-mlx -r requirements.txt
export TYPESAFE_API_KEY=...   # and OPENAI_API_KEY=... to regenerate data
python bench/gen_data.py && python bench/gen_needle.py    # optional: regenerate data
python bench/run_speed.py
python bench/run_accuracy.py
python bench/report.py && python bench/assemble_report.py
python bench/disagreements.py triage is_urgent
```

Laya checkpoints download from Hugging Face on first use (`aac6fef/laya-mlx`, `aac6fef/laya-multilingual-mlx`, `aac6fef/laya-typed-decisions-mlx`; about 840 MB each for the 421M models).

## Notes on the data

All items are synthetic and were generated for this benchmark. The `moderation` and `guard` sets deliberately contain toxic posts, threats with slurs masked, and one-line harmful or jailbreak-style requests, because that is what a moderation or guardrail classifier has to judge; no harmful answers or technical detail are included. Gold labels are the generation targets, filtered by a blind re-label; see the report for the label-noise estimates and the ceiling caveat.

## License

MIT for the code, data, and results in this repository. Laya weights and `laya-mlx` are Apache-2.0 and belong to their authors; Jev is a hosted service under TypeSafe's terms.
