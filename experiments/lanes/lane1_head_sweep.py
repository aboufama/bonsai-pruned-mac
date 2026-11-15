# Lane 1: which depth should a frozen-model pointing head read? Eight pointer heads, 6,000 steps.
exec(open(f"{lab.root}/experiments/_prelude.py").read())
chosen010 = "pod"
SPECS16 = [("pointer q16 k16", "pointer", 16, 16), ("pointer q18 k18", "pointer", 18, 18), ("pointer q20 k20", "pointer", 20, 20),
           ("pointer q22 k22", "pointer", 22, 22), ("pointer q24 k24", "pointer", 24, 24), ("pointer q20 k16", "pointer", 20, 16),
           ("pointer q24 k20", "pointer", 24, 20), ("pointer q20 k12", "pointer", 20, 12)]
LR16, STEPS16, ROUND16, TAG16 = 1e-3, 6000, 1000, "sweep"
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
