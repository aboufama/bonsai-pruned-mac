"""Export one scored step of a joint decoder run (lab/ckpt/joint018_<tag>_s<step>.pt) outside the lab
session: the trunk as a patch and the decoder as a safetensors file. They only work as a pair.

usage (on a pod):  BONSAI_SIZE=4B python3 tools/joint_export.py <base patch> <joint018_*.pt> <out trunk patch> <out head file> [layer=20]

The copy holds the decoder and one log-multiplier tensor per ternary matrix of the trained layers
(0..layer-1), in the joint tuner's order, relative to the state the run started from. So the base patch
must be exactly that state. This loads the model (needs GPU room for one more copy), lays the base
patch over it, multiplies the multipliers by exp(log-multiplier) and writes the patch the way the lab
does (weights/make_patch.py against the original pack).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
import torch
from safetensors.torch import save_file
from weightlab import head as headmod, state, ternary
from weightlab.core import Lab
from weightlab.distill import BlockDistiller

base, snap, out_patch, out_head = sys.argv[1:5]
layer = int(sys.argv[5]) if len(sys.argv) > 5 else 20
ck = torch.load(snap, map_location="cpu")
lab = Lab(ROOT)
lab.B
state.apply_patch(lab, base)
J = headmod.JointHeadTuner(lab, range(0, layer), kind="pointer", layer=layer)
assert len(J.mods) == len(ck["gains"]), (len(J.mods), len(ck["gains"]))
with torch.no_grad():
    for m, g in zip(J.mods, ck["gains"]):
        assert m.scales.shape == g.shape, (m.scales.shape, g.shape)
        m.scales.data.mul_(torch.exp(g.float()).to(m.scales.device, m.scales.dtype)); m.invalidate()
tmp = out_patch + ".pack"
ternary.export_pack(lab.tern, lab.paths["pack"], tmp)
n_layers = lab.B.config.text_config.num_hidden_layers
ckpt = BlockDistiller(lab, 4, n_layers - 1, teacher=None).save(range(0, n_layers), out_patch + ".ckpt.safetensors")
r = subprocess.run([sys.executable, f"{ROOT}/weights/make_patch.py", lab.paths["pack"], out_patch, "--pack", tmp, "--ckpt", ckpt, "--note",
                    f"trunk of a joint decoder run at step {ck['steps']} ({os.path.basename(snap)} over {os.path.basename(base)}); pair it with {os.path.basename(out_head)}"],
                   capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip()[-800:], flush=True)
shutil.rmtree(tmp, ignore_errors=True); os.remove(ckpt)
if r.returncode:
    sys.exit("make_patch.py failed; nothing exported")
save_file({k: v.contiguous() for k, v in ck["head"].items()}, out_head)
print("JOINT EXPORT step %d: %s + %s" % (ck["steps"], out_patch, out_head), flush=True)
