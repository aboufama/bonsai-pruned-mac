# 4B codes sweep, arm A3: codes of layers 4..19, codes rate 0.03 (see codes_arm.py).
ARM, ARM_LO, ARM_HI, ARM_LR = "A3", 4, 19, 0.03
exec(open(f"{lab.root}/experiments/lanes/codes_arm.py").read())
