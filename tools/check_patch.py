"""Load a patch into a fresh Bonsai outside the lab session and score it (teacher-forced p_hit on the
select and report sets). Runs beside a training job if the GPU has room (9B about 35 GB, 4B about 18 GB).

usage (on a pod):  BONSAI_SIZE=<9B|4B> python3 tools/check_patch.py <patch file> [more patch files]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
import torch
from weightlab import state, ternary
from weightlab.core import Lab

lab = Lab(ROOT)
lab.B
sel, rep = lab.data("ssv2", mod=(8, 1)), lab.data("ssv2", mod=(8, 5))
first = True
for path in sys.argv[1:]:
    if not first:                                     # back to the original pack before the next patch
        del lab.models["B"]
        torch.cuda.empty_cache()
        lab.B
    first = False
    counts = state.apply_patch(lab, path)
    fS, fR = lab.fast(sel, "B", keep={0, 4}), lab.fast(rep, "B", keep={0, 4})
    print("PATCH CHECK %s (%s, %s): select %.3f   report %.3f" % (os.path.basename(path), lab.size, counts, fS.baseline["p_hit"], fR.baseline["p_hit"]), flush=True)
    del fS, fR
