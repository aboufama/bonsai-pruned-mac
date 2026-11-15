# Benchmark: the repaired Bonsai 2 9B at pointing and tool calling

Status: 15 November 2026, 02:55 EST. The headline sets (ScreenSpot-v2 and the reserved macOS set) are complete for every model listed. Work was cut back to those two and the detector ablation; everything else is listed under "Not run". Cells marked † are runs that were still going, with the cases done; "not run" means not run.

What is compared: Ternary Bonsai 2 9B with our repair (PrismML's original pack plus a patch file; `v3-gentle` is the checkpoint to report, `v2` and `v4-gentle` are an earlier and a later one), the original, its full-precision parent Qwen3.5-9B, the full-precision specialist UI-Venus-2-9B, a general model of about the same memory footprint (Qwen3.5-4B at 4 bits), and Bonsai 2 4B. Every number below was produced by `bench/run.py` with generated answers and greedy decoding, and every table is rebuilt from the per-case files by `bench/report.py` ([bench/README.md](../bench/README.md) has the command for each table).

## Headline

Share of cases answered correctly, in percent. Pointing: the model's point lies inside the target. "1280 px" means the screenshot is shrunk so that its longer side is at most 1280 px, which is what the target assistant captures; "full resolution" is the reference evaluator's setting (up to 12.8 million pixels).

<!-- begin:headline -->
| Model | ScreenSpot-v2, 1280 px | ScreenSpot-v2, full resolution | ScreenSpot-Pro, 1280 px | ScreenSpot-Pro, full resolution | OSWorld-G refined | macOS app windows, 1280 px | Our generated screens, 1280 px | Tool calls (ours) | BFCL v3 subset |
|---|---|---|---|---|---|---|---|---|---|
| Bonsai 2 9B, repaired [v3-gentle] | 82.1 | not run | not run | not run | not run | 44.9 | not run | not run | not run |
| Bonsai 2 9B, repaired [v2] | 76.8 | not run | not run | not run | not run | 40.9 | 38.3 | not run | not run |
| Bonsai 2 9B, repaired [v3-tools] | 71.9 †160/1272 | not run | not run | not run | not run | not run | not run | not run | not run |
| Bonsai 2 9B, repaired [v4-gentle] | 81.0 | not run | not run | not run | not run | 43.8 | not run | not run | not run |
| Ternary Bonsai 2 9B, original | 43.3 | not run | not run | not run | not run | 13.2 | not run | not run | not run |
| Qwen3.5-9B (parent) | 91.7 | 92.7 | not run | not run | not run | 63.8 | not run | not run | not run |
| UI-Venus-2-9B | 95.8 | 96.2 | not run | 71.9 | not run | 68.4 | not run | not run | not run |
| Qwen3.5-4B, 4-bit (Q4_K_M GGUF) | 89.9 | not run | not run | not run | not run | 58.8 | not run | not run | not run |
| Bonsai 2 4B, repaired | 67.0 | not run | not run | not run | not run | 32.7 | not run | not run | not run |
| Ternary Bonsai 2 4B, original | 12.2 | not run | not run | not run | not run | 3.7 | not run | not run | not run |
<!-- end:headline -->

Reading the table:

- **The repair roughly doubles the original.** On ScreenSpot-v2 the repaired 9B (`v3-gentle`) is right on 82.1% of cases (80.0 to 84.2) against 43.3% for the original; on the reserved macOS set 44.9% against 13.2%. Both differences are far outside chance (paired tables below).
- **It is still behind every full-precision or 4-bit model here.** At the same 1280 px input it trails its parent by 9.5 points on ScreenSpot-v2 and 18.9 on macOS, UI-Venus by 13.7 and 23.5, and the 4-bit Qwen3.5-4B, which is about the same size on disk, by 7.7 and 13.9.
- **Icons and web pages are where it loses.** Text targets on phones are at 92.8%; web icons are at 65.5%.
- **`v4-gentle` is not better than `v3-gentle`** with generated answers (81.0 against 82.1 on ScreenSpot-v2, 43.8 against 44.9 on macOS), although its development score was higher. `v3-gentle` gains 5.3 points over `v2` on ScreenSpot-v2 and 4.0 on macOS.
- **The 4B follows the same pattern lower down:** 12.2% to 67.0% on ScreenSpot-v2, 3.7% to 32.7% on macOS. The original 4B refuses 107 and 259 cases outright.
- **The macOS numbers are depressed by label noise.** On the 114 checked cases whose label is right, UI-Venus reaches 90.3%, the parent 76.3% and the repaired 9B 49.1%.

## Results by benchmark

Intervals in brackets are 95% bootstrap intervals over cases.

### ScreenSpot-v2 (1,272 cases: phone, desktop and web screens)

<!-- begin:ssv2 -->
| Model | Input | All 1,272 (95% interval) | Mobile text | Mobile icon | Desktop text | Desktop icon | Web text | Web icon | Unreadable answers | Refusals |
|---|---|---|---|---|---|---|---|---|---|---|
| Bonsai 2 9B, repaired [v3-gentle] | 1280 px | 82.1 (80.0–84.2) | 92.8 | 79.6 | 88.7 | 72.1 | 85.9 | 65.5 | 0 | 0 |
| Bonsai 2 9B, repaired [v2] | 1280 px | 76.8 (74.5–79.1) | 91.7 | 72.5 | 83.5 | 65.0 | 80.3 | 57.6 | 0 | 0 |
| Bonsai 2 9B, repaired [v3-tools] †160/1272 | 1280 px | 71.9 (65.0–78.8) | – | – | 74.2 | 68.2 | – | – | 0 | 0 |
| Bonsai 2 9B, repaired [v4-gentle] | 1280 px | 81.0 (78.8–83.2) | 93.5 | 77.7 | 87.6 | 70.7 | 84.6 | 63.0 | 0 | 0 |
| Ternary Bonsai 2 9B, original | 1280 px | 43.3 (40.6–46.0) | 66.5 | 51.2 | 40.7 | 27.9 | 33.3 | 26.6 | 0 | 7 |
| Qwen3.5-9B (parent) | full resolution | 92.7 (91.3–94.1) | 98.3 | 85.8 | 98.5 | 88.6 | 94.4 | 87.2 | 0 | 1 |
| Qwen3.5-9B (parent) | 1280 px | 91.7 (90.2–93.2) | 97.2 | 85.8 | 98.5 | 87.1 | 94.4 | 83.2 | 0 | 2 |
| UI-Venus-2-9B | full resolution | 96.2 (95.0–97.2) | 98.3 | 93.4 | 100.0 | 92.9 | 95.7 | 95.1 | 0 | 3 |
| UI-Venus-2-9B | 1280 px | 95.8 (94.7–96.9) | 98.3 | 93.4 | 99.5 | 92.9 | 96.2 | 93.1 | 0 | 2 |
| Qwen3.5-4B, 4-bit (Q4_K_M GGUF) | 1280 px | 89.9 (88.2–91.4) | 97.2 | 85.8 | 96.9 | 87.9 | 86.3 | 82.3 | 0 | 3 |
| Bonsai 2 4B, repaired | 1280 px | 67.0 (64.4–69.6) | 92.1 | 69.7 | 74.7 | 57.1 | 56.8 | 39.4 | 0 | 0 |
| Ternary Bonsai 2 4B, original | 1280 px | 12.2 (10.5–14.0) | 21.0 | 10.4 | 16.5 | 8.6 | 7.7 | 4.9 | 0 | 107 |
<!-- end:ssv2 -->

The same scores counted three ways. Eight desktop cases share their screens with public macOS training data that entered our training mix, and one eighth of the set was used to choose between training runs, so the last column is the cleanest for the repaired model.

<!-- begin:ssv2_three_ways -->
| Model | Input | All cases | Without the 8 overlap cases | Also without the eighth used to choose checkpoints |
|---|---|---|---|---|
| Bonsai 2 9B, repaired [v3-gentle] | 1280 px | 82.1 (80.0–84.2), n=1272 | 82.1 (80.0–84.3), n=1264 | 83.0 (80.8–85.2), n=1105 |
| Bonsai 2 9B, repaired [v2] | 1280 px | 76.8 (74.5–79.1), n=1272 | 76.9 (74.5–79.2), n=1264 | 77.1 (74.6–79.5), n=1105 |
| Bonsai 2 9B, repaired [v3-tools] | 1280 px | 71.9 (65.0–78.8), n=160 | 71.9 (65.0–78.8), n=160 | 70.7 (62.9–77.9), n=140 |
| Bonsai 2 9B, repaired [v4-gentle] | 1280 px | 81.0 (78.8–83.2), n=1272 | 80.9 (78.7–83.1), n=1264 | 81.3 (79.0–83.5), n=1105 |
| Ternary Bonsai 2 9B, original | 1280 px | 43.3 (40.6–46.0), n=1272 | 43.4 (40.7–46.1), n=1264 | 44.2 (41.3–47.2), n=1105 |
| Qwen3.5-9B (parent) | full resolution | 92.7 (91.3–94.1), n=1272 | 92.6 (91.2–94.1), n=1264 | 92.6 (91.0–94.1), n=1105 |
| Qwen3.5-9B (parent) | 1280 px | 91.7 (90.2–93.2), n=1272 | 91.6 (90.0–93.1), n=1264 | 91.6 (90.0–93.2), n=1105 |
| UI-Venus-2-9B | full resolution | 96.2 (95.0–97.2), n=1272 | 96.1 (95.0–97.2), n=1264 | 96.2 (95.0–97.3), n=1105 |
| UI-Venus-2-9B | 1280 px | 95.8 (94.7–96.9), n=1272 | 95.8 (94.7–96.8), n=1264 | 95.9 (94.8–97.1), n=1105 |
| Qwen3.5-4B, 4-bit (Q4_K_M GGUF) | 1280 px | 89.9 (88.2–91.4), n=1272 | 89.8 (88.1–91.5), n=1264 | 90.0 (88.2–91.8), n=1105 |
| Bonsai 2 4B, repaired | 1280 px | 67.0 (64.4–69.6), n=1272 | 67.0 (64.5–69.6), n=1264 | 66.9 (64.1–69.7), n=1105 |
| Ternary Bonsai 2 4B, original | 1280 px | 12.2 (10.5–14.0), n=1272 | 12.3 (10.5–14.2), n=1264 | 12.8 (10.9–14.8), n=1105 |
<!-- end:ssv2_three_ways -->

### ScreenSpot-Pro (1,581 cases: professional software at up to 6K)

<!-- begin:sspro -->
| Model | Input | All 1,581 (95% interval) | Text | Icon | Dev | Creative | CAD | Scientific | Office | OS | Unreadable answers |
|---|---|---|---|---|---|---|---|---|---|---|---|
| UI-Venus-2-9B | full resolution | 71.9 (69.7–74.1) | 82.1 | 55.5 | 74.6 | 64.8 | 71.7 | 69.7 | 83.5 | 69.9 | 1 |
<!-- end:sspro -->

### OSWorld-G (564 cases, 54 of them with no valid target)

<!-- begin:osworld_g_refined -->
| Model | Input | All 564, refined instructions (95% interval) | The 510 with a target | Refused correctly (of 54 with no target) | Refused a real target | Unreadable answers |
|---|---|---|---|---|---|---|
<!-- end:osworld_g_refined -->

<!-- begin:osworld_g -->
| Model | Input | All 564, original instructions (95% interval) | The 510 with a target | Refused correctly (of 54 with no target) | Refused a real target | Unreadable answers |
|---|---|---|---|---|---|---|
<!-- end:osworld_g -->

### macOS app windows, the target platform (2,106 cases on 134 screenshots)

Screen2AX-Task, restricted to the 27 app keys that no training run saw ([MAC_DATA.md](MAC_DATA.md)). The cases of one screenshot are not independent, so the interval over screenshots is the honest one.

<!-- begin:mac -->
| Model | Input | All 2,106 unless noted (95% interval over cases) | Interval over screenshots | Unreadable answers | Refusals |
|---|---|---|---|---|---|
| Bonsai 2 9B, repaired [v3-gentle] | 1280 px | 44.9 (42.8–47.1) | 39.4–50.9 | 0 | 0 |
| Bonsai 2 9B, repaired [v2] | 1280 px | 40.9 (38.8–43.1) | 35.7–46.7 | 0 | 0 |
| Bonsai 2 9B, repaired [v4-gentle] | 1280 px | 43.8 (41.7–46.0) | 38.5–49.7 | 0 | 0 |
| Ternary Bonsai 2 9B, original | 1280 px | 13.2 (11.7–14.6) | 10.6–16.1 | 0 | 12 |
| Qwen3.5-9B (parent) | 1280 px | 63.8 (61.8–65.9) | 57.6–70.4 | 0 | 7 |
| UI-Venus-2-9B | 1280 px | 68.4 (66.4–70.3) | 63.0–73.9 | 0 | 2 |
| Qwen3.5-4B, 4-bit (Q4_K_M GGUF) | 1280 px | 58.8 (56.7–60.9) | 52.8–65.4 | 0 | 0 |
| Bonsai 2 4B, repaired | 1280 px | 32.7 (30.7–34.8) | 28.2–37.8 | 0 | 0 |
| Ternary Bonsai 2 4B, original | 1280 px | 3.7 (2.9–4.5) | 2.7–4.8 | 0 | 259 |
<!-- end:mac -->

**Labels checked by eye.** Some of this set's boxes do not match their request ([RESOLUTION_BY_EYE.md](RESOLUTION_BY_EYE.md)). We looked at 150 evenly spaced cases, each as a crop with the box drawn and the request beside it, and asked whether a careful person doing the request would click inside the box. 114 labels are right, 17 are wrong (most often the box sits on a neighbouring control, or the request names an action the boxed control does not perform) and 19 cannot be decided from the crop. So about one label in nine is wrong and one in four is not clearly right, which caps what any model can score on the full set. The table gives every model on the 150 cases and on the 114 with a right label (`bench/mac_verified.json`).

<!-- begin:mac_verified -->
| Model, 1280 px | The cases looked at | Those whose label is right | Hits on the cases with a wrong or unclear label |
|---|---|---|---|
| Bonsai 2 9B, repaired [v3-gentle] | 38.7 (30.7–46.7), n=150 | 49.1 (40.3–57.9), n=114 | 2/36 |
| Bonsai 2 9B, repaired [v2] | 34.0 (26.7–42.0), n=150 | 43.9 (35.1–52.6), n=114 | 1/36 |
| Bonsai 2 9B, repaired [v4-gentle] | 38.0 (30.0–46.0), n=150 | 47.4 (38.6–56.1), n=114 | 3/36 |
| Ternary Bonsai 2 9B, original | 12.0 (7.3–17.3), n=150 | 14.9 (8.8–21.9), n=114 | 1/36 |
| Qwen3.5-9B (parent) | 62.7 (54.7–70.0), n=150 | 76.3 (68.4–84.2), n=114 | 7/36 |
| UI-Venus-2-9B | 76.0 (69.3–82.7), n=150 | 90.3 (85.1–95.6), n=114 | 11/36 |
| Qwen3.5-4B, 4-bit (Q4_K_M GGUF) | 60.7 (52.7–68.7), n=150 | 75.4 (67.5–83.3), n=114 | 5/36 |
| Bonsai 2 4B, repaired | 28.7 (21.3–36.0), n=150 | 36.0 (27.2–44.7), n=114 | 2/36 |
| Ternary Bonsai 2 4B, original | 4.7 (1.3–8.0), n=150 | 6.1 (1.8–10.5), n=114 | 0/36 |
<!-- end:mac_verified -->

### macOS, held-out AgentNet sessions (504 human click points)

A second, rougher macOS set: full desktops recorded by annotators, with a click point and no box, so a square of 1.2% of the image width around the click counts as the target. Other sessions of the same source were in the repair's training mix.

<!-- begin:mac_agentnet -->
Not run.
<!-- end:mac_agentnet -->

### Our generated screens (413 cases on 52 screens, seed 20261114)

Rendered from scratch with exact boxes ([bench/pointing](../bench/pointing/README.md)); no model can have seen them. The set has no case whose right answer is "nothing to point at".

<!-- begin:gen -->
| Model | Input | All 413 (95% interval) | Text, named | Text, by function | Icon, named | Icon, by function | Target large / medium / small / very small |
|---|---|---|---|---|---|---|---|
| Bonsai 2 9B, repaired [v2] | 1280 px | 38.3 (33.7–43.1) | 63.2 | 45.1 | 21.9 | 17.4 | 63.3 / 59.5 / 28.9 / 10.1 |
<!-- end:gen -->

### Tool calling

Our seeded set (400 cases in eight categories, [bench/toolcall](../bench/toolcall/README.md)). A model that never calls a tool scores 25%.

<!-- begin:toolcall -->
Not run yet.
<!-- end:toolcall -->

BFCL v3, a 400-case evenly spaced subset of its five single-turn Python categories that are checked without running code, scored with our re-implementation of its check. These are not leaderboard numbers.

<!-- begin:bfcl -->
Not run yet.
<!-- end:bfcl -->

### What remains of the original model

<!-- begin:general -->
Not run yet.
<!-- end:general -->

### Cost

Measured on one RTX PRO 6000 (96 GB) with nothing else on the GPU.

<!-- begin:cost -->
Not run yet.
<!-- end:cost -->

### Input size

Accuracy on ScreenSpot-v2 by the longer side of the image sent, with the mean number of prompt tokens in brackets.

<!-- begin:sizes_ssv2 -->
Not run yet.
<!-- end:sizes_ssv2 -->

### One look or two

The second look shows the model a window around its first answer (a third of each side of the original screenshot, shown at 1024 px) and asks again.

<!-- begin:looks -->
Not run yet.
<!-- end:looks -->

### Shipped file in llama.cpp

The tables above read the pack in PyTorch. The file a Mac actually runs is a GGUF: `weights/export_gguf.py` wrote patch v2 into PrismML's `PTQ1_0` file (203 of 427 tensors rewritten, every other byte identical), and that file was served by `llama-server` with the same prompt and images.

<!-- begin:runtime -->
Not run yet.
<!-- end:runtime -->

### Paired comparisons

The new model at 1280 px against each other model on the cases both answered (ScreenSpot-v2 without the 8 overlap cases).

<!-- begin:paired -->
| Set | New model at 1280 px against | Cases both answered | New | Other | Difference in points (95% interval) | Only the new model right | Only the other right | McNemar exact p |
|---|---|---|---|---|---|---|---|---|
| ssv2 | original Bonsai, 1280 px | 1264 | 82.1 | 43.4 | +38.7 (+35.7 to +41.6) | 527 | 38 | <0.0001 |
| ssv2 | parent, 1280 px | 1264 | 82.1 | 91.6 | -9.5 (-11.6 to -7.5) | 31 | 151 | <0.0001 |
| ssv2 | parent, full resolution | 1264 | 82.1 | 92.6 | -10.5 (-12.7 to -8.5) | 30 | 163 | <0.0001 |
| ssv2 | UI-Venus, 1280 px | 1264 | 82.1 | 95.8 | -13.7 (-15.8 to -11.6) | 13 | 186 | <0.0001 |
| ssv2 | UI-Venus, full resolution | 1264 | 82.1 | 96.1 | -14.0 (-16.1 to -11.9) | 16 | 193 | <0.0001 |
| ssv2 | Qwen3.5-4B 4-bit, 1280 px | 1264 | 82.1 | 89.8 | -7.7 (-9.8 to -5.5) | 49 | 146 | <0.0001 |
| mac | original Bonsai, 1280 px | 2106 | 44.9 | 13.2 | +31.8 (+27.7 to +36.1) | 708 | 39 | <0.0001 |
| mac | parent, 1280 px | 2106 | 44.9 | 63.8 | -18.9 (-22.0 to -15.9) | 66 | 464 | <0.0001 |
| mac | UI-Venus, 1280 px | 2106 | 44.9 | 68.4 | -23.5 (-26.2 to -20.7) | 44 | 538 | <0.0001 |
| mac | Qwen3.5-4B 4-bit, 1280 px | 2106 | 44.9 | 58.8 | -13.9 (-16.9 to -11.1) | 98 | 390 | <0.0001 |
<!-- end:paired -->

## Detector assist

An ablation, run offline on the answers already saved: a small UI-element detector looks at the same screenshot, and a model's point is moved to the centre of a detected box when it lands inside one or within 20 px of one (at 1280 px scale). Three pretrained detectors were tried at 1280 px on the long side; nothing was trained. The scripts and the full sweep stayed on the GPU machine (`detector/`) and are not in this repository; the numbers are in `bench/results/detector.json`.

**Detectors**

| | OmniParser v2 `icon_detect` | OmniParser v2 `icon_detect_v3` | MacPaw Screen2AX elements |
|---|---|---|---|
| Source | `microsoft/OmniParser-v2.0` | same repository | `macpaw-research/yolov11l-ui-elements-detection` |
| Licence of the weights | AGPL-3.0 | MIT | AGPL-3.0 |
| Size on disk | 41 MB | 281 MB | 51 MB |
| Parameters | 20.1 M | 69.4 M | 25.3 M |
| GPU, ms per screenshot (median of 30, GPU shared with other jobs) | 36 | 37 | 35 |
| CPU, 8 threads, ms per screenshot | 174 | 1,901 | 199 |

**Snap test** (`icon_detect_v3`, confidence 0.05, 20 px). "Outside only" moves a point only when it lies outside every detected box. Runs marked partial were not finished when this was computed.

| Model and set | Cases | Hits before | Full snap: hits after (misses fixed / hits broken) | Outside only: hits after (misses fixed / hits broken) |
|---|---|---|---|---|
| Bonsai 2 9B repaired [v2], Mac, 1280 px | 2,106 | 862 | 1,037 (197 / 22) | 954 (95 / 3) |
| Bonsai 2 9B repaired [v2], ScreenSpot-v2, 1280 px | 1,272 | 977 | 993 (71 / 55) | 1,024 (57 / 10) |
| UI-Venus-2-9B, Mac, 1280 px | 2,106 | 1,440 | 1,405 (6 / 41) | 1,440 (0 / 0) |
| Qwen3.5-9B, Mac, 1280 px (partial) | 1,849 | 1,148 | 1,121 (24 / 51) | 1,152 (5 / 1) |
| Qwen3.5-9B, ScreenSpot-v2, full resolution | 1,272 | 1,179 | 1,140 (4 / 43) | 1,178 (2 / 3) |
| UI-Venus-2-9B, ScreenSpot-v2, full resolution | 1,272 | 1,223 | 1,177 (0 / 46) | 1,221 (0 / 2) |

- **It helps the repaired Bonsai and nobody else.** On the Mac set the repaired 9B goes from 40.9% to 49.2% with a full snap and to 45.3% with the safer outside-only rule; on ScreenSpot-v2 from 76.8% to 80.5% (outside only). The references lose hits with a full snap and are unchanged with the outside-only rule: their misses are not near-misses.
- **Why:** the repaired 9B has 384 Mac misses and 163 ScreenSpot-v2 misses within 20 px of the target; UI-Venus has 66 and 2.
- **Sweep:** confidence 0.05 is best for both OmniParser detectors; 20 px beats 10 and 40 for the outside-only rule. The other two detectors gain less (best net over the five complete runs: +136 hits for `icon_detect_v3`, +93 MacPaw, +85 `icon_detect`).
- **Not yet run on the 4B or on v3-gentle**, which is what this was aimed at: their answers were not saved when the test ran. `analyze.py` on the pod picks them up when rerun.

**Recall ceiling** (confidence 0.05): the share of targets with a detected box overlapping by at least 0.5, and the share with a detected box whose centre lies inside the target, which is what a pick-a-box design needs.

| Detector and set | Overlap at least 0.5 | Box centre inside the target | Boxes per screenshot |
|---|---|---|---|
| `icon_detect_v3`, Mac | 79.2% | 92.6% | 58 |
| `icon_detect_v3`, ScreenSpot-v2 | 69.4% | 90.9% | 50 |
| `icon_detect_v3`, ScreenSpot-Pro | 45.7% | 58.2% | 189 |
| `icon_detect`, Mac | 60.4% | 87.7% | 50 |
| `icon_detect`, ScreenSpot-v2 | 80.1% | 91.8% | 45 |
| `icon_detect`, ScreenSpot-Pro | 62.9% | 78.4% | 343 |
| MacPaw, Mac | 63.6% | 86.6% | 84 |
| MacPaw, ScreenSpot-v2 | 51.6% | 86.6% | 82 |
| MacPaw, ScreenSpot-Pro | 54.5% | 67.7% | 288 |

On Mac targets under 16 px the best detector still finds 86% by centre. Recall on the Mac set is above the 85% bar set for training our own detector, so none was trained. The pick-a-box run (numbered marks, ask for the number) was not run.

## Published scores of other models ("as reported")

Collected on 14 and 15 November 2026 by opening each linked page. We did not run these. Settings differ between sources (input resolution, a second zoom pass, a planner, original or refined OSWorld-G instructions), so read them as context, not as a ranking.

<!-- begin:published -->
| Model (as reported) | ScreenSpot-v2 | ScreenSpot-Pro | OSWorld-G | OSWorld-G refined | Source | Setting |
|---|---|---|---|---|---|---|
| UI-Venus-2-9B | – | 73.0 | – | 78.5 | [own model card and README](https://huggingface.co/inclusionAI/UI-Venus-2-9B) | Single pass, reasoning off, temperature 0. ScreenSpot-v2 and original OSWorld-G not reported. |
| UI-Venus-2-27B | – | 74.1 | – | 79.1 | [own model card and README](https://github.com/inclusionAI/UI-Venus) | Same setting. |
| Qwen3.5-9B | – | 65.2 | – | – | [own model card](https://huggingface.co/Qwen/Qwen3.5-9B) | No resolution or reasoning-mode note. Nothing reported on ScreenSpot-v2 or OSWorld-G. |
| Qwen3.5-4B | – | 60.3 | – | – | [Qwen3.5-9B model card (comparison column)](https://huggingface.co/Qwen/Qwen3.5-9B) | Full precision, not the 4-bit file we ran. |
| UI-Venus-1.5-8B | 95.9 | 68.4 | 69.7 | 74.1 | [own paper](https://arxiv.org/abs/2602.09082) | End to end, no zoom. |
| MAI-UI-8B | 95.2 | 65.8 | 60.1 | 68.6 | [own paper](https://arxiv.org/abs/2512.22047) | Single pass. With its zoom-in second pass: ScreenSpot-Pro 70.9, OSWorld-G 64.2 / 72.9. |
| Holo2-8B | 93.2 | 58.9 | – | 70.1 | [own model card](https://huggingface.co/Hcompany/Holo2-30B-A3B) | Single step. The card does not say which OSWorld-G instructions; the UI-Venus-1.5 paper lists the value as refined. |
| GTA1-7B | 92.4 | 50.1 | 55.1 | 67.7 | [own paper](https://arxiv.org/abs/2507.05791) | The ScreenSpot-Pro leaderboard lists 55.5 for the released weights. |
| OpenCUA-7B | 92.3 | 50.0 | 55.3 | – | [own paper](https://arxiv.org/abs/2508.09123) | Up to 12,845,056 pixels per image. The paper does not say which OSWorld-G instructions. |
| Jedi-7B | 91.7 | 39.5 | 54.1 | 63.8 | [own paper; refined value from the GTA1 paper's table](https://arxiv.org/abs/2505.13227) | Images limited to about 1080p. |
| GUI-Actor-7B (Qwen2.5-VL) | 92.1 | 44.6 | – | – | [own paper](https://arxiv.org/abs/2506.03143) | Without its verifier model. |
| UI-TARS-1.5 (size not stated) | 94.2 | 61.6 | – | – | [own README](https://github.com/bytedance/UI-TARS) | The 7B release is listed there at 49.6 on ScreenSpot-Pro; other papers' own runs of it give 39.0 to 42.0. |
| UI-TARS-7B | 91.6 | 35.7 | 47.5 | – | [own paper; OSWorld-G from the Jedi paper's table](https://arxiv.org/abs/2501.12326) |  |
| Qwen3-VL-8B | 91.7 | 49.9 | 54.8 | 64.4 | [MAI-UI paper's table (their run)](https://arxiv.org/abs/2512.22047) | Not Qwen's own numbers. |
| Qwen2.5-VL-7B | 88.8 | 26.8 | 31.4 | – | [Jedi paper's table; ScreenSpot-Pro from its leaderboard](https://gui-agent.github.io/grounding-leaderboard/) |  |
| UGround-V1-7B | 87.6 | 31.1 | 36.4 | – | [GUI-Actor paper's table, ScreenSpot-Pro leaderboard, Jedi paper's table](https://gui-agent.github.io/grounding-leaderboard/) |  |
| OS-Atlas-7B | 84.1 | 18.9 | 27.7 | – | [UI-TARS paper's table, ScreenSpot-Pro leaderboard, Jedi paper's table](https://gui-agent.github.io/grounding-leaderboard/) | Other papers print 85.1 for the same ScreenSpot-v2 cells. |
| ShowUI-2B | 77.3 | 7.7 | – | – | [grounding leaderboard](https://gui-agent.github.io/grounding-leaderboard/) |  |
| SeeClick | 55.1 | 1.1 | – | – | [UI-TARS paper's table, ScreenSpot-Pro leaderboard](https://gui-agent.github.io/grounding-leaderboard/) |  |
| OpenAI Operator | 70.5 | 36.6 | 40.6 | 57.8 | [Jedi and GTA1 papers' tables](https://arxiv.org/abs/2505.13227) | Not OpenAI's own numbers. |
| Claude (Computer Use) | – | 17.1 | – | – | [ScreenSpot-Pro leaderboard](https://gui-agent.github.io/grounding-leaderboard/) | The 2024 computer-use model. |
| Claude Haiku 5.5 | – | 85.4 | – | – | [Inkling 2 Small release table](https://thinkingmachines.ai/news/inkling-2-small/) | 88.7 when the model may run Python on the image. Not Anthropic's own number. |
| GPT-6 Luna | – | 81.1 | – | – | [Inkling 2 Small release table](https://thinkingmachines.ai/news/inkling-2-small/) | 87.7 with Python. |
| Gemini 3.8 Flash | – | 65.7 | – | – | [Inkling 2 Small release table](https://thinkingmachines.ai/news/inkling-2-small/) | 93.7 with Python. |
| Inkling 2 Small | – | 83.8 | – | – | [own release post](https://thinkingmachines.ai/news/inkling-2-small/) | 92.0 with Python. Its model card says images are capped at 4,096 px on the long side. |
<!-- end:published -->

## Method

### Models and files

| Name in the tables | What was run | Source |
|---|---|---|
| Bonsai 2 9B, repaired | PrismML's pack `Ternary-Bonsai-2-9B-mlx-2bit` (`model.safetensors`, 3.46 GB, sha256 `b8ebd134…`) with the patch `bonsai2-9b-point-v2.patch.safetensors` (243 MB, sha256 `fde98d68…`: multipliers of 176 matrices, codes of 2, 27 small tensors) applied in memory by `weightlab/state.py` | this project |
| Ternary Bonsai 2 9B, original | The same pack, no patch | `prism-ml/Ternary-Bonsai-2-9B-mlx-2bit` |
| Qwen3.5-9B (parent) | The released checkpoint in its own precision (bfloat16) | `Qwen/Qwen3.5-9B` |
| UI-Venus-2-9B | The released checkpoint (bfloat16) | `inclusionAI/UI-Venus-2-9B` |
| Qwen3.5-4B, 4-bit | `Qwen3.5-4B-Q4_K_M.gguf` (2.74 GB) with `mmproj-BF16.gguf` (0.68 GB), served by `llama-server` from PrismML's llama.cpp fork (`prism` branch, commit `6447906`), one slot | `unsloth/Qwen3.5-4B-GGUF` |
| Ternary Bonsai 2 4B, original | The pack `Ternary-Bonsai-2-4B-mlx-2bit` (1.87 GB) | `prism-ml/Ternary-Bonsai-2-4B-mlx-2bit` |

The Bonsai packs are read by the weight lab ([WEIGHTLAB.md](WEIGHTLAB.md)): ternary codes times per-group multipliers, folded into bfloat16 matrices, with the vision tower (byte-identical to the parent's) and tokenizer taken from the parent. The full-precision models are loaded with transformers 5.23.0. All of these run in PyTorch 2.9.1 on one NVIDIA RTX PRO 6000 Blackwell (96 GB, CUDA 12.8). One change is made to every PyTorch model: the vision tower's first step, a convolution whose stride equals its kernel, is computed as the equivalent matrix product (`weightlab.core._fast_patch_embed`), because the convolution takes 8 s per screenshot on this GPU; on the 317 development cases this moves the teacher-forced score by at most 0.002.

### Prompt and decoding

Every model is asked with the Qwen3.5 family's grounding prompt, verbatim from UI-Venus-2's reference evaluator (`models/grounding/ui_venus2_gd.py`, branch `UI-Venus-2` of github.com/inclusionAI/UI-Venus), as one user message with the image first:

```
Output the center point of the position corresponding to the following instruction: 
{instruction}. 

The output should just be the coordinates of a point, in the format [x,y]. Additionally, if the task is infeasible (e.g., the task is not related to the image), the output should be [-1,-1].
```

- One trailing full stop of the instruction is removed first, as the reference evaluator does. No system message, no tools.
- Thinking is off (`enable_thinking=False` in the chat template). Decoding is greedy, at most 32 new tokens for pointing, 512 for tool calls, 8 for MMLU and 32 for ChartQA.
- One request at a time; nothing is batched. The GGUF model is served with one slot, the only setting in which `llama-server` repeats its answers exactly (FINDINGS.md, section 6).
- The same prompt is used for the repaired Bonsai: it is the prompt it was trained with.

### What the model sees

- **Full resolution**: the screenshot as it is, shrunk only above 12,845,056 pixels (the reference evaluator's `max_pixels`); the model's own processor then rounds each side to a multiple of 32.
- **1280 px** (and 448, 640, 896, 1920 in the size table): the screenshot is first shrunk with Lanczos resampling so that its longer side is at most that many pixels, never enlarged. This is what a screen assistant that captures at that size sends, and it is the size the repair was trained at.

Answers are coordinates on a 0 to 1000 scale and are mapped back to the pixels of the original screenshot.

### Scoring

- A case is right when the point lies inside the target box (edges included) or polygon (OSWorld-G's own rule).
- The answer is read with the reference evaluator's rules: `[x, y]`; four numbers are a box and count as its centre; `[-1,-1]` is a refusal.
- A refusal is right only when the case has no target (54 OSWorld-G cases). An answer with no readable coordinates is a miss and is counted in its own column.
- ScreenSpot-v2 boxes are `[x, y, width, height]` in the source and are converted; OSWorld-G boxes likewise.

### Statistics

- 95% intervals are percentile bootstraps over cases: 10,000 resamples, seed 20261114 ([bench/stats.py](../bench/stats.py)). They describe how much the score would move with a different draw of cases, not run-to-run or hardware variation: each number is one greedy run.
- Where one screenshot carries several cases (macOS: 15.7 on average; our generated screens: 8), an interval that resamples screenshots is given as well.
- Comparisons between two models use the cases both answered: the difference with a paired bootstrap interval, and McNemar's exact test on the cases where exactly one is right.

### Is the harness right?

- **A published number reproduces.** UI-Venus-2-9B on all 1,581 ScreenSpot-Pro cases at full resolution: 71.9% (text 82.1, icon 55.5), against 73.0 on its model card, a difference of 1.1 points. The first 660 cases ran on the RTX PRO 6000 and the remaining 921 on the DGX Spark, with the same code.
- **It agrees with the weight lab.** For patch v2 at 1280 px on the 158-case development eighth, this runner and the lab's own script give the same 116 hits and the same mean prompt length (923 tokens). For the references on the same cases the lab on the Spark got 152 (UI-Venus) and 145 (parent); this runner on the pod gets 153 and 143.
- No answer of any model on the headline sets was unreadable.

### The export loses about 0.01 of the development score

During training the model scored 0.810 / 0.797 on the two development eighths of ScreenSpot-v2 (teacher-forced probability of an answer inside the box, [WEIGHTLAB.md](WEIGHTLAB.md)); the exported patch v2 scores 0.800 / 0.790 on every machine. `experiments/bench_patch_check.py` settled where the difference comes from, inside the lab session on the Spark (it changes the weights in place and puts them back; `bench/results/patch_check.json`):

| State | Select (159) | Report (158) |
|---|---|---|
| The training state, as found in the session | 0.8101 | 0.7974 |
| Original pack + patch v2 on the Spark (the shipped artifact) | 0.8010 | 0.7901 |
| The same with the vision tower's first step as a matrix product (as on the pods) | 0.8007 | 0.7917 |
| Training state rebuilt from its files (patch v1 + the best checkpoint of experiment 010) | 0.8099 | 0.7974 |
| Rebuilt, with the multipliers rounded to float16 | 0.8118 | 0.7980 |
| Rebuilt, with only the 27 small tensors that the patch kept | 0.7999 | 0.7894 |
| After putting everything back | 0.8101 | 0.7974 |

- **It is the export, not the hardware.** The patch gives the same score on the Spark as on the pods.
- **It is not the float16 multipliers.** Rounding them changes nothing.
- **It is the small full-precision tensors.** Training moved 112 of them (layer-norm weights and the small parts of the linear-attention layers). `weights/make_patch.py` writes a small tensor only when it moved by more than 4e-3 of its largest value, which kept 27 and dropped 85. Dropping those 85 reproduces the exported score.
- Every number in this report for the repaired model is the exported artifact, so it includes this loss. The export rule was not changed here; a rule that compares against the pack's value rounded to bfloat16 would keep all 112.

### Reproducing

Each run writes a `.meta.json` next to its per-case file with the command line, the git commit of the code, library versions, the GPU, the model files (with the patch's sha256), the decoding settings and the prompt. The runs behind this report:

<!-- begin:environment -->
| Model | Files | Jobs | Code (git commit) | torch | transformers | GPU |
|---|---|---|---|---|---|---|
| Bonsai 2 9B, repaired [v3-gentle] | Ternary-Bonsai-2-9B-mlx-2bit + bonsai2-9b-point-v3-gentle.patch.safetensors (sha256 bcea0672) | 2 | 5f176be+ | 2.9.1+cu128 | 5.23.0 | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Bonsai 2 9B, repaired [v2] | Ternary-Bonsai-2-9B-mlx-2bit + bonsai2-9b-point-v2.patch.safetensors (sha256 fde98d68) | 3 | 7f27eb0+ | 2.9.1+cu128 | 5.23.0 | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Bonsai 2 9B, repaired [v4-gentle] | Ternary-Bonsai-2-9B-mlx-2bit + bonsai2-9b-point-v4-gentle.patch.safetensors (sha256 d3249925) | 2 | 5f176be+ | 2.9.1+cu128 | 5.23.0 | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Ternary Bonsai 2 9B, original | Ternary-Bonsai-2-9B-mlx-2bit | 2 | 5f176be+ | 2.9.1+cu128 | 5.23.0 | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Qwen3.5-9B (parent) | Qwen3.5-9B | 3 | 5f176be+, 7f27eb0+ | 2.9.1+cu128 | 5.23.0 | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| UI-Venus-2-9B | UI-Venus-2-9B | 4 | 5f176be+, 7f27eb0+, ab007d6 | 2.14.1+cu130, 2.9.1+cu128 | 5.23.0 | NVIDIA GB10 |
| Qwen3.5-4B, 4-bit (Q4_K_M GGUF) | Qwen3.5-4B-Q4_K_M.gguf | 2 | 5f176be+ | 2.9.1+cu128 | 5.23.0 | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Bonsai 2 4B, repaired | Ternary-Bonsai-2-4B-mlx-2bit + bonsai2-4b-point-v1.patch.safetensors (sha256 e9013fd9) | 2 | 5f176be+ | 2.9.1+cu128 | 5.23.0 | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Ternary Bonsai 2 4B, original | Ternary-Bonsai-2-4B-mlx-2bit | 2 | 5f176be+ | 2.9.1+cu128 | 5.23.0 | NVIDIA RTX PRO 6000 Blackwell Server Edition |
<!-- end:environment -->

The commands are in [bench/README.md](../bench/README.md). Per-case files (model, prompt id, raw answer, parsed point, hit, seconds) are on the machine that ran them, under `benchruns/`, and are not in the repository; the summaries in `bench/results/` are.

## Contamination

What each model could have seen of each test set, as far as we can establish it.

**The repaired Bonsai (our training).** Patch v2 was trained on generated screens (`bench/pointing`, train split) and on macOS screens from OS-Atlas, Screen2AX-Tree, ScaleCUA, ShowUI and AgentNet ([MAC_DATA.md](MAC_DATA.md), `weightlab/mixes.py`).

| Test set | Used in training | Used to choose checkpoints or settings | Known overlap |
|---|---|---|---|
| ScreenSpot-v2 | No | Yes: one eighth (159 cases, "select") chose between runs; another eighth ("report") was quoted during development | 8 desktop cases show screens that also occur in OS-Atlas / ScaleCUA macOS training data. Both are removed in the third column of the "three ways" table |
| ScreenSpot-Pro | No | No. 40 cases were used early on to diagnose the original model | Not checked by image comparison |
| OSWorld-G | No | No | Not checked by image comparison (Ubuntu screens; our real training screens are macOS) |
| macOS app windows (Screen2AX-Task, reserved apps) | No | 60 to 200 of its cases were scored during training runs as a progress readout, and one run kept its best checkpoint by the ScreenSpot-v2 select score, not by this set | None: split by app key, no app or screenshot on both sides; closest train/test thumbnail difference 3.8 of 255 |
| AgentNet macOS, held-out sessions | Other sessions of the same source were in the mix (1,500 cases) | No | Split by recording session, near-duplicate screenshots removed; the same applications occur on both sides |
| Our generated screens (dev split) | The train split of the same generator | A 150 to 200 case sample was a progress readout | None by construction: the splits share no layout family, theme, icon, label or wording (`bench/pointing/check_disjoint.py`) |
| Our tool-calling set (dev split) | No (patch v2 trained on pointing only) | No | None by construction |
| BFCL v3, MMLU, ChartQA | No | No | Public for years; any of the base models may have seen them in pre-training. They are used here only to compare the repaired model with the original and the parent, which share that exposure |

**The reference models.** We do not know what Qwen3.5 or UI-Venus-2 were trained on beyond what their cards say. UI-Venus-2 is a GUI specialist trained on large collections of screens; its card does not list them, so overlap with ScreenSpot-v2, ScreenSpot-Pro, OSWorld-G or Screen2AX cannot be excluded. Our generated screens and tool-calling cases were created for this project in November 2026 and cannot be in any released model.

## Limitations

- **One run per number.** Decoding is greedy, so a rerun on the same hardware repeats, but intervals cover the choice of cases only. Different hardware changes a few answers per thousand.
- **The Bonsai models are measured in PyTorch, not in the runtime they ship in.** The pack is folded to bfloat16 and run on an NVIDIA GPU. The exported GGUF file was also run through llama.cpp on one set (see "Shipped file in llama.cpp"); MLX on the Mac was not benchmarked here.
- **Input size is part of the comparison.** The repair was trained at 1280 px; the references are strongest at full resolution. Both are shown; neither alone is the whole picture.
- **Pointing only, one step.** No benchmark here measures a multi-step computer-use task (OSWorld, AndroidWorld) or the assistant built around the model.
- **The macOS set is one source.** 27 app keys, app windows not full desktops, short human commands. AgentNet's held-out cases have click points with a tolerance box, not element boxes.
- **BFCL is a subset with our own checker**, and thinking is off everywhere, so those numbers are not comparable with leaderboards.
- **Qwen3.5-4B was run only as a 4-bit GGUF in llama.cpp.** Differences from the PyTorch models include the runtime.
- **Speed and memory are for a server GPU in PyTorch.** They rank the models against each other; they are not what a Mac laptop does. Mac measurements are in [FINDINGS.md](../FINDINGS.md), section 3 and 8.
- **The macOS labels are noisy.** Of 150 checked cases 17 have a wrong box and 19 cannot be decided, so about one label in nine is wrong and one in four is not clearly right; scores on the full set understate every model.
- **Checkpoints kept moving.** `v3-gentle` is the one reported; patches made after it were not measured here.

## Not run

The plan was cut back on 15 November to the headline sets and the detector ablation. Not run, or run only in part:

- **ScreenSpot-Pro**: only UI-Venus-2-9B at full resolution (the reproduction above). No other model.
- **OSWorld-G**: not run (the data and loader are in place).
- **AgentNet held-out macOS sessions**: not run.
- **Our generated screens, our tool-calling set, the canary**: queued behind the headline runs for our models only; any that finished appear in their tables, the rest read "not run".
- **BFCL v3 subset, MMLU, ChartQA**: not run.
- **Input sizes**: 896, 640 and 448 px were queued for our models only; not run for the references. Full resolution on ScreenSpot-v2 was run for the parent and UI-Venus only.
- **Second look**: not run in this harness (the lab measured +2.5 points for patch v2 on 158 cases).
- **Cost table**: not run. File sizes are in the method table; speeds on the Mac are in FINDINGS.md.
- **Shipped GGUF in llama.cpp**: the patched file was exported and verified byte for byte, but not benchmarked.
- **Detector assist for the 4B and v3-gentle, and the pick-a-box run**: not run.
- **Later checkpoints** (mixed-size 9B and 4B, the actions patches, `v2-full`): not run.
