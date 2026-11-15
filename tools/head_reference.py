"""Reference outputs of an exported pointing decoder, for porting it to another runtime.
Loads the model and a patch outside the lab session, loads the head from its safetensors file, and for
the first N cases of the report set at 1280 px writes one JSON line each (id, image file, instruction,
box1000, the head's point on 0-1000, its click logit, hit) plus the image exactly as the lab hands it to
the processor (PNG, already shrunk). Also the written answer's hit on the same cases.

usage (on a pod):  BONSAI_SIZE=4B python3 tools/head_reference.py <patch> <head.safetensors> <out dir> [N=50]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
import torch
from safetensors.torch import load_file
from weightlab import head as headmod, state
from weightlab.core import Lab

patch, head_file, out_dir = sys.argv[1:4]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 50
os.makedirs(f"{out_dir}/images", exist_ok=True)
lab = Lab(ROOT)
lab.B
state.apply_patch(lab, patch)
spec = ("H1 dec2x768 k20", "cross_dec:768:2", 20, (20,))
HB = headmod.HeadBench(lab, [spec])
HB.heads[spec[0]].load_state_dict(load_file(head_file))
HB.heads[spec[0]].eval()
data = lab.data("ssv2", mod=(8, 5))[:n]
written = lab.score(lab.B, data, tag="head_reference:written")["answers"]
hits = whits = 0
with open(f"{out_dir}/reference.jsonl", "w") as f, torch.no_grad():
    for it, text in zip(data, written):
        inputs, n_prompt = lab._inputs(lab.B, it)
        states, img, centres, cell, grid = HB.forward(inputs)
        ranges = [(int(img[-1]) + 1, n_prompt)]
        out = HB.heads[spec[0]](*HB.features(HB.specs[0], states, img, centres, cell, grid, ranges))
        x, y = out[1][0].tolist()
        b = it["box1000"]
        hit = bool(b[0] <= x <= b[2] and b[1] <= y <= b[3])
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
        whit = bool(len(nums) >= 2 and b[0] <= nums[0] <= b[2] and b[1] <= nums[1] <= b[3])
        hits += hit; whits += whit
        name = it["id"] + ".png"
        lab.image(it).save(f"{out_dir}/images/{name}")
        f.write(json.dumps({"id": it["id"], "image": name, "instruction": it["instruction"], "box1000": [round(v, 2) for v in b],
                            "point": [round(x, 2), round(y, 2)], "click_logit": round(out[2][0].item(), 4), "hit": hit,
                            "written_answer": text, "written_hit": whit, "image_tokens": int(img.numel()), "grid_rows_cols": list(grid),
                            "request_token_range": list(ranges[0])}) + "\n")
print("HEAD REFERENCE: %d cases; decoder on target %d (%.1f%%); written answer on target %d (%.1f%%); files in %s" % (
    len(data), hits, 100 * hits / len(data), whits, 100 * whits / len(data), out_dir), flush=True)
