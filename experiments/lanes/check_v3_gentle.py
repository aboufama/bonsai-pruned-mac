# Check of the v3-gentle patch file: lay it over the session's model and score it. Lane 3's best
# checkpoint scored select 0.837, report 0.853; the patch must give the same, or the export lost
# something (the first build did: the patch tool dropped most trained small tensors).
# Runs in any 9B session whose changes since the v2 patch are confined to layers 4..31 and the head
# (the patch replaces all of those). The job after it must put its own start state back.
import os

exec(open(f"{lab.root}/experiments/_prelude.py").read())
for _n in ("J", "E", "T14"):
    if getattr(globals().get(_n), "training", False) or getattr(globals().get(_n), "open", False) is True:
        raise RuntimeError(f"{_n} is still open in this session")
_p = f"{lab.root}/export/patches/bonsai2-9b-point-v3-gentle.patch.safetensors"
print("patch applied over the session's state:", state.apply_patch(lab, _p), os.path.basename(_p))
lab.stack[:] = [f"patch:{os.path.basename(_p)}"]
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("V3-GENTLE PATCH CHECK: select %.3f   report %.3f   (lane 3's checkpoint: 0.837 / 0.853; difference %+.3f / %+.3f)" % (
    _a["p_hit"], _b["p_hit"], _a["p_hit"] - 0.837, _b["p_hit"] - 0.853), flush=True)
