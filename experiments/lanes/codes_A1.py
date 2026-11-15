# 4B codes sweep, arm A1: codes of layers 4..19, codes rate 0.01 (see codes_arm.py).
ARM, ARM_LO, ARM_HI, ARM_LR = "A1", 4, 19, 0.01
exec(open(f"{lab.root}/experiments/lanes/codes_arm.py").read())
