#!/usr/bin/env python3
"""Choose the action cases experiment 023 trains and scores on, and list the files a pod needs.

  python3 tools/action_images.py <bonsai root> [--n 3000] [--reserved 300] [--kinds all | name,name,...]

Run it where the AgentNet screenshots are (the Spark). It needs no torch and no lab. It writes
<root>/data/mac/agentnet/action_pick.json (the chosen case ids, training and reserved) and prints,
one per line and relative to the bonsai root, every file experiment 023 reads for them: the pick
file, cases_actions.jsonl and the screenshots. Copy them to a pod with, for example:

  python3 tools/action_images.py ~/bonsai > /tmp/files.txt && tar cf - -C ~/bonsai -T /tmp/files.txt | ssh pod 'tar xf - -C /workspace/bonsai'

Training cases: actions.pick() over the training cases whose screenshot is on this machine, with
the shares of actions.DEFAULT_SHARE (seed 10), restricted to --kinds (default: clicks and scrolls).
Reserved cases: trajectories no training pool has seen (never_trained), same shares, seed 11.
Experiment 023 takes its cases from the pick file, so the pod uses exactly these.
"""
import argparse
import json
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("root")
ap.add_argument("--n", type=int, default=3000)
ap.add_argument("--reserved", type=int, default=300)
ap.add_argument("--kinds", default="clicks_scrolls")
args = ap.parse_args()
root = os.path.abspath(os.path.expanduser(args.root))
sys.path.insert(0, os.path.join(root, "weightlab"))
import actions                                          # as a plain module: the lab (torch) is not needed

kinds = None if args.kinds == "all" else (actions.CLICKS + actions.SCROLLS if args.kinds == "clicks_scrolls" else tuple(args.kinds.split(",")))
adir = os.path.join(root, "data/mac/agentnet")
path = os.path.join(adir, "cases_actions.jsonl")
keep = lambda cs: [c for c in cs if kinds is None or c["action"]["name"] in kinds]
train = actions.pick(keep(actions.load_cases(path, "train")), args.n, seed=10)
reserved = actions.pick(keep(actions.load_cases(path, "reserved", never_trained=True)), args.reserved, seed=11)
count = lambda cs: {k: sum(c["action"]["name"] == k for c in cs) for k in sorted({c["action"]["name"] for c in cs})}
json.dump({"train": [c["id"] for c in train], "reserved": [c["id"] for c in reserved],
           "kinds": list(kinds) if kinds else None, "counts": {"train": count(train), "reserved": count(reserved)}},
          open(os.path.join(adir, "action_pick.json"), "w"))
print("training:", count(train), " reserved:", count(reserved), file=sys.stderr)
files = ["data/mac/agentnet/action_pick.json", "data/mac/agentnet/cases_actions.jsonl"]
files += sorted({os.path.relpath(os.path.normpath(os.path.join(adir, c["image"])), root) for c in train + reserved})
print("\n".join(files))
