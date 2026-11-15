# Task environment: can the model actually do something?

Written 2026-11-15. Code in `taskenv/`. **Until the afternoon of 15 Nov this was test only. Since then it is
split by app: seven apps may be used for planner training data, three stay test apps (see "Planner mode and
the split by app"). Every result in the Results section below was measured before the split.**

Every earlier measurement in this project is one screenshot, one request, one point. This one
is the loop a screen assistant runs: the model sees the screen, emits one action, the action is
executed with real pointer and keyboard events, and this repeats until the model says it is done
or runs out of steps. Success is decided by the state of the app at the end, never by where the
model pointed.

<!-- RESULTS:BEGIN -->
## Results

State at 01:17 EST on 15 Nov 2026. Seed 9101 unless a row says more; runs are still in progress.

Reserved seeds only. "Tasks done" is decided by the state of the apps at the end. Intervals are 95% bootstrap intervals over tasks. Every run can be replayed step by step (see "Replay pages" below).

### Agent mode: the model chooses every action

| Model | Input | Tasks done | 95% interval | Done and said so | Episodes | Steps used (needed) | Seconds per step | Unreadable or invalid actions | Stopped by itself | Cut as stuck |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B (parent, full precision) | 1280 px | **34%** | 25% to 43% | 15% | 97 | 5.2 (2.1) | 1.5 | 22 of 502 (4%) | 24% | 14% |
| UI-Venus-2-9B (full precision) | 1280 px | **20%** | 12% to 28% | 5% | 97 | 6.0 (2.1) | 1.5 | 338 of 583 (58%) | 6% | 9% |
| Bonsai 2 9B, action-trained (v1, update 500) | 1280 px | **16%** | 10% to 25% | 1% | 97 | 5.1 (2.1) | 1.3 | 15 of 492 (3%) | 1% | 52% |
| Bonsai 2 4B, repaired + tool calls (tools-v1) | 1280 px | **5%** | 1% to 10% | 0% | 97 | 5.3 (2.1) | 1.6 | 190 of 510 (37%) | 0% | 39% |
| Bonsai 2 4B, action-trained (v1, update 500) | 1280 px | **4%** | 1% to 8% | 0% | 97 | 4.0 (2.1) | 1.5 | 13 of 390 (3%) | 0% | 66% |
| Bonsai 2 9B, repaired + tool calls (v3-tools) | 1280 px | **3%** | 0% to 7% | 0% | 97 | 6.1 (2.1) | 1.2 | 498 of 587 (85%) | 1% | 12% |
| Bonsai 2 9B, original | 1280 px | **1%** | 0% to 3% | 0% | 97 | 4.1 (2.1) | 1.3 | 7 of 400 (2%) | 4% | 66% |

### Guided mode: each step is given in words, the model only points

Tasks with nothing to do (already done, cannot be done) are not part of guided mode.

| Model | Runs on | Input | Aids | Tasks done | 95% interval | Episodes | Points inside the element | No point in the answer | Model seconds per point | Model seconds per step, all asks | Tokens read per look | Peak memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bonsai 2 9B, repaired (v3-gentle) | Mac mini M6, MLX | 1280 px | none | **75%** | 64% to 84% | 75 | 85% of 154 | 0 | 2.46 | 2.65 | 1090 | 5.89 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer | Mac mini M6, MLX | 1600 px | snap to element + second look when nothing changed (6 no, 6 retries) (2 points moved) | **73%** | 63% to 84% | 75 | 81% of 161 | 0 | 1.71 | 1.87 | 1603 | 3.31 GB |
| Bonsai 2 9B, repaired (v3-mixed896) | Mac mini M6, MLX | 1280 px | none | **73%** | 64% to 84% | 75 | 84% of 154 | 0 | 2.46 | 2.65 | 1090 | 5.89 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer | Mac mini M6, MLX | 1600 px | none | **71%** | 60% to 81% | 75 | 81% of 154 | 0 | 1.73 | 1.86 | 1640 | 3.3 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer | Mac mini M6, MLX | 1280 px | snap to element + second look when nothing changed (9 no, 9 retries) (6 points moved) | **65%** | 55% to 76% | 75 | 76% of 164 | 0 | 1.07 | 1.19 | 1068 | 3.25 GB |
| Bonsai 2 4B, repaired (v2-mixed) | Mac mini M6, MLX | 1280 px | second look when nothing changed (17 no, 17 retries) | **65%** | 55% to 76% | 75 | 73% of 172 | 0 | 1.44 | 1.68 | 1051 | 4.3 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer | Mac mini M6, MLX | 1600 px | snap to element + second look when nothing changed (8 no, 8 retries) (4 points moved) | **63%** | 52% to 73% | 75 | 71% of 163 | 0 | 1.68 | 1.85 | 1591 | 3.32 GB |
| Bonsai 2 4B, repaired (v2-mixed) | Mac mini M6, MLX | 1280 px | snap to element (7 points moved) | **61%** | 51% to 72% | 75 | 73% of 154 | 0 | 1.47 | 1.58 | 1090 | 4.3 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer | Mac mini M6, MLX | 1280 px | none | **60%** | 49% to 71% | 75 | 74% of 154 | 0 | 1.10 | 1.18 | 1090 | 3.24 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s4000), no written answer | Mac mini M6, MLX | 1280 px | snap to element + second look when nothing changed (6 no, 6 retries) (10 points moved) | **60%** | 48% to 71% | 75 | 76% of 161 | 0 | 1.10 | 1.22 | 1075 | 3.24 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer | Mac mini M6, MLX | 1600 px | none | **59%** | 48% to 69% | 75 | 70% of 154 | 0 | 1.70 | 1.84 | 1640 | 3.3 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer | Mac mini M6, MLX | 1280 px | snap to element + second look when nothing changed (15 no, 15 retries) (10 points moved) | **59%** | 47% to 69% | 75 | 69% of 170 | 0 | 1.37 | 1.57 | 1055 | 3.26 GB |
| Bonsai 2 4B, repaired (v2-mixed) | Mac mini M6, MLX | 1280 px | none | **57%** | 47% to 68% | 75 | 70% of 154 | 0 | 1.44 | 1.55 | 1090 | 4.3 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s4000), no written answer | Mac mini M6, MLX | 1280 px | none | **53%** | 43% to 64% | 75 | 72% of 154 | 0 | 1.12 | 1.20 | 1090 | 3.24 GB |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer | Mac mini M6, MLX | 1280 px | none | **53%** | 43% to 65% | 75 | 66% of 154 | 0 | 1.12 | 1.21 | 1090 | 3.24 GB |
| Bonsai 2 4B, repaired (v2-mixed) | Mac mini M6, MLX | 1280 px | snap to element + yes/no check, first version (72 no, 47 retries) (15 points moved) | **49%** | 37% to 60% | 75 | 66% of 207 | 0 | 1.44 | 3.37 | 1089 | 4.32 GB |
| Bonsai 2 4B, repaired (v2-mixed) | Mac mini M6, MLX | 1280 px | yes/no check (68 no, 44 retries) | **48%** | 37% to 59% | 75 | 66% of 205 | 0 | 1.46 | 3.40 | 1089 | 4.32 GB |
| Bonsai 2 4B v2-mixed, pointing decoder on 20 layers (s6000), no written answer | Mac mini M6, MLX | 1280 px | none | **44%** | 33% to 55% | 75 | 60% of 154 | 0 | 1.08 | 1.15 | 1090 | 3.27 GB |
| Bonsai 2 9B, original | Mac mini M6, MLX | 1280 px | none | **8%** | 3% to 15% | 75 | 19% of 154 | 12 | 3.07 | 3.27 | 1090 | 5.89 GB |
| Bonsai 2 4B, original | Mac mini M6, MLX | 1280 px | none | **3%** | 0% to 7% | 75 | 5% of 154 | 21 | 1.44 | 1.55 | 1090 | 4.3 GB |
| UI-Venus-2-9B (full precision) | pod, PyTorch | 1280 px | none | **98%** | 96% to 100% | 225 | 99% of 463 | 2 | 0.42 | 0.45 | 1090 | n/a |
| Qwen3.5-9B (parent, full precision) | pod, PyTorch | 1280 px | none | **93%** | 88% to 98% | 225 | 96% of 463 | 0 | 0.37 | 0.39 | 1090 | n/a |
| Bonsai 2 9B, repaired (v3-gentle) | pod, PyTorch | 1280 px | none | **78%** | 71% to 85% | 225 | 86% of 463 | 0 | 0.40 | 0.43 | 1090 | n/a |
| Bonsai 2 9B, repaired (v3-mixed896) | pod, PyTorch | 1280 px | none | **76%** | 68% to 83% | 225 | 83% of 463 | 0 | 0.37 | 0.39 | 1090 | n/a |
| Bonsai 2 9B, repaired (v2) | pod, PyTorch | 1280 px | none | **63%** | 52% to 73% | 75 | 71% of 154 | 0 | 0.36 | 0.39 | 1090 | n/a |
| Bonsai 2 4B, repaired (v2-mixed) | pod, PyTorch | 1280 px | none | **56%** | 46% to 64% | 225 | 68% of 463 | 0 | 0.37 | 0.39 | 1090 | n/a |
| Bonsai 2 9B, repaired (v3-mixed896) | pod, PyTorch | 896 px | none | **51%** | 39% to 61% | 75 | 68% of 154 | 0 | 0.37 | 0.39 | 594 | n/a |
| Bonsai 2 4B, repaired (v1) | pod, PyTorch | 1280 px | none | **48%** | 36% to 59% | 75 | 59% of 154 | 0 | 0.46 | 0.50 | nan | n/a |
| Bonsai 2 4B, repaired (v2-mixed) | pod, PyTorch | 896 px | none | **32%** | 21% to 43% | 75 | 47% of 153 | 1 | 0.45 | 0.48 | nan | n/a |
| Bonsai 2 9B, repaired (v3-gentle) | pod, PyTorch | 896 px | none | **32%** | 21% to 43% | 75 | 48% of 154 | 0 | 0.37 | 0.40 | 594 | n/a |
| Bonsai 2 9B, original | pod, PyTorch | 1280 px | none | **9%** | 5% to 14% | 225 | 17% of 463 | 40 | 0.33 | 0.36 | 1090 | n/a |
| Bonsai 2 4B, original | pod, PyTorch | 1280 px | none | **3%** | 0% to 7% | 75 | 4% of 153 | 24 | 0.46 | 0.50 | nan | n/a |

### The 4B on the tasks: written answers and the pointing decoder side by side

Guided mode on the Mac mini in MLX, seed 9101, 75 tasks. "Written" means the model generates "[x, y]" with all 32 layers; "decoder" means the small pointing decoder reads the state after layer 20 and no token is generated. On a screenshot that has already been read through layer 20, one more request costs the decoder 76 ms at 1280 px (74 ms at 896 px); reading the screenshot that far takes 520 ms plus 364 ms for the vision part (242 + 158 ms at 896 px). 

| Weights | Pointer | Input | Aids | Tasks done | 95% interval | Points inside the element | Model seconds per step, all asks |
|---|---|---|---|---|---|---|---|
| joint trunk + pointing decoder on 20 layers (s11000), no written answer | decoder | 1600 px | snap + second look | **55 of 75 (73%)** | 63% to 84% | 81% | 1.87 |
| joint trunk + pointing decoder on 20 layers (s11000), no written answer | decoder | 1600 px | none | **53 of 75 (71%)** | 60% to 81% | 81% | 1.86 |
| joint trunk + pointing decoder on 20 layers (s11000), no written answer | decoder | 1280 px | snap + second look | **49 of 75 (65%)** | 55% to 76% | 76% | 1.19 |
| repaired (v2-mixed) | written | 1280 px | second look | **49 of 75 (65%)** | 55% to 76% | 73% | 1.68 |
| joint trunk + pointing decoder on 20 layers (s7500), no written answer | decoder | 1600 px | snap + second look | **47 of 75 (63%)** | 52% to 73% | 71% | 1.85 |
| repaired (v2-mixed) | written | 1280 px | snap | **46 of 75 (61%)** | 51% to 72% | 73% | 1.58 |
| joint trunk + pointing decoder on 20 layers (s11000), no written answer | decoder | 1280 px | none | **45 of 75 (60%)** | 49% to 71% | 74% | 1.18 |
| joint trunk + pointing decoder on 20 layers (s4000), no written answer | decoder | 1280 px | snap + second look | **45 of 75 (60%)** | 48% to 71% | 76% | 1.22 |
| joint trunk + pointing decoder on 20 layers (s7500), no written answer | decoder | 1600 px | none | **44 of 75 (59%)** | 48% to 69% | 70% | 1.84 |
| joint trunk + pointing decoder on 20 layers (s7500), no written answer | decoder | 1280 px | snap + second look | **44 of 75 (59%)** | 47% to 69% | 69% | 1.57 |
| repaired (v2-mixed) | written | 1280 px | none | **43 of 75 (57%)** | 47% to 68% | 70% | 1.55 |
| joint trunk + pointing decoder on 20 layers (s4000), no written answer | decoder | 1280 px | none | **40 of 75 (53%)** | 43% to 64% | 72% | 1.20 |
| joint trunk + pointing decoder on 20 layers (s7500), no written answer | decoder | 1280 px | none | **40 of 75 (53%)** | 43% to 65% | 66% | 1.21 |
| repaired (v2-mixed) | written | 1280 px | snap + yes/no check, first version | **37 of 75 (49%)** | 37% to 60% | 66% | 3.37 |
| repaired (v2-mixed) | written | 1280 px | yes/no check | **36 of 75 (48%)** | 37% to 59% | 66% | 3.40 |
| v2-mixed, pointing decoder on 20 layers (s6000), no written answer | decoder | 1280 px | none | **33 of 75 (44%)** | 33% to 55% | 60% | 1.15 |
| original | written | 1280 px | none | **2 of 75 (3%)** | 0% to 7% | 5% | 1.55 |

### Reference agents

| Agent | Tasks done | Episodes |
|---|---|---|
| Scripted oracle (solves through the page) | 100% | 97 |
| Does nothing, says done | 10% | 291 |
| Random clicks | 0% | 291 |

### By kind of task

| Run | One click | Chain | Typing | Drag | Scroll to find | Menus | Shortcut | Already done | Cannot be done |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B (parent, full precision), agent, 1280 px | 67% (8/12) | 50% (8/16) | 58% (7/12) | 20% (2/10) | 11% (1/9) | 50% (6/12) | 17% (1/6) | 0% (0/10) | 0% (0/10) |
| UI-Venus-2-9B (full precision), agent, 1280 px | 50% (6/12) | 25% (4/16) | 17% (2/12) | 20% (2/10) | 0% (0/9) | 25% (3/12) | 33% (2/6) | 0% (0/10) | 0% (0/10) |
| Bonsai 2 9B, action-trained (v1, update 500), agent, 1280 px | 50% (6/12) | 31% (5/16) | 0% (0/12) | 0% (0/10) | 11% (1/9) | 8% (1/12) | 50% (3/6) | 0% (0/10) | 0% (0/10) |
| Bonsai 2 4B, repaired + tool calls (tools-v1), agent, 1280 px | 33% (4/12) | 6% (1/16) | 0% (0/12) | 0% (0/10) | 0% (0/9) | 0% (0/12) | 0% (0/6) | 0% (0/10) | 0% (0/10) |
| Bonsai 2 4B, action-trained (v1, update 500), agent, 1280 px | 25% (3/12) | 6% (1/16) | 0% (0/12) | 0% (0/10) | 0% (0/9) | 0% (0/12) | 0% (0/6) | 0% (0/10) | 0% (0/10) |
| Bonsai 2 9B, repaired + tool calls (v3-tools), agent, 1280 px | 17% (2/12) | 0% (0/16) | 0% (0/12) | 10% (1/10) | 0% (0/9) | 0% (0/12) | 0% (0/6) | 0% (0/10) | 0% (0/10) |
| Bonsai 2 9B, original, agent, 1280 px | 8% (1/12) | 0% (0/16) | 0% (0/12) | 0% (0/10) | 0% (0/9) | 0% (0/12) | 0% (0/6) | 0% (0/10) | 0% (0/10) |
| Bonsai 2 9B, repaired (v3-gentle), guided, 1280 px, MLX | 75% (9/12) | 69% (11/16) | 50% (6/12) | 80% (8/10) | 89% (8/9) | 92% (11/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided+snap+second look, 1600 px, MLX | 83% (10/12) | 69% (11/16) | 75% (9/12) | 60% (6/10) | 78% (7/9) | 75% (9/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 9B, repaired (v3-mixed896), guided, 1280 px, MLX | 75% (9/12) | 69% (11/16) | 58% (7/12) | 70% (7/10) | 89% (8/9) | 83% (10/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided, 1600 px, MLX | 67% (8/12) | 69% (11/16) | 75% (9/12) | 60% (6/10) | 78% (7/9) | 75% (9/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided+snap+second look, 1280 px, MLX | 83% (10/12) | 56% (9/16) | 50% (6/12) | 70% (7/10) | 78% (7/9) | 58% (7/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B, repaired (v2-mixed), guided+second look, 1280 px, MLX | 83% (10/12) | 56% (9/16) | 42% (5/12) | 70% (7/10) | 67% (6/9) | 83% (10/12) | 50% (2/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided+snap+second look, 1600 px, MLX | 50% (6/12) | 56% (9/16) | 83% (10/12) | 70% (7/10) | 67% (6/9) | 50% (6/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B, repaired (v2-mixed), guided+snap, 1280 px, MLX | 75% (9/12) | 50% (8/16) | 42% (5/12) | 70% (7/10) | 67% (6/9) | 75% (9/12) | 50% (2/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided, 1280 px, MLX | 67% (8/12) | 50% (8/16) | 50% (6/12) | 70% (7/10) | 78% (7/9) | 50% (6/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s4000), no written answer, guided+snap+second look, 1280 px, MLX | 75% (9/12) | 69% (11/16) | 50% (6/12) | 60% (6/10) | 67% (6/9) | 42% (5/12) | 50% (2/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided, 1600 px, MLX | 50% (6/12) | 50% (8/16) | 75% (9/12) | 70% (7/10) | 56% (5/9) | 50% (6/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided+snap+second look, 1280 px, MLX | 67% (8/12) | 62% (10/16) | 50% (6/12) | 50% (5/10) | 67% (6/9) | 50% (6/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B, repaired (v2-mixed), guided, 1280 px, MLX | 67% (8/12) | 44% (7/16) | 33% (4/12) | 70% (7/10) | 67% (6/9) | 75% (9/12) | 50% (2/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s4000), no written answer, guided, 1280 px, MLX | 58% (7/12) | 62% (10/16) | 42% (5/12) | 60% (6/10) | 56% (5/9) | 42% (5/12) | 50% (2/4) | n/a | n/a |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided, 1280 px, MLX | 58% (7/12) | 50% (8/16) | 50% (6/12) | 60% (6/10) | 44% (4/9) | 50% (6/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B, repaired (v2-mixed), guided+snap+check (first version), 1280 px, MLX | 75% (9/12) | 38% (6/16) | 25% (3/12) | 20% (2/10) | 56% (5/9) | 67% (8/12) | 100% (4/4) | n/a | n/a |
| Bonsai 2 4B, repaired (v2-mixed), guided+check, 1280 px, MLX | 67% (8/12) | 31% (5/16) | 33% (4/12) | 10% (1/10) | 67% (6/9) | 67% (8/12) | 100% (4/4) | n/a | n/a |
| Bonsai 2 4B v2-mixed, pointing decoder on 20 layers (s6000), no written answer, guided, 1280 px, MLX | 58% (7/12) | 31% (5/16) | 25% (3/12) | 40% (4/10) | 67% (6/9) | 58% (7/12) | 25% (1/4) | n/a | n/a |
| Bonsai 2 9B, original, guided, 1280 px, MLX | 17% (2/12) | 6% (1/16) | 8% (1/12) | 10% (1/10) | 0% (0/9) | 0% (0/12) | 25% (1/4) | n/a | n/a |
| Bonsai 2 4B, original, guided, 1280 px, MLX | 0% (0/12) | 0% (0/16) | 8% (1/12) | 0% (0/10) | 11% (1/9) | 0% (0/12) | 0% (0/4) | n/a | n/a |
| UI-Venus-2-9B (full precision), guided, 1280 px | 100% (36/36) | 98% (47/48) | 97% (35/36) | 93% (28/30) | 100% (27/27) | 100% (36/36) | 92% (11/12) | n/a | n/a |
| Qwen3.5-9B (parent, full precision), guided, 1280 px | 97% (35/36) | 90% (43/48) | 89% (32/36) | 80% (24/30) | 100% (27/27) | 100% (36/36) | 100% (12/12) | n/a | n/a |
| Bonsai 2 9B, repaired (v3-gentle), guided, 1280 px | 78% (28/36) | 77% (37/48) | 78% (28/36) | 80% (24/30) | 81% (22/27) | 81% (29/36) | 67% (8/12) | n/a | n/a |
| Bonsai 2 9B, repaired (v3-mixed896), guided, 1280 px | 75% (27/36) | 73% (35/48) | 67% (24/36) | 77% (23/30) | 85% (23/27) | 83% (30/36) | 67% (8/12) | n/a | n/a |
| Bonsai 2 9B, repaired (v2), guided, 1280 px | 58% (7/12) | 50% (8/16) | 50% (6/12) | 80% (8/10) | 78% (7/9) | 75% (9/12) | 50% (2/4) | n/a | n/a |
| Bonsai 2 4B, repaired (v2-mixed), guided, 1280 px | 58% (21/36) | 46% (22/48) | 47% (17/36) | 53% (16/30) | 67% (18/27) | 67% (24/36) | 58% (7/12) | n/a | n/a |
| Bonsai 2 9B, repaired (v3-mixed896), guided, 896 px | 75% (9/12) | 31% (5/16) | 42% (5/12) | 40% (4/10) | 56% (5/9) | 58% (7/12) | 75% (3/4) | n/a | n/a |
| Bonsai 2 4B, repaired (v1), guided, 1280 px | 67% (8/12) | 25% (4/16) | 42% (5/12) | 50% (5/10) | 67% (6/9) | 50% (6/12) | 50% (2/4) | n/a | n/a |
| Bonsai 2 4B, repaired (v2-mixed), guided, 896 px | 33% (4/12) | 38% (6/16) | 25% (3/12) | 30% (3/10) | 33% (3/9) | 33% (4/12) | 25% (1/4) | n/a | n/a |
| Bonsai 2 9B, repaired (v3-gentle), guided, 896 px | 42% (5/12) | 12% (2/16) | 33% (4/12) | 40% (4/10) | 33% (3/9) | 33% (4/12) | 50% (2/4) | n/a | n/a |
| Bonsai 2 9B, original, guided, 1280 px | 17% (6/36) | 4% (2/48) | 14% (5/36) | 3% (1/30) | 15% (4/27) | 0% (0/36) | 25% (3/12) | n/a | n/a |
| Bonsai 2 4B, original, guided, 1280 px | 0% (0/12) | 0% (0/16) | 8% (1/12) | 0% (0/10) | 11% (1/9) | 0% (0/12) | 0% (0/4) | n/a | n/a |
| Scripted oracle (solves through the page) | 100% (12/12) | 100% (16/16) | 100% (12/12) | 100% (10/10) | 100% (9/9) | 100% (12/12) | 100% (6/6) | 100% (10/10) | 100% (10/10) |
| Does nothing, says done | 0% (0/36) | 0% (0/48) | 0% (0/36) | 0% (0/30) | 0% (0/27) | 0% (0/36) | 0% (0/18) | 100% (30/30) | 0% (0/30) |
| Random clicks | 0% (0/36) | 0% (0/48) | 0% (0/36) | 0% (0/30) | 0% (0/27) | 0% (0/36) | 0% (0/18) | 0% (0/30) | 0% (0/30) |

### By number of steps the task needs

| Run | 0 | 1 | 2-3 | 4-5 | 6+ |
|---|---|---|---|---|---|
| Qwen3.5-9B (parent, full precision), agent, 1280 px | 0% (0/20) | 45% (10/22) | 41% (16/39) | 45% (5/11) | 40% (2/5) |
| UI-Venus-2-9B (full precision), agent, 1280 px | 0% (0/20) | 36% (8/22) | 23% (9/39) | 9% (1/11) | 20% (1/5) |
| Bonsai 2 9B, action-trained (v1, update 500), agent, 1280 px | 0% (0/20) | 32% (7/22) | 18% (7/39) | 9% (1/11) | 20% (1/5) |
| Bonsai 2 4B, repaired + tool calls (tools-v1), agent, 1280 px | 0% (0/20) | 18% (4/22) | 3% (1/39) | 0% (0/11) | 0% (0/5) |
| Bonsai 2 4B, action-trained (v1, update 500), agent, 1280 px | 0% (0/20) | 14% (3/22) | 3% (1/39) | 0% (0/11) | 0% (0/5) |
| Bonsai 2 9B, repaired + tool calls (v3-tools), agent, 1280 px | 0% (0/20) | 14% (3/22) | 0% (0/39) | 0% (0/11) | 0% (0/5) |
| Bonsai 2 9B, original, agent, 1280 px | 0% (0/20) | 5% (1/22) | 0% (0/39) | 0% (0/11) | 0% (0/5) |
| Bonsai 2 9B, repaired (v3-gentle), guided, 1280 px, MLX | n/a | 80% (16/20) | 72% (28/39) | 82% (9/11) | 60% (3/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided+snap+second look, 1600 px, MLX | n/a | 75% (15/20) | 74% (29/39) | 64% (7/11) | 80% (4/5) |
| Bonsai 2 9B, repaired (v3-mixed896), guided, 1280 px, MLX | n/a | 75% (15/20) | 72% (28/39) | 73% (8/11) | 80% (4/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided, 1600 px, MLX | n/a | 65% (13/20) | 74% (29/39) | 64% (7/11) | 80% (4/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided+snap+second look, 1280 px, MLX | n/a | 75% (15/20) | 56% (22/39) | 73% (8/11) | 80% (4/5) |
| Bonsai 2 4B, repaired (v2-mixed), guided+second look, 1280 px, MLX | n/a | 75% (15/20) | 72% (28/39) | 45% (5/11) | 20% (1/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided+snap+second look, 1600 px, MLX | n/a | 55% (11/20) | 67% (26/39) | 64% (7/11) | 60% (3/5) |
| Bonsai 2 4B, repaired (v2-mixed), guided+snap, 1280 px, MLX | n/a | 70% (14/20) | 67% (26/39) | 45% (5/11) | 20% (1/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided, 1280 px, MLX | n/a | 65% (13/20) | 56% (22/39) | 64% (7/11) | 60% (3/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s4000), no written answer, guided+snap+second look, 1280 px, MLX | n/a | 70% (14/20) | 51% (20/39) | 64% (7/11) | 80% (4/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided, 1600 px, MLX | n/a | 55% (11/20) | 62% (24/39) | 55% (6/11) | 60% (3/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided+snap+second look, 1280 px, MLX | n/a | 65% (13/20) | 51% (20/39) | 64% (7/11) | 80% (4/5) |
| Bonsai 2 4B, repaired (v2-mixed), guided, 1280 px, MLX | n/a | 65% (13/20) | 64% (25/39) | 36% (4/11) | 20% (1/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s4000), no written answer, guided, 1280 px, MLX | n/a | 60% (12/20) | 46% (18/39) | 64% (7/11) | 60% (3/5) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided, 1280 px, MLX | n/a | 60% (12/20) | 49% (19/39) | 55% (6/11) | 60% (3/5) |
| Bonsai 2 4B, repaired (v2-mixed), guided+snap+check (first version), 1280 px, MLX | n/a | 50% (10/20) | 54% (21/39) | 45% (5/11) | 20% (1/5) |
| Bonsai 2 4B, repaired (v2-mixed), guided+check, 1280 px, MLX | n/a | 45% (9/20) | 54% (21/39) | 45% (5/11) | 20% (1/5) |
| Bonsai 2 4B v2-mixed, pointing decoder on 20 layers (s6000), no written answer, guided, 1280 px, MLX | n/a | 55% (11/20) | 41% (16/39) | 45% (5/11) | 20% (1/5) |
| Bonsai 2 9B, original, guided, 1280 px, MLX | n/a | 15% (3/20) | 8% (3/39) | 0% (0/11) | 0% (0/5) |
| Bonsai 2 4B, original, guided, 1280 px, MLX | n/a | 0% (0/20) | 5% (2/39) | 0% (0/11) | 0% (0/5) |
| UI-Venus-2-9B (full precision), guided, 1280 px | n/a | 97% (58/60) | 97% (115/118) | 100% (31/31) | 100% (16/16) |
| Qwen3.5-9B (parent, full precision), guided, 1280 px | n/a | 88% (53/60) | 93% (110/118) | 100% (31/31) | 94% (15/16) |
| Bonsai 2 9B, repaired (v3-gentle), guided, 1280 px | n/a | 78% (47/60) | 80% (94/118) | 74% (23/31) | 75% (12/16) |
| Bonsai 2 9B, repaired (v3-mixed896), guided, 1280 px | n/a | 75% (45/60) | 76% (90/118) | 71% (22/31) | 81% (13/16) |
| Bonsai 2 9B, repaired (v2), guided, 1280 px | n/a | 65% (13/20) | 56% (22/39) | 91% (10/11) | 40% (2/5) |
| Bonsai 2 4B, repaired (v2-mixed), guided, 1280 px | n/a | 57% (34/60) | 60% (71/118) | 48% (15/31) | 31% (5/16) |
| Bonsai 2 9B, repaired (v3-mixed896), guided, 896 px | n/a | 65% (13/20) | 44% (17/39) | 55% (6/11) | 40% (2/5) |
| Bonsai 2 4B, repaired (v1), guided, 1280 px | n/a | 60% (12/20) | 49% (19/39) | 36% (4/11) | 20% (1/5) |
| Bonsai 2 4B, repaired (v2-mixed), guided, 896 px | n/a | 35% (7/20) | 38% (15/39) | 18% (2/11) | 0% (0/5) |
| Bonsai 2 9B, repaired (v3-gentle), guided, 896 px | n/a | 45% (9/20) | 23% (9/39) | 45% (5/11) | 20% (1/5) |
| Bonsai 2 9B, original, guided, 1280 px | n/a | 12% (7/60) | 10% (12/118) | 3% (1/31) | 6% (1/16) |
| Bonsai 2 4B, original, guided, 1280 px | n/a | 0% (0/20) | 5% (2/39) | 0% (0/11) | 0% (0/5) |
| Scripted oracle (solves through the page) | 100% (20/20) | 100% (22/22) | 100% (39/39) | 100% (11/11) | 100% (5/5) |
| Does nothing, says done | 50% (30/60) | 0% (0/66) | 0% (0/118) | 0% (0/31) | 0% (0/16) |
| Random clicks | 0% (0/60) | 0% (0/66) | 0% (0/118) | 0% (0/31) | 0% (0/16) |

### By app

| Run | browser | calculator | calendar | files | mail | music | notes | reminders | settings | sheet |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B (parent, full precision), agent, 1280 px | 33% (3/9) | 43% (3/7) | 10% (1/10) | 25% (3/12) | 55% (6/11) | 30% (3/10) | 44% (4/9) | 22% (2/9) | 55% (6/11) | 22% (2/9) |
| UI-Venus-2-9B (full precision), agent, 1280 px | 11% (1/9) | 29% (2/7) | 20% (2/10) | 33% (4/12) | 18% (2/11) | 40% (4/10) | 0% (0/9) | 0% (0/9) | 27% (3/11) | 11% (1/9) |
| Bonsai 2 9B, action-trained (v1, update 500), agent, 1280 px | 33% (3/9) | 14% (1/7) | 10% (1/10) | 25% (3/12) | 27% (3/11) | 10% (1/10) | 11% (1/9) | 0% (0/9) | 27% (3/11) | 0% (0/9) |
| Bonsai 2 4B, repaired + tool calls (tools-v1), agent, 1280 px | 11% (1/9) | 0% (0/7) | 0% (0/10) | 8% (1/12) | 0% (0/11) | 0% (0/10) | 11% (1/9) | 0% (0/9) | 18% (2/11) | 0% (0/9) |
| Bonsai 2 4B, action-trained (v1, update 500), agent, 1280 px | 0% (0/9) | 0% (0/7) | 0% (0/10) | 8% (1/12) | 0% (0/11) | 0% (0/10) | 11% (1/9) | 0% (0/9) | 18% (2/11) | 0% (0/9) |
| Bonsai 2 9B, repaired + tool calls (v3-tools), agent, 1280 px | 0% (0/9) | 0% (0/7) | 0% (0/10) | 8% (1/12) | 0% (0/11) | 20% (2/10) | 0% (0/9) | 0% (0/9) | 0% (0/11) | 0% (0/9) |
| Bonsai 2 9B, original, agent, 1280 px | 0% (0/9) | 0% (0/7) | 0% (0/10) | 0% (0/12) | 0% (0/11) | 10% (1/10) | 0% (0/9) | 0% (0/9) | 0% (0/11) | 0% (0/9) |
| Bonsai 2 9B, repaired (v3-gentle), guided, 1280 px, MLX | 83% (5/6) | 80% (4/5) | 62% (5/8) | 100% (10/10) | 78% (7/9) | 86% (6/7) | 86% (6/7) | 57% (4/7) | 56% (5/9) | 57% (4/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided+snap+second look, 1600 px, MLX | 100% (6/6) | 80% (4/5) | 62% (5/8) | 90% (9/10) | 78% (7/9) | 57% (4/7) | 86% (6/7) | 57% (4/7) | 67% (6/9) | 57% (4/7) |
| Bonsai 2 9B, repaired (v3-mixed896), guided, 1280 px, MLX | 83% (5/6) | 80% (4/5) | 50% (4/8) | 100% (10/10) | 67% (6/9) | 86% (6/7) | 86% (6/7) | 57% (4/7) | 67% (6/9) | 57% (4/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided, 1600 px, MLX | 100% (6/6) | 80% (4/5) | 50% (4/8) | 90% (9/10) | 78% (7/9) | 43% (3/7) | 86% (6/7) | 57% (4/7) | 67% (6/9) | 57% (4/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided+snap+second look, 1280 px, MLX | 83% (5/6) | 80% (4/5) | 62% (5/8) | 90% (9/10) | 56% (5/9) | 57% (4/7) | 71% (5/7) | 43% (3/7) | 67% (6/9) | 43% (3/7) |
| Bonsai 2 4B, repaired (v2-mixed), guided+second look, 1280 px, MLX | 83% (5/6) | 60% (3/5) | 62% (5/8) | 80% (8/10) | 56% (5/9) | 71% (5/7) | 57% (4/7) | 100% (7/7) | 67% (6/9) | 14% (1/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided+snap+second look, 1600 px, MLX | 67% (4/6) | 40% (2/5) | 50% (4/8) | 70% (7/10) | 56% (5/9) | 43% (3/7) | 100% (7/7) | 43% (3/7) | 89% (8/9) | 57% (4/7) |
| Bonsai 2 4B, repaired (v2-mixed), guided+snap, 1280 px, MLX | 83% (5/6) | 60% (3/5) | 50% (4/8) | 80% (8/10) | 44% (4/9) | 71% (5/7) | 57% (4/7) | 86% (6/7) | 67% (6/9) | 14% (1/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s11000), no written answer, guided, 1280 px, MLX | 83% (5/6) | 60% (3/5) | 50% (4/8) | 80% (8/10) | 56% (5/9) | 57% (4/7) | 71% (5/7) | 43% (3/7) | 56% (5/9) | 43% (3/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s4000), no written answer, guided+snap+second look, 1280 px, MLX | 83% (5/6) | 60% (3/5) | 50% (4/8) | 90% (9/10) | 56% (5/9) | 57% (4/7) | 57% (4/7) | 29% (2/7) | 78% (7/9) | 29% (2/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided, 1600 px, MLX | 67% (4/6) | 40% (2/5) | 50% (4/8) | 70% (7/10) | 56% (5/9) | 43% (3/7) | 86% (6/7) | 43% (3/7) | 67% (6/9) | 57% (4/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided+snap+second look, 1280 px, MLX | 83% (5/6) | 60% (3/5) | 50% (4/8) | 70% (7/10) | 44% (4/9) | 57% (4/7) | 71% (5/7) | 43% (3/7) | 78% (7/9) | 29% (2/7) |
| Bonsai 2 4B, repaired (v2-mixed), guided, 1280 px, MLX | 67% (4/6) | 60% (3/5) | 38% (3/8) | 80% (8/10) | 33% (3/9) | 71% (5/7) | 57% (4/7) | 86% (6/7) | 67% (6/9) | 14% (1/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s4000), no written answer, guided, 1280 px, MLX | 83% (5/6) | 60% (3/5) | 50% (4/8) | 80% (8/10) | 44% (4/9) | 57% (4/7) | 57% (4/7) | 29% (2/7) | 44% (4/9) | 29% (2/7) |
| Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s7500), no written answer, guided, 1280 px, MLX | 83% (5/6) | 40% (2/5) | 50% (4/8) | 70% (7/10) | 44% (4/9) | 43% (3/7) | 57% (4/7) | 43% (3/7) | 67% (6/9) | 29% (2/7) |
| Bonsai 2 4B, repaired (v2-mixed), guided+snap+check (first version), 1280 px, MLX | 67% (4/6) | 40% (2/5) | 62% (5/8) | 40% (4/10) | 11% (1/9) | 71% (5/7) | 57% (4/7) | 57% (4/7) | 56% (5/9) | 43% (3/7) |
| Bonsai 2 4B, repaired (v2-mixed), guided+check, 1280 px, MLX | 67% (4/6) | 60% (3/5) | 38% (3/8) | 50% (5/10) | 11% (1/9) | 71% (5/7) | 57% (4/7) | 57% (4/7) | 56% (5/9) | 29% (2/7) |
| Bonsai 2 4B v2-mixed, pointing decoder on 20 layers (s6000), no written answer, guided, 1280 px, MLX | 50% (3/6) | 40% (2/5) | 38% (3/8) | 60% (6/10) | 44% (4/9) | 57% (4/7) | 57% (4/7) | 43% (3/7) | 33% (3/9) | 14% (1/7) |
| Bonsai 2 9B, original, guided, 1280 px, MLX | 17% (1/6) | 20% (1/5) | 0% (0/8) | 40% (4/10) | 0% (0/9) | 0% (0/7) | 0% (0/7) | 0% (0/7) | 0% (0/9) | 0% (0/7) |
| Bonsai 2 4B, original, guided, 1280 px, MLX | 0% (0/6) | 20% (1/5) | 12% (1/8) | 0% (0/10) | 0% (0/9) | 0% (0/7) | 0% (0/7) | 0% (0/7) | 0% (0/9) | 0% (0/7) |
| UI-Venus-2-9B (full precision), guided, 1280 px | 100% (18/18) | 100% (15/15) | 100% (24/24) | 93% (28/30) | 100% (27/27) | 95% (20/21) | 100% (21/21) | 100% (21/21) | 96% (26/27) | 95% (20/21) |
| Qwen3.5-9B (parent, full precision), guided, 1280 px | 89% (16/18) | 93% (14/15) | 88% (21/24) | 100% (30/30) | 89% (24/27) | 86% (18/21) | 100% (21/21) | 100% (21/21) | 85% (23/27) | 100% (21/21) |
| Bonsai 2 9B, repaired (v3-gentle), guided, 1280 px | 94% (17/18) | 80% (12/15) | 62% (15/24) | 87% (26/30) | 81% (22/27) | 81% (17/21) | 86% (18/21) | 57% (12/21) | 78% (21/27) | 76% (16/21) |
| Bonsai 2 9B, repaired (v3-mixed896), guided, 1280 px | 83% (15/18) | 87% (13/15) | 54% (13/24) | 87% (26/30) | 74% (20/27) | 81% (17/21) | 81% (17/21) | 67% (14/21) | 74% (20/27) | 71% (15/21) |
| Bonsai 2 9B, repaired (v2), guided, 1280 px | 83% (5/6) | 40% (2/5) | 25% (2/8) | 90% (9/10) | 89% (8/9) | 71% (5/7) | 86% (6/7) | 14% (1/7) | 56% (5/9) | 57% (4/7) |
| Bonsai 2 4B, repaired (v2-mixed), guided, 1280 px | 89% (16/18) | 60% (9/15) | 38% (9/24) | 63% (19/30) | 52% (14/27) | 57% (12/21) | 71% (15/21) | 67% (14/21) | 52% (14/27) | 14% (3/21) |
| Bonsai 2 9B, repaired (v3-mixed896), guided, 896 px | 50% (3/6) | 40% (2/5) | 25% (2/8) | 90% (9/10) | 44% (4/9) | 57% (4/7) | 71% (5/7) | 43% (3/7) | 44% (4/9) | 29% (2/7) |
| Bonsai 2 4B, repaired (v1), guided, 1280 px | 83% (5/6) | 60% (3/5) | 25% (2/8) | 70% (7/10) | 11% (1/9) | 43% (3/7) | 71% (5/7) | 71% (5/7) | 56% (5/9) | 0% (0/7) |
| Bonsai 2 4B, repaired (v2-mixed), guided, 896 px | 67% (4/6) | 40% (2/5) | 12% (1/8) | 50% (5/10) | 22% (2/9) | 29% (2/7) | 71% (5/7) | 29% (2/7) | 11% (1/9) | 0% (0/7) |
| Bonsai 2 9B, repaired (v3-gentle), guided, 896 px | 50% (3/6) | 40% (2/5) | 12% (1/8) | 50% (5/10) | 22% (2/9) | 29% (2/7) | 43% (3/7) | 43% (3/7) | 11% (1/9) | 29% (2/7) |
| Bonsai 2 9B, original, guided, 1280 px | 22% (4/18) | 20% (3/15) | 12% (3/24) | 20% (6/30) | 0% (0/27) | 5% (1/21) | 14% (3/21) | 0% (0/21) | 4% (1/27) | 0% (0/21) |
| Bonsai 2 4B, original, guided, 1280 px | 0% (0/6) | 20% (1/5) | 12% (1/8) | 0% (0/10) | 0% (0/9) | 0% (0/7) | 0% (0/7) | 0% (0/7) | 0% (0/9) | 0% (0/7) |
| Scripted oracle (solves through the page) | 100% (9/9) | 100% (7/7) | 100% (10/10) | 100% (12/12) | 100% (11/11) | 100% (10/10) | 100% (9/9) | 100% (9/9) | 100% (11/11) | 100% (9/9) |
| Does nothing, says done | 11% (3/27) | 14% (3/21) | 10% (3/30) | 8% (3/36) | 9% (3/33) | 10% (3/30) | 11% (3/27) | 11% (3/27) | 9% (3/33) | 11% (3/27) |
| Random clicks | 0% (0/27) | 0% (0/21) | 0% (0/30) | 0% (0/36) | 0% (0/33) | 0% (0/30) | 0% (0/27) | 0% (0/27) | 0% (0/33) | 0% (0/27) |

Still running or stopped early (not in the tables): Bonsai 2 4B, action-trained (v1, update 500), agent, 896 px: 1 of 2 so far; Orchestrator Bonsai 2 9B (orch-u500) says the step, pointer 4b-decoder-s11000 finds it, agent+snap, 1280 px, MLX: 1 of 1 so far.

### Speed on the Mac mini (M6, 16 GB): ternary Bonsai against ordinary 4-bit and 8-bit builds of the same designs

One pointing answer on the same screenshot (11 tokens written), best of three, nothing else running. UI-Venus-2-9B has the parent's shape, so the 9B rows stand for it.

| Model | Seconds per answer, 1280 px | 896 px | Tokens read per second | Tokens written per second | Peak memory | Size on disk |
|---|---|---|---|---|---|---|
| Bonsai 2 9B (ternary) | 2.46 | 1.36 | 509 | 48 | 5.9 GB | 3.6 GB |
| Qwen3.5-9B, 4-bit | 2.00 | 1.21 | 688 | 33 | 7.1 GB | 6.0 GB |
| Qwen3.5-9B, 8-bit | 2.36 | 1.58 | 636 | 18 | 11.5 GB | 10.4 GB |
| Bonsai 2 4B (ternary) | 1.43 | 0.80 | 879 | 82 | 4.3 GB | 1.9 GB |
| Qwen3.5-4B, 4-bit | 1.15 | 0.69 | 1178 | 58 | 4.2 GB | 3.1 GB |

### Drafting head (the pack's MTP speculative decoding) on the Mac mini

Generated tokens per second, greedy, about 150 tokens; "same" means the text is identical to plain decoding. It works with mlx-vlm 0.7.8 as installed.

| Model | Weights | Output | Plain | Block 2 | Block 3 | Block 4 | Text identical |
|---|---|---|---|---|---|---|---|
| Bonsai 2 9B | original | tool call | 46 | 46.2 | 42.3 | 40.4 | yes |
| Bonsai 2 9B | original | reasoning | 45 | 46.8 | 41.1 | 36.8 | yes |
| Bonsai 2 9B | patched | tool call | 46 | 46.3 | 44.1 | 40.4 | yes |
| Bonsai 2 9B | patched | reasoning | 45 | 43.8 | 40.5 | 36.7 | yes |
| Bonsai 2 4B | original | tool call | 78 | 73.0 | 67.3 | 55.2 | yes |
| Bonsai 2 4B | original | reasoning | 78 | 70.6 | 64.2 | 55.7 | yes |
| Bonsai 2 4B | patched | tool call | 77 | 79.7 | 79.8 | 71.5 | yes |
| Bonsai 2 4B | patched | reasoning | 78 | 73.3 | 69.5 | 57.2 | yes |
<!-- RESULTS:END -->

## Planner mode and the split by app

Decided on 15 Nov 2026 to get planner training data in the hours that were left: the environment is split.

| | apps | tasks |
|---|---|---|
| training apps | files, settings, mail, notes, reminders, calendar, browser | 71 |
| test apps, never trained on | music, sheet, calculator | 26 |

On the training apps two task templates per app are held out as well (14: `browser.add_bookmark`,
`browser.book_appointment`, `calendar.move_event`, `calendar.new_event`, `files.missing_file`, `files.rename`,
`mail.already_flagged`, `mail.delete_old`, `notes.add_line`, `notes.new_note`, `reminders.already_completed`,
`reminders.reorder`, `settings.join_wifi`, `settings.slider_end`), and so are the seeds 9101 to 9103. Training
rows use seeds from 20001, training rollouts from 30001. After training two numbers are reported: the held-out
tasks on the training apps, and the test apps. The Results above (guided and agent mode on all 97 tasks) are
the "before" numbers of the older modes; nothing in them was trained on.

**Planner mode** (`taskenv/planmode.py`) is the assistant's format v1 (Planner.swift at e751270,
`weightlab/planner.py`): no screenshot; each turn the model gets the task, the apps, the front app, the steps
done so far and the front window as a numbered list of at most 80 controls, and answers with one `next_step`
call (open_app, open_url, click, double_click, right_click, type, key, menu, scroll, drag, look, done).

- The control list is read from the page: the pressable and editable elements of the front window that are in
  view, then the items of an open menu. A control's name is its own text, a field's placeholder or the label of
  its row, and for an icon-only button the name of what it does. The same rule reads the test apps; their code
  is not touched.
- `planmode.execute` carries a step out with real pointer and keyboard events: `open_app` through the Dock,
  `menu` by walking the menu bar by names, `type` with an id clicks the field first, `scroll` turns the largest
  scrolling box of the front window by most of a page.
- `look` and the end of a `drag` cannot be resolved from names. With `--pointer-model` a pointer finds them on a
  screenshot. Without one the harness stands in as a perfect pointer, but only when the oracle's own step from
  that state is the same kind of step. So the planner numbers below measure planning; pointing is measured in
  guided mode.

**Training rows** (`python -m taskenv.plan_gen`): the oracle's solution of a task is translated step by step
into `next_step` answers (a menu-bar click and its items become one `menu`, a click on a field and the typing
become one `type`, an address typed into the browser becomes `open_url`, a click through the Dock becomes
`open_app`, a reveal becomes `scroll`). Then the episode is played again from the recorded answers through
`execute` alone; it is kept when the checker accepts both runs. Long tasks are chains of two or three tasks in
different training apps, joined into one request ("…. Then …. Finally, …"), with both checkers applied. One
task in two starts with its app in front; otherwise the app is closed or behind another, so the first step is
`open_app`. 8% of clicks have their control left out of the list, so that the right answer is `look`.

**Rollouts** (`python -m taskenv.plan_run`): a model runs in this format; a step that changes nothing gets
" (nothing changed)" in "Done so far", as in the app. Each turn records what the model saw and answered and the
oracle's step from that state, when the state is one the oracle's own run passes through or the goal is already
reached. An episode ends at `done`, after twice the oracle's steps plus three (at most 15), or after the same
step three times with no effect. The verdict is the state checker's, and the model must say `done`. With the
oracle as the model the harness scores 42 of 42 on the held-out tasks and 78 of 78 on the test apps.

Options: `--system-file` runs another system text (`taskenv/prompts/`); `--app-rules` adds the two rules of the app's
own loop (Return is not pressed right after a step that pressed it; a click or look without effect is done once
more before it is marked). With `--app-rules` the oracle fails `calendar.new_event`: the click on the empty slot
works but does not change the list, so the repeated click disturbs the new event. `python -m taskenv.plan_tally
<run> <run>` prints runs side by side with the failure tallies. A Bonsai 9B needs about 42 GB of GPU memory while
it loads (it folds its weights once) and 27 GB afterwards; `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`
lowers the peak a little, and a run waits and asks again when the shared GPU is full during a step.

Not built: an oracle for states off its own path. After a wrong turn the rollout has no label; trying the rest of
the oracle's steps from the reached state in a second browser, and keeping the longest tail the checker accepts,
would label those states too.

<!-- PLANNER:BEGIN -->
### Planner mode: before and after training on simulator rows

All three reserved seeds (9101 to 9103), 120 episodes a model: the 14 held-out task templates of the training apps
(42 episodes) and the 26 tasks of the test apps (78 episodes). Lane 5, text only, no pointer model, shipped system
text. Success = the state checker accepts the end state and the model said `done`.

| model | held-out tasks on training apps (42) | test apps (78) | all (120) | does the oracle's step in known states |
|---|---|---|---|---|
| oracle through the harness (ceiling) | 42 | 78 | 120 | |
| parent Qwen3.5-9B | 4 = 10% (95% 4 to 22) | 5 = 6% (3 to 14) | 9 | 19% of 347 |
| Bonsai 9B + orchestrator u3000 (the planner before these rows) | 1 = 2% (0 to 12) | 2 = 3% (1 to 9) | 3 | 15% of 324 |
| Bonsai 9B + point-v3-mixed896 (the tuned pointer, used as planner) | 0 = 0% (0 to 8) | 1 = 1% (0 to 7) | 1 | 12% of 344 |
| Bonsai 9B + planpoint-v1-u500 (500 updates on the first 13,241 oracle turns and rule-built turns) | 11 = 26% (15 to 41) | 10 = 13% (7 to 22) | 21 | 22% of 326 |
| Bonsai 9B + planpoint-v1-u1500 (1,500 updates; **the planner that ships**) | 12 = 29% (17 to 44) | 15 = 19% (12 to 29) | 27 | 27% of 289 |
| Bonsai 9B + planpoint-v1-dagger2-u1000 (u1500 plus 1,000 updates with the round-1 rollout turns) | 11 = 26% (15 to 41) | 15 = 19% (12 to 29) | 26 | 26% of 312 |

How the failed episodes ended:

| model | failed | same no-effect step three times | never said `done` | wrong result | out of steps |
|---|---|---|---|---|---|
| parent | 111 | 54 | 34 | 7 | 16 |
| orchestrator u3000 | 117 | 67 | 38 | 3 | 9 |
| point-v3-mixed896 | 119 | 63 | 35 | 2 | 19 |
| planpoint-v1-u500 | 99 | 54 | 22 | 17 | 6 |
| planpoint-v1-u1500 | 93 | 33 | 20 | 37 | 3 |
| planpoint-v1-dagger2-u1000 | 94 | 28 | 19 | 41 | 6 |

What this says. Before these rows no model finished long tasks in this format (1 to 9 of 120). Training on the
oracle's turns took the Bonsai 9B from 3 to 27 of 120; the gain holds on apps it never saw (2 to 15 of 78), though
it is smaller there than on new tasks in known apps. More updates turned stuck episodes into finished ones and into
ones that say `done` too early ("wrong result" grows from 17 to 37). The DAgger patch and u1500 are level: paired,
25 episodes are solved by both, 2 only by u1500, 1 only by the DAgger patch. One round of 501 rollout states did
not cure `done` too early. The trained patches answer in about 1 to 1.5 s a step on the pod.

Seed 9101 alone (the first numbers reported, 40 episodes): parent 2 and 2, orchestrator u3000 0 and 1,
point-v3-mixed896 0 and 0, u500 5 and 4.

### A longer system text does not replace training

A candidate system text (`taskenv/prompts/planner_system_candidate1.txt`: seven numbered rules,
among them "never repeat the last step" and "say done when Done so far covers the task") had taken orchestrator
u3000 from 51% to 77% fully right on 91 single turns. On whole tasks, same 40 episodes, only the system text
changed, app loop rules off:

| orchestrator u3000 with | held-out (14) | test apps (26) | stuck / never done / wrong / out of steps | said `done` | no-effect steps | agrees with the oracle |
|---|---|---|---|---|---|---|
| shipped system text | 0 | 1 | 23 / 12 / 2 / 2 | 3 episodes | 135 of 205 | 16 of 109 |
| candidate system text | 1 | 0 | 19 / 13 / 5 / 2 | 6 episodes | 117 of 189 | 17 of 106 |

One task of 40 either way. The trained patch does not care either: `planpoint-v1-u500` solves 5 of 14 and 4 of 26
with the shipped text and 5 of 14 and 4 of 26 with the candidate text (six different tasks; failures 16 / 8 / 6 / 1
against 18 / 8 / 4 / 1).

### Rollout round 1 (for the DAgger pass)

`planpoint-v1-u500` on fresh episodes of the training apps (seeds 30001 up; single tasks and chains mixed): 154
episodes in 37 minutes, 23 accepted by the checker (15%). `turns_rollout.jsonl`: 501 turns labelled with the
oracle's step from the state the model reached (the model did the same on 240). `turns_success.jsonl`: 109 turns
from the accepted episodes. Of the 131 failures 63 were a wrong result (mostly `done` said too early), 57 a
repeated no-effect step, 8 never said `done`, 3 ran out of steps.

### Rollout round 2

`planpoint-v1-u1500` (seeds 31001 up, two processes, 07:22 to 07:46 EST): 270 episodes, 68 accepted (25%).
`turns_rollout.jsonl`: 1,119 labelled turns (the model did the oracle's step on 680, 61%); `turns_success.jsonl`:
384 turns. Failures: 129 wrong result, 64 repeated no-effect step, 4 never said `done`, 5 out of steps.

### Planner rows made

`~/bonsai/data/mac/planner_sim_s1/` on the Spark. `turns_sim_train.jsonl`: 87,348 turns from 15,000 episodes
(seeds 20001, 21001 and 22001 up; 5,700 single tasks, 7,000 chains of two, 2,300 chains of three), every one
accepted by the checker on the oracle run and on the replay; none was skipped. The first 13,241 turns (2,440
episodes) were ready at 05:50 EST and are what the first planner patch trained on; the rest by 06:55.
The third batch adds verb synonyms and politeness wrappers inside chains. `turns_sim_held_out.jsonl`: 128 turns
from the 14 held-out templates on seeds 9101 to 9103, split "dev", for scoring only.
<!-- PLANNER:END -->

## What is measured

- **97 tasks in ten apps**: Files, Mail, Calendar, Notes, Reminders, Music, Browser (Safari
  style, with forms), Sheets, Calculator and System Settings. Each app is a web page written
  for this test and shown inside a macOS-style desktop (menu bar, Dock, windows with traffic
  lights, a wallpaper, sometimes a second app's window behind the first), 1440 x 900 points at
  device scale 2, so a screenshot is 2880 x 1800 like a MacBook's.
- **A task** is a start state built from a seed (names, order, contents, window position and
  wallpaper all change with the seed), a request as a person would say it ("Move
  budget-2026.xlsx into the Archive folder."), a checker on the app's state, and a step limit.
- **Kinds of task** (each task has one label):

| Kind | Tasks | What it takes |
|---|---|---|
| One click | 12 | A single click or double click |
| Chain | 16 | Two to eight steps in the right order |
| Typing | 12 | Text into the right field, then confirm or send |
| Drag | 10 | A file into a folder, a row to another place, a slider to a value, an event to another day |
| Scroll to find | 9 | The target is out of view at the start |
| Menus | 12 | The menu bar or a right-click menu, sometimes a submenu |
| Shortcut | 6 | The solution uses a key combination (other routes count if the state is right) |
| Already done | 10 | The request is already satisfied: stop, change nothing |
| Cannot be done | 10 | What the request names does not exist: say so, change nothing |

- **The checker** reads the apps' state after the last step and requires two things: the
  thing asked for is true, and nothing else changed in any app (a second email archived, a
  file renamed on the way, a setting flipped: all fail). Typed text is compared without regard
  to case, repeated spaces and a final full stop.
- **Seeds.** 1 to 5 are for development (tasks, prompts, harness). 9101, 9102 and 9103 are
  reserved for reported runs; no prompt or rule was tuned on them.

## How a model is run

**Agent mode** is the test that matters: the model gets the screenshot, the request and its
own previous actions as text, and writes one `computer_use` call (the schema of
[ACTION_FORMAT.md](ACTION_FORMAT.md): click, double click, right click, drag with both ends,
type, key, scroll, wait, terminate with success or failure). The parser, the tool definition
and the history lines are the ones of `weightlab/actions.py`, so the test asks exactly what
action training teaches. The episode ends when the model calls `terminate`, when the step limit
is reached (one and a half times the steps of the scripted solution, plus three), or when the
model has written the same action three times in a row on an unchanged screen.

- An "already done" task counts only if the model stops with `terminate success` and nothing
  changed; a "cannot be done" task only with `terminate failure` and nothing changed.
- For the other tasks the state decides. Whether the model also stopped by itself is reported
  next to it ("done and said so"): an assistant that finishes the job and then keeps clicking
  is not finished.
- An answer that is not a readable `computer_use` call costs the step.

**Guided mode** isolates pointing inside the loop. The task's own solution is read to the
model one step at a time ("Click the Archive button in the Mail toolbar") and the model only
answers with a point; typing, key presses and scrolling are executed as written. A wrong point
is not corrected: the next step is asked on whatever screen results. This runs with the
pointing models as they are today. Tasks with nothing to point at are left out.

**Reference agents.** The scripted oracle executes each task's solution through the page with
the same pointer and keyboard events and must pass everything; it runs again before the models
on the machine that runs them, and its action count is the "steps needed" of each episode. The
agent that does nothing and the random clicker are the floors.

Input size: the 2880 x 1800 screenshot is shrunk to 1280 px (or 896 px) on its longer side
before the model sees it, as in the pointing benchmark. Decoding is greedy. The models are
loaded by `bench/models.py`, so any model the benchmark can load can be run here.

## Limits, stated plainly

- **These are web replicas, not macOS.** They look and behave like the real apps for the
  things the tasks need, and a great deal is missing: no real file system, no windows that
  resize, no Mission Control, no system dialogs, no animations, a clean font rendering (Inter,
  not San Francisco), and far fewer controls than the real apps have. A model that passes here
  has shown it can run the loop on Mac-like screens; it has not shown it can operate a Mac.
  `taskenv/real_mac_tasks.md` lists fifteen tasks in real macOS apps for a later supervised run.
- **The pointer is not drawn** in the screenshots, as in ordinary macOS screenshots.
- **97 tasks is a small set.** The 95% intervals in the tables are about plus or minus ten
  points for one seed; differences inside that are noise. Categories have 6 to 16 tasks, so a
  single category moves by one task at a time.
- **One protocol per mode.** Agent mode shows the model only the current screenshot and a text
  history; a model that needs to see earlier screenshots, or to think before it acts, is not
  given the chance. The prompt was written once on the development seeds and not tuned per
  model.
- **The scroll amount** in the action schema is a number of wheel clicks in some harnesses and
  a distance in others; values up to 30 are read as clicks of 60 points, larger ones as points.
- **Greedy decoding** makes a stuck model stay stuck; the cut after three identical actions on
  an unchanged screen saves time and cannot turn a failure into a success.
- **The apps were written by this project** for this test in one night. The oracle proves
  every task can be solved and every checker can pass; it does not prove that a checker never
  passes a wrong outcome, although each was also tried against wrong outcomes and against the
  agent that does nothing.

## Running it

    # the oracle and the environment's own checks (no GPU)
    python -m taskenv.selftest
    python -m taskenv.run --agent oracle --seeds test --out runs/oracle-test

    # a model (on a GPU machine)
    python -m taskenv.run --agent guided --model bonsai9b-new --patch export/patches/<patch> --tag <name> \
        --input s1280 --seeds 9101 --needed-from runs/oracle-test/episodes.jsonl --out runs/guided-<name>-s1280
    python -m taskenv.run --agent agent --model qwen35-9b --input s1280 --seeds 9101 \
        --needed-from runs/oracle-test/episodes.jsonl --out runs/agent-qwen35-9b-s1280

    # tables and replay pages
    python -m taskenv.report --runs <runs folder> --out taskenv/results
    python -m taskenv.viewer --runs <runs folder>

Every step of every episode is saved (`episodes.jsonl`: raw model output, parsed action,
seconds, error; `shots/`: the screenshot before each step and after the last). The replay
pages show them step by step.
