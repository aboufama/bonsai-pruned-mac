# Lane 4: one set of weights that points (as a tool call) and calls tools (experiment 014).
exec(open(f"{lab.root}/experiments/_prelude.py").read())
UPDATES14, LR14, ACC14, TAG14 = 800, 2e-4, 2, "joint_u800"
exec(open(f"{lab.root}/experiments/014_joint.py").read())
