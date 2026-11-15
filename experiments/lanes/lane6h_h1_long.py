# Lane 6, after the five-head job: H1 (decoder 2 x 768 on layer 20 of the frozen 4B v2-mixed) continued
# alone from its 6,000-step weights to 20,000 steps, scores on all sets every 2,000 steps, a copy of the
# head kept at every scored step. Runs in the session of lane6g (same frozen trunk), right after it.
import os

if not globals().get("prelude_done") or lab.size != "4B" or not os.path.exists(f"{lab.dir}/ckpt/heads016_4b_big_heads.pt"):
    raise RuntimeError("run this after lane6g_4b_big_heads, in the same 4B session")
chosen010 = "pod"
SPECS16 = [("H1 dec2x768 k20", "cross_dec:768:2", 20, (20,))]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16 = {"pointer": 1e-3, "cross": 3e-4}, 20000, 2000, "4b_h1_long", 16, 0
SIZES16, SCORE_SIZES16, ALLSETS16, RESUME16, KEEP_ROUNDS16 = (1280, 896), None, True, f"{lab.dir}/ckpt/heads016_4b_big_heads.pt", True
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
KEEP_ROUNDS16 = None
