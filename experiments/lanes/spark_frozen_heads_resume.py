# Spark: the long frozen-trunk head run, RESUMED from its step-6,000 file (all three heads); results go to tag frozen20k_b.
# Original header: the long frozen-trunk head run (14 Nov 23:45). The two best designs of
# experiment 016, "pointer q20 k20" and "cross q20 k0+12+20", continued from lab/ckpt/heads016_v2.pt
# (step 4,000) to 20,000 steps on the trunk they were trained on, which stays frozen. The Spark's
# training mix is the only one with AgentNet in it, which is why this run is here. A third head starts
# fresh beside them: the cross head with the repaired click output (kind "cross_qclick": the click
# logit reads the last prompt position; in 016 the cross heads' click output sat at 50%).
# All four sets are scored every 2,000 steps. Runs in the Spark's long-lived lab session, where
# experiment 016 ran (it needs that session's model state, sets and training packs).
import os

_missing = [n for n in ("chosen010", "packs", "fS", "fR") if n not in globals()]
if _missing or not os.path.exists(f"{lab.dir}/ckpt/heads016_v2.pt"):
    raise RuntimeError(f"this needs the session experiment 016 ran in (missing: {_missing}) and lab/ckpt/heads016_v2.pt")
SPECS16 = [("pointer q20 k20", "pointer", 20, 20), ("cross q20 k0+12+20", "cross", 20, (0, 12, 20)),
           ("crossq q20 k0+12+20", "cross_qclick", 20, (0, 12, 20))]
LR16, STEPS16, ROUND16, TAG16, ALLSETS16 = 5e-4, 20000, 2000, "frozen20k_b", True
SEED16, HEADSEED16, RESUME16 = 16, 0, f"{lab.dir}/ckpt/heads016_frozen20k.pt"      # paused at step 6,000 on 15 Nov 00:59 for the benchmark job
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
