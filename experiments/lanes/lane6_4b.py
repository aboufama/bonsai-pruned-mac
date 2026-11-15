# Lane 6: Bonsai 2 4B. Multipliers first, then the block trainer over layers 4..31 on the Mac mix.
PATCH = ""
exec(open(f"{lab.root}/experiments/_prelude.py").read())
UPDATES20, LR20 = 500, 1e-3
exec(open(f"{lab.root}/experiments/020_port_4b.py").read())
LO10, HI10, STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 4, 31, 2000, 250, 2e-4, 2e-5, False, 100, 60, "4b_block"
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
