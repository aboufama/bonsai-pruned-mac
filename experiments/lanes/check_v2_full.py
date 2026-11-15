# Check of the v2-full patch (v2 rebuilt with every trained small tensor): lay it over the session and score it.




import os

exec(open(f"{lab.root}/experiments/_prelude.py").read())
for _n in ("J", "E", "T14"):
    if getattr(globals().get(_n), "training", False) or getattr(globals().get(_n), "open", False) is True:
        raise RuntimeError(f"{_n} is still open in this session")
_p = f"{lab.root}/export/patches/bonsai2-9b-point-v2-full.patch.safetensors"
print("patch applied over the session's state:", state.apply_patch(lab, _p), os.path.basename(_p))
lab.stack[:] = [f"patch:{os.path.basename(_p)}"]
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("V2-FULL PATCH CHECK: select %.3f   report %.3f   (the Spark's training state: 0.810 / 0.797; difference %+.3f / %+.3f)" % (
    _a["p_hit"], _b["p_hit"], _a["p_hit"] - 0.810, _b["p_hit"] - 0.797), flush=True)
