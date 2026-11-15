# Lane 6, second job: which depth should a pointing head read on the 4B? The trunk is frozen at the
# repaired 4B that lane6_4b leaves in memory (020's multipliers, then the block trainer's best
# checkpoint over layers 4..31). Pointer heads reading layers 12, 16, 20, 24; 4,000 steps. The 4B is
# the size that fits the laptop best and its best depth may differ from the 9B's (20).
# Runs in the same lab session as lane6_4b (BONSAI_SIZE=4B), right after it.
if not globals().get("prelude_done") or "E" not in globals():
    raise RuntimeError("run this right after lane6_4b, in the same lab session")
chosen010 = "pod"
SPECS16 = [("pointer q12 k12", "pointer", 12, 12), ("pointer q16 k16", "pointer", 16, 16),
           ("pointer q20 k20", "pointer", 20, 20), ("pointer q24 k24", "pointer", 24, 24)]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16, ALLSETS16 = 1e-3, 4000, 1000, "4b_sweep", 16, 0, False
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
