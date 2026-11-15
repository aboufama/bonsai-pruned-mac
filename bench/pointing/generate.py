#!/usr/bin/env python3
"""Render seeded GUI screens with exact element boxes and pointing instructions.

    generate.py --seed S --n-screens N --split {dev,test,train} --out DIR

Writes DIR/images/<screen id>.png, DIR/cases.jsonl (one instruction per line) and
DIR/screens.jsonl (every labelled element of every screen). Output depends only on the seed,
the split and the screen index, not on the number of worker processes.

Useful extras:
  --cases-per-screen K   keep at most K cases per screen, balanced over text/icon and
                         direct/functional (default 0 = every element that has a valid instruction)
  --start I              first screen index (to generate a large split in shards)
  --workers W            parallel browser processes (default: half the CPU cores, at most 12)
  --check-boxes          cross-check boxes against Playwright's bounding_box() on a sample
  --archetype NAME ...   debugging: restrict to some archetypes (changes what each index renders)
"""
import argparse
import json
import multiprocessing as mp
import os
import random
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pointgen import screen  # noqa: E402
from pointgen.instruct import make_cases  # noqa: E402

_R = None
_A = None


def _init(args):
    global _R, _A
    from pointgen.render import Renderer
    _A = args
    screen.load()
    _R = Renderer()


def _one(index):
    a = _A
    spec, ctx, html, ovs = screen.build(a.seed, a.split, index, a.archetype, a.variant, a.overlay)
    sid = f"{a.split}-{a.seed}-{index:06d}"
    rel = f"images/{sid}.png"
    if a.html_dir:
        with open(os.path.join(a.html_dir, sid + ".html"), "w", encoding="utf-8") as f:
            f.write(html)
    report = _R.render(html, spec["w"], spec["h"], spec["dpr"], ovs, os.path.join(a.out, rel), a.check_boxes)
    cases, elements = make_cases(ctx, report, random.Random(f"pointgen-cases:{a.seed}:{a.split}:{index}"),
                                 a.split, a.cases_per_screen)
    W, H = spec["w"] * spec["dpr"], spec["h"] * spec["dpr"]
    overlay = "none" if report["failed"] else spec["overlay_kind"]
    meta = {"seed": a.seed, "split": a.split, "screen": index, "archetype": spec["arch"], "variant": spec["variant"],
            "theme_family": spec["theme"]["family"], "accent": spec["theme"]["accent"], "font": spec["style"]["font"],
            "density": spec["style"]["density"], "chrome": "browser-" + spec["chrome"] if spec["web"] else spec["chrome"],
            "os_bars": spec["shell"], "floating": spec["floating"], "overlay": overlay, "dpr": spec["dpr"]}
    out = []
    for k, c in enumerate(cases):
        tags = dict(c["tags"], archetype=spec["arch"], theme=spec["theme"]["mode"], window_size=f'{spec["w"]}x{spec["h"]}',
                    overlay=overlay, chrome=meta["chrome"], dpr=spec["dpr"])
        out.append({"id": f"{sid}-{k:03d}", "image": rel, "width": W, "height": H, "instruction": c["instruction"],
                    "bbox": c["bbox"], "element": c["element"], "tags": tags, "meta": meta})
    srec = {"id": sid, "image": rel, "width": W, "height": H, "meta": meta, "elements": elements,
            "n_registered": len(ctx.targets), "n_valid": len(elements), "n_cases": len(out)}
    if a.check_boxes:
        srec["box_check_max_diff"] = report.get("box_check_max_diff")
    return index, out, srec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n-screens", type=int, required=True)
    ap.add_argument("--split", choices=("dev", "test", "train"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--workers", type=int, default=min(12, max(1, (os.cpu_count() or 2) // 2)))
    ap.add_argument("--cases-per-screen", type=int, default=0)
    ap.add_argument("--check-boxes", action="store_true")
    ap.add_argument("--archetype", nargs="*", default=None)
    ap.add_argument("--variant", default=None)
    ap.add_argument("--overlay", nargs="*", default=None, help="debugging: force one of these overlay kinds")
    ap.add_argument("--html-dir", default=None, help="debugging: also write each page's HTML here")
    args = ap.parse_args()

    os.makedirs(os.path.join(args.out, "images"), exist_ok=True)
    if args.html_dir:
        os.makedirs(args.html_dir, exist_ok=True)
    screen.load()
    indices = list(range(args.start, args.start + args.n_screens))
    started = time.time()
    n_cases = 0
    tags = {k: Counter() for k in ("ui_type", "instruction_kind", "archetype", "size", "theme", "overlay")}
    worst = 0.0
    suffix = f".{args.start:06d}" if args.start else ""
    with open(os.path.join(args.out, f"cases{suffix}.jsonl"), "w", encoding="utf-8") as fc, \
            open(os.path.join(args.out, f"screens{suffix}.jsonl"), "w", encoding="utf-8") as fs, \
            mp.get_context("spawn").Pool(args.workers, _init, (args,)) as pool:
        for n, (index, cases, srec) in enumerate(pool.imap(_one, indices, chunksize=2), 1):
            for c in cases:
                fc.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")
                for k in tags:
                    tags[k][c["tags"][k]] += 1
            fs.write(json.dumps(srec, ensure_ascii=False, sort_keys=True) + "\n")
            n_cases += len(cases)
            worst = max(worst, srec.get("box_check_max_diff") or 0.0)
            if n % 200 == 0:
                print(f"  {n}/{len(indices)} screens, {n_cases} cases, {n / (time.time() - started):.1f} screens/s", flush=True)
    took = time.time() - started
    print(f"{len(indices)} screens, {n_cases} cases in {took:.1f}s  ({len(indices) / took:.2f} screens/s, "
          f"{args.workers} workers) -> {args.out}")
    for k, c in tags.items():
        print(f"  {k}: " + ", ".join(f"{name} {cnt}" for name, cnt in sorted(c.items())))
    if args.check_boxes:
        print(f"  largest difference from Playwright bounding_box(): {worst:.3f} px")


if __name__ == "__main__":
    main()
