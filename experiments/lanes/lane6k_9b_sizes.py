# Lane 6: a 9B written-answer run aimed at small targets (15 Nov 03:05). The miss split showed
# the 9B's whole gap is targets under 24 px (56.2% on target against about 90% for the rest). From
# bonsai2-9b-point-v3-mixed896 with the block trainer as in lane 8b (block 4..19, multipliers and small
# parts, no codes, gentle, 2,500 steps), long sides spread over 896, 1280 and 1600, small targets drawn
# three times as often, the Fable train cases and the GroundCUA slice as extra sets (a third of the steps).
# Scored every 500 steps at 1600, 1280 and 896 on select and report, Mac windows at 1280.
# Needs a fresh 9B session, data/mac/fable_teacher and (if present) data/mac/groundcua_200k.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-mixed896.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 9B session on the v3-mixed896 patch (size {lab.size}, stack {lab.stack})")
LO10, HI10 = 4, 19
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 2500, 500, 1e-4, 2e-5, False, 100, 60, "9b_sizes"
SIZES10 = globals().get("SIZES6K", (896, 1280, 1600))
SIZE_SCORES10, MAC_SIZES10 = (1600, 1280, 896), (1280,)
KEEP10, TEACHER10, TEACH10 = None, None, 0.0
_fb = f"{lab.root}/data/mac/fable_teacher"
DROP10 = f"{_fb}/bad_source_cases.json" if os.path.exists(f"{_fb}/bad_source_cases.json") else None
EXTRA10 = [(n, None, None, 1) for n in ("mac:fable_teacher:train", "mac:groundcua_200k:train")
           if os.path.exists(f"{lab.root}/data/mac/{n.split(':')[1]}/cases.jsonl")]
EXTRA_SHARE10, EMPH10 = 0.33, True
EXTRA_SCORES10 = {"fable test": "mac:fable_teacher:test"} if os.path.exists(f"{_fb}/cases.jsonl") else None
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
EXTRA10 = EXTRA_SHARE10 = DROP10 = EXTRA_SCORES10 = EMPH10 = None      # variables persist in the session
