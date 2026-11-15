# 4B codes sweep, arm A2: codes of layers 0..31, codes rate 0.01 (see codes_arm.py).
ARM, ARM_LO, ARM_HI, ARM_LR = "A2", 0, 31, 0.01
exec(open(f"{lab.root}/experiments/lanes/codes_arm.py").read())
