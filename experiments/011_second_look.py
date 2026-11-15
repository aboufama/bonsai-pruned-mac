# Experiment 011: a zoomed second look, with no training.
# Pass 1: the model points on the whole screenshot (1280 px). Pass 2: a window around that point
# is cut from the original image, shown larger, and the model points again inside it; the answer
# is mapped back to the full screen. Bonsai now gets the coarse position right about as often as
# its parent, and what it lacks is fine position, which is exactly what a zoom turns into a
# coarse problem. Generated answers, ScreenSpot-v2 report set.
# Settings: ZOOMS11 (window = 1/zoom of each side), SIDE11 (long side the window is shown at), N11.
import json
import re
import time
import torch
from PIL import Image

ZOOMS = globals().get("ZOOMS11", (2, 3))
SIDE = globals().get("SIDE11", 1024)
data = lab.data("ssv2", mod=(8, 5))[:globals().get("N11", None)]
model = lab.B


@torch.inference_mode()
def ask(sample):
    inputs, n_prompt = lab._inputs(model, sample)
    out = model.generate(**inputs, max_new_tokens=16, do_sample=False, eos_token_id=lab._stop_ids())
    text = lab.processor.decode(out[0, n_prompt:], skip_special_tokens=True)
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
    return (nums[0], nums[1]) if len(nums) >= 2 else None, inputs["input_ids"].shape[1]


def inside(p, b):
    return p is not None and b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]


hits = {"first look only": 0, **{f"second look, window 1/{z}": 0 for z in ZOOMS}}
reach = {z: 0 for z in ZOOMS}                # target centre inside the window: the most a second look can get
tokens = {"first": 0, **{z: 0 for z in ZOOMS}}
t0 = time.time()
for it in data:
    p1, n1 = ask(it)
    tokens["first"] += n1
    hits["first look only"] += inside(p1, it["box1000"])
    if p1 is None:
        continue
    full = Image.open(it["path"]).convert("RGB")
    W, H = full.size
    for z in ZOOMS:
        cw, ch = W / z, H / z
        cx = min(max(p1[0] / 1000 * W, cw / 2), W - cw / 2)
        cy = min(max(p1[1] / 1000 * H, ch / 2), H - ch / 2)
        x0, y0 = cx - cw / 2, cy - ch / 2
        tx, ty = it["target"][0] / 1000 * W, it["target"][1] / 1000 * H
        reach[z] += (x0 <= tx <= x0 + cw and y0 <= ty <= y0 + ch)
        crop = full.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch)))
        s = SIDE / max(crop.size)
        crop = crop.resize((round(crop.width * s), round(crop.height * s)), Image.LANCZOS)
        p2, n2 = ask({"image": crop, "instruction": it["instruction"]})
        tokens[z] += n2
        if p2 is not None:
            back = (1000 * (x0 + p2[0] / 1000 * cw) / W, 1000 * (y0 + p2[1] / 1000 * ch) / H)
            hits[f"second look, window 1/{z}"] += inside(back, it["box1000"])
n = len(data)
print("%d screens, %.0f s" % (n, time.time() - t0))
for k, v in hits.items():
    print("  %-28s %5.1f%%" % (k, 100 * v / n))
for z in ZOOMS:
    print("  window 1/%d: target inside the window on %.1f%% of screens; second look reads %d tokens on average (first look %d)" % (
        z, 100 * reach[z] / n, tokens[z] / n, tokens["first"] / n))
json.dump({"n": n, "hits": {k: v / n for k, v in hits.items()}, "reach": {str(z): reach[z] / n for z in ZOOMS},
           "tokens": {str(k): v / n for k, v in tokens.items()}, "side": SIDE, "state": list(lab.stack)},
          open(f"{lab.dir}/exp011_second_look_{globals().get('TAG11', 'scales')}.json", "w"), indent=1)
