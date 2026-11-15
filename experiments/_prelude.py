# Brings a fresh lab session to the state the experiments expect: the current best model (the
# original pack plus a patch), the two 159-screen sets with their score caches, and the training
# mix. Run once per session; later runs do nothing. Settings: PATCH (path), SKIP_SETS.
import os
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab import mixes, state

if not globals().get("prelude_done"):
    t0 = time.time()
    PATCH = globals().get("PATCH", f"{lab.root}/export/patches/bonsai2-9b-point-v2.patch.safetensors")
    lab.B
    if PATCH and os.path.exists(PATCH):
        print("patch applied:", state.apply_patch(lab, PATCH), os.path.basename(PATCH))
        lab.stack[:] = [f"patch:{os.path.basename(PATCH)}"]
    else:
        print("no patch: this is the original Bonsai")
    sel = lab.data("ssv2", mod=(8, 1))
    rep = lab.data("ssv2", mod=(8, 5))
    fS = lab.fast(sel, "B", keep={0, 4})
    fR = lab.fast(rep, "B", keep={0, 4})
    mix, packs, mix_counts = mixes.build(lab)
    print("select %.3f (%d screens)   report %.3f (%d)   training mix %s in %d packs   [%.0f s]" % (
        fS.baseline["p_hit"], len(sel), fR.baseline["p_hit"], len(rep), mix_counts, len(packs), time.time() - t0), flush=True)
    prelude_done = True
