# Lane 6: the 4B mixed-size recipe of lane 6c continued for 3,000 more steps, in a FRESH 4B session started
# on the verified patch of lane 6c's best checkpoint (bonsai2-4b-point-v2-mixed: select 0.749, report
# 0.749). Replaces lane6e, which died at its first checkpoint when the pod's volume filled up (another
# session's download). Layers 4..31, multipliers and small parts, no codes, lr 1e-4 / 2e-5, warm-up 100,
# 896-weighted long sides, scores every 500 steps at 1280 / 1024 / 896 / 768 / 640, Mac windows at 896.
# It is also the control for the Fable-data arm on lane 4 (equal steps).
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v2-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session on the v2-mixed patch (size {lab.size}, stack {lab.stack})")
LO10, HI10 = 4, 31
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 3000, 500, 1e-4, 2e-5, False, 100, 60, "4b_mixed_896_b"
SIZES10 = (896, 896, 896, 896, 640, 768, 1024, 1280)
SIZE_SCORES10, MAC_SIZES10 = (1280, 1024, 896, 768, 640), (896,)
KEEP10, TEACHER10, TEACH10, EXTRA10, EXTRA_SHARE10, EXTRA_SCORES10, DROP10 = None, None, 0.0, None, None, None, None
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
