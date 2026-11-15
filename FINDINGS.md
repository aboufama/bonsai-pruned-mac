# Findings

Everything measured so far, with the conditions it was measured under. Dated 2026-11-14 unless noted. Small-sample results are marked as such; treat differences of a few points on 40 samples as noise.

## 1. Pointing (GUI grounding)

### Method

- Model served by PrismML's llama.cpp fork (`llama-server`) on the Spark, vision file loaded, `--image-max-tokens 16384` so screenshots are not shrunk.
- Prompt: the Qwen3.5 family's grounding prompt, taken from UI-Venus's reference evaluator. The model answers `[x,y]` in coordinates normalised to 0-1000.
- Thinking off, temperature 0. A hit means the point lies inside the annotated box.
- Bonsai files: `PTQ1_0` packing with the `BF16` vision file. References: `Q8_0` GGUF with `BF16` vision file.
- Script: `spark/eval_ground.py`.

### ScreenSpot-Pro (4K professional applications), 40 evenly spaced samples

| Model | Hits | Icon targets | Text targets | Published (full set) |
|---|---|---|---|---|
| UI-Venus-2-9B | 29/40 (72%) | 7/14 | 22/26 | 73.0 |
| Qwen3.5-9B | 24/40 (60%) | 3/14 | 21/26 | 65.2 |
| Bonsai 2 27B | 8/40 (20%) | 0/14 | 8/26 | none |
| Bonsai 2 9B | 1/40 | 0/14 | 1/26 | none |
| Bonsai 2 4B | 1/40 | 0/14 | 1/26 | none |
| Bonsai 2 2B | 1/40 | 0/14 | 1/26 | none |

Both references land near their published scores, so the harness is sound.

### ScreenSpot-v2 (ordinary desktop, mobile and web screens), 150 evenly spaced samples

| Model | Hits | Desktop | Mobile | Web | Icon targets | Text targets |
|---|---|---|---|---|---|---|
| Qwen3.5-9B | 143/150 (95.3%) | 100% (n=40) | 96.6% (n=59) | 90.2% (n=51) | 91.1% (n=56) | 97.9% (n=94) |
| Bonsai 2 9B | 78/150 (52.0%) | 42.5% | 72.9% | 35.3% | 48.2% | 54.3% |

UI-Venus was still running on this set when this was written.

### Is it the weights or the runtime?

Same 18 ScreenSpot-Pro screenshots (those at or below 2560x1600):

| Setup | Hits |
|---|---|
| Qwen3.5-9B, llama.cpp on the Spark | 12/18 |
| Bonsai 9B, llama.cpp on the Spark (`PTQ1_0` GGUF) | 0/18 |
| Bonsai 9B, MLX on the Mac (2-bit MLX pack, `mlx-vlm` 0.7.8) | 0/18 |

The two Bonsai runtimes returned the same coordinates on most samples (for example `[492, 726]` from both, target box `[372, 824, 468, 836]`). Two independent runtimes and two file formats agreeing means the fault is in the weights.

### What the failure looks like

- **Right neighbourhood, wrong spot.** Median distance from the target centre on ScreenSpot-Pro was 125 units on the 0-1000 scale; 5 of 39 answers were within 30 units.
- **Collapsed digits.** Last digit of every coordinate the model wrote (40 samples, 80 values):

| Model | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | 12 | 9 | 5 | 11 | 5 | 4 | 4 | 11 | 9 | 8 |
| Bonsai 9B | 17 | 0 | 8 | 5 | 1 | 1 | 29 | 1 | 15 | 1 |

- **Bigger is less broken.** The 27B is the only Bonsai above 1/40.
- **Resolution matters.** At ordinary resolutions the 9B gets about half of ScreenSpot-v2; on 4K screens with tiny targets it gets almost nothing.
- **Icons are hard for everyone.** Even the references score far lower on icon targets than on text targets.

### Not in PrismML's own evaluation

PrismML's whitepaper tests vision with question answering, chart reading, OCR and document parsing, where answers are words. None requires exact coordinates. Its weakest vision result, document parsing (about 83% retention), is the closest relative of this failure.

## 2. Tool calling

### Our seeded benchmark (`bench/toolcall/`, dev split, seed 20261114, 400 cases)

Generated from scratch, so no model can have seen it. Served by llama.cpp with thinking off; a model that never calls a tool scores exactly 25.0%.

| Category | Bonsai 2 9B (`PTQ1_0`) | Qwen3.5-9B (`Q8_0`) |
|---|---|---|
| Single call | 50/50 | 49/50 |
| Choosing among tools | 50/50 | 48/50 |
| Parallel calls | 45/50 | 50/50 |
| Multi-step chains | 43/50 | 47/50 |
| A required value is missing (should ask) | 13/50 | 18/50 |
| No tool applies (should not call) | 50/50 | 49/50 |
| Argument types and formats | 45/50 | 49/50 |
| Computer-use actions (from an element list) | 43/50 | 46/50 |
| **Overall** | **339/400 = 84.8%** | **356/400 = 89.0%** |

Reading: tool calling survived the ternary conversion far better than pointing did. Bonsai is about 4 points behind its parent. Each category has 50 cases, so single categories are plus or minus about 6 points.

Where both models fail:

- **They invent a missing value instead of asking** (37 of Bonsai's 61 failures, 32 of Qwen's 44): asked for a forecast with no city, Qwen filled in "New York".
- **Picking from a returned list**: Bonsai gets 8 of 12 on four-step chains that include a list result and once invented an id.
- **Neither scrolls**: when the target is below the fold, Bonsai is 0/5 and Qwen 1/5.
- **Relative dates across a boundary** ("the 20th of next month" on 18 December).

Open: 12 of the 400 cases used a correction phrase (", or rather") that reads as a choice inside a question; it was replaced afterwards, and those 12 have not been re-run. Without them the scores are 84.5% and 89.4%. Bonsai 2B and 4B have not been run.

### PrismML's published numbers

For the 9B against Qwen3.5-9B: BFCL v3 71.8 vs 73.8, BFCL v4 Mobile 78.0 vs 82.0, tau2-Bench 73.0 vs 85.3. The same picture: a few points behind, not broken.

## 3. Speed

### DGX Spark, idle GPU, llama.cpp fork with CUDA, `PTQ1_0`

| Model | Generation, one request | Prompt processing | 8 requests at once (total) | 32 at once (total) |
|---|---|---|---|---|
| 2B | 383 tok/s | 9,202 tok/s | 975 | 1,416 |
| 4B | 187 tok/s | 4,389 tok/s | 448 | 623 |
| 9B | 109 tok/s | 3,011 tok/s | 331 | 544 |
| 27B | 36.6 tok/s | 985 tok/s | 111 | 190 |

"One request" is `llama-bench` (tg128, pp512). The simultaneous-request columns were measured with all four models loaded at once (about 23 GB), each loaded in turn. With other jobs holding the GPU at 95%, generation dropped to 64, 47, 33 and 13 tok/s.

### 13-inch M4 MacBook, 16 GB

| Setup | Generation |
|---|---|
| LM Studio, GGUF `Q2_0`: 2B / 4B / 9B / 27B | about 90 / 45 / 28 / 10 tok/s |
| LM Studio, 9B MLX pack | 24 tok/s |
| llama.cpp fork, 9B `PQ2_0`, plain decoding | 27.6 to 30.1 tok/s |
| Same with the built-in draft head (speculative decoding) | 10 to 19 tok/s (slower) |
| Browser, WebGPU, 2B community ONNX conversion | 9 to 25 tok/s (measured in a throttled background tab) |

The 27B loads on 16 GB but pushes swap to about 4.3 of 5 GB.

### Evaluation throughput

Full-resolution ScreenSpot-Pro takes about 8 seconds per sample for a 9B model with 8 parallel slots, so a full 1,581-sample run is about 3.5 hours. This is the main drag on iteration speed.

## 4. The weight format

Bonsai's MLX pack can be read without MLX and folded into a standard dense checkpoint. Checks on one full layer against MLX: unpacking difference 0, rotation difference 0, end-to-end layer output difference 2.7e-7. Codes are exactly ternary (roughly a third each of -1, 0, +1). Details in [docs/WEIGHTS.md](docs/WEIGHTS.md).

## 5. Published context

Average over the 13 benchmarks that every Bonsai 2 size and reference shares (PrismML's numbers, our averaging): Bonsai 27B 84.0 (5.93 GB) vs Qwen3.8-27B 85.5 (53.8 GB); Bonsai 9B 78.5 (2.0 GB) vs Qwen3.5-9B 81.3 (17.9 GB); Bonsai 4B 75.6 vs 78.3; Bonsai 2B 63.4 vs 63.6. On those tests the ternary models hold up well, which is why the pointing collapse is surprising.

## 6. Where the damage is (weight lab, 2026-11-14)

All on 32 evenly spaced ScreenSpot-v2 screens at 1280 px unless noted. `p_hit` is the teacher-forced probability that every digit of the answer is acceptable (see [docs/WEIGHTLAB.md](docs/WEIGHTLAB.md)); it is deterministic, unlike the server-based runs.

### Bonsai against its parent, digit by digit

| | p_hit | Hundreds digit acceptable | Tens | Units |
|---|---|---|---|---|
| Parent (Qwen3.5-9B) | 0.707 | 0.876 | 0.937 | 1.000 |
| Bonsai 2 9B | 0.255 | 0.609 | 0.715 | 1.000 |

The error is in coarse-to-medium position, not the last digit. Coordinates are tokenised one digit per token.

### The weights themselves

- All 333 vision tensors (encoder and merger) are byte-identical to the parent's.
- Every ternary projection has relative error about 0.50 and cosine about 0.87 against the parent's, uniform over depth (about 30 degrees per row). 32.8% of codes are zero.
- The small full-precision parts were retrained: normalisation weights differ by 10 to 17%, the linear-attention gate projections by 19 to 32%.

### Activations

Relative distance between Bonsai's and the parent's residual stream is 0.1 to 0.3 for the first six layers, jumps to about 1.1 at the seventh layer, stays near 1.0 until about layer 19, then falls to about 0.65. Restoring the seventh layer alone does not help, so the jump is a property of how the ternary model was trained, not the fault itself.

### Swapping parent weights into Bonsai

| Given the parent's weights | p_hit |
|---|---|
| Nothing (Bonsai) | 0.255 |
| All 32 layers | 0.747 |
| Output head | 0.284 |
| Full attention v, o | 0.290 |
| Full attention q, k | 0.137 |
| All MLPs | 0.078 |
| Small full-precision parts only | 0.070 |
| Linear-attention projections | 0.051 |
| Any single layer | 0.09 to 0.29 |

| Bottom-up: parent layers 0..k, Bonsai above | p_hit | Top-down: Bonsai below, parent layers k..31 | p_hit |
|---|---|---|---|
| 0..3 | 0.250 | 28..31 | 0.228 |
| 0..7 | 0.229 | 24..31 | 0.229 |
| 0..11 | 0.294 | 20..31 | 0.243 |
| 0..15 | 0.438 | 16..31 | 0.309 |
| 0..19 | 0.725 | 12..31 | 0.419 |
| 0..23 | 0.733 | 8..31 | 0.611 |
| 0..27 | 0.736 | 4..31 | 0.712 |

Reading: single pieces do not transplant, because Bonsai's matrices are co-adapted. Bonsai's last 12 layers read the answer out correctly when given the parent's state, and its first 4 layers hand the parent's layers a usable state.

### A middle block only (experiment 002)

Bonsai keeps its own first and last layers; only the named block uses 16-bit weights from the parent (Qwen3.5-9B) or from UI-Venus-2-9B. Layer numbers are 0-based.

| Block replaced | From the parent | From UI-Venus | Weights in the block |
|---|---|---|---|
| none (Bonsai) | 0.255 | 0.255 | |
| 4..19 | **0.692** | not measured | 3.46 B |
| 8..19 | 0.531 | **0.608** | 2.59 B |
| 12..23 | 0.416 | 0.421 | 2.59 B |
| 12..19 | 0.259 | 0.277 | 1.73 B |
| 8..15 | 0.240 | 0.246 | 1.73 B |
| 10..17 | 0.181 | 0.192 | 1.73 B |
| 14..19 | 0.247 | 0.262 | 1.29 B |
| 16..19 | 0.249 | 0.290 | 0.86 B |
| 12..15 | 0.182 | 0.181 | 0.86 B |

Reading:

- **The whole fault is in layers 4..19.** With the parent's layers there and everything else Bonsai's, p_hit is 0.692 against the parent's own 0.707.
- **It is not one small region.** No block of 8 layers or fewer helps; 12 layers recover about half to three quarters; all 16 are needed for the rest. The block has to be repaired as a whole.
- **UI-Venus is the better donor** wherever a block helps (8..19: 0.608 against 0.531), so it is the teacher for the repair.

The run was cut short, when the machine ran out of memory, before "4..19 from UI-Venus" and "all layers from UI-Venus"; the first of the two is measured at the start of experiment 004.

These are diagnostics, not a ternary result: the donor's layers are 16-bit. Kept that way, the block would add 0.65 to 0.86 GB at 4 bits per weight and slow generation by roughly a fifth to a quarter. The aim is to get the same behaviour from ternary layers (section 8).

With real generated answers on 50 screens: Bonsai 46%, all weights from the parent 96%, vision part only 46%, output head 44%, embeddings 50%, head and embeddings 42%.

### Measurement noise

Re-running an identical server-based evaluation (8 parallel slots) reproduced only 21 or 22 of 24 answers. Use the lab's teacher-forced score to judge edits, and treat server-based accuracies on small samples as plus or minus several points.

## 7. The target machine

The target laptop's display (a 13-inch M4 MacBook) is 2560 x 1664 native and runs scaled at 2940 x 1912 pixels (1470 x 956 points). A Clicky-style capture at 1280 px on the long side is 1280 x 832, which is 1,040 image tokens. At the measured 150 tokens per second prompt processing for the 9B on this machine, reading one screenshot takes about 7 seconds.

## 8. Repair, staying ternary (2026-11-14)

Everything here keeps Bonsai's file format: ternary codes, one multiplier per group of 128 weights, the usual small full-precision parts. Size and speed do not change. Training screens are generated (`bench/pointing`, train split); ScreenSpot-v2 is only ever used to measure.

### Experiment 005: multipliers only

- **What changed:** the multipliers of the ternary matrices in layers 4..19, about 27 million numbers. No code changed.
- **Training:** 400 steps, one generated screen per step (240 screens, seed 101), 13 minutes on the Spark. The loss is the probability mass on answer digits that keep the point inside the target box (`weightlab/tune.py`).

Teacher-forced score on ScreenSpot-v2 (32 screens each):

| | Original Bonsai | Multipliers tuned | Parent |
|---|---|---|---|
| p_hit, first set | 0.256 | **0.570** | 0.707 |
| Hundreds digit acceptable | 0.609 | 0.871 | 0.876 |
| Tens digit acceptable | 0.715 | 0.805 | 0.937 |
| p_hit, second set | 0.355 | **0.689** | not measured |

Generated answers on 120 further ScreenSpot-v2 screens that neither score above used:

| | Original Bonsai | Multipliers tuned |
|---|---|---|
| Hits | 44.2% | **63.3%** |
| Desktop (39) | 46.2% | 66.7% |
| Mobile (54) | 50.0% | 64.8% |
| Web (27) | 29.6% | 55.6% |
| Median distance from the target centre (0-1000 scale) | 64.6 | 45.2 |

The canary (50 short questions in seven skills, `bench/canary`) did not get worse: all answer tokens top-ranked on 86% of questions before and 90% after; mean negative log-probability per answer token 0.074 before and 0.067 after.

Reading:

- The codes PrismML trained are good enough to point; the multipliers were not set for it. Thirteen minutes on synthetic screens recovers about two thirds of the gap to the parent on real screens.
- Coarse position (the hundreds digit) is now at the parent's level. What remains is the tens digit: fine position.
- 120 screens give about plus or minus 9 points on each number; the comparison is on the same screens.

### Experiments 006 and 006a: continuing is not automatically better

Experiment 006 started from the 005 state and opened everything in layers 4..19 (codes, multipliers, small parts) on 1,500 new generated screens. After 150 steps the teacher-forced score had fallen from 0.570 to 0.417 (second set 0.689 to 0.521), and no code had flipped yet, so the run was stopped. Experiment 006a then ran 100-step continuations from the 005 state, each with the learning rate annealed to a tenth:

| Continuation (100 steps) | p_hit, first set | Second set |
|---|---|---|
| none (005 state) | 0.570 | 0.689 |
| Block trainer, multipliers only, new screens | 0.453 | 0.653 |
| Block trainer, multipliers and small parts, new screens | 0.508 | 0.633 |
| Block trainer, multipliers only, the screens 005 used | 0.518 | 0.667 |
| Task tuner (005's own code), multipliers only, new screens | 0.452 | 0.645 |

Reading:

- Neither the opened codes nor the small parts caused the loss; every continuation loses a little, with either trainer and either set of screens.
- The cause is the restart: Adam's first updates are full-sized whatever the gradient, and with one screen per update the model is knocked off a good spot, then has too few steps to settle. Runs must be judged at the end of their anneal, and continuations need a warm-up and a lower learning rate.
- Sets of 32 screens move by 0.05 or more between equivalent runs. From experiment 008 on, runs are compared on two disjoint sets of 159 ScreenSpot-v2 screens.

### Experiment 008: a larger yardstick and a gentle continuation

Two disjoint sets of 159 ScreenSpot-v2 screens (positions 1 and 5 modulo 8 after sorting by id): "select" for choosing between runs, "report" for the number quoted. Teacher-forced p_hit:

| State | Select (159) | Report (159) | Hundreds / tens acceptable (select) |
|---|---|---|---|
| Original Bonsai | 0.327 | 0.372 | 0.634 / 0.760 |
| Multipliers tuned (005) | 0.640 | 0.645 | 0.893 / 0.859 |
| Plus gentle continuation (008) | 0.661 | 0.672 | 0.888 / 0.876 |
| Plus multipliers of layers 4..31 and the output head (008, second run) | **0.698** | **0.704** | 0.902 / 0.894 |

The same score for the full-precision models on the same screens: parent (Qwen3.5-9B) 0.848 select and 0.843 report (hundreds 0.920, tens 0.979); UI-Venus-2-9B 0.932 and 0.939 (hundreds 0.963, tens 0.996). So the repaired Bonsai has closed about two thirds of the gap to its parent, and UI-Venus is a further 0.09 above the parent. Most of what is missing is the tens digit.

The continuation used a learning rate five times lower (2e-4) with a 30-update warm-up, two screens per update, 300 updates on a mix of both generated training sets, and wrote back the running average of the multipliers. It gains a little on every set, where the same continuation at the original learning rate lost ground (006a). Restarting gently is the rule from here on.

The second run opened the multipliers of layers 4..31 and of the output head (learning rate 3e-4, 400 updates of two screens, same warm-up and averaging) and gained again on every set. All of this is still multipliers only: no ternary code has changed, and the model is exported as an ordinary MLX pack (`~/bonsai/export/bonsai2-9b-point-v1-mlx` on the Spark).

From this point the eight ScreenSpot-v2 cases that share screens with public macOS training data (`~/bonsai/ssv2/excluded_overlap.json`, see [docs/MAC_DATA.md](docs/MAC_DATA.md)) are excluded from every score; one of them was in the report set, which now has 158 screens (0.708 for the state above).

### How small the repair is

Comparing the exported model with PrismML's original pack: 352 tensors differ (the multipliers and their mirrored offsets of 176 ternary matrices in layers 4..31 and the output head), 1,014 are byte-identical, and no code differs. The mean relative change of a multiplier is 0.7% (at most 1.2% averaged over any one matrix). A change of about one percent to 55 million numbers is the whole difference between 0.33 and 0.70. The patch is a 221 MB file applied to the original 3.5 GB pack in memory (`export/patches/bonsai2-9b-point-v1.patch.safetensors` on the Spark).

### Experiment 011: a zoomed second look, no training

The model points on the whole screenshot (1280 px), a window around its answer is cut from the original image and shown at 1024 px, and it points again inside the window. Generated answers on the ScreenSpot-v2 report set (159 screens; the multiplier-tuned model above):

| | Hits | Target inside the window |
|---|---|---|
| One look | 65.4% | |
| Second look, window half of each side | 73.6% | 93.7% |
| Second look, window a third of each side | **74.2%** | 84.3% |

When the target is inside the smaller window the second look hits 88% of the time, so the limit is now the first look's coarse aim. The second look reads about 660 tokens against 920 for the first. It stacks with any training gain, at the cost of a second pass.

### On the target Mac

Through `mlx-vlm` on the M4 MacBook (old and new model share one copy of the weights; the patch is swapped in memory), four generated sample screens: the original model missed all four, the repaired one hit three. One look took 14 to 33 s there (35 to 73 tokens/s of prompt processing while the machine was in use), far slower than the llama.cpp fork measured earlier (about 150 tokens/s), which is why a GGUF export is being built.

### Experiment 010 so far: the block open on Mac and synthetic screens (in progress)

Layers 4..19 fully open (codes with a low learning rate, multipliers, small parts), the task signal only, up to five questions per screenshot in one step, about 28,000 cases: generated screens, real macOS screens with boxes (OS-Atlas, Screen2AX, ScaleCUA, ShowUI) and a minority of AgentNet click points. Scored every 250 steps on the select set and on 60 Mac app-window cases from reserved apps:

| Step | Select (159) | Hundreds / tens | Mac app windows (60) | Codes flipped |
|---|---|---|---|---|
| 0 | 0.699 | 0.902 / 0.894 | 0.403 | 0 |
| 250 | 0.700 | 0.885 / 0.905 | 0.443 | 0 |
| 500 | **0.752** | 0.918 / 0.914 | 0.440 | 0 |

No code has flipped yet at step 500 (a code needs hundreds of consistent steps), so the gain up to here comes from the multipliers and small parts learning on the larger and more real mix. The run was paused at step 636 to release cached GPU memory (the session had crept to 89 GB reserved, 22 GB left on the machine) and resumed from the same trainer state with the cache released every 50 steps.

### The repaired model in the llama.cpp format

`weights/export_gguf.py` writes the patch into a copy of PrismML's GGUF. The base GGUF equals the pack bit for bit (202 modules), the exported file differs from it only in the scale fields of the 176 patched tensors, and through `llama-server` on the Mac it gives the same answers as the patched MLX model on four sample screens (old model: 0 of 4 on target; new: 3 of 4). Measured on the M4 MacBook with other apps open: about 105 prompt tokens/s and 10 s per screenshot, the same as `mlx-vlm` measured the same evening. A different question about the same screenshot is not faster with the standard prompt (the model's recurrent layers leave no cache point between image and instruction); with the screenshot in its own message, later questions take about 1.2 s, but that prompt layout changes the original model's answers.

### What did not work, and why

- **Pulling Bonsai's internal states toward the teacher's.** Even when Bonsai points well, its state after layer 19 is further from UI-Venus's than the state before the block is (relative error 1.14). Bonsai solves the task in its own representation. Eight training steps with that pull took p_hit from 0.57 to 0.44.
- **Layer by layer**, Bonsai's layers 4..19 are poor copies of UI-Venus's (error 0.46 to 2.6 against the teacher's output for the same input; above 1 means worse than doing nothing). The swap experiments in section 6 measured the same thing from the other side.

### Our own pointing benchmark (`bench/pointing`, dev split, seed 20261114, 413 cases, 1280 px)

Generated from scratch with exact boxes. Served by llama.cpp, thinking off.

| | Qwen3.5-9B | Bonsai 2 9B (original) |
|---|---|---|
| Overall | 53.8% | 7.3% |
| Text target, named directly (117) | 84.6% | 18.8% |
| Text target, described by function (102) | 56.9% | 3.9% |
| Icon, named directly (96) | 43.8% | 0.0% |
| Icon, described by function (98) | 23.5% | 4.1% |
| Target size large / medium / small / very small | 75.5 / 73.8 / 43.6 / 30.3% | 18.4 / 11.1 / 4.0 / 1.1% |

It is harder than ScreenSpot-v2 (dense toolbars, per-row icons, functional wording). UI-Venus and the tuned Bonsai have not been run on it yet.

