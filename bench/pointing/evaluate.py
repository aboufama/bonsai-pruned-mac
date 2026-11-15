#!/usr/bin/env python3
"""Score a model served over an OpenAI-compatible API on a generated pointing set.

    evaluate.py --data DIR --base-url http://127.0.0.1:8122/v1 --label NAME
                [--limit N] [--max-side 1280] [--concurrency 8]

Each case sends the screenshot and the Qwen3.5-family grounding prompt; the model answers
"[x,y]" in coordinates normalised to 0-1000. A case is a hit when that point, scaled back to
pixels, lies inside the target box. --max-side shrinks the screenshot (LANCZOS) so its longer
side is at most that many pixels before sending; scoring is unaffected because the answer is
normalised. Results go to DIR/results_<label>.jsonl, one line per case; rerunning skips cases
already answered with the same --max-side.
"""
import argparse
import base64
import io
import json
import os
import re
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

PROMPT = (
    "Output the center point of the position corresponding to the following instruction: \n"
    "{instruction}. \n\n"
    "The output should just be the coordinates of a point, in the format [x,y]. "
    "Additionally, if the task is infeasible (e.g., the task is not related to the image), "
    "the output should be [-1,-1]."
)
NUM = r"-?\d+(?:\.\d+)?"


def parse_point(text):
    """(x, y) from the answer, or None. A box answer is reduced to its centre."""
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


def encode(path, max_side):
    """(base64 PNG, sent width, sent height); downscaled so the longer side is at most max_side."""
    from PIL import Image
    with Image.open(path) as im:
        if not max_side or max(im.size) <= max_side:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode(), im.width, im.height
        im = im.convert("RGB")
        scale = max_side / max(im.size)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode(), im.width, im.height


def ask(base_url, data_dir, case, max_side, model):
    image, sw, sh = encode(os.path.join(data_dir, case["image"]), max_side)
    body = {
        "temperature": 0,
        "max_tokens": 64,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image}},
            {"type": "text", "text": PROMPT.format(instruction=case["instruction"].rstrip("."))},
        ]}],
    }
    if model:
        body["model"] = model
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            d = json.load(r)
        text = d["choices"][0]["message"].get("content") or ""
        prompt_tokens = d.get("usage", {}).get("prompt_tokens")
    except Exception as e:  # a failed request counts as a miss and is retried on the next run
        text, prompt_tokens = f"ERROR {e}", None
    point = parse_point(text) if not text.startswith("ERROR") else None
    w, h = case["width"], case["height"]
    row = {"id": case["id"], "raw": text[:300], "point": point, "prompt_tokens": prompt_tokens,
           "seconds": round(time.time() - started, 2), "max_side": max_side, "sent_size": [sw, sh],
           "hit": False, "hit_abs": False, "tags": case["tags"]}
    if point:
        row["hit"] = inside(point[0] * w / 1000, point[1] * h / 1000, case["bbox"])
        row["hit_abs"] = inside(point[0] * w / sw, point[1] * h / sh, case["bbox"])
    return row


def table(rows, key, title):
    buckets = defaultdict(list)
    for r in rows:
        buckets[key(r)].append(r)
    print(f"  by {title}:")
    for k in sorted(buckets):
        v = buckets[k]
        print(f"    {str(k):<28} {100 * sum(r['hit'] for r in v) / len(v):5.1f}%  (n={len(v)})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--base-url", default="http://127.0.0.1:8122/v1")
    ap.add_argument("--label", required=True)
    ap.add_argument("--limit", type=int, default=0, help="evenly spaced subset of this many cases")
    ap.add_argument("--max-side", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--model", default=None, help="model name to send, if the server needs one")
    args = ap.parse_args()

    with open(os.path.join(args.data, "cases.jsonl"), encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]
    if args.limit and args.limit < len(cases):
        step = len(cases) / args.limit
        cases = [cases[int(i * step)] for i in range(args.limit)]

    out_path = os.path.join(args.data, f"results_{args.label}.jsonl")
    done = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                if not row["raw"].startswith("ERROR") and row.get("max_side", 0) == args.max_side:
                    done[row["id"]] = row
    todo = [c for c in cases if c["id"] not in done]
    print(f"{args.label}: {len(cases)} cases, {len(cases) - len(todo)} already done, {len(todo)} to run", flush=True)

    started = time.time()
    with open(out_path, "a", encoding="utf-8") as out, ThreadPoolExecutor(args.concurrency) as pool:
        for n, row in enumerate(pool.map(lambda c: ask(args.base_url, args.data, c, args.max_side, args.model), todo), 1):
            done[row["id"]] = row
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            if n % 100 == 0:
                rs = [done[c["id"]] for c in cases if c["id"] in done]
                print(f"  {len(rs)}/{len(cases)}  running accuracy {100 * sum(r['hit'] for r in rs) / len(rs):.1f}%  "
                      f"({(time.time() - started) / n:.2f}s per case)", flush=True)

    rows = [done[c["id"]] for c in cases if c["id"] in done]
    if not rows:
        print("no results")
        return
    acc = lambda rs, k="hit": 100 * sum(r[k] for r in rs) / max(1, len(rs))
    print(f"\n== {args.label} on {args.data} (max side {args.max_side or 'original'}): "
          f"accuracy {acc(rows):.1f}% over {len(rows)} cases")
    print(f"   read as absolute pixels of the sent image instead: {acc(rows, 'hit_abs'):.1f}%")
    print(f"   unparseable or refused: {sum(r['point'] is None for r in rows)}, "
          f"request errors: {sum(r['raw'].startswith('ERROR') for r in rows)}")
    tag = lambda name: (lambda r: r["tags"].get(name))
    table(rows, tag("instruction_kind"), "instruction_kind")
    table(rows, tag("ui_type"), "ui_type")
    table(rows, lambda r: f'{r["tags"]["ui_type"]} / {r["tags"]["instruction_kind"]}', "ui_type / instruction_kind")
    for name in ("size", "theme", "window_size", "archetype", "overlay", "disambiguation"):
        table(rows, tag(name), name)
    tokens = [r["prompt_tokens"] for r in rows if r["prompt_tokens"]]
    if tokens:
        print(f"   prompt tokens per case: mean {sum(tokens) / len(tokens):.0f}, max {max(tokens)}")
    print(f"   wall time this run: {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
