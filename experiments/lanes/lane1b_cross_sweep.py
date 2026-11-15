# Lane 1, second job: the cross-attention head around layer 20 (the best region so far), frozen model.
exec(open(f"{lab.root}/experiments/_prelude.py").read())
chosen010 = "pod"
SPECS16 = [("cross q20 k20", "cross", 20, (20,)), ("cross q18 k18", "cross", 18, (18,)), ("cross q22 k22", "cross", 22, (22,)),
           ("cross q20 k16+20", "cross", 20, (16, 20)), ("cross q20 k12+16+20", "cross", 20, (12, 16, 20)),
           ("cross q20 k0+20", "cross", 20, (0, 20)), ("cross q24 k20", "cross", 24, (20,)), ("cross q16 k16", "cross", 16, (16,))]
LR16, STEPS16, ROUND16, TAG16 = 5e-4, 8000, 1000, "cross_sweep"
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
