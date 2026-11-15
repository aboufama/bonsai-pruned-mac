# Lane 6: the 9B's written answers on neighbouring controls (15 Nov 04:25). In use
# of the app the tuned 9B clicked the arrow beside Calendar's "Today" button: three small controls in a
# row. From bonsai2-9b-point-v3-mixed896 (lane 6's sizes result checked out lower on generated answers:
# 84.2% against 86.1% on report), block trainer as lane 8b (block 4..19, multipliers and small parts, no
# codes, gentle, 2,500 steps), long sides 1280 and 896. Neighbour cases (another labelled box within
# 80 px sideways in the same row; tools/neighbour_cases.py) are drawn three times as often and Apple's
# own apps twice as often again; extra sets: the Fable train cases and 6,000 of GroundCUA's neighbour
# cases, a third of the steps. Scored before and every 500 steps: select and report at 1280 and 896, the
# held-out Mac windows, and the held-out neighbour slice (600 cases on 98 Screen2AX-Task screenshots that
# no training list uses). Needs a fresh 9B session and the files tools/neighbour_cases.py writes.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-mixed896.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"] or not os.path.exists(f"{lab.root}/data/mac/neighbour_ids.json"):
    raise RuntimeError(f"this needs a fresh 9B session on the v3-mixed896 patch and data/mac/neighbour_ids.json (size {lab.size}, stack {lab.stack})")
LO10, HI10 = 4, 19
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 2500, 500, 1e-4, 2e-5, False, 100, 60, "9b_neighbours"
SIZES10 = (1280, 896)
SIZE_SCORES10, MAC_SIZES10 = (1280, 896), (1280,)
KEEP10, TEACHER10, TEACH10 = None, None, 0.0
_fb = f"{lab.root}/data/mac/fable_teacher"
DROP10 = f"{_fb}/bad_source_cases.json" if os.path.exists(f"{_fb}/bad_source_cases.json") else None
EXTRA10 = [("mac:fable_teacher:train", None, None, 1), ("mac:neighbour_gcua:train", 6000, None, 1)]
EXTRA_SHARE10, EMPH10, EMPH_FILE10 = 0.33, True, "_neighbours.py"
EXTRA_SCORES10 = {"neighbour slice": "mac:neighbour_test:test", "fable test": "mac:fable_teacher:test"}
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
EXTRA10 = EXTRA_SHARE10 = DROP10 = EXTRA_SCORES10 = EMPH10 = EMPH_FILE10 = None      # variables persist in the session
