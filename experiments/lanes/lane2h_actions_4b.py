# Lane 2: action training on the 4B (15 Nov 00:35), the same job as lane 1's on the 9B:
# experiment 023, 3,000 updates, scores every 500, 896-weighted long sides, clicks and scrolls first.
# Start state: the 4B tools patch (bonsai2-4b-point-tools-v1: the repaired 4B plus the joint
# pointing-and-tools multipliers), laid over the session. The 4B's output head is not ternary, so
# only the multipliers of layers 4..31 move. Patch at the best step: bonsai2-4b-actions-v1.
# Runs in lane 2's 4B session after lane2e, or in a fresh 4B session.
import os

_p = f"{lab.root}/export/patches/bonsai2-4b-point-tools-v1.patch.safetensors"
PATCH = _p                                                # a fresh session starts on it directly
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or not os.path.exists(_p):
    raise RuntimeError("this needs a 4B lab session and export/patches/bonsai2-4b-point-tools-v1.patch.safetensors")
for _n in ("T14", "T23", "E", "J"):
    if getattr(globals().get(_n), "training", False) or getattr(globals().get(_n), "open", False) is True:
        raise RuntimeError(f"{_n} is still open in this session")
if lab.stack != [f"patch:{os.path.basename(_p)}"]:
    print("patch applied over the session's state:", state.apply_patch(lab, _p), os.path.basename(_p))
    lab.stack[:] = [f"patch:{os.path.basename(_p)}"]
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("start state (4B tools patch): plain pointing select %.3f   report %.3f   (lane 2 measured 0.686 / 0.695 after its joint tools run)" % (
    _a["p_hit"], _b["p_hit"]), flush=True)
if abs(_a["p_hit"] - 0.686) > 0.02 or abs(_b["p_hit"] - 0.695) > 0.02:
    raise RuntimeError("the model is not at the 4B tools state; check the patch file")
UPDATES23, EVERY23, LR23, ACC23, TAG23, HEAD23 = 3000, 500, 2e-4, 2, "actions_4b", False
ACTIONS23, PATCHNAME23 = 3000, "bonsai2-4b-actions-v1"
exec(open(f"{lab.root}/experiments/023_actions.py").read())
