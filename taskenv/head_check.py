"""Check the MLX port of the pointing decoder against the PyTorch reference (tools/head_reference.py).

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    ~/bonsai/venv/bin/python -m taskenv.head_check        # on the Mac mini; reads ~/bonsai/headref/
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402

from taskenv.mlx_head import HeadModel  # noqa: E402

H = os.path.expanduser("~/bonsai")
head = sys.argv[1] if len(sys.argv) > 1 else "bonsai2-4b-h1-dec2x768-L20-s6000.safetensors"
m = HeadModel("mlx-4b-head", H, patch="bonsai2-4b-point-v2-mixed.patch.safetensors", head=head)
rows = [json.loads(l) for l in open(H + "/headref/reference.jsonl")]
hits = ref_hits = same = 0
dist, tok, bad = [], 0, []
for r in rows:
    img = Image.open(os.path.join(H, "headref", r["image"] if "/" in r["image"] else "images/" + r["image"])).convert("RGB")
    o = m.point(img, r["instruction"])
    x, y = [float(v) for v in o["raw"].strip("[]").split(",")]
    b = r["box1000"]
    hit = b[0] <= x <= b[2] and b[1] <= y <= b[3]
    d = ((x - r["point"][0]) ** 2 + (y - r["point"][1]) ** 2) ** 0.5
    hits += hit
    ref_hits += bool(r["hit"])
    same += hit == bool(r["hit"])
    dist.append(d)
    first, end = r.get("request_token_range", [0, 0])
    tok += (o["prompt_tokens"] == end)
    if d > 15:
        bad.append((r["id"], [round(x), round(y)], [round(v) for v in r["point"]], round(d), o["prompt_tokens"], end))
print(f"cases {len(rows)} | MLX on target {hits} | PyTorch on target {ref_hits} | same verdict {same} | prompt length equal {tok}")
print(f"distance between the two points (0-1000 scale): median {statistics.median(dist):.1f}, mean {statistics.mean(dist):.1f}, max {max(dist):.1f}, within 5: {sum(d <= 5 for d in dist)}, within 15: {sum(d <= 15 for d in dist)}")
for x in bad[:8]:
    print("  far:", x)
