# Lane 2 as the second 4B lane, job 2 of 2: the 4B block trainer continued from lane 6's step-2000
# checkpoint (select was still rising there: 0.683, 0.699, 0.702 over the last three scores) for
# 3,000 more steps, every screenshot at 1280 px. Layers 4..31, multipliers and small parts, no
# codes. Gentle continuation: half the first run's learning rate (1e-4 instead of 2e-4), warm-up 100.
# The exact checkpoint file is loaded (not the patch, which rounds the multipliers to float16).
# The best checkpoint is exported as export/patches/bonsai2-4b-point-v2.patch.safetensors.
# Runs in a 4B lab session, fresh (tools/restart_lane.sh <this file> 4B) or after lane2e.
import os
import subprocess
import sys

from weightlab.distill import BlockDistiller

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v1.patch.safetensors"      # a fresh session starts from the 4B patch
exec(open(f"{lab.root}/experiments/_prelude.py").read())
_ck0 = f"{lab.dir}/ckpt/qat010_4b_block_best.safetensors"
if lab.size != "4B" or not globals().get("prelude_done") or not os.path.exists(_ck0):
    raise RuntimeError("this needs the 4B lab session and lane 6's checkpoint qat010_4b_block_best.safetensors in lab/ckpt")
for _n in ("T14", "E", "J"):
    if getattr(globals().get(_n), "training", False) or getattr(globals().get(_n), "open", False) is True:
        raise RuntimeError(f"{_n} is still open in this session")
BlockDistiller(lab, 4, 31, teacher=None).restore(_ck0)
lab.stack[:] = ["4b:020 multipliers, block trainer L4-31 step 2000 (checkpoint)"]
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("checkpoint loaded: select %.3f   report %.3f   (lane 6 measured 0.700 / 0.712)" % (_a["p_hit"], _b["p_hit"]), flush=True)
if abs(_a["p_hit"] - 0.700) > 0.01 or abs(_b["p_hit"] - 0.712) > 0.01:
    raise RuntimeError("the model is not at the step-2000 checkpoint")
LO10, HI10 = 4, 31
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 3000, 250, 1e-4, 2e-5, False, 100, 60, "4b_block_cont"
SIZES10 = SIZE_SCORES10 = MAC_SIZES10 = None
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())

if best_step:
    _out = f"{lab.root}/export/patches/bonsai2-4b-point-v2.patch.safetensors"
    _r = subprocess.run([sys.executable, f"{lab.root}/weights/make_patch.py", lab.paths["pack"], _out, "--ckpt", best_path,
                         "--note", f"Bonsai 2 4B: point-v1 continued, block trainer L4-31 at 1280 px, best checkpoint at step {best_step} of 3000 (4b_block_cont)"],
                        capture_output=True, text=True)
    print(_r.stdout.strip() or "(no output)", _r.stderr.strip()[-1500:], flush=True)
    if _r.returncode:
        raise RuntimeError("make_patch.py failed")
else:
    print("no checkpoint beat the start; no new patch written (bonsai2-4b-point-v1 stays the best 4B)")
