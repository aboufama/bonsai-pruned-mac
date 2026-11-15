# Lane 8: the block trainer exactly as on lane 3 (block 4..19, multipliers and small parts, no codes,
# gentle), but every training screenshot at a random long side from 640, 768, 896, 1024, 1280 instead
# of always 1280. Written answers are scored on select and report at 1280, 896 and 640 before and
# every 500 steps. Why: experiment 013 gave 73.4% at 1280 px, 51.9% at 896 and 30.4% at 640, while the
# information is still in the image at 640 (docs/RESOLUTION_BY_EYE.md). At 896 the image read costs
# 528 tokens instead of 923. Success: 896 within 5 points of 1280, 1280 not more than 2 lower.
# Needs a fresh lab session (the model must be the v2 patch).
exec(open(f"{lab.root}/experiments/_prelude.py").read())
LO10, HI10 = 4, 19
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 2500, 500, 1e-4, 2e-5, False, 100, 60, "mixed_size"
SIZES10, SIZE_SCORES10 = (640, 768, 896, 1024, 1280), (1280, 896, 640)
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
