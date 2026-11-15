# Experiment 013: generated answers from the model in its current state, and how small the first
# look can be made.
#
# On the target Mac nearly all the time goes into reading the screenshot (about 105 image tokens
# per second), so the cost of an answer is the number of tokens read. A look at 1280 px reads
# about 1,000 tokens; at 640 px about 260. A zoomed second look restores precision. Each setting
# below is (long side of the first look, zoom of the second look or None, long side the zoomed
# window is shown at). Hits are answers inside the target box; tokens are everything read.
# Settings: TAG13, N13 (cases per extra set).
import json
import re
import time

import torch
from PIL import Image

TAG = globals().get("TAG13", "current")
N = globals().get("N13", 150)
MAC_TPS = 105.0                       # prompt tokens per second measured on the M4 MacBook
model = lab.B


@torch.inference_mode()
def ask(sample):
    inputs, n_prompt = lab._inputs(model, sample)
    out = model.generate(**inputs, max_new_tokens=16, do_sample=False, eos_token_id=lab._stop_ids())
    text = lab.processor.decode(out[0, n_prompt:], skip_special_tokens=True)
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
    return ((nums[0], nums[1]) if len(nums) >= 2 else None), inputs["input_ids"].shape[1]


def fit(im, side):
    s = side / max(im.size)
    return im if s >= 1 else im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)


def inside(p, b):
    return p is not None and b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]


def run(name, data, configs):
    res = {c: {"hits": 0, "tokens": 0, "looks": 0} for c in configs}
    t0 = time.time()
    for it in data:
        full = Image.open(it["path"]).convert("RGB")
        W, H = full.size
        first = {f: ask({"image": fit(full, f), "instruction": it["instruction"]}) for f in sorted({c[0] for c in configs})}
        for c in configs:
            f, z, side2 = c
            p, n = first[f]
            r = res[c]
            r["tokens"] += n; r["looks"] += 1
            if z is None:
                r["hits"] += inside(p, it["box1000"])
                continue
            if p is None:
                continue
            cw, ch = W / z, H / z
            cx = min(max(p[0] / 1000 * W, cw / 2), W - cw / 2)
            cy = min(max(p[1] / 1000 * H, ch / 2), H - ch / 2)
            x0, y0 = cx - cw / 2, cy - ch / 2
            crop = full.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch)))
            s = side2 / max(crop.size)
            crop = crop.resize((round(crop.width * s), round(crop.height * s)), Image.LANCZOS)
            p2, n2 = ask({"image": crop, "instruction": it["instruction"]})
            r["tokens"] += n2; r["looks"] += 1
            if p2 is not None:
                r["hits"] += inside((1000 * (x0 + p2[0] / 1000 * cw) / W, 1000 * (y0 + p2[1] / 1000 * ch) / H), it["box1000"])
    n = len(data)
    print(f"\n{name}: {n} cases, {time.time() - t0:.0f} s")
    rows = []
    for c, r in res.items():
        f, z, side2 = c
        label = f"{f} px" + ("" if z is None else f", then a 1/{z} window at {side2} px")
        est = r["tokens"] / n / MAC_TPS + 0.4 * r["looks"] / n
        rows.append({"first": f, "zoom": z, "second": side2, "hits": r["hits"] / n, "tokens": r["tokens"] / n, "mac_seconds": est})
        print("  %-36s %5.1f%% on target   %5.0f tokens read   about %4.1f s on the Mac" % (label, 100 * r["hits"] / n, r["tokens"] / n, est), flush=True)
    return rows


out = {"state": list(lab.stack)}
out["ScreenSpot-v2 report set"] = run("ScreenSpot-v2 report set", lab.data("ssv2", mod=(8, 5)),
    [(1280, None, None), (1280, 3, 1024), (896, None, None), (896, 3, 768), (640, None, None), (640, 2, 768), (640, 3, 768)])
out["Mac app windows (Screen2AX, reserved apps)"] = run("Mac app windows (Screen2AX, reserved apps)", lab.data("mac:screen2ax_task:test", n=N),
    [(1280, None, None), (1280, 3, 1024), (640, 3, 768)])
out["our benchmark (dev)"] = run("our benchmark (dev)", lab.data("gen:benchdata/pointing/dev_20261114", n=N),
    [(1280, None, None), (1280, 3, 1024)])
json.dump(out, open(f"{lab.dir}/exp013_looks_{TAG}.json", "w"), indent=1)
