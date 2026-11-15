# Lane 4: do the Fable-written cases help the 4B (the demo model)? The 4B recipe of lane 6 (layers 4..31,
# multipliers and small parts, no codes, lr 1e-4 / 2e-5, warm-up 100, 896-weighted long sides) from the
# verified patch of lane 6c's best checkpoint (bonsai2-4b-point-v2-mixed: 0.749 / 0.749), plus every
# data/mac/fable_teacher train case on half of the steps; 3,000 steps, scored every 500 like lane 6 plus
# mac:fable_teacher:test by kind (direct, intent, next). The control at equal steps is lane 6's own
# continuation (lane6f, tag 4b_mixed_896_b), which has no Fable cases; the 85 flagged source cases are
# left out here and not there. The absent requests are not used.
# Needs a fresh 4B session: tools/restart_lane.sh <this file> 4B
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v2-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
_fb = f"{lab.root}/data/mac/fable_teacher"
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"] or not os.path.exists(f"{_fb}/cases.jsonl"):
    raise RuntimeError(f"this needs a fresh 4B session on the v2-mixed patch and data/mac/fable_teacher (size {lab.size}, stack {lab.stack})")
LO10, HI10 = 4, 31
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 3000, 500, 1e-4, 2e-5, False, 100, 60, "4b_fable_with"
SIZES10 = (896, 896, 896, 896, 640, 768, 1024, 1280)
SIZE_SCORES10, MAC_SIZES10 = (1280, 1024, 896, 768, 640), (896,)
KEEP10, TEACHER10, TEACH10 = None, None, 0.0
DROP10 = f"{_fb}/bad_source_cases.json"
EXTRA10, EXTRA_SHARE10 = [("mac:fable_teacher:train", None, None, 3)], 0.5
EXTRA_SCORES10 = {"fable test": "mac:fable_teacher:test"}
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
EXTRA10 = EXTRA_SHARE10 = DROP10 = EXTRA_SCORES10 = None      # variables persist in the session
