# Lane 3: reward passes on the simulator's pointing set for the 9B's written answers (15 Nov;
# experiment 030). Start: the orchestrator patch u3000 (the model in the app's planner
# GGUF), so the app's own model learns from its verified misses; planner turns and tool calls ride along
# as anchors. A smoke pass first, then 4 passes of 1,200 fresh cases and 300 gentle updates.
# Needs a fresh 9B session, the u3000 patch, the simulator sets and data/mac/planner_sim_s1.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-orch-v1-u3000.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 9B session on the orchestrator patch u3000 (size {lab.size}, stack {lab.stack})")
ANCHORS30, PATCHNAME30, TAG30 = ("data/mac/planner_sim_s1",), "bonsai2-9b-orch-reward", "9b_reward_macsim"
SMOKE30 = True
exec(open(f"{lab.root}/experiments/030_reward_loop_9b.py").read())
exec(open(f"{lab.root}/experiments/030_reward_loop_9b.py").read())
