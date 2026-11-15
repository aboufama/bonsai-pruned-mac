# Lane 2, after the joint run: the pointer-head depth sweep of lane 1 (eight heads, 6,000 steps, lr
# 1e-3) on the best trunk so far, frozen: the v3-gentle patch (v2 plus lane 3's gentle continuation
# of block 4..19: select 0.837, report 0.853, against 0.800 / 0.791 for v2). Lane 1 ran the same
# sweep on v2, so the two tables show what the better trunk does for a head.
# Works in a fresh session (the prelude applies the patch) and in a used one (the patch is laid over
# whatever multipliers, codes and small parts of layers 4..31 and the head the session has).
import os

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-gentle.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    for _n in ("J", "E", "T14"):
        if getattr(globals().get(_n), "training", False) or getattr(globals().get(_n), "open", False) is True:
            raise RuntimeError(f"{_n} is still open in this session; restart the lab session and queue this job again")
    print("patch applied over the session's state:", state.apply_patch(lab, PATCH), os.path.basename(PATCH))
    lab.stack[:] = [f"patch:{os.path.basename(PATCH)}"]
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("trunk: select %.3f   report %.3f   (lane 3 measured 0.837 / 0.853)" % (_a["p_hit"], _b["p_hit"]), flush=True)
if abs(_a["p_hit"] - 0.837) > 0.01 or abs(_b["p_hit"] - 0.853) > 0.01:
    raise RuntimeError("the trunk is not the v3-gentle state; restart the lab session and queue this job again")
chosen010 = "pod"
SPECS16 = [("pointer q16 k16", "pointer", 16, 16), ("pointer q18 k18", "pointer", 18, 18), ("pointer q20 k20", "pointer", 20, 20),
           ("pointer q22 k22", "pointer", 22, 22), ("pointer q24 k24", "pointer", 24, 24), ("pointer q20 k16", "pointer", 20, 16),
           ("pointer q24 k20", "pointer", 24, 20), ("pointer q20 k12", "pointer", 20, 12)]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16 = 1e-3, 6000, 1000, "sweep_v3gentle", 16, 0
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
