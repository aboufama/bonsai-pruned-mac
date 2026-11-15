# Export the joint pointing-and-tools multipliers of experiment 014 (lab/ckpt/tune_joint_u800.pt, from
# lane 4) as a patch for the original 9B pack: export/patches/bonsai2-9b-point-v3-tools.patch.safetensors.
# v3-tools = the v2 patch with the multipliers of layers 4..31 and of the output head replaced by the
# jointly tuned ones. The session's model is put back to v2 afterwards, and both states are scored so
# the output shows that the right weights went out and that nothing was left behind.
# Needs a session whose model is the plain v2 patch.
import os
import shutil
import subprocess
import sys

import torch
from weightlab import ternary
from weightlab.distill import BlockDistiller
from weightlab.tune import TaskTuner

exec(open(f"{lab.root}/experiments/_prelude.py").read())
if len(lab.stack) != 1 or not lab.stack[0].startswith("patch:bonsai2-9b-point-v2"):
    raise RuntimeError(f"the model is not the plain v2 patch (stack: {lab.stack}); restart the lab session first")


def both(label):
    a, b = fS.evaluate(4), fR.evaluate(4)
    fS.discard(); fR.discard()
    print("%-34s plain pointing select %.3f   report %.3f" % (label, a["p_hit"], b["p_hit"]), flush=True)


snap3 = torch.load(f"{lab.dir}/ckpt/tune_joint_u800.pt")
Tx = TaskTuner(lab, list(range(4, 32)), scales=True, head=True)
keep3 = Tx.snapshot()
assert len(snap3["tern"]) == len(keep3["tern"]), (len(snap3["tern"]), len(keep3["tern"]))
both("v2 (before)")
Tx.restore(snap3)
both("joint multipliers loaded")          # lane 4's job printed: select 0.771   report 0.791
tmp_pack = f"{lab.root}/export/tmp_v3_tools_pack"
ternary.export_pack(lab.tern, lab.paths["pack"], tmp_pack)
ck3 = BlockDistiller(lab, 4, 31, teacher=None).save(range(4, 32), f"{lab.dir}/ckpt/v3_tools_L4-31.safetensors")
Tx.restore(keep3)
both("v2 again (multipliers put back)")
out3 = f"{lab.root}/export/patches/bonsai2-9b-point-v3-tools.patch.safetensors"
r = subprocess.run([sys.executable, f"{lab.root}/weights/make_patch.py", lab.paths["pack"], out3, "--pack", tmp_pack, "--ckpt", ck3,
                    "--note", "v2 plus the jointly tuned multipliers of layers 4..31 and the output head (experiment 014, joint_u800)"],
                   capture_output=True, text=True)
print(r.stdout.strip() or "(no output)", r.stderr.strip()[-1500:], flush=True)
shutil.rmtree(tmp_pack, ignore_errors=True)
del snap3, keep3, Tx
if r.returncode:
    raise RuntimeError("make_patch.py failed")
