# Lane 6: the app's 9B, one model that plans and points with written answers (started
# 15 Nov 04:56). Start: the orchestrator's best patch (bonsai2-9b-orch-v1-u3000: 29.2% of
# reserved steps fully right). Trained jointly (experiment 027, multipliers of layers 4..31 and the head):
# step calls without thoughts, a pointing part of 40% that draws neighbour
# cases three times as often (Apple's apps twice again; Fable and GroundCUA neighbour cases added), tool
# calls with no-call cases. 2,500 updates, scored every 500: steps fully right, action right, the held-out
# neighbour slice and Mac windows (generated), report and select, the tool check, canary. A patch at
# every best (steps fully right + neighbour slice). Needs a fresh 9B session, the u3000 patch, the step
# cases with screenshots and the files tools/neighbour_cases.py writes.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-orch-v1-u3000.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"] or not os.path.exists(f"{lab.root}/data/mac/neighbour_ids.json"):
    raise RuntimeError(f"this needs a fresh 9B session on the orchestrator patch u3000 and data/mac/neighbour_ids.json (size {lab.size}, stack {lab.stack})")
UPDATES27, EVERY27, LR27, ACC27, TAG27, PATCHNAME27, THOUGHT27 = 2000, 500, 2e-4, 2, "planpoint_9b", "bonsai2-9b-planpoint-v1", False
POINT_SHARE27, NEIGHBOUR27 = 0.4, True
# 06:10: planner turns in format v1 built by rule from 601 real Mac control lists (tools/planner_rule_turns.py;
# the Fable-written lessons are held out on main's order) are the larger part of the step training; the old
# screenshot steps stay as a minority (1,200). The pointing part now has half its targets under 24 px and
# rule-written structured descriptions in its pool. The dev screens' turns are scored every round.
# 05:55: the simulator's oracle turns (planner_sim_s1: 13,241 train turns from 2,440 checker-verified episodes; 128
# held-out turns) lead the planner part; the rule turns stay beside them. Up to 9,000 planner turns in the list.
PLANNER27, STEPS27, PLANNER_N27, PLANNER_DEV27 = ("data/mac/planner_sim_s1", "data/mac/planner_rule_s1"), 1200, 9000, 128
exec(open(f"{lab.root}/experiments/027_orchestrator.py").read())
