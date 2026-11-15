# Lane 1: the H1 decoder (2 layers x 768 on layer 20) trained together with the trunk
# (15 Nov 02:00). H1 starts from lane 6's weights (frozen 4B v2-mixed trunk; 66.7% on select at 4,000
# steps); the trunk is that same v2-mixed and the multipliers of layers 0..20 learn with the head at
# the gentle rate 1e-4 (head 3e-4); layers 21..31 are not touched. No written-answer loss: pointing is
# meant to go through the decoder, so the trunk's own written pointing may fall. 4,000 steps, scored
# every 500 (head on select; written answers select / report for information) with two guards on the
# trunk: the canary (stop under 0.88) and the tool benchmark. Not done here: the small full-precision
# parts stay fixed (the joint tuner moves multipliers only) and training screenshots are all at 1280 px.
# Needs a fresh 4B session and lab/ckpt/h1_from_lane6.pt (H1's state dict).
import os

import torch
import weightlab.head as headmod

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v2-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
_h = f"{lab.dir}/ckpt/h1_from_lane6.pt"
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"] or not os.path.exists(_h):
    raise RuntimeError(f"this needs a fresh 4B session on the v2-mixed patch and {_h} (size {lab.size}, stack {lab.stack})")
_ck = torch.load(_h, map_location=lab.B.device)
HEAD18 = headmod.DecoderHead((20,), d=lab.B.config.text_config.hidden_size, r=768, layers=2).to(lab.B.device).float()
HEAD18.load_state_dict(_ck["head"])
print("H1 loaded from lane 6 at step %d" % _ck["steps"], flush=True)
STEPS18, ROUND18, KIND18, LAYER18, KEYS18, LRS18, LRH18, DIGITS18, TAG18 = 4000, 500, "cross_dec:768:2", 20, (20,), 1e-4, 3e-4, 0.0, "4b_joint_h1"
LO18, GUARDS18 = 0, True
exec(open(f"{lab.root}/experiments/018_joint_head.py").read())
