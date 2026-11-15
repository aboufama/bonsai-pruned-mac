# Lane 1: reward passes on pointing for the best 4B pair (15 Nov 05:10; experiment 029).
# Start: the s12500 pair (83.5% on report from its files). A smoke pass first, then 6 passes of 3,000
# fresh cases and 600 steps. Needs a fresh 4B session, the pair, data/mac/neighbour_ids.json and
# data/mac/neighbour_gcua.
import os


PATCH = f"{lab.root}/export/patches/bonsai2-4b-joint-h1-trunk-s12500.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
_h = f"{lab.root}/export/heads/bonsai2-4b-joint-h1-dec2x768-L20-s12500.safetensors"
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"] or not os.path.exists(f"{lab.root}/data/mac/neighbour_ids.json"):
    raise RuntimeError(f"this needs a fresh 4B session on the s12500 trunk and data/mac/neighbour_ids.json (size {lab.size}, stack {lab.stack})")


SMOKE29, HEAD29 = True, _h
exec(open(f"{lab.root}/experiments/029_reward_loop_4b.py").read())
print(state.apply_patch(lab, PATCH), "(start state back after the smoke pass)", flush=True)
exec(open(f"{lab.root}/experiments/029_reward_loop_4b.py").read())
