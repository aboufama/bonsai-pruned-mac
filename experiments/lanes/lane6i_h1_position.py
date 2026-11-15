# Lane 6, test P2 (15 Nov 02:20): does writing each image token's screen position into its
# vector help the decoder? Two heads side by side on the frozen 4B (v2-mixed), both starting from H1's
# 6,000-step weights:
#   H1    continued as it is
#   H1p   the same weights plus a position module: the centre of each image token's square (x, y in 0..1),
#         sine and cosine at 32 frequencies per axis (128 numbers), one linear layer that starts at zero,
#         added to the image-token states the decoder attends over
# To 12,000 steps, scored every 1,000 on select and report at 1280 and 896 (on target, within 20 px).
# The difference between the two columns is the answer. Note: H1 already receives a small position input
# (x, y and their sines through a little network added after the projection); H1p adds the richer one.
# Runs in lane 6's session (same frozen trunk as the five-head job).
import os

if not globals().get("prelude_done") or lab.size != "4B" or not os.path.exists(f"{lab.dir}/ckpt/heads016_4b_big_heads.pt"):
    raise RuntimeError("run this in lane 6's 4B session, after lane6g_4b_big_heads")
chosen010 = "pod"
SPECS16 = [("H1 dec2x768 k20", "cross_dec:768:2", 20, (20,)), ("H1p +position", "cross_decp:768:2", 20, (20,))]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16 = {"pointer": 1e-3, "cross": 3e-4}, 12000, 1000, "4b_h1_position", 16, 0
SIZES16, SCORE_SIZES16, ALLSETS16, KEEP_ROUNDS16 = (1280, 896), (896,), True, True
ONLYSETS16 = ("select", "report", "select at 896 px", "report at 896 px")
RESUME16, RESUME_AS16 = f"{lab.dir}/ckpt/heads016_4b_big_heads.pt", {"H1p +position": "H1 dec2x768 k20"}
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
KEEP_ROUNDS16 = None
