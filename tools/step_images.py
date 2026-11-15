#!/usr/bin/env python3
"""Choose the orchestrator-step cases experiment 027 trains and scores on, and list the files a pod needs.

  python3 tools/step_images.py <bonsai root> [--n 3600] [--reserved 300]

The twin of tools/action_images.py for cases_steps.jsonl. Run it where the AgentNet screenshots are (the
Spark); no torch, no lab. Writes <root>/data/mac/agentnet/step_pick.json and prints, relative to the
bonsai root, the pick file, cases_steps.jsonl and the screenshots of the chosen cases. Training cases:
actions.pick() with actions.STEP_SHARE, seed 10. Reserved: trajectories no pointing run has trained
on (never_trained), same shares, seed 11.
"""
import argparse
import json
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("root")
ap.add_argument("--n", type=int, default=3600)
ap.add_argument("--reserved", type=int, default=300)
args = ap.parse_args()
root = os.path.abspath(os.path.expanduser(args.root))
sys.path.insert(0, os.path.join(root, "weightlab"))
import actions                                          # as a plain module: the lab (torch) is not needed

adir = os.path.join(root, "data/mac/agentnet")
path = os.path.join(adir, "cases_steps.jsonl")
name = lambda c: c["step"]["action"]
train = actions.pick(actions.load_cases(path, "train"), args.n, actions.STEP_SHARE, seed=10, name=name)
reserved = actions.pick(actions.load_cases(path, "reserved", never_trained=True), args.reserved, actions.STEP_SHARE, seed=11, name=name)
count = lambda cs: {k: sum(name(c) == k for c in cs) for k in sorted({name(c) for c in cs})}
json.dump({"train": [c["id"] for c in train], "reserved": [c["id"] for c in reserved],
           "counts": {"train": count(train), "reserved": count(reserved)}}, open(os.path.join(adir, "step_pick.json"), "w"))
print("training:", count(train), " reserved:", count(reserved), file=sys.stderr)
files = ["data/mac/agentnet/step_pick.json", "data/mac/agentnet/cases_steps.jsonl"]
files += sorted({os.path.relpath(os.path.normpath(os.path.join(adir, c["image"])), root) for c in train + reserved})
print("\n".join(files))
