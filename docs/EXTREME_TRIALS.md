# Extreme trials on the 9B (experiment 022)

Run 15 Nov 2026 on one rented GPU machine, from v3-gentle. Code: `experiments/022_extreme_*.py`; numbers: `lab/exp022_extreme.json` (kept with the run, not in this repository). Select and report are teacher-forced p_hit; generated hits are written answers on the report set (158 cases, 1280 px). Two hits up or down is noise: weights that differ by less than 3e-8 moved the count from 130 to 132.

| Trial | Setting | Select | Report | Generated hits | Canary (exact / nll) | Minutes | Can ship under the Bonsai requirement |
|---|---|---|---|---|---|---|---|
| base | v3-gentle | 0.837 | 0.851 | 130 (82.3%) | 0.92 / 0.065 | 4.5 | yes |
| T0 | constant offset from select (dx -2.8, dy +0.6) subtracted from report answers | - | - | 130 (+0) | - | 1 | yes |
| T1 | parent's vision tower + merger (sanity) | 0.838 | 0.852 | 132 | 0.92 / 0.065 | 1.4 | yes |
| T1 | UI-Venus vision tower | 0.838 | 0.851 | 131 | 0.92 / 0.065 | 1.4 | yes |
| T1 | UI-Venus vision tower + merger | 0.838 | 0.852 | 132 | 0.92 / 0.065 | 1.4 | yes |
| T1 | UI-Venus tower, then 400 gentle updates, layers 0..31 | 0.848 | 0.845 | 127 (80.4%) | 0.92 / 0.065 | 8.4 | yes |
| T1 | control: the same 400 updates with Bonsai's own tower | 0.848 | 0.839 | 127 (80.4%) | 0.94 / 0.064 | 7.4 | yes |
| T4 | coarse-to-fine, (a) acceptable digits equal, step 500 | 0.566 | 0.580 | 83 (52.5%) | 0.92 / 0.063 | about 7 | yes |
| T4 | (a), step 1000 | 0.754 | 0.751 | 121 (76.6%) | 0.92 / 0.063 | about 14 | yes |
| T4 | (a), step 1500 | 0.779 | 0.784 | 116 (73.4%) | 0.90 / 0.063 | 22.4 | yes |
| T4 | coarse-to-fine, (b) digits weighted by box share, step 500 | 0.393 | 0.440 | 80 (50.6%) | 0.92 / 0.058 | about 7 | yes |
| T4 | (b), step 1000 | 0.547 | 0.576 | 111 (70.3%) | 0.92 / 0.059 | about 14 | yes |
| T4 | (b), step 1500 | 0.614 | 0.641 | 118 (74.7%) | 0.92 / 0.058 | 22.5 | yes |
| T2 | teacher's change written into the multipliers | not run | | | | | yes |
| T3 | vision tower's last 6 blocks and merger trainable | not run | | | | | yes |

**T0, coordinate bias.** No usable offset: answers near their target sit -2.8 thousandths in x (standard error 2.0) and +0.6 in y (1.4), under the 3-thousandth bar, and subtracting it adds no hit on report.
Only large targets and mobile screens lean left of centre (about -11 and -10 thousandths), which costs nothing because those boxes are wide.
Next: nothing here; the best constant shift picked on the report set itself would add 2 hits, which is the noise.

**T1, vision transplant.** There is nothing to transplant: UI-Venus-2-9B's vision tower and merger are the parent's, and Bonsai ships the same weights (every tensor within 3e-8), so all three swaps are the baseline within noise.
The 400-update tune over layers 0..31 gives the same result with or without the "transplant": select +0.011, report -0.007 to -0.013, 3 fewer generated hits, so it did not win and the 1,500-step continuation and the export were not run.
Next: UI-Venus differs from the parent only in the language model, so the one way left to use it is T2 (written, not run) or as a teacher on answers.

**T4, coarse-to-fine coordinates.** Worse than the usual order after 1,500 steps: (a) reaches select 0.779 and 116 hits against 0.837 and 130 for v3-gentle, and the all-layers run in the usual order (`experiments/lanes/lane3b_all_layers.py`) was at select 0.867 by step 1000. Per position, (a) for x and y against v3-gentle (which pools both): hundreds equal on report (0.926, 0.921 against 0.925) and lower for y on select (0.947, 0.892 against 0.937); tens worse (report 0.919, 0.915 against 0.958); units equal (1.000).
(b), the exact box-share targets, does not beat (a): 118 against 116 hits at the end is a tie, it was 10 hits behind at step 1000, and its digit probabilities are far lower (select 0.614), partly because its loss asks for a spread over the box and not for mass on acceptable digits.
Both were still rising when the rate had decayed, and the format started from 0.095, so this shows the cost of relearning the answer format in 1,500 gentle steps, not its ceiling. Next: continue (a) from its step-1500 checkpoint for 3,000 more steps at a constant rate before judging; checkpoints `x22_t4a_step1500` and `x22_t4b_step1500` were kept.

**T2, T3.** Dropped before they ran; the files are written and untested.
The T3 variant that matches UI-Venus's vision outputs would start at zero loss and only hold the tower in place, since the two towers are identical.
Next: T2 is the cheaper of the two (no training for its first table) and the only one that uses what UI-Venus changed.
