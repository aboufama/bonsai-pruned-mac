#!/usr/bin/env python3
"""Check that train, dev and test share no layout variant, theme, icon glyph or label.

    check_disjoint.py [--n 1500] [--seed 7]            build N screens per split (no browser) and compare
    check_disjoint.py --data DIR_A DIR_B [...]         compare generated sets (their screens.jsonl / cases.jsonl)

The first form exercises the generator itself: every text label that a split can turn into a
target, every glyph it draws, and every variant and theme it picks. Labels with fewer than three
letters (numbers, dates, cell references) are exempt. Exit status 1 if anything is shared.
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pointgen import instruct, screen, theme, vocab  # noqa: E402
from pointgen.splits import SPLITS, is_generic, norm  # noqa: E402


def from_generator(n, seed):
    screen.load()
    sets = {k: {s: set() for s in SPLITS} for k in ("variant", "theme family", "accent colour", "icon glyph", "text label")}
    where = defaultdict(set)
    for split in SPLITS:
        for i in range(n):
            spec, ctx, html, _ = screen.build(seed, split, i, overlay_kinds=None)
            sets["variant"][split].add(spec["arch"] + "/" + spec["variant"])
            sets["theme family"][split].add(spec["theme"]["family"])
            sets["accent colour"][split].add(spec["theme"]["accent"])
            sets["icon glyph"][split].update(re.findall(r'data-i="([^"]+)"', html))
            for t in ctx.targets.values():
                if t.ui == "text" and not t.foreign and not is_generic(t.label):
                    key = norm(t.label)
                    sets["text label"][split].add(key)
                    where[key].add(f"{split}:{spec['arch']}/{spec['variant']}")
    return sets, where


def from_data(dirs):
    sets = {k: {} for k in ("variant", "theme family", "accent colour", "icon glyph", "text label", "instruction")}
    where = defaultdict(set)
    for d in dirs:
        name = os.path.basename(os.path.normpath(d))
        for k in sets:
            sets[k][name] = set()
        with open(os.path.join(d, "screens.jsonl"), encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                m = r["meta"]
                sets["variant"][name].add(m["archetype"] + "/" + m["variant"])
                sets["theme family"][name].add(m["theme_family"])
                sets["accent colour"][name].add(m["accent"])
                for e in r["elements"]:
                    if e.get("icon"):
                        sets["icon glyph"][name].add(e["icon"])
                    if e.get("label_visible", e["ui_type"] == "text") and not is_generic(e["label"]):
                        sets["text label"][name].add(norm(e["label"]))
                        where[norm(e["label"])].add(f"{name}:{m['archetype']}/{m['variant']}")
        with open(os.path.join(d, "cases.jsonl"), encoding="utf-8") as f:
            for line in f:
                sets["instruction"][name].add(json.loads(line)["instruction"].lower())
    return sets, where


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--data", nargs="+")
    ap.add_argument("--show", type=int, default=25)
    args = ap.parse_args()
    sets, where = from_data(args.data) if args.data else from_generator(args.n, args.seed)
    bad = 0
    for kind, by in sets.items():
        names = list(by)
        print(f"{kind}: " + ", ".join(f"{k} {len(v)}" for k, v in by.items()))
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                both = by[a] & by[b]
                if both:
                    bad += len(both)
                    print(f"  SHARED by {a} and {b}: {len(both)}")
                    for x in sorted(both)[:args.show]:
                        print(f"      {x!r}  {sorted(where.get(x, []))[:4]}")
    if not args.data:
        print("phrasing templates: " + ", ".join(f"{s} {len(set(instruct.DIRECT_WRAP[s]) | set(instruct.FUNC_WRAP[s]))}" for s in SPLITS)
              + " (disjointness asserted at import)")
        print(f"vocabulary: {len(vocab.CONCEPTS)} concepts; label, glyph and intent ownership asserted at import")
    print("OK: nothing shared" if not bad else f"FAILED: {bad} shared items")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
