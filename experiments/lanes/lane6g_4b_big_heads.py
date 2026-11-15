# Lane 6: bigger pointing heads on the frozen 4B (the idea: a pointing model well under a billion
# parameters that uses the thinking model's cached image read). Trunk frozen at the best 4B pointer
# (bonsai2-4b-point-v2-mixed: written answers 67.1% at 1280 px, 58.2% at 896 px on the report set).
# Four heads trained side by side, 6,000 steps, training long sides half 1280 and half 896:
#   H0  the pointer head at layer 20 (the baseline: 61% on the repaired 4B after 4,000 steps)
#   H1  decoder, 2 layers, width 768: request tokens at layer 20 attend to the image tokens at layer 20
#   H2  decoder, 4 layers, width 1024, image states of layers 12 and 20 concatenated
#   H3  like H2 but reading only the vision tower's output (layer 0) and layer 8, request tokens at layer 8
#   H4  the purest form ("keep the eyes, make the execution layers tiny"): decoder, 6 layers, width 1024;
#       its image input is the vision tower's output tokens as handed to the language model and its request
#       tokens are the model's own token embeddings (state 0): no language-model layer runs at all
# Scored on select every 1,000 steps; at the end on select / report / fresh / Mac app windows at 1280 and
# 896, with the share within 20 px, the parameter counts and the milliseconds per answer of each head
# alone (given the model's states; the trunk's time for the request tokens is not in that figure).
# Needs a fresh 4B session: tools/restart_lane.sh <this file> 4B
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v2-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session on the v2-mixed patch (size {lab.size}, stack {lab.stack})")
chosen010 = "pod"
SPECS16 = [("H0 pointer q20 k20", "pointer", 20, 20),
           ("H1 dec2x768 k20", "cross_dec:768:2", 20, (20,)),
           ("H2 dec4x1024 k12+20", "cross_dec:1024:4", 20, (12, 20)),
           ("H3 dec4x1024 k0+8", "cross_dec:1024:4", 8, (0, 8)),
           ("H4 dec6x1024 eyes", "cross_dec:1024:6", 0, (0,))]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16 = {"pointer": 1e-3, "cross": 3e-4}, 6000, 1000, "4b_big_heads", 16, 0
SIZES16, SCORE_SIZES16, ALLSETS16 = (1280, 896), (896,), False
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
