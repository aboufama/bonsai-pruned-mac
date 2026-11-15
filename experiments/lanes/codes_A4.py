# 4B codes sweep, arm A4: codes of layers 0..31, codes rate 0.003 (see codes_arm.py).
ARM, ARM_LO, ARM_HI, ARM_LR = "A4", 0, 31, 0.003
exec(open(f"{lab.root}/experiments/lanes/codes_arm.py").read())
