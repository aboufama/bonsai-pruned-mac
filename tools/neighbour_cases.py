#!/usr/bin/env python3
"""Find "neighbour" cases: targets with another labelled box close beside them in the same row
(toolbar buttons, segmented controls, tab rows, stepper arrows). These are where a pointer picks the
element next to the right one.

  python3 tools/neighbour_cases.py <bonsai root> [--gap 80] [--test 600]

A case is a neighbour case when, with the screenshot's long side at 1280 px, its box is at most 80 px
tall and another labelled box of the same screenshot (any case of the same set) lies beside it: the
sideways gap between the two is at most --gap px, they do not overlap sideways by more than 2 px, and
they overlap vertically by at least half of the lower one's height. Boxes come from cases.jsonl of
every folder under data/mac (the Fable set's boxes count with the screenshots of the set they were
written on) and of benchdata/pointing/*_train_* (generated screens).

Writes:
  data/mac/neighbour_ids.json            {"ids": [...]} every neighbour case id (training and test)
  data/mac/neighbour_gcua/cases.jsonl    GroundCUA's neighbour cases, split "train" (mac:neighbour_gcua:train)
  data/mac/neighbour_test/cases.jsonl    the held-out slice: neighbour cases of the test splits (screenshots
                                         in no training list), at most --test, spread over applications,
                                         split "test"; load with "mac:neighbour_test:test"
and prints the counts per set. No torch, no lab.
"""
import argparse
import collections
import glob
import json
import os
import random

ap = argparse.ArgumentParser()
ap.add_argument("root")
ap.add_argument("--gap", type=float, default=80)
ap.add_argument("--test", type=int, default=600)
a = ap.parse_args()
root = os.path.abspath(os.path.expanduser(a.root))
ids, tests, stats, trained, gcua = [], [], {}, set(), []
files = sorted(glob.glob(f"{root}/data/mac/*/cases.jsonl")) + sorted(glob.glob(f"{root}/benchdata/pointing/*_train_*/cases.jsonl"))
for path in files:
    folder = os.path.dirname(path)
    name = os.path.basename(folder)
    if name in ("neighbour_test", "neighbour_gcua"):
        continue
    by = collections.defaultdict(list)
    for line in open(path):
        c = json.loads(line)
        if c.get("split") == "train":
            trained.add(os.path.normpath(os.path.join(folder, c["image"])))
        if c.get("bbox"):
            by[os.path.normpath(os.path.join(folder, c["image"]))].append(c)
    n = k = 0
    for image, cases in by.items():
        boxes = sorted({tuple(c["bbox"]) for c in cases})
        for c in cases:
            n += 1
            s = 1280 / max(c["width"], c["height"])
            x0, y0, x1, y1 = c["bbox"]
            if (y1 - y0) * s > 80:
                continue
            for b in boxes:
                if b == tuple(c["bbox"]):
                    continue
                gap = max(b[0] - x1, x0 - b[2])
                over = min(y1, b[3]) - max(y0, b[1])
                if -2 <= gap * s <= a.gap and over >= 0.5 * min(y1 - y0, b[3] - b[1]) and (b[3] - b[1]) * s <= 80:
                    k += 1
                    ids.append(c["id"])
                    if name.startswith("groundcua") and c.get("split") == "train":
                        gcua.append(dict(c, image=os.path.relpath(image, f"{root}/data/mac/neighbour_gcua")))
                    if c.get("split") == "test":
                        tests.append(dict(c, image=os.path.relpath(image, f"{root}/data/mac/neighbour_test"), split="test", _path=image,
                                          meta=dict(c.get("meta") or {}, neighbour_of=name)))
                    break
    stats[name] = {"cases with a box": n, "neighbour cases": k, "screenshots": len(by)}
    print("%-28s %7d cases on %6d screenshots, %6d neighbour cases (%.0f%%)" % (name, n, len(by), k, 100 * k / max(n, 1)), flush=True)
n_all = len(tests)                                           # held out = on a screenshot no training case of any set uses
tests = [{k: v for k, v in c.items() if k != "_path"} for c in tests if c["_path"] not in trained]
print("test-split neighbour cases: %d, of which %d on screenshots that no training case uses" % (n_all, len(tests)), flush=True)
rng = random.Random(7)
by_app = collections.defaultdict(list)
for c in sorted(tests, key=lambda c: c["id"]):
    by_app[(c["meta"]["neighbour_of"], c.get("app"))].append(c)
for v in by_app.values():
    rng.shuffle(v)
picked = []
while len(picked) < a.test and any(by_app.values()):          # one per application in turn
    for key in sorted(by_app, key=str):
        if by_app[key] and len(picked) < a.test:
            picked.append(by_app[key].pop())
os.makedirs(f"{root}/data/mac/neighbour_test", exist_ok=True)
with open(f"{root}/data/mac/neighbour_test/cases.jsonl", "w") as f:
    for c in sorted(picked, key=lambda c: c["id"]):
        f.write(json.dumps(c) + "\n")
if gcua:                                                     # GroundCUA's neighbour cases as a training set of their own
    os.makedirs(f"{root}/data/mac/neighbour_gcua", exist_ok=True)
    with open(f"{root}/data/mac/neighbour_gcua/cases.jsonl", "w") as f:
        for c in gcua:
            f.write(json.dumps(c) + "\n")
    print("data/mac/neighbour_gcua: %d training cases (mac:neighbour_gcua:train)" % len(gcua), flush=True)
json.dump({"ids": sorted(set(ids)), "gap": a.gap, "stats": stats}, open(f"{root}/data/mac/neighbour_ids.json", "w"))
print("neighbour ids: %d; held-out slice: %d cases (of %d test-split neighbour cases) on %d screenshots, by source %s" % (
    len(set(ids)), len(picked), len(tests), len({c["image"] for c in picked}),
    dict(collections.Counter(c["meta"]["neighbour_of"] for c in picked))), flush=True)
