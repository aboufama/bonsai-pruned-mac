# Lane 2, second job: the cross-attention head at layer 20 trained together with the multipliers.
exec(open(f"{lab.root}/experiments/_prelude.py").read())
STEPS18, ROUND18, KIND18, LAYER18, KEYS18, LRS18, DIGITS18, TAG18 = 5000, 500, "cross", 20, (20,), 2e-4, 1.0, "cross_L20"
exec(open(f"{lab.root}/experiments/018_joint_head.py").read())
