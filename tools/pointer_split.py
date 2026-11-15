"""Where a pointer misses: the report set (158 ScreenSpot-v2 cases at 1280 px) split by element type
(ScreenSpot's own text / icon label) and by the target's smaller side in pixels of the shrunk image
(under 24, 24 to 48, over 48). Per group: cases, share on target, share within 20 px of the box.
Scores the written answer, and the exported decoder too when a head file is given. Runs outside the
lab session (needs free GPU memory for one more copy of the model).

usage (on a pod):  BONSAI_SIZE=4B [SIDES=1280,1600,1920] python3 tools/pointer_split.py <patch> [head.safetensors]\nSIDES: long sides of the input image to score at; groups and the 20 px stay on the 1280 scale.
"""
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
import torch
from safetensors.torch import load_file
from weightlab import head as headmod, state
from weightlab.core import Lab

patch = sys.argv[1]
head_file = sys.argv[2] if len(sys.argv) > 2 else None
lab = Lab(ROOT)
WHICH = os.environ.get("MODEL", "B")                 # B = Bonsai (with the patch); P = the parent; V = UI-Venus (patch "-")
MODEL = lab.load(WHICH)
if WHICH == "B" and patch != "-":
    state.apply_patch(lab, patch)


CLASSES = {}                                         # generated sets: the failure class of each case (tags.challenge)
if os.environ.get("SET", "").startswith("gen:"):
    import json as _json
    for _line in open(f"{ROOT}/{os.environ['SET'][4:]}/cases.jsonl"):
        _c = _json.loads(_line)
        CLASSES[_c["id"]] = (_c.get("tags") or {}).get("challenge") or (_c.get("meta") or {}).get("kind")


def dims(it):
    """The screenshot's size with its long side at 1280: groups and the 20 px are always on this scale."""
    w, h = it["size"]
    k = 1280 / max(w, h)
    return w * k, h * k


for SIDE in [int(v) for v in os.environ.get("SIDES", "1280").split(",")]:
    if os.environ.get("SET"):                            # e.g. SET=mac:neighbour_test:test N=600: another set, all N cases
        data = lab.data(os.environ["SET"], n=int(os.environ.get("N", 300)), max_side=SIDE)
    else:
        data = lab.data("ssv2", mod=(8, 5), max_side=SIDE)
    written = lab.score(MODEL, data, tag="pointer_split:written")["answers"]
    points = {"written answer": []}
    for text in written:
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
        points["written answer"].append(tuple(nums[:2]) if len(nums) >= 2 else None)
    if os.environ.get("SECOND"):
        # second look: a window of SECOND px of the full-resolution screenshot (or, with SECOND_AT1280, of the
        # screenshot at a 1280 px long side) around the first written
        # answer, shown enlarged twice; the model is asked again and its answer is mapped back
        from PIL import Image
        win, tmp = int(os.environ["SECOND"]), f"/tmp/second_look_{os.getpid()}"
        os.makedirs(tmp, exist_ok=True)
        items2, frames = [], []
        for i, (it, p) in enumerate(zip(data, points["written answer"])):
            W, H = it["size"]
            cx, cy = (p[0] * W / 1000, p[1] * H / 1000) if p is not None else (W / 2, H / 2)
            wpx = int(win * max(W, H) / 1280) if os.environ.get("SECOND_AT1280") else win      # window given at the 1280 scale
            cw, ch = min(wpx, W), min(wpx, H)
            x0, y0 = int(min(max(cx - cw / 2, 0), W - cw)), int(min(max(cy - ch / 2, 0), H - ch))
            path = f"{tmp}/{i}.png"
            Image.open(it["path"]).convert("RGB").crop((x0, y0, x0 + cw, y0 + ch)).save(path)
            b = it["bbox"]
            box = [b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0]
            items2.append(dict(it, id=f"{it['id']}:second", path=path, size=(cw, ch), max_side=int(os.environ.get("SECOND_SIDE", 2 * max(cw, ch))), bbox=box,
                               box1000=[1000 * box[0] / cw, 1000 * box[1] / ch, 1000 * box[2] / cw, 1000 * box[3] / ch]))
            frames.append((x0, y0, cw, ch, W, H))
        points["second look"] = []
        for text, (x0, y0, cw, ch, W, H) in zip(lab.score(MODEL, items2, tag="pointer_split:second")["answers"], frames):
            nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
            points["second look"].append(((x0 + nums[0] * cw / 1000) * 1000 / W, (y0 + nums[1] * ch / 1000) * 1000 / H) if len(nums) >= 2 else None)
    if head_file:
        spec = ("H1 dec2x768 k20", "cross_dec:768:2", 20, (20,))
        HB = headmod.HeadBench(lab, [spec])
        HB.heads[spec[0]].load_state_dict(load_file(head_file)); HB.heads[spec[0]].eval()
        points["decoder"] = []
        with torch.no_grad():
            for it in data:
                inputs, n_prompt = lab._inputs(lab.B, it)
                states, img, centres, cell, grid = HB.forward(inputs)
                out = HB.heads[spec[0]](*HB.features(HB.specs[0], states, img, centres, cell, grid, [(int(img[-1]) + 1, n_prompt)]))
                points["decoder"].append(tuple(out[1][0].tolist()))


    def groups(it):
        w, h = dims(it)
        b = it["box1000"]
        side = min((b[2] - b[0]) * w, (b[3] - b[1]) * h) / 1000
        return (["class " + str(CLASSES[it["id"]])] if CLASSES.get(it["id"]) else []) + ["all", "type " + str(it.get("ui_type")), "smaller side " + ("under 24 px" if side < 24 else "24 to 48 px" if side <= 48 else "over 48 px")]


    for name, pts in points.items():
        tab = {}
        for it, p in zip(data, pts):
            w, h = dims(it)
            b = it["box1000"]
            hit = near = False
            if p is not None:
                x, y = p
                hit = b[0] <= x <= b[2] and b[1] <= y <= b[3]
                near = math.hypot(max(b[0] - x, 0, x - b[2]) * w / 1000, max(b[1] - y, 0, y - b[3]) * h / 1000) <= 20
            for g in groups(it):
                t = tab.setdefault(g, [0, 0, 0]); t[0] += 1; t[1] += hit; t[2] += near
        print("SPLIT %s at %d px, %s (%s%s):" % (os.environ.get("SET", "report"), SIDE, name, os.path.basename(patch) if WHICH == "B" else {"P": "parent Qwen3.5", "V": "UI-Venus-2-9B"}[WHICH], " + " + os.path.basename(head_file) if head_file and name == "decoder" else ""), flush=True)
        for g in sorted(tab):
            n, a, c = tab[g]
            print("  %-26s %3d cases   on target %5.1f%%   within 20 px %5.1f%%" % (g, n, 100 * a / n, 100 * c / n), flush=True)
if os.environ.get("CANARY"):
    print("CANARY %s: %s" % (os.path.basename(patch), lab.canary(lab.B, tag="pointer_split")["all"]), flush=True)
