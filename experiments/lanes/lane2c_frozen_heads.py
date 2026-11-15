# Lane 2, replacement job (14 Nov 23:35): pointing heads on a FROZEN trunk at the v2
# patch, long run. Started if lane2_joint_head still has written answers under 0.78 at step 2000.
# The two best designs of experiment 016 plus the best depth from lane 1's sweep, 20,000 steps on
# the full training mix (Mac sets included; one question in five packs is a target-absent
# negative, HeadBench.train's default), all four sets scored every 2,000 steps. The cross head's
# click output reads the last prompt position here (kind "cross_qclick" in weightlab/head.py),
# which is the repair being tested: in 016 it sat at 50%. Kind "cross" elsewhere is unchanged.
#
# Needs a fresh lab session: tools/restart_lane.sh experiments/lanes/lane2c_frozen_heads.py 9B
# (a stopped joint run leaves trained multipliers in memory, and this run must see the v2 trunk).
exec(open(f"{lab.root}/experiments/_prelude.py").read())
_left = [n for n in ("J", "T14", "T20", "E") if n in globals()]
if _left or len(lab.stack) != 1 or not lab.stack[0].startswith("patch:"):
    raise RuntimeError(f"the trunk is not the plain v2 patch (left over: {_left}, stack: {lab.stack}); "
                       "restart the lab session with tools/restart_lane.sh and queue this job again")
chosen010 = "pod"
# Best depth in lane 1's sweep (exp016_sweep.json, select after 5,000 steps): pointer q20 k20 71.7%,
# then q24 k24 64.8%, q22 k22 and q24 k20 61.6%, q20 k12 57.2%. So the best depth is 20 itself.
BEST_DEPTH_SPEC = ("pointer q20 k20", "pointer", 20, 20)
# dict.fromkeys drops the third spec if lane 1's best depth turns out to be q20 k20 itself
SPECS16 = list(dict.fromkeys([("pointer q20 k20", "pointer", 20, 20), ("cross q20 k0+12+20", "cross_qclick", 20, (0, 12, 20)),
                              BEST_DEPTH_SPEC]))
# Learning rate per kind of head: pointer heads 1e-3 (lane 1's sweep: pointer q20 k20 reached 71.7%
# on select after 5,000 steps at 1e-3, against 62.3% after 4,000 at 5e-4 on the Spark), the cross
# head 5e-4 (what it had in experiment 016: 63.5% on select; 1e-3 is high for its attention layers).
LR16, STEPS16, ROUND16, TAG16, ALLSETS16 = {"pointer": 1e-3, "cross": 5e-4}, 20000, 2000, "frozen20k", True
SEED16, HEADSEED16 = 16, 0
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
