# Lane 2: last planner stage before the 08:30 stop: a DAgger pass from planner u1500 (lane 6, no thoughts:
# 73.7% of dev turns fully right) on ALL of rollout round 1 (501 states the planner reached with the
# oracle's step, five times each, plus 109 verified turns), the simulator's oracle turns at their final
# size (87,348) and the rule turns; 600 screenshot steps; tools; pointing 30%. 1,000 updates, scored every
# 500. Patches bonsai2-9b-planpoint-v1-dagger2-u<step>. Needs a fresh 9B session and those folders.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-planpoint-v1-u1500.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"] or not os.path.exists(f"{lab.root}/data/mac/planner_rollout_r1"):
    raise RuntimeError(f"this needs a fresh 9B session on {os.path.basename(PATCH)} and data/mac/planner_rollout_r1 (size {lab.size}, stack {lab.stack})")
UPDATES27, EVERY27, LR27, ACC27, TAG27, PATCHNAME27, THOUGHT27 = 1000, 500, 1e-4, 2, "planpoint_9b_dagger2", "bonsai2-9b-planpoint-v1-dagger2", False
POINT_SHARE27, NEIGHBOUR27, NOSTART27 = 0.3, True, True
PLANNER27, STEPS27, PLANNER_N27, PLANNER_DEV27 = ("data/mac/planner_rollout_r1", "data/mac/planner_sim_s1", "data/mac/planner_rule_s1"), 600, 14000, 128
exec(open(f"{lab.root}/experiments/027_orchestrator.py").read())
