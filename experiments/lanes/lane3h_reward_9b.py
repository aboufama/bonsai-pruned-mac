# Lane 3, the research pod (15 Nov 04:56): reward fine-tuning of the
# 9B's written pointing answers against plain supervised training on the same cases (experiment 028).
# Start: bonsai2-9b-point-v3-mixed896. A smoke run first (the code is new), then 4 rounds of 300 cases.
# Needs a fresh 9B session.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-mixed896.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 9B session on the v3-mixed896 patch (size {lab.size}, stack {lab.stack})")
SMOKE28 = True
exec(open(f"{lab.root}/experiments/028_reward_pointing.py").read())
exec(open(f"{lab.root}/experiments/028_reward_pointing.py").read())
