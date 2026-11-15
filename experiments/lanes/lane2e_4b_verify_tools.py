# Lane 2 as the second 4B lane (14 Nov 23:55), job 1 of 2.
# (1) Check the 4B patch: a fresh 4B session loads the original pack plus
#     export/patches/bonsai2-4b-point-v1.patch.safetensors and must score what the block trainer's
#     best checkpoint scored on lane 6 (select 0.700, report 0.712).
# (2) The joint pointing-and-tools recipe of lane 4 (experiment 014, 800 updates, lr 2e-4) on that
#     repaired 4B, with the same before/after lines, to see whether the 4B takes tool calls as well
#     as the 9B did. The 4B's output head is tied to the token embeddings (not ternary), so only the
#     multipliers of layers 4..31 move.
# Then the joint state is written out as export/patches/bonsai2-4b-point-tools-v1.patch.safetensors
# and the session is put back to the pointing-only 4B for the next job.
# Needs a fresh lab session with BONSAI_SIZE=4B: tools/restart_lane.sh <this file> 4B
import os
import shutil
import subprocess
import sys

from weightlab import ternary
from weightlab.distill import BlockDistiller

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v1.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session with the 4B patch (size {lab.size}, stack {lab.stack})")
_ds, _dr = fS.baseline["p_hit"] - 0.700, fR.baseline["p_hit"] - 0.712
print("4B PATCH CHECK: select %.3f   report %.3f   (best checkpoint on lane 6: 0.700 / 0.712; difference %+.3f / %+.3f)" % (
    fS.baseline["p_hit"], fR.baseline["p_hit"], _ds, _dr), flush=True)
if abs(_ds) > 0.02 or abs(_dr) > 0.02:
    raise RuntimeError("the 4B patch does not reproduce the checkpoint's scores")

UPDATES14, LR14, ACC14, TAG14, HEAD14 = 800, 2e-4, 2, "4b_joint_u800", False
exec(open(f"{lab.root}/experiments/014_joint.py").read())

_tmp = f"{lab.root}/export/tmp_4b_tools_pack"
ternary.export_pack(lab.tern, lab.paths["pack"], _tmp)
_ck = BlockDistiller(lab, 4, 31, teacher=None).save(range(4, 32), f"{lab.dir}/ckpt/4b_tools_L4-31.safetensors")
T14.restore(snap14)
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("pointing-only multipliers put back: plain pointing select %.3f   report %.3f" % (_a["p_hit"], _b["p_hit"]), flush=True)
_out = f"{lab.root}/export/patches/bonsai2-4b-point-tools-v1.patch.safetensors"
_r = subprocess.run([sys.executable, f"{lab.root}/weights/make_patch.py", lab.paths["pack"], _out, "--pack", _tmp, "--ckpt", _ck,
                     "--note", "Bonsai 2 4B: point-v1 plus the jointly tuned multipliers of layers 4..31 (experiment 014, 4b_joint_u800)"],
                    capture_output=True, text=True)
print(_r.stdout.strip() or "(no output)", _r.stderr.strip()[-1500:], flush=True)
shutil.rmtree(_tmp, ignore_errors=True)
if _r.returncode:
    raise RuntimeError("make_patch.py failed")
