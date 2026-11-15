"""A patch from a TaskTuner snapshot saved in the middle of a run (lab/ckpt/tune_*_best.pt), without the
lab: the base patch with its multipliers replaced by the snapshot's. CPU only.

usage: snapshot_patch.py <original pack dir> <base patch> <snapshot.pt> <out.patch.safetensors> [--note text]

The snapshot holds one multiplier tensor per ternary matrix the tuner opened, in the tuner's order, with
no names. Each is matched to the matrix of the same shape whose current multipliers (base patch, else
original pack) are nearest; a match must be unique and clearly nearer than the runner-up, or the tool
stops. Codes and small tensors come from the base patch, so the base must be the state the run started
from in everything but the multipliers.
"""
import argparse
import os
import sys

import numpy as np
import torch
from safetensors import safe_open
from safetensors.numpy import save_file

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "weights"))
import pack  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("original"); ap.add_argument("base"); ap.add_argument("snapshot"); ap.add_argument("out")
ap.add_argument("--note", default="")
a = ap.parse_args()
src = f"{a.original}/model.safetensors"
hs, ss = pack.read_header(src)
patch = {}
with safe_open(a.base, "np") as f:
    for k in f.keys():
        patch[k] = f.get_tensor(k)
cur = {k: (patch[k] if k in patch else np.array(pack.read_tensor(src, hs, ss, k))).astype(np.float32) for k in hs if k.endswith(".scales")}
snap = torch.load(a.snapshot, map_location="cpu")
assert not snap.get("small"), "this snapshot also holds small tensors; use the lab's export instead"
used, worst = {}, 0.0
for i, (s, c) in enumerate(snap["tern"]):
    assert c is None, "this snapshot also holds codes; use the lab's export instead"
    s = s.float().numpy()
    d = sorted((float(np.linalg.norm(s - v) / max(1e-12, np.linalg.norm(v))), k) for k, v in cur.items() if v.shape == s.shape)
    assert d, f"no matrix of shape {s.shape}"
    best, key = d[0]
    if key in used or best > 0.25 or (len(d) > 1 and d[1][0] < 3 * best + 1e-6):
        sys.exit(f"tensor {i}: no clear match (nearest {d[:2]}, already used: {key in used})")
    used[key] = i
    worst = max(worst, best)
    s16 = s.astype(np.float16)
    patch[key], patch[key[:-7] + ".biases"] = s16, (-s16).astype(np.float16)
save_file(patch, a.out, metadata={"base": "prism-ml/" + os.path.basename(os.path.normpath(a.original)), "note": a.note})
print(f"{a.out}: {len(patch)} tensors, {os.path.getsize(a.out) / 1e6:.0f} MB; multipliers of {len(used)} matrices from the snapshot "
      f"(largest relative distance to the base {worst:.4f}), head {'yes' if any('lm_head' in k for k in used) else 'no'}")
