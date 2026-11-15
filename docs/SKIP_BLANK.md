# Skipping the blank areas of a screenshot (experiment 021)

Run on 2026-11-15 (UTC) on a rented GPU pod (RTX PRO 6000), Bonsai 2 9B with the patch
`bonsai2-9b-point-v2`. Code: `weightlab/sparse.py`, `experiments/021_skip_blank.py`. Results:
`lab/exp021_skip_blank.json` and `lab/exp021_mac_share.json` on the pod (not in this repository).

## Result in short

**Removing blank image tokens works mechanically and is exact, but this model pays for it: every
rule tried loses accuracy, roughly in step with the tokens removed. It should not be switched on
for the current weights.**

| Rule (exactly flat areas only) | Image tokens removed | p_hit select | p_hit report | p_hit Mac windows | Generated answers on target (report) | Read time on the Mac (estimate) |
|---|---|---|---|---|---|---|
| Nothing removed | 0 | 0.800 | 0.790 | 0.456 | 73.4% | 9.9 s |
| Inside flat 5x5 blocks (`win5`, threshold 1) | 9 to 13% | 0.744 | 0.754 | 0.389 | 69.0% | 9.0 s |
| Inside flat 3x3 blocks (`win3`, threshold 1) | 14 to 21% | 0.687 | 0.685 | 0.363 | 60.8% | 8.5 s |
| Every flat cell (`cell`, threshold 1) | 30 to 40% | 0.486 | 0.445 | 0.243 | not run | 7.0 s |

- The baseline on this pod is select 0.800, report 0.790 (every 9B pod prints this; the Spark
  prints 0.810 and 0.797). All comparisons are against this pod's own baseline, same cases.
- The mildest filter that still removes large chunks (`win5`, exactly flat) saves about 0.9 s of
  a 9.9 s read and costs 0.04 to 0.07 p_hit and 4 points of generated hits.
- A short adaptation (400 updates, multipliers only, tokens dropped during training) did not
  close the gap. See "Adaptation".
- Why: 24 of the model's 32 layers are recurrent and have no positions. They read the image as a
  stream, and the model takes much of its sense of place from that stream. Removing tokens shifts
  it, whatever position ids are passed. See "Controls".

## What has to be passed to drop tokens correctly

Read from `transformers/models/qwen3_5/modeling_qwen3_5.py` (transformers 5.23) and confirmed by
the check below.

1. **`inputs_embeds`**: the token embeddings with the vision tower's features already written
   over the image placeholders (what `Qwen3_5Model.forward` does with `masked_scatter`), then
   indexed by the sequence positions that remain. The vision tower still sees the whole image, so
   the features of the kept cells are the usual ones.
2. **`position_ids` with three rows** (time, height, width), computed for the whole sequence by
   `model.model.get_rope_index(...)` and indexed the same way. An image token's rows are
   (start, start + row, start + column). Text after the image continues at
   start + max(rows, columns), whatever the number of image tokens (measured: a 17x30 grid
   starting at 4 is followed by text at 34). So every kept token and all the text keep their
   positions without any renumbering.
3. **`attention_mask`**: ones, of the reduced length.
4. The fourth row that `generate` adds (text order) only reaches the mask builders, never the
   rotary embedding, and can be left out. `model.generate` rebuilds position ids itself, so
   generation is a short greedy loop in `sparse.generate`: the reduced prompt once with
   `use_cache=True`, then one token at a time, each at the next position on all three axes.

What no argument can preserve: the 24 "linear attention" layers (a gated delta rule behind a
causal convolution over the previous 3 tokens) take no positions at all. For them a dropped token
is simply absent: its neighbours close up, and its contribution to the running state is missing.
Only the 8 full-attention layers see the original geometry.

## Correctness

- Nothing dropped against the normal forward pass, logits at every position, 32 cases (16 select,
  8 report, 8 Mac): **largest absolute difference 0**, same top token at 23,859 of 23,859
  positions. The reference was called both with `use_cache=False` and with defaults.
- The greedy loop with nothing dropped gives the same text as `model.generate` on 40 of 40 cases.
- The teacher-forced score through the new path reproduces the lab's caches: select 0.800,
  report 0.790.
- Cell layout: the image rebuilt from `pixel_values` under the assumed layout (four consecutive
  rows per token, tokens row by row) equals a bicubic resize of the lab's image to the
  processor's size to within 1 level (3 screenshots); a wrong layout differs by 7 to 16 levels on
  average.

## The rules

A cell is the 32x32 px area of one image token, measured on the pixels the model receives (after
the lab's resize to 1280 px and the processor's resize). Its colour range is the largest, over
the three channels, of maximum minus minimum. Threshold 1 means exactly flat.

| Name | A cell is dropped when |
|---|---|
| `cell` | its own colour range is below the threshold |
| `nbr` | it and its 8 neighbours are each below the threshold |
| `win3` | the whole 3x3 block around it (96x96 px) is one colour: range over the block below the threshold |
| `win5` | the same over the 5x5 block (160x160 px) |
| `bands` | it lies in a row or a column of the grid that is one colour from edge to edge |

`win3` and `win5` are the "remove huge chunks only" filters: every cell that touches anything is
kept, with a margin of one or two cells. `nbr` and `win3` remove almost the same cells.

## Measurements, no training

Teacher-forced p_hit, with the paired change against nothing dropped and its standard error.
Sets: select (159 ScreenSpot-v2 screens), report (158), Mac (120 app-window cases of
`mac:screen2ax_task:test`). Mean image tokens per case: 845, 840, 1,073. "Tokens read" is the
whole sequence, averaged over all 437 cases. "On the Mac" is tokens / 105 per second + 0.4 s, the
estimate used in experiment 013; it was not measured on the Mac.

| Rule | Threshold | Image tokens dropped (select / report / Mac) | Range over cases | p_hit select | p_hit report | p_hit Mac | Tokens read | Seconds per pass | On the Mac |
|---|---|---|---|---|---|---|---|---|---|
| none | | 0 | | 0.800 | 0.790 | 0.456 | 999 | 0.065 | 9.9 s |
| win5 | 1 | 10% / 9% / 13% | 0–85% | 0.744 (-0.056 ±0.018) | 0.754 (-0.037 ±0.014) | 0.389 (-0.067 ±0.022) | 906 | 0.061 (×1.07) | 9.0 s |
| win5 | 4 | 11% / 10% / 13% | 0–85% | 0.733 (-0.067 ±0.020) | 0.741 (-0.049 ±0.017) | 0.378 (-0.078 ±0.023) | 895 | 0.061* | 8.9 s |
| win5 | 8 | 11% / 11% / 14% | 0–85% | 0.728 (-0.072 ±0.020) | 0.730 (-0.060 ±0.017) | 0.377 (-0.079 ±0.023) | 890 | 0.060 (×1.08) | 8.9 s |
| win5 | 16 | 12% / 13% / 16% | 0–85% | 0.723 (-0.077 ±0.021) | 0.705 (-0.085 ±0.020) | 0.354 (-0.102 ±0.026) | 873 | 0.059* | 8.7 s |
| win5 | 32 | 16% / 17% / 22% | 0–86% | 0.669 (-0.131 ±0.026) | 0.670 (-0.120 ±0.023) | 0.333 (-0.123 ±0.028) | 833 | 0.057 (×1.14) | 8.3 s |
| win5 | 64 | 20% / 21% / 27% | 0–86% | 0.648 (-0.152 ±0.028) | 0.631 (-0.160 ±0.025) | 0.316 (-0.140 ±0.029) | 794 | 0.055* | 8.0 s |
| win3 | 1 | 15% / 14% / 21% | 0–90% | 0.687 (-0.113 ±0.025) | 0.685 (-0.105 ±0.021) | 0.363 (-0.093 ±0.025) | 848 | 0.058 (×1.13) | 8.5 s |
| win3 | 4 | 17% / 17% / 22% | 0–90% | 0.676 (-0.124 ±0.025) | 0.636 (-0.155 ±0.026) | 0.352 (-0.104 ±0.027) | 829 | 0.057* | 8.3 s |
| win3 | 8 | 18% / 19% / 22% | 0–90% | 0.664 (-0.136 ±0.026) | 0.612 (-0.178 ±0.027) | 0.351 (-0.105 ±0.027) | 819 | 0.057 (×1.16) | 8.2 s |
| win3 | 16 | 21% / 23% / 26% | 0–90% | 0.649 (-0.151 ±0.027) | 0.580 (-0.211 ±0.029) | 0.337 (-0.119 ±0.029) | 789 | 0.055* | 7.9 s |
| win3 | 32 | 26% / 28% / 34% | 0–90% | 0.578 (-0.222 ±0.031) | 0.523 (-0.267 ±0.031) | 0.287 (-0.169 ±0.031) | 729 | 0.053 (×1.25) | 7.3 s |
| win3 | 64 | 32% / 34% / 40% | 1–91% | 0.512 (-0.288 ±0.033) | 0.459 (-0.331 ±0.032) | 0.233 (-0.223 ±0.035) | 678 | 0.050* | 6.9 s |
| nbr | 1 | 15% / 14% / 21% | 0–90% | 0.688 (-0.114 ±0.025) | 0.685 (-0.105 ±0.021) | 0.363 (-0.093 ±0.025) | 848 | 0.058* | 8.5 s |
| nbr | 8 | 18% / 20% / 22% | 0–90% | 0.655 (-0.146 ±0.027) | 0.609 (-0.182 ±0.027) | 0.352 (-0.105 ±0.027) | 816 | 0.056* | 8.2 s |
| nbr | 32 | 27% / 29% / 35% | 0–90% | 0.578 (-0.223 ±0.031) | 0.508 (-0.283 ±0.031) | 0.291 (-0.166 ±0.031) | 724 | 0.052* | 7.3 s |
| cell | 1 | 32% / 30% / 40% | 0–94% | 0.486 (-0.316 ±0.034) | 0.445 (-0.346 ±0.038) | 0.243 (-0.214 ±0.036) | 689 | 0.051* | 7.0 s |
| cell | 8 | 42% / 43% / 45% | 0–94% | 0.348 (-0.453 ±0.033) | 0.330 (-0.460 ±0.037) | 0.232 (-0.225 ±0.036) | 608 | 0.047 (×1.39) | 6.2 s |
| cell | 32 | 54% / 57% / 61% | 5–96% | 0.238 (-0.563 ±0.034) | 0.233 (-0.557 ±0.036) | 0.110 (-0.347 ±0.038) | 480 | 0.041* | 5.0 s |
| bands | 1 | 6% / 6% / 1% | 0–87% | 0.767 (-0.034 ±0.013) | 0.769 (-0.021 ±0.012) | 0.457 (+0.001 ±0.001) | 965 | 0.064* | 9.6 s |
| bands | 8 | 8% / 8% / 2% | 0–87% | 0.758 (-0.043 ±0.015) | 0.752 (-0.039 ±0.014) | 0.456 (-0.000 ±0.001) | 952 | 0.063 (×1.04) | 9.5 s |
| bands | 32 | 13% / 14% / 7% | 0–94% | 0.727 (-0.074 ±0.018) | 0.681 (-0.110 ±0.022) | 0.414 (-0.043 ±0.017) | 906 | 0.061* | 9.0 s |

Seconds per pass is the language model's body on the GPU, one case at a time. Values with a
factor come from the paired timing (each setting run back to back with nothing dropped on the same
case); values with * come from the sweep itself and are less clean. `nbr`, `cell` and `bands`
were run at three thresholds only.

Reading:

- No rule is free. Even dropping only whole flat rows and columns (`bands`, 6% of tokens) costs
  0.02 to 0.03 on the ScreenSpot sets.
- The cost grows faster than the saving. On the ScreenSpot sets `win5` at threshold 1 loses about
  0.05 for 10% of the image tokens, `win3` about 0.11 for 15%, `cell` about 0.33 for 31%.
- Raising the threshold buys little and costs more. From threshold 1 to 8, `win3` removes 1 to 5
  points more tokens and loses a further 0.01 to 0.07. Screens are mostly exactly flat or not flat.

### Speed

Paired timing on the GPU (seconds per pass and factor against nothing dropped):

| Setting | Select | Report | Mac |
|---|---|---|---|
| nothing dropped | 0.0629 s, 938 tokens | 0.0627 s, 933 tokens | 0.0724 s, 1,165 tokens |
| win5, 1 | 0.0588 s (×1.07), 857 | 0.0593 s (×1.06), 862 | 0.0666 s (×1.09), 1,027 |
| win5, 8 | 0.0583 s (×1.08), 846 | 0.0580 s (×1.08), 838 | 0.0662 s (×1.09), 1,018 |
| win5, 32 | 0.0563 s (×1.12), 804 | 0.0554 s (×1.13), 793 | 0.0612 s (×1.18), 922 |
| win3, 1 | 0.0562 s (×1.12), 811 | 0.0565 s (×1.11), 818 | 0.0622 s (×1.16), 938 |
| win3, 8 | 0.0551 s (×1.14), 786 | 0.0541 s (×1.16), 774 | 0.0617 s (×1.17), 924 |
| win3, 32 | 0.0515 s (×1.22), 715 | 0.0507 s (×1.24), 695 | 0.0562 s (×1.29), 794 |
| cell, 8 | 0.0463 s (×1.36), 584 | 0.0454 s (×1.38), 574 | 0.0504 s (×1.44), 684 |
| bands, 8 | 0.0602 s (×1.04), 882 | 0.0596 s (×1.05), 872 | 0.0718 s (×1.01), 1,150 |

On this GPU a pass costs about 19 ms whatever the length plus about 47 µs per token, so the
speed-up is a little below the share of tokens removed (38% fewer tokens gives ×1.36, not ×1.61).
On the Mac the fixed part is negligible next to 9.5 ms per token, so there the saving should be
close to proportional; that is an expectation, not a measurement. The vision tower (0.04 to
0.06 s here) is unchanged: it still reads the whole image.

### Generated answers (report set, 158 cases)

| Setting | On target | Prompt pass | Whole answer |
|---|---|---|---|
| nothing dropped | 116/158 = 73.4% | 0.066 s | 0.251 s |
| win5, 1 | 109/158 = 69.0% | 0.059 s | 0.228 s |
| win5, 8 | 104/158 = 65.8% | 0.057 s | 0.216 s |
| win3, 1 | 96/158 = 60.8% | 0.056 s | 0.219 s |
| win3, 8 | 84/158 = 53.2% | 0.054 s | 0.231 s |

One set of 158 cases gives about plus or minus 7 points on each number; the comparison is on the
same cases.

### Controls

| Control | Tokens dropped (select / report / Mac) | p_hit select | p_hit report | p_hit Mac |
|---|---|---|---|---|
| win3, 8 (from the table above) | 18% / 19% / 22% | 0.664 (-0.136) | 0.612 (-0.178) | 0.351 (-0.105) |
| The same number of cells per image, chosen at random | 18% / 19% / 22% | 0.639 (-0.161 ±0.029) | 0.587 (-0.204 ±0.027) | 0.268 (-0.188 ±0.034) |
| win3, 8, position ids not passed | 18% / 19% / 22% | 0.504 (-0.296 ±0.033) | 0.508 (-0.282 ±0.031) | 0.289 (-0.167 ±0.030) |
| win5, 1 (from the table above) | 10% / 9% / 13% | 0.744 (-0.056) | 0.754 (-0.037) | 0.389 (-0.067) |
| The same number of cells per image, chosen at random | 10% / 9% / 13% | 0.741 (-0.059 ±0.018) | 0.699 (-0.092 ±0.022) | 0.384 (-0.072 ±0.025) |
| win5, 1, position ids not passed | 10% / 9% / 13% | 0.544 (-0.256 ±0.031) | 0.625 (-0.165 ±0.025) | 0.300 (-0.156 ±0.027) |
| Nothing dropped, position ids not passed | 0 | 0.582 (-0.218 ±0.029) | 0.641 (-0.149 ±0.023) | 0.341 (-0.115 ±0.023) |

Reading:

- Passing the original positions matters: at `win3`, threshold 8, the loss without them is 0.17
  to 0.30 instead of 0.11 to 0.18.
- Dropping blank cells costs somewhat less than dropping the same number of random cells, but the
  same order (at `win3`, threshold 8: -0.14 / -0.18 / -0.11 against -0.16 / -0.20 / -0.19). So
  most of the loss is not missing content. It is the disturbance of the sequence itself.
- With no position ids at all and nothing dropped, the model still scores 0.58 and 0.64. It gets
  a large part of its geometry from the order of the tokens, through the recurrent layers. That
  is the part a drop disturbs and no position id can restore.

## How much the rule removes on real Mac screenshots

Up to 250 screenshots per folder of `data/mac`, shown at 1280 px like everything else. Share of
image tokens removed: mean, with the 10th and 90th percentile over screenshots in brackets.

| Folder | Screenshots | Image tokens | win5, 1 | win5, 8 | win3, 1 | win3, 8 | win3, 32 | cell, 8 | bands, 8 |
|---|---|---|---|---|---|---|---|---|---|
| os_atlas_mac | 250 | 1,000 | 12% (0–35) | 13% (0–37) | 17% (0–47) | 19% (1–51) | 27% (6–61) | 37% (12–71) | 3% (0–8) |
| scalecua_mac | 250 | 1,000 | 26% (0–61) | 27% (0–65) | 34% (0–73) | 37% (9–75) | 48% (17–81) | 57% (35–87) | 10% (0–64) |
| screen2ax_task | 134 | 1,051 | 14% (0–34) | 16% (0–36) | 23% (3–47) | 25% (4–49) | 36% (15–59) | 47% (28–70) | 4% (0–8) |
| screen2ax_tree | 250 | 1,146 | 19% (0–45) | 21% (1–47) | 27% (1–54) | 30% (3–58) | 43% (14–69) | 51% (24–75) | 3% (0–11) |
| showui_desktop_mac | 61 | 1,000 | 15% (0–56) | 19% (0–61) | 20% (0–66) | 26% (0–70) | 36% (6–75) | 45% (15–83) | 10% (0–56) |

So on Mac screens the "large flat regions only" filter removes about a fifth to a third of the
image tokens on average (`win3`), an eighth to a quarter with the wider margin (`win5`), and very
unevenly: one screenshot in ten loses almost nothing, one in ten loses about half or more.

## Adaptation (one short run)

The untrained drop costs far more than 0.02, so the short adaptation was run: `TaskTuner`, the
usual loss, multipliers only, layers 0 to 31, 400 updates of two cases from the training mix,
learning rate 2e-4, 30 warm-up updates, averaged multipliers, with `win3` at threshold 8 dropping
tokens during training (`sparse.dropping`, which replaces `chat.answer_logits` for the duration;
`tune.py` is unchanged). 7.4 minutes. Training loss 3.62 over the first 25 updates, 1.44 over the
last 25. Scores are against the untrained model with nothing dropped.

| After the adaptation | p_hit select | p_hit report | p_hit Mac | Generated, report |
|---|---|---|---|---|
| nothing dropped | 0.740 (-0.060 ±0.015) | 0.770 (-0.020 ±0.014) | 0.416 (-0.040 ±0.015) | 122/158 = 77.2% |
| win3, 1 | 0.652 (-0.148 ±0.024) | 0.706 (-0.085 ±0.023) | 0.380 (-0.076 ±0.022) | not run |
| win3, 8 (trained with) | 0.633 (-0.167 ±0.025) | 0.648 (-0.143 ±0.024) | 0.367 (-0.089 ±0.024) | 99/158 = 62.7% |
| win3, 16 | 0.624 (-0.176 ±0.026) | 0.603 (-0.187 ±0.025) | 0.359 (-0.097 ±0.026) | not run |
| win3, 32 | 0.584 (-0.217 ±0.028) | 0.557 (-0.233 ±0.028) | 0.329 (-0.127 ±0.026) | not run |
| cell, 8 | 0.385 (-0.415 ±0.034) | 0.388 (-0.402 ±0.034) | 0.257 (-0.199 ±0.034) | not run |

Against the untrained model with the same tokens dropped (win3, 8: 0.664 / 0.612 / 0.351 and
53.2% generated): select fell by 0.03, report rose by 0.04, Mac rose by 0.02, generated answers
rose from 53.2% to 62.7%. With nothing dropped the teacher-forced score fell on all three sets
while generated answers rose from 73.4% to 77.2%; with one run these two cannot be told apart
from the usual cost and noise of restarting training (FINDINGS section 8, experiment 006a).

Reading: 400 updates of the multipliers move the model a little toward tolerating the drop, and
leave it 11 points of generated hits (and 0.09 to 0.17 p_hit) below not dropping at all. The gap
is not closed by a short multiplier-only run. The tuned multipliers are on the pod at
`lab/ckpt/exp021_drop_win38.pt`; the session's weights were put back afterwards.

## Recommendation

1. **Do not ship the filter with the current weights.** The best trade-off measured is `win5` at
   threshold 1 (inside exactly flat 160x160 px areas): about 10% fewer image tokens on
   ScreenSpot-v2 and 12 to 26% on Mac screenshots, roughly 1 s of a 10 s read, for 0.04 to 0.07
   p_hit and 4 points of generated hits. The other route to fewer tokens, a smaller first look
   followed by a zoomed second look (experiments 011 and 013), keeps the stream a complete grid,
   which is what this model is used to reading.
2. **If the filter is wanted, use threshold 1.** A higher threshold removes few extra tokens and
   costs clearly more. Prefer `win5` to `win3`; never drop single flat cells (`cell`).
3. **To make dropping cheap it has to be trained in, not bolted on.** The loss comes from the
   recurrent layers reading a shortened stream, which only training can teach them to tolerate.
   That means dropping tokens through the whole pointing training (as ShowUI does), with more than
   the multipliers open. One short multiplier-only run recovered about half of the generated-hit
   loss at `win3`, threshold 8, and none of the teacher-forced loss. Whether a full run closes the
   gap is not known.
4. The mechanics are ready whichever way this goes: `sparse.py` gives exact reduced passes,
   scoring, generation and a training hook, and the Mac runtime would need the same two things
   (embeddings with tokens removed, original position ids).

## Not verified

- **Nothing was run on the Mac.** Read times there are tokens / 105 per second + 0.4 s. Whether
  llama.cpp or mlx-vlm can be given a reduced image sequence with the original positions was not
  checked.
- **The 0.01 gap to the Spark's baseline** (0.810 / 0.797 there, 0.800 / 0.790 on every 9B pod)
  is being resolved elsewhere. A check here: the matrix-product patch embedding in bfloat16 and
  in float32 give select 0.8001 and 0.8010, so its rounding is unlikely to be the cause (the
  original Conv3d was run on 10 cases only: 0.801 against 0.797 for the same cases).
- `nbr`, `cell` and `bands` at thresholds 1, 8 and 32 only. Generated answers on the report set
  only, five settings; none for `cell`, `nbr`, `bands`.
- The adaptation is a single run with one rule, one threshold, one seed and multipliers only. No
  canary was run on the adapted weights.
- After the adaptation the weights were restored from a snapshot; the score with nothing dropped
  then read 0.801 / 0.791 instead of 0.800 / 0.790 (per-case differences around 0.001). The rows
  for `cell`, `nbr`, `bands` and the paired timing were measured in that state. Restart the lab
  session on the pod before using it for anything that needs the exact baseline.
- One image size (1280 px on the long side), one prompt format (plain "[x, y]" pointing). Pointing
  as a tool call was not measured.
- The first run of the `win3` / `win5` sweep shared the pod's CPU with the Mac-screenshot count, so
  its own seconds column (the values marked *) is less clean than the paired timing.

## How to run it again

```
# on a GPU machine with the lab session running, in the bonsai root, after experiments/_prelude.py:
./venv/bin/python weightlab/client.py run experiments/021_skip_blank.py
```

Stages and settings are listed at the top of `experiments/021_skip_blank.py` (`STAGES21`,
`THRS21`, `GEN21`, `CTRL21`, `TIME21`, `UPDATES21`). The `macshare` stage needs only the
processor and also runs outside the lab session.
