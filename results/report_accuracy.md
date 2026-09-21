## 5. Accuracy

![Accuracy per question](results/charts/accuracy_by_question.png)

**Headline.** Jev answered 92.9% of the 3,386 judgments correctly (exact level for Score questions). The Laya 421M English checkpoint answered 65.3%, the typed-decisions checkpoint 71.1%, and the multilingual checkpoint 52.4% (it is not meant for English and is included for completeness). Jev beat Laya 421M on every one of the 19 questions, and on every one the paired 95% confidence interval over the same items excludes zero. The smallest gap is on reviews/recommends (+4.7 points) and the largest on needle/wants (+55.6 points).

MASTER_TABLE

**By question type.** Jev is essentially at ceiling on the Choice (99.3%) and Noul (98.6%) questions. Its Score exact-level accuracy of 76.1% is bounded by the fuzziness of ordinal labels rather than by reading failures: it is within one level of gold 97 to 100% of the time and its expected-value MAE is 0.19 to 0.36 of a level. Laya's Score answers are within one level 75 to 96% of the time with MAE of 0.65 to 0.93, so it is typically off by most of a level even when the direction is right.

PAIRED_TABLE

**Calibration of Noul answers.** Jev's Brier scores are 0.002 to 0.024 and its predicted positive rates match the gold rates to within a point on every question. Laya's ranking ability is fair (AUROC 0.83 to 0.93 on most questions, though only 0.66 on needs_tools) but its probabilities are miscalibrated in inconsistent directions: it predicts "urgent" for 13% of tickets (gold 44%), "harassment" for 8% of posts (gold 35%), "needs tools" for 4% of requests (gold 31%), yet "prompt injection" for 75% of prompts (gold 38%). A 0.5 threshold therefore does not work for Laya out of the box; each question would need its own tuned threshold, and the sign of the bias is not predictable in advance.

![Reliability of Noul answers](results/charts/calibration_noul.png)

NOUL_TABLE

**Score questions.** Jev's returned distributions are unimodal 98.7% of the time; Laya's are non-unimodal (a second peak on a non-adjacent level) in 22.9% of answers, which is why its expected-value MAE is worse than its exact-level accuracy would suggest. One consequence worth noting on the other side: Jev's Score distributions are sharply peaked (mean confidence 0.87), so when it does miss a level it misses confidently, and on triage/frustration its log-loss (1.48) is actually worse than Laya's (1.34) despite 26 points higher accuracy.

SCORE_TABLE

**Choice questions and confidence gating.** Laya's confidence signal is usable as a gate: on items where its confidence is at least 0.8 it is 98 to 100% accurate, but that covers only 21 to 39% of items. Jev clears the same threshold on 97 to 100% of items.

CHOICE_TABLE

**Long states (needle task).** Jev found the buried customer ask in 450 of 450 items regardless of state length (100 to 4,000 tokens) or needle position. Its only misses in this task were on the companion damage question, and all four affected needle sentences are genuinely borderline (a watch that stopped after a year, a jamming paper tray, a frayed cord, a loose hinge), where Jev returned probabilities near 0.5 rather than a confident wrong answer. Laya 421M scored 61% at 100 tokens, where nothing is truncated, and 39 to 44% at 250 tokens and above. By position the mechanism is clear: with the needle at the start of the notes Laya stays at 56 to 84% at every length, because the start survives truncation; with the needle in the middle or at the end it falls to 16 to 40%, near the 20% chance level for five options. When the needle has been cut off, Laya answers "not_stated" 93% of the time, which is the correct reading of what it was actually given; the failure is the 512-token window, not confabulation.

![Needle accuracy by length](results/charts/needle_by_length.png)

NEEDLE_LEN_TABLE

NEEDLE_POS_TABLE

**Non-English states.** Jev classified intent and urgency correctly on all 128 non-English tickets across seven languages, despite its documentation describing English as the primary training language. Laya's English checkpoint drops to 48% on intent (21% on German, 22% on Japanese), and its dedicated multilingual checkpoint reaches 64% on intent and 62% on urgency.

MULTI_TABLE
