# One arm of the 4B codes sweep (15 Nov 01:25): train the 4B's ternary CODES for real.
# Every run so far moved multipliers and small tensors and flipped almost no code (the codes rate of
# 0.002 was too low: a code flips only after its latent value has moved by 0.5). Each arm starts from
# bonsai2-4b-point-v2-mixed (0.749 / 0.749), opens the codes of layers ARM_LO..ARM_HI at codes rate
# ARM_LR with multipliers and small parts as on lane 6 (lr 1e-4 / 2e-5, warm-up 100), long sides half
# 1280 and half 896, 1,000 steps, scored every 250: select and report at 1280 and 896 (teacher-forced)
# and the share of codes flipped, in all and by group of four layers. At the end, for the best
# checkpoint: generated hits on the report set at 1280 and 896, and the canary. Stops early if select
# is more than 0.05 under the start at steps 250 and 500. Control: lane 6's multiplier-only run.
# Set before running: ARM (name), ARM_LO, ARM_HI, ARM_LR. Runs in a fresh 4B session on the v2-mixed
# patch, or after another arm in the same session (that arm's start checkpoint is restored first).
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v2-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B":
    raise RuntimeError(f"this needs a 4B session (size {lab.size})")
if "E" in globals():                                  # a previous arm ran here: put its block back to the start
    if getattr(E, "training", False) or not os.path.exists(start_path):
        raise RuntimeError("the previous arm's block is still open or its start checkpoint is gone; restart the lab session")
    E.D.restore(start_path)
    lab.stack[:] = [f"patch:{os.path.basename(PATCH)}"]
elif lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session on the v2-mixed patch (stack {lab.stack})")
_a, _b = fS.evaluate(0), fR.evaluate(0)
fS.discard(); fR.discard()
print("arm %s: codes of layers %d..%d open at rate %g; start state select %.3f   report %.3f   (v2-mixed: 0.749 / 0.749)" % (
    ARM, ARM_LO, ARM_HI, ARM_LR, _a["p_hit"], _b["p_hit"]), flush=True)
if abs(_a["p_hit"] - 0.749) > 0.005 or abs(_b["p_hit"] - 0.749) > 0.005:
    raise RuntimeError("the model is not at the v2-mixed state; restart the lab session and queue this arm again")
LO10, HI10 = ARM_LO, ARM_HI
STEPS10, EVERY10, LR_CODES10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 1000, 250, ARM_LR, 1e-4, 2e-5, True, 100, 60, f"4b_codes_{ARM}"
STOPMIN10 = 500
SIZES10 = (1280, 896)
SIZE_SCORES10, MAC_SIZES10 = (1280, 896), (896,)
KEEP10, TEACHER10, TEACH10, EXTRA10, EXTRA_SHARE10, EXTRA_SCORES10, DROP10 = None, None, 0.0, None, None, None, None
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
