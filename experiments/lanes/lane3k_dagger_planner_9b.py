# Lane 3: a DAgger-style pass for the planner (15 Nov). The task environment ran
# planner u500 in the simulator (rollout round 1): for every state the model reached where the oracle knows
# the next step, a turn with the oracle's step as the answer (data/mac/planner_rollout_r1, each turn five
# times so it weighs in the list). Start: planner u1000 (lane 6, no thoughts). Training list: those rollout
# turns, the simulator's oracle turns (the 50,215-turn file), the rule turns; 600 screenshot steps; tools;
# pointing 30% with the neighbour emphasis. 1,000 updates, scored every 500 like the other planner lanes
# (dev turns per set, neighbour slice, report, tools, canary). Patches bonsai2-9b-planpoint-v1-dagger-u<step>.
# Needs a fresh 9B session, the u1000 patch, the planner folders, the step cases and neighbour files.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-planpoint-v1-u1000.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"] or not os.path.exists(f"{lab.root}/data/mac/planner_rollout_r1"):
    raise RuntimeError(f"this needs a fresh 9B session on planner u1000 and data/mac/planner_rollout_r1 (size {lab.size}, stack {lab.stack})")
UPDATES27, EVERY27, LR27, ACC27, TAG27, PATCHNAME27, THOUGHT27 = 1000, 500, 1e-4, 2, "planpoint_9b_dagger", "bonsai2-9b-planpoint-v1-dagger", False
POINT_SHARE27, NEIGHBOUR27 = 0.3, True
PLANNER27, STEPS27, PLANNER_N27, PLANNER_DEV27 = ("data/mac/planner_rollout_r1", "data/mac/planner_sim_s1", "data/mac/planner_rule_s1"), 600, 12000, 128
exec(open(f"{lab.root}/experiments/027_orchestrator.py").read())
