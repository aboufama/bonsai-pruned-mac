# Lane 7 filler (15 Nov 02:27, while the Seg2Click transplant is being written): the H1
# decoder shape on the frozen 9B. Trunk = bonsai2-9b-point-v3-mixed896 (written answers 86.1% generated on
# report at 1280 px, 77.2% at 896). Heads: H0 pointer at layer 20 and H1 decoder 2 x 768 on layer 20, from
# scratch, 6,000 steps, long sides half 1280 half 896; select every 1,000 steps; at the end all four sets
# at 1280 and 896 with the share within 20 px and the milliseconds per answer. It answers what the decoder
# gives on the stronger trunk (the 9B is the careful mode). Needs a fresh 9B session.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-mixed896.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 9B session on the v3-mixed896 patch (size {lab.size}, stack {lab.stack})")
chosen010 = "pod"
SPECS16 = [("H0 pointer q20 k20", "pointer", 20, 20), ("H1 dec2x768 k20", "cross_dec:768:2", 20, (20,))]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16 = {"pointer": 1e-3, "cross": 3e-4}, 6000, 1000, "9b_decoder", 16, 0
SIZES16, SCORE_SIZES16, ALLSETS16, KEEP_ROUNDS16 = (1280, 896), (896,), False, True
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
KEEP_ROUNDS16 = None
