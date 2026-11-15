# Lane 7: the Seg2Click transplant on the 9B (experiment 026; 15 Nov 02:45). The 4B transplant
# failed outright (generated hits on report 70.9% -> 8.9% with the side paths; nothing within 5 points of
# the start), and this is the one run on the 9B that is run regardless, since the 9B has more room.
# Seg2Click-Qwen3.5-9B minus Qwen/Qwen3.5-9B as rank-16 side paths on bonsai2-9b-point-v3-mixed896, with
# and without its vision tower, generated hits on report, then 400 gentle updates under the best variant.
# Needs a fresh 9B session, hf/Seg2Click-Qwen3.5-9B and the full hf/Qwen3.5-9B weights. Weight files only.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-mixed896.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 9B session on the v3-mixed896 patch (size {lab.size}, stack {lab.stack})")
TAG26, UPDATES26, RANK26 = "seg2click_on_9b_mixed896", 400, 16
exec(open(f"{lab.root}/experiments/026_seg2click_transplant.py").read())
