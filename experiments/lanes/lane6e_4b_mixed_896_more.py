# Lane 6, fourth job: lane6c continued for 3,000 more steps from its best checkpoint (it was still rising at its last score: select 0.750, report 0.750 at step 2000). Same recipe.
# codes) with mixed long sides weighted to 896: half of the training screenshots at 896, the other
# half spread over 640, 768, 1024 and 1280. Gentle continuation: half the learning rate of the first
# run (1e-4 instead of 2e-4), warm-up 100. Written answers scored at 1280, 1024, 896, 768 and 640 on
# select and report before training and every 500 steps; Mac app windows at 1280 and 896.
# Runs in the same lab session as lane6_4b and the head sweep (the trunk is still the repaired 4B).
if not globals().get("prelude_done") or "E" not in globals():
    raise RuntimeError("run this after lane6_4b, in the same lab session")
LO10, HI10 = 4, 31
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 3000, 500, 1e-4, 2e-5, False, 100, 60, "4b_mixed_896_b"
SIZES10 = (896, 896, 896, 896, 640, 768, 1024, 1280)
SIZE_SCORES10, MAC_SIZES10 = (1280, 1024, 896, 768, 640), (896,)
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
