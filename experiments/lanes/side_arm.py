# Design L (15 Nov 01:45): low-rank full-precision side paths beside every ternary matrix of
# layers 4..19 of the 4B, y += B (A x), rank SIDE_RANK10 (A small and random, B zero at the start), trained
# at 1e-4 together with the multipliers and small parts as usual (lr 1e-4 / 2e-5, warm-up 100). The ternary
# weights are not touched. From bonsai2-4b-point-v3-mixed (0.762 / 0.766), long sides half 1280 half 896,
# 1,500 steps, scored every 250 at 1280 and 896; generated answers and the canary for the best checkpoint.
# Control: lane 6's multiplier-only run (0.749 -> 0.762 in 500 steps). The side tensors are saved beside
# every checkpoint (lab/ckpt/qat010_<tag>_best_side.safetensors).
# Set SIDE_RANK10 before running. Needs a fresh 4B session: tools/restart_lane.sh <file> 4B
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v3-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session on the v3-mixed patch (size {lab.size}, stack {lab.stack})")
LO10, HI10 = 4, 19
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 1500, 250, 1e-4, 2e-5, False, 100, 60, f"4b_side_r{SIDE_RANK10}"
SIDE_LR10, STOPMIN10 = 1e-4, 750
SIZES10 = (1280, 896)
SIZE_SCORES10, MAC_SIZES10 = (1280, 896), (896,)
KEEP10, TEACHER10, TEACH10, EXTRA10, EXTRA_SHARE10, EXTRA_SCORES10, DROP10 = None, None, 0.0, None, None, None, None
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
SIDE_RANK10 = None                                   # variables persist in the session
