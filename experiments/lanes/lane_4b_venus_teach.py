# A 4B lane: UI-Venus-2-9B as a teacher on answers for the 4B (15 Nov 00:55). The teacher
# shares the tokenizer and the answer format, so its digit distributions apply to the 4B directly.
# (A) is model-independent: lab/venus_teacher.json and .npz are used if they are on this pod (copy
#     them from lane 3: about 5 MB), and experiment 022 only fills in what is missing, which needs
#     hf/UI-Venus-2-9B here (19 GB on the GPU beside the 4B).
# (B) The block trainer from the 4B state this session holds: layers 4..31, multipliers and small
#     parts, no codes, lr 1e-4 / 2e-5, warm-up 100, 3,000 steps, 896-weighted long sides, loss = label
#     loss + 1.0 x cross-entropy to the teacher's digit distributions where its point is inside the
#     box, Mac cases it puts outside left out. Scores every 500 at 1280 / 896 / 640, Mac windows at
#     1280 and 896. Compare with the no-teacher 4B runs at equal steps (lane 6's 4b_mixed_896, lane
#     2's 4b_block_cont).
# Runs in a 4B lab session whose model is the 4B to continue (after a prelude with the 4B patch, or
# after another 4B job that leaves its best state loaded).
import json
import os

if not globals().get("prelude_done") or lab.size != "4B":
    raise RuntimeError("run this in a 4B lab session that has run the prelude (BONSAI_SIZE=4B)")
for _n in ("J", "E", "T14"):
    if getattr(globals().get(_n), "training", False) or getattr(globals().get(_n), "open", False) is True:
        raise RuntimeError(f"{_n} is still open in this session; restart the lab session and queue this job again")
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("start state (this session's 4B): select %.3f   report %.3f   stack %s" % (_a["p_hit"], _b["p_hit"], lab.stack), flush=True)
_have = os.path.exists(f"{lab.dir}/venus_teacher.json") and os.path.exists(f"{lab.dir}/venus_teacher.npz")
print("teacher file on this pod: %s" % ("yes (%d cases judged)" % len(json.load(open(f"{lab.dir}/venus_teacher.json"))) if _have else "no"), flush=True)
if os.path.exists(f"{lab.paths['V']}/config.json"):
    exec(open(f"{lab.root}/experiments/022_venus_clean.py").read())      # skips every case already done
elif not _have:
    raise RuntimeError("neither lab/venus_teacher.json/.npz nor hf/UI-Venus-2-9B is on this machine")
else:
    print("UI-Venus is not on this pod: using the teacher file as it is")

LO10, HI10 = 4, 31
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 3000, 500, 1e-4, 2e-5, False, 100, 60, "4b_venus_teach"
SIZES10 = (896, 896, 896, 896, 640, 768, 1024, 1280)
SIZE_SCORES10, MAC_SIZES10 = (1280, 896, 640), (896,)
KEEP10, TEACHER10, TEACH10 = f"{lab.dir}/venus_teacher.json", f"{lab.dir}/venus_teacher.npz", 1.0
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
KEEP10, TEACHER10, TEACH10 = None, None, 0.0     # variables persist in the session; later jobs train as before
