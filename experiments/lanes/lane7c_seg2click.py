# Lane 7: the Seg2Click transplant on the best 4B trunk (experiment 026), then on the original 4B.
# Needs a fresh 4B session, hf/Seg2Click-Qwen3.5-4B and the full hf/Qwen3.5-4B weights.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v3-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session on the v3-mixed patch (size {lab.size}, stack {lab.stack})")
TAG26, UPDATES26, RANK26 = "seg2click_on_v3mixed", 400, 16
exec(open(f"{lab.root}/experiments/026_seg2click_transplant.py").read())
