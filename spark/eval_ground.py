"""GUI grounding accuracy (ScreenSpot-Pro or ScreenSpot-v2) for a model served by llama-server.

usage: eval_ground.py <label> <port> [--dataset sspro|ssv2] [--limit N] [--max-side PX]
                      [--concurrency N] [--thinking]

--max-side downscales each screenshot so its longer side is at most PX before sending it,
e.g. 1280 to match what the Clicky app captures.

For each sample the model sees the screenshot and the instruction and must answer with one
click point. A sample counts as correct when the point falls inside the annotated box.
Results go to ~/bonsai/eval/<dataset>_<label>.jsonl (one line per sample, resumable) and a
summary is printed at the end.

The model answers in coordinates normalised to 0-1000 (the Qwen-VL convention); the script
also scores the answer read as absolute pixels so a wrong convention shows up immediately.
"""
import argparse
import base64
import glob
import io
import json
import os
import re
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.expanduser("~/bonsai")
# The grounding prompt the Qwen3.5 family is evaluated with (taken from UI-Venus's reference
# evaluator, models/grounding/ui_venus2_gd.py): user-only, answer is "[x,y]" in 0-1000 space.
PROMPT = (
    "Output the center point of the position corresponding to the following instruction: \n"
    "{instruction}. \n\n"
    "The output should just be the coordinates of a point, in the format [x,y]. "
    "Additionally, if the task is infeasible (e.g., the task is not related to the image), "
    "the output should be [-1,-1]."
)
NUM = r"-?\d+(?:\.\d+)?"


def parse_point(text):
    """Return (x, y) from the model's answer, or None. A box answer is reduced to its centre."""
    nums = [float(n) for n in re.findall(NUM, text)]
    if len(nums) >= 4:
        point = (nums[0] + nums[2]) / 2, (nums[1] + nums[3]) / 2
    elif len(nums) >= 2:
        point = nums[0], nums[1]
    else:
        return None
    return None if point[0] < 0 or point[1] < 0 else point


def inside(x, y, box):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def load_items(dataset):
    """Return samples as dicts with id, path, bbox [x1, y1, x2, y2], img_size, instruction, group, ui_type."""
    items = []
    if dataset == "sspro":
        for path in sorted(glob.glob(f"{ROOT}/sspro/annotations/*.json")):
            for it in json.load(open(path)):
                items.append({**it, "path": f"{ROOT}/sspro/images/{it['img_filename']}"})
    else:
        from PIL import Image
        for split in ("desktop", "mobile", "web"):
            for n, it in enumerate(json.load(open(f"{ROOT}/ssv2/screenspot_{split}_v2.json"))):
                path = f"{ROOT}/ssv2/screenspotv2_image/{it['img_filename']}"
                x, y, w, h = it["bbox"]
                with Image.open(path) as im:
                    size = list(im.size)
                items.append({"id": f"{split}_{n:04d}", "path": path, "bbox": [x, y, x + w, y + h],
                              "img_size": size, "instruction": it["instruction"], "group": split,
                              "ui_type": it["data_type"], "application": it.get("data_source", split)})
    items.sort(key=lambda x: x["id"])
    return items


def encode(path, max_side):
    """PNG bytes as base64, downscaled so the longer side is at most max_side (0 = untouched)."""
    if not max_side:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        scale = max_side / max(im.size)
        if scale < 1:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def ask(port, item, thinking, max_side=0):
    image = encode(item["path"], max_side)
    body = {
        "temperature": 0,
        "max_tokens": 2048 if thinking else 64,
        "chat_template_kwargs": {"enable_thinking": thinking},
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image}},
            {"type": "text", "text": PROMPT.format(instruction=item["instruction"].rstrip("."))},
        ]}],
    }
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 json.dumps(body).encode(), {"Content-Type": "application/json"})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            d = json.load(r)
        text = d["choices"][0]["message"].get("content") or ""
        prompt_tokens = d.get("usage", {}).get("prompt_tokens")
    except Exception as e:  # keep going; a failed request counts as a miss
        text, prompt_tokens = f"ERROR {e}", None
    point = parse_point(text) if not text.startswith("ERROR") else None
    w, h = item["img_size"]
    row = {"id": item["id"], "group": item["group"], "ui_type": item["ui_type"],
           "application": item["application"], "raw": text[:300], "point": point,
           "prompt_tokens": prompt_tokens, "seconds": round(time.time() - started, 2),
           "hit_norm": False, "hit_abs": False}
    if point:
        row["hit_norm"] = inside(point[0] * w / 1000, point[1] * h / 1000, item["bbox"])
        row["hit_abs"] = inside(point[0], point[1], item["bbox"])
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("port", type=int)
    ap.add_argument("--limit", type=int, default=0, help="evenly spaced subset of this many samples")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--thinking", action="store_true")
    ap.add_argument("--dataset", choices=("sspro", "ssv2"), default="sspro")
    ap.add_argument("--max-side", type=int, default=0)
    args = ap.parse_args()

    items = load_items(args.dataset)
    if args.limit and args.limit < len(items):
        step = len(items) / args.limit
        items = [items[int(i * step)] for i in range(args.limit)]

    suffix = (("_think" if args.thinking else "") + (f"_side{args.max_side}" if args.max_side else "")
              + (f"_n{args.limit}" if args.limit else ""))
    out_path = f"{ROOT}/eval/{args.dataset}_{args.label}{suffix}.jsonl"
    done = {}
    if os.path.exists(out_path):
        for line in open(out_path):
            row = json.loads(line)
            if not row["raw"].startswith("ERROR"):
                done[row["id"]] = row
    todo = [x for x in items if x["id"] not in done]
    print(f"{args.label}: {len(items)} samples, {len(done)} already done, {len(todo)} to run", flush=True)

    started = time.time()
    with open(out_path, "a") as out, ThreadPoolExecutor(args.concurrency) as pool:
        for n, row in enumerate(pool.map(lambda it: ask(args.port, it, args.thinking, args.max_side), todo), 1):
            done[row["id"]] = row
            out.write(json.dumps(row) + "\n")
            out.flush()
            if n % 100 == 0:
                hits = sum(r["hit_norm"] for r in done.values())
                print(f"  {len(done)}/{len(items)}  running accuracy {100 * hits / len(done):.1f}%  "
                      f"({(time.time() - started) / n:.2f}s per sample)", flush=True)

    rows = [done[x["id"]] for x in items if x["id"] in done]
    total = len(rows)
    acc = lambda rs, key="hit_norm": 100 * sum(r[key] for r in rs) / max(1, len(rs))
    print(f"\n== {args.dataset} {args.label}{suffix}: accuracy {acc(rows):.1f}% over {total} samples "
          f"(read as absolute pixels: {acc(rows, 'hit_abs'):.1f}%)")
    print(f"   unparseable answers: {sum(r['point'] is None for r in rows)}, "
          f"request errors: {sum(r['raw'].startswith('ERROR') for r in rows)}")
    for field in ("ui_type", "group"):
        buckets = defaultdict(list)
        for r in rows:
            buckets[r[field]].append(r)
        print("   by " + field + ": " + ", ".join(f"{k} {acc(v):.1f}% (n={len(v)})" for k, v in sorted(buckets.items())))
    tokens = [r["prompt_tokens"] for r in rows if r["prompt_tokens"]]
    if tokens:
        print(f"   prompt tokens per sample: mean {sum(tokens) / len(tokens):.0f}, max {max(tokens)}")
    print(f"   wall time this run: {time.time() - started:.0f}s", flush=True)


main()
