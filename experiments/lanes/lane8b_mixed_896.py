# Lane 8b: lane 8 again with 896 px as the target size. Half of the training screenshots get a long
# side of 896, the other half is spread over 640, 768, 1024 and 1280 (lane 8 drew the five sizes
# evenly). Everything else as lane 8 and lane 3: block 4..19, multipliers and small parts, no codes,
# 2,500 steps, gentle. Written answers scored at 1280, 1024, 896, 768 and 640 on select and report
# before training and every 500 steps, Mac app windows at 1280 and 896.
# Starts from the v3-gentle patch (lane 3's result, the 9B base since 15 Nov), laid over the session's state.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-gentle.patch.safetensors"     # the 9B base since 15 Nov
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    for _n in ("J", "E", "T14"):
        if getattr(globals().get(_n), "training", False) or getattr(globals().get(_n), "open", False) is True:
            raise RuntimeError(f"{_n} is still open in this session; restart the lab session and queue this job again")
    print("patch applied over the session's state:", state.apply_patch(lab, PATCH), os.path.basename(PATCH))
    lab.stack[:] = [f"patch:{os.path.basename(PATCH)}"]
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("start state (v3-gentle): select %.3f   report %.3f   (lane 3 measured 0.837 / 0.853)" % (_a["p_hit"], _b["p_hit"]), flush=True)
if abs(_a["p_hit"] - 0.837) > 0.01 or abs(_b["p_hit"] - 0.853) > 0.01:
    raise RuntimeError("the model is not at the v3-gentle state; restart the lab session and queue this job again")
LO10, HI10 = 4, 19
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 2500, 500, 1e-4, 2e-5, False, 100, 60, "mixed_896"
SIZES10 = (896, 896, 896, 896, 640, 768, 1024, 1280)
SIZE_SCORES10, MAC_SIZES10 = (1280, 1024, 896, 768, 640), (896,)
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
