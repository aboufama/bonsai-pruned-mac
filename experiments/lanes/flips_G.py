# Lane 2, design G: code flips chosen by evidence and checked (experiment 024), on the best 4B
# (bonsai2-4b-point-v3-mixed, 0.762 / 0.766), layers 4..19, 20 rounds of 256 packs, 0.005% of the codes
# per round, held-out check on 128 packs, scores every 5 rounds. Needs a fresh 4B session.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v3-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session on the v3-mixed patch (size {lab.size}, stack {lab.stack})")
LO24, HI24, ROUNDS24, EVERY24, ACC24, HELD24, SHARE24, TAG24, SIZES24 = 4, 19, 20, 5, 256, 128, 5e-5, "4b_G", (1280, 896)
exec(open(f"{lab.root}/experiments/024_evidence_flips.py").read())
