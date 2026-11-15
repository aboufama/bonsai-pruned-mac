# Lane 3: carry the base model on gently (block 4..19: multipliers and small parts, no codes),
# with a learning rate ten times lower than the run that produced it, scored every 250 steps.
exec(open(f"{lab.root}/experiments/_prelude.py").read())
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 2500, 250, 1e-4, 2e-5, False, 100, 60, "gentle_nocodes"
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
