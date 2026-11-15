# Lane 6: D4, the decoder with a finer-than-token output (15 Nov 02:30), on the frozen best
# 4B trunk bonsai2-4b-point-v3-fable. D4 = the H1 shape (2 layers x 768 on layer 20) whose output is a mask:
# 32 x 32 scores per image token by pixel shuffle, target = the box as a mask, loss 0.5 BCE + 0.5 Dice,
# rate 1e-4, point = centre of mass of the top region. Its decoder layers start from H1's 6,000-step
# weights (the mask output layers start fresh) to save time; H1 itself continues beside it as the control
# on the same trunk. 6,000 more steps, long sides half 1280 half 896, select and report at 1280 and 896
# every 1,000 steps (on target, within 20 px), a copy of the heads at every score.
# Needs a fresh 4B session and lab/ckpt/heads016_4b_big_heads.pt.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v3-fable.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"] or not os.path.exists(f"{lab.dir}/ckpt/heads016_4b_big_heads.pt"):
    raise RuntimeError(f"this needs a fresh 4B session on the v3-fable patch and the five-head file (size {lab.size}, stack {lab.stack})")
chosen010 = "pod"
SPECS16 = [("H1 dec2x768 k20", "cross_dec:768:2", 20, (20,)), ("D4 mask 2x768 k20", "cross_mask:768:2", 20, (20,))]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16 = {"pointer": 1e-3, "cross": 1e-4}, 12000, 1000, "4b_mask_decoder", 16, 0
SIZES16, SCORE_SIZES16, ALLSETS16, KEEP_ROUNDS16 = (1280, 896), (896,), True, True
ONLYSETS16 = ("select", "report", "select at 896 px", "report at 896 px")
RESUME16, RESUME_AS16 = f"{lab.dir}/ckpt/heads016_4b_big_heads.pt", {"D4 mask 2x768 k20": "H1 dec2x768 k20"}
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
KEEP_ROUNDS16 = None
