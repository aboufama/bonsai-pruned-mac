# Lane 3, second job: the block trainer over layers 4..31 (multipliers and small parts), gentle.
exec(open(f"{lab.root}/experiments/_prelude.py").read())
LO10, HI10, STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 4, 31, 2500, 250, 1e-4, 2e-5, False, 100, 60, "gentle_L4-31"
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
