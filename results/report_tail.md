## 7. Limitations

- **Synthetic, generator-labelled data.** Gold labels are the generation targets, filtered by a blind re-label from the same model family (`gpt-5.5`). That removes ambiguous items and makes the categorical questions clean, which is why Jev's Choice and Noul scores are near 100%: the suite measures whether a model reads a clear decision correctly, not how it handles the messy long tail of real tickets. A ceiling effect means the suite cannot separate Jev from another strong model; it can and does separate Jev from Laya.
- **Ordinal labels are noisy.** The blind re-label only reproduced the Score levels exactly 51 to 79% of the time, so exact-level accuracy has a ceiling well below 100 for any model. Within-one-level accuracy and MAE are the better Score metrics.
- **One machine, one network path.** Laya numbers are for an M3 Pro with 18 GB; the project's own M3 Max figures are about 3x faster. Jev numbers include roughly 50 ms of transit from this location and would differ elsewhere. The Laya accuracy runs briefly overlapped with a CPU-heavy data-building script and, for the typed-decisions checkpoint's last two English tasks, showed a 4x per-call slowdown of unknown cause (swap was in use on this 18 GB machine); those accuracy-run timings are excluded from the speed section, whose controlled runs were separate.
- **No adversarial or numeric tasks.** The documented weak spots of Jev (counting, arithmetic, dates, multi-hop indirection, injected text in state) were not targeted. All eight tasks are single-hop semantic judgments, which is the design centre of both models.
- **Laya was used as shipped.** No per-question threshold tuning, no prompt adaptation, no calibration set. Its published presets use the same phrasing style as the questions here (backticked field names, short criteria), so the questions are within its intended usage.
- **Jev is a moving alias.** Results are for `jev-1.13.0`, the version reported in every response during this run.

## 8. Reproduction

```
uv venv --python 3.12 .venv && source .venv/bin/activate
git clone https://github.com/mizorewww/laya-mlx && git -C laya-mlx checkout fc1df62828a3fedf4d8229fdac1cbd85f1cdf337
uv pip install ./laya-mlx -r requirements.txt
export TYPESAFE_API_KEY=...  OPENAI_API_KEY=...   # OpenAI only needed to regenerate data
.venv/bin/python bench/gen_data.py            # optional: regenerate the 7 LLM-generated tasks + filler (about 8 min)
.venv/bin/python bench/gen_needle.py          # optional: rebuild the programmatic long-context task
.venv/bin/python bench/run_speed.py           # controlled latency / throughput sweeps
.venv/bin/python bench/run_accuracy.py        # all backends, all tasks
.venv/bin/python bench/report.py              # tables + charts into results/
.venv/bin/python bench/assemble_report.py     # this file
.venv/bin/python bench/disagreements.py triage is_urgent   # per-item Jev vs Laya diffs
```

Files: `bench/tasks.py` holds the exact questions sent to both models; `bench/data/*.jsonl` the datasets with gold labels and the blind re-label; `results/predictions/<backend>/<task>.jsonl` every answer with probabilities and per-call timing; `results/speed.json` every latency sample; `results/summary.json` all metrics; `results/charts/*.png` the figures.
