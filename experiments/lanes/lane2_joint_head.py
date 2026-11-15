# Lane 2: the layer-20 pointer head trained together with the multipliers of layers 4..19.
exec(open(f"{lab.root}/experiments/_prelude.py").read())
STEPS18, ROUND18, KIND18, LAYER18, LRS18, DIGITS18, TAG18 = 4000, 500, "pointer", 20, 2e-4, 1.0, "pointer_L20"
exec(open(f"{lab.root}/experiments/018_joint_head.py").read())
