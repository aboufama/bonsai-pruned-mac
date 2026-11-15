# Lane 3, after lane3b_all_layers (15 Nov 00:55): UI-Venus as a teacher on answers.
# (A) Experiment 022: one pass of UI-Venus-2-9B over every pointing case of the training mix at 1280 px.
#     Kept per case: its greedy point, whether that is inside the labelled box, and its probability
#     over the ten digit tokens at each digit it wrote (lab/venus_teacher.json and .npz).
# (B) The block trainer from the best 9B state (lane 3b's best, which this session holds, if it scores
#     above v3-gentle; else v3-gentle) with  loss = label loss + 1.0 x cross-entropy to the teacher's
#     digit distributions  on cases where the teacher's point is inside the box, label loss only
#     elsewhere; Mac cases the teacher puts outside the box are left out. Layers 4..31 as lane 3b,
#     multipliers and small parts, no codes, lr 1e-4 / 2e-5, warm-up 100, 3,000 steps, 896-weighted
#     long sides, scores every 500 at 1280 / 896 / 640 and Mac windows at 1280 and 896.
# Compare with the no-teacher runs at equal steps: lane 3b (same layers, from v3-gentle, 1280 only)
# and lane 8b (block 4..19, 896-weighted, from v3-gentle).
# Needs hf/UI-Venus-2-9B on the pod. Runs in lane 3's session, no restart.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-gentle.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if not os.path.exists(f"{lab.paths['V']}/config.json"):
    raise RuntimeError("UI-Venus-2-9B is not on this machine (hf/UI-Venus-2-9B)")
for _n in ("J", "E", "T14"):
    if getattr(globals().get(_n), "training", False) or getattr(globals().get(_n), "open", False) is True:
        raise RuntimeError(f"{_n} is still open in this session; restart the lab session and queue this job again")
# Start state (00:30): lane 3b's best checkpoint if it ended above v3-gentle, else v3-gentle.
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("session state: select %.3f   report %.3f   stack %s" % (_a["p_hit"], _b["p_hit"], lab.stack), flush=True)
if _a["p_hit"] + _b["p_hit"] > 0.837 + 0.853 + 0.004:
    print("start state: the session's own (lane 3b's best), above v3-gentle's 0.837 / 0.853", flush=True)
else:
    print("patch applied over the session's state:", state.apply_patch(lab, PATCH), os.path.basename(PATCH))
    lab.stack[:] = [f"patch:{os.path.basename(PATCH)}"]
    _a, _b = fS.evaluate(4), fR.evaluate(4)
    fS.discard(); fR.discard()
    print("start state (v3-gentle): select %.3f   report %.3f   (lane 3 measured 0.837 / 0.853)" % (_a["p_hit"], _b["p_hit"]), flush=True)
    if abs(_a["p_hit"] - 0.837) > 0.01 or abs(_b["p_hit"] - 0.853) > 0.01:
        raise RuntimeError("the model is not at the v3-gentle state; restart the lab session and queue this job again")

# Teacher pass cut down (00:45): every Mac case, the generator cases thinned to 300 per folder
# (they have exact boxes; cases without teacher data train on the label loss only).
FOLDERS22 = ("mac:",)
exec(open(f"{lab.root}/experiments/022_venus_clean.py").read())
FOLDERS22, LIMIT22 = ("gen:",), 300
exec(open(f"{lab.root}/experiments/022_venus_clean.py").read())

LO10, HI10 = 4, 31
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 3000, 500, 1e-4, 2e-5, False, 100, 60, "venus_teach"
SIZES10 = (896, 896, 896, 896, 640, 768, 1024, 1280)
SIZE_SCORES10, MAC_SIZES10 = (1280, 896, 640), (896,)
KEEP10, TEACHER10, TEACH10 = f"{lab.dir}/venus_teacher.json", f"{lab.dir}/venus_teacher.npz", 1.0
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
KEEP10, TEACHER10, TEACH10 = None, None, 0.0     # variables persist in the session; later jobs train as before
