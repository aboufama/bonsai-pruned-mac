"""Generated answers of a patched model on the report set at several input sizes: hits, and how close the
misses are. For a two-stage design (rough point, then a detector on a crop) the share of answers within
20 / 40 / 80 px of the target box says how much a detector could rescue. Distance is from the point to
the nearest edge of the box (0 if inside), in pixels of the screenshot shrunk to a 1280 px long side.
Runs outside the lab session, beside a training job if the GPU has room.

usage (on a pod):  [GREY=1] BONSAI_SIZE=<9B|4B|2B> python3 tools/closeness.py <patch file or "original"> [sizes, default 1280,896,640,448]
"""
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
from weightlab import state
from weightlab.core import Lab

path = sys.argv[1]
sizes = [int(s) for s in (sys.argv[2] if len(sys.argv) > 2 else "1280,896,640,448").split(",")]
lab = Lab(ROOT)
GREY = os.environ.get("GREY") == "1"                # greyscale screenshots: luminance copied into the three channels
if GREY:
    _image = lab.image
    lab.image = lambda it: _image(it).convert("L").convert("RGB")
model = lab.B
name = "original"
if path != "original":
    state.apply_patch(lab, path)
    name = os.path.basename(path).replace(".patch.safetensors", "")
if GREY:
    name += "-grey"
out = {}
for side in sizes:
    data = lab.data("ssv2", mod=(8, 5), max_side=side)
    t = time.time()
    r = lab.score(model, data, tag=f"closeness:{name}:{side}")
    near = {20: 0, 40: 0, 80: 0}
    hits = 0
    for it, text in zip(data, r["answers"]):
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
        if len(nums) < 2:
            continue
        w, h = it["size"]
        k = 1280 / max(w, h)                          # pixels per unit of the original image at a 1280 long side
        b = it["box1000"]
        dx = max(b[0] - nums[0], 0, nums[0] - b[2]) / 1000 * w * k
        dy = max(b[1] - nums[1], 0, nums[1] - b[3]) / 1000 * h * k
        d = (dx * dx + dy * dy) ** 0.5
        hits += d == 0
        for px in near:
            near[px] += d <= px
    n = len(data)
    out[side] = {"n": n, "hit": hits / n, **{f"within_{px}": c / n for px, c in near.items()}, "seconds_per_answer": (time.time() - t) / n}
    print("CLOSENESS %s (%s) at %4d px: on target %5.1f%%   within 20 px %5.1f%%   40 px %5.1f%%   80 px %5.1f%%   of %d   [%.2f s per answer]" % (
        name, lab.size, side, 100 * hits / n, 100 * near[20] / n, 100 * near[40] / n, 100 * near[80] / n, n, (time.time() - t) / n), flush=True)
json.dump(out, open(f"{lab.dir}/closeness_{name}.json", "w"), indent=1)
