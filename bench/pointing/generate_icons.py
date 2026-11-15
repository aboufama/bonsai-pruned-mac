#!/usr/bin/env python3
"""Render icon-dense, Mac-style screens whose targets are icon-only controls (pointgen/iconscreens.py).

    generate_icons.py --seed S --n-screens N --split {train,dev,test} --out DIR [--start I] [--workers W]
    generate_icons.py --describe                    icons per split and source, unresolved vocabulary names
    generate_icons.py --check DIR --against DEV_DIR [...]   nothing in DIR may appear in the other sets

Output has the format of generate.py (images/, cases.jsonl, screens.jsonl), so the lab's "gen:" loader
reads it unchanged. Output depends only on the seed, the split and the screen index. With --start the
shard is written as cases.<start>.jsonl / screens.<start>.jsonl; concatenate shards in order.
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

from pointgen import iconscreens  # noqa: E402

_R = None
_A = None


def _init(args):
    global _R, _A
    from pointgen.render import Renderer
    _A = args
    iconscreens.load()
    _R = Renderer()


def _one(index):
    global _R
    from pointgen.render import Renderer
    a = _A
    s = iconscreens.Screen(a.seed, a.split, index)
    html = s.html()
    sid = f"icons-{a.split}-{a.seed}-{index:06d}"
    rel = f"images/{sid}.png"
    if a.html_dir:
        with open(os.path.join(a.html_dir, sid + ".html"), "w", encoding="utf-8") as f:
            f.write(html)
    report = None
    for attempt in range(3):        # a screenshot can time out when the machine is busy: retry with a fresh browser
        try:
            report = _R.render(html, 1280, s.vh, s.dsf, [], os.path.join(a.out, rel))
            break
        except Exception:
            if attempt == 2:
                raise
            _R.close()
            _R = Renderer()
    cases, elements = s.cases(report, random.Random(f"iconscreens-cases:{a.seed}:{a.split}:{index}"), a.cases_per_screen)
    meta = s.meta(a.seed, index)
    W, H = round(report["W"] * s.dsf), round(report["H"] * s.dsf)
    out = []
    for k, c in enumerate(cases):
        tags = dict(c["tags"], archetype=iconscreens.ARCH, theme=s.theme["mode"], window_size=f"{W}x{H}", overlay="none",
                    chrome="mac", dpr=meta["dpr"])
        out.append({"id": f"{sid}-{k:03d}", "image": rel, "width": W, "height": H, "instruction": c["instruction"],
                    "bbox": c["bbox"], "element": c["element"], "tags": tags, "meta": meta})
    srec = {"id": sid, "image": rel, "width": W, "height": H, "meta": meta, "elements": elements,
            "n_registered": len(s.targets), "n_valid": len(elements), "n_cases": len(out)}
    return index, out, srec


def check(data, against):
    """Glyphs, instructions, themes, accents and layout variants of `data` must not occur in `against`."""
    def read(d):
        got = {k: set() for k in ("icon glyph", "instruction", "theme family", "accent colour", "variant")}
        with open(os.path.join(d, "cases.jsonl"), encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r["element"].get("icon"):
                    got["icon glyph"].add(r["element"]["icon"])
                got["instruction"].add(r["instruction"].lower())
                got["theme family"].add(r["meta"]["theme_family"])
                got["accent colour"].add(r["meta"]["accent"])
                got["variant"].add(r["meta"]["archetype"] + "/" + r["meta"]["variant"])
        p = os.path.join(d, "screens.jsonl")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    got["icon glyph"].update(e["icon"] for e in json.loads(line)["elements"] if e.get("icon"))
        return got
    mine, bad = read(data), 0
    for other in against:
        theirs = read(other)
        for k in mine:
            both = mine[k] & theirs[k]
            print(f"{k}: {len(mine[k])} here, {len(theirs[k])} in {os.path.basename(os.path.normpath(other))}, shared {len(both)}"
                  + (f"  e.g. {sorted(both)[:5]}" if both else ""))
            bad += len(both)
    print("OK: nothing shared" if not bad else f"FAILED: {bad} shared items")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--n-screens", type=int)
    ap.add_argument("--split", choices=("dev", "test", "train"), default="train")
    ap.add_argument("--out")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--workers", type=int, default=min(8, max(1, (os.cpu_count() or 2) // 2)))
    ap.add_argument("--cases-per-screen", type=int, default=8)
    ap.add_argument("--html-dir", default=None)
    ap.add_argument("--describe", action="store_true")
    ap.add_argument("--check")
    ap.add_argument("--against", nargs="+")
    args = ap.parse_args()
    if args.describe:
        print(json.dumps(iconscreens.describe(), indent=1))
        return
    if args.check:
        sys.exit(check(args.check, args.against or []))
    os.makedirs(os.path.join(args.out, "images"), exist_ok=True)
    if args.html_dir:
        os.makedirs(args.html_dir, exist_ok=True)
    indices = list(range(args.start, args.start + args.n_screens))
    started = time.time()
    n_cases = 0
    tags = {k: Counter() for k in ("icon_set", "surface", "instruction_kind", "disambiguation", "state", "theme")}
    sizes = []
    suffix = f".{args.start:06d}" if args.start else ""
    with open(os.path.join(args.out, f"cases{suffix}.jsonl"), "w", encoding="utf-8") as fc, \
            open(os.path.join(args.out, f"screens{suffix}.jsonl"), "w", encoding="utf-8") as fs, \
            mp.get_context("spawn").Pool(args.workers, _init, (args,)) as pool:
        for n, (index, cases, srec) in enumerate(pool.imap(_one, indices, chunksize=2), 1):
            for c in cases:
                fc.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")
                for k in tags:
                    tags[k][c["tags"][k]] += 1
                sizes.append(min(c["tags"]["w1280"], c["tags"]["h1280"]))
            fs.write(json.dumps(srec, ensure_ascii=False, sort_keys=True) + "\n")
            n_cases += len(cases)
            if n % 200 == 0:
                fc.flush()
                fs.flush()
                print(f"  {n}/{len(indices)} screens, {n_cases} cases, {n / (time.time() - started):.1f} screens/s", flush=True)
    took = time.time() - started
    print(f"{len(indices)} screens, {n_cases} cases in {took:.1f}s  ({len(indices) / took:.2f} screens/s, {args.workers} workers) -> {args.out}")
    for k, c in tags.items():
        print(f"  {k}: " + ", ".join(f"{name} {cnt}" for name, cnt in sorted(c.items())))
    sizes.sort()
    if sizes:
        q = lambda p: sizes[min(len(sizes) - 1, int(p * len(sizes)))]
        print(f"  short side at 1280 px: min {sizes[0]}, p10 {q(.1)}, median {q(.5)}, p90 {q(.9)}, max {sizes[-1]}")


if __name__ == "__main__":
    main()
