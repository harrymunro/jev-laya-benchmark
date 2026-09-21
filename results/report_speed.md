## 4. Speed

![Single-question latency](results/charts/latency_single.png)

**One question, short state.** Laya is the faster call by about 3x on this machine: 42 to 43 ms median for the 421M English checkpoint (two runs) against 136 ms for Jev, with the 322M multilingual checkpoint at 16 to 18 ms. Roughly 50 ms of Jev's figure is network transit from this Mac (the no-inference round trip to the API measured 49 to 60 ms at the time), so the API's own budget is in the region of 85 ms. Jev's tail is wider (p95 256 ms, p99 343 ms) because it crosses the public internet; Laya's tail is tight (p95 43 to 50 ms) because nothing leaves the GPU. Laya's documented `compile=True, cache_prompts=True, pad_to_multiple=16` path shaved the median to 39 ms and tightened p95 to 40 ms.

A second single-question run about 90 minutes later, on an otherwise idle machine, reproduced every Laya figure within 2 ms but put Jev at 360 ms. The no-inference round trip to the API had risen to 295 ms by then, and so had round trips to unrelated hosts (141 ms ping to 1.1.1.1, with a VPN tunnel interface active), so this is a change in this machine's network path, not in the service. Both runs are in the table; the difference between Jev's latency and the measured network floor (65 to 85 ms) is the stable part. The practical reading is that Jev's single-call latency is "your round trip plus about 80 ms", and a hosted model is only as fast as the network in front of it.

SINGLE_TABLE

**Several questions on one state.** This is where the two architectures diverge. Jev ingests the state once and answers every question in parallel, so a request with 50 questions took 170 ms against 142 ms for one question. Laya runs each question as its own encoder pass over the full state, so latency grows almost linearly: 111 ms for 3 questions, 349 ms for 10, 1,002 ms for 50. The crossover is at about 3 to 4 questions per request, above which the hosted API is faster end-to-end than the local model on this hardware, and at 50 questions Jev is about 6x faster.

![Latency vs question count](results/charts/latency_multiq.png)

MULTIQ_TABLE

**Longer states.** Laya's latency rises from 50 to 104 ms as the state grows to about 400 tokens and then flattens, because its 512-token window (minus the question prefix) is full and the rest of the state is silently dropped. Jev's latency drifts from 138 to 183 ms across 50 to 6,400 tokens. The accuracy consequence of Laya's truncation is covered in the needle task below.

![Latency vs state length](results/charts/latency_statelen.png)

STATELEN_TABLE

**Throughput.** For many independent items (64 distinct messages, one question each) sequential Laya reaches 24 items/s. Jev at one request in flight manages 6 items/s, but the API accepts concurrent requests, so 8 in flight gives 44 items/s and 32 in flight gives 72 items/s, still under the published 1,200 requests/minute limit. The 16-concurrent point (42 items/s) landing below the 8-concurrent one is noise from two repeats of 64 items. For many questions on one state, Jev answered 50 questions in one 166 ms request (301 questions/s) against Laya's 50 questions/s at its default `batch_size=16`; raising Laya's `batch_size` to 64 was slower on this 18 GB machine (30 questions/s), the opposite of the README's M3 Max result.

![Throughput](results/charts/throughput.png)

TPUT_TABLE

**Wall-clock of the accuracy suite.** Running all 1,470 items with 6 requests in flight, Jev finished each task at 33 to 39 items/s (about 45 s for the whole suite). Sequential Laya took 90 to 135 ms per item on the three-question tasks and 27 to 112 ms on the two-question tasks.

TIMING_TABLE
