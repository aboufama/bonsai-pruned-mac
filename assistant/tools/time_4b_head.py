#!/usr/bin/env python
"""Times the Bonsai 2 4B with its pointing decoder (early exit after layer 20) in MLX on this Mac.

    ~/Bonsai-demo/.venv-vlm/bin/python assistant/tools/time_4b_head.py [--patch FILE] [--head FILE] [--no-hits]

Uses the loader of the task benchmark (taskenv/mlx_head.py: pack + trunk patch, layers cut to 20,
decoder on their output). Prints, for 1280 px and 1600 px on one saved whole-screen screenshot:
seconds for the first question, for a further question on the same screenshot, the split into
"read the image ahead" and "answer one request on a read image", and the peak memory; then the
hits on the saved screenshots' known targets at 1280 px. Loads one model; nothing is written.
Unload LM Studio's model first: the two should not be in memory together.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
ROOT = Path.home() / "Bonsai-demo"
SAMPLES = ROOT / "samples"


def fit(image, side):
    from PIL import Image
    s = side / max(image.size)
    return image if s >= 1 else image.resize((round(image.width * s), round(image.height * s)), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", default=str(ROOT / "models/patches/bonsai2-4b-joint-h1-trunk-s12500.patch.safetensors"))
    ap.add_argument("--head", default=str(ROOT / "models/heads/bonsai2-4b-joint-h1-dec2x768-L20-s12500.safetensors"))
    ap.add_argument("--no-hits", action="store_true")
    args = ap.parse_args()
    for f in (args.patch, args.head, ROOT / "models/Ternary-Bonsai-2-4B-mlx-2bit/config.json"):
        if not Path(f).is_file():
            sys.exit(f"missing: {f}")

    import mlx.core as mx
    from PIL import Image
    from taskenv.mlx_head import LAYER, HeadModel

    t = time.time()
    m = HeadModel("mlx-4b-head", str(ROOT), patch=args.patch, head=args.head)
    print(json.dumps({"load_seconds": round(time.time() - t, 1), "layers_kept": len(m.lm.model.layers), "exit_after_layer": LAYER,
                      "patch": Path(args.patch).name, "head": Path(args.head).name}), flush=True)

    shot = Image.open(SAMPLES / "06-monday-board.jpg").convert("RGB")
    other = Image.open(SAMPLES / "09-vscode-welcome.jpg").convert("RGB")
    for side in (1280, 1600):
        a = fit(shot, side)
        rows = [("first question", a, "Point at the Automate button"), ("further question, same screenshot", a, "Filter the tasks by person"),
                ("another screenshot", fit(other, side), "Create a new file")]
        for what, image, q in rows:
            r = m.point(image, q)
            print(json.dumps({"side": side, "what": what, "seconds": r["seconds"], "read_seconds": r["read_seconds"], "decoder_ms": r["head_ms"],
                              "answer": r["raw"], "prompt_tokens": r["prompt_tokens"], "image": list(image.size)}), flush=True)
        # the same work split as an app would do it: read the image ahead, then answer on the read
        print(json.dumps(dict(m.split_timing(a, "Filter the tasks by person", repeats=3), side=side, what="split: read ahead / one request")), flush=True)
        print(json.dumps({"side": side, "peak_memory_gb": round(mx.get_peak_memory() / 1e9, 2)}), flush=True)

    if not args.no_hits:
        hints = json.loads((SAMPLES / "hints.json").read_text())
        hit = total = 0
        seconds = []
        for name in sorted(hints):
            entry = hints[name]
            image = None
            for h in entry.get("hints", []) if isinstance(entry, dict) else []:
                if "box" not in h:
                    continue
                image = image or fit(Image.open(SAMPLES / name).convert("RGB"), 1280)
                r = m.point(image, h["q"])
                nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", r["raw"])]
                ok = len(nums) >= 2 and h["box"][0] <= nums[0] / 1000 <= h["box"][2] and h["box"][1] <= nums[1] / 1000 <= h["box"][3]
                hit += ok
                total += 1
                seconds.append(r["seconds"])
                print(f"  {'HIT ' if ok else 'MISS'} {name}: \"{h['q']}\" -> {r['raw']} in {r['seconds']} s", flush=True)
        print(json.dumps({"hits": hit, "of": total, "side": 1280, "median_seconds": sorted(seconds)[len(seconds) // 2] if seconds else None,
                          "peak_memory_gb": round(mx.get_peak_memory() / 1e9, 2)}), flush=True)


if __name__ == "__main__":
    main()
