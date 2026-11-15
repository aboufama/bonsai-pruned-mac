#!/usr/bin/env python3
"""Structured target descriptions, written by rule from accessibility data (15 Nov 05:35,
from a scan of the literature: a grounder trained on descriptions of the form role + visible label + one
neighbour does much better on small targets when the planner writes targets that way).

  python3 tools/structured_cases.py <bonsai root>

For every Screen2AX-Tree training case that has a label and a role word, the request is rewritten as
"the <label> <role>" plus, when another labelled element sits beside it in the same row (within 80 px
at the 1280 scale), where it is: "between the <left> <role> and the <right> <role>", "to the right of
the <left> <role>" or "to the left of the <right> <role>"; half of the cases (by a hash of the id) get
a short verb in front ("Click ..."). Same screenshots and boxes as the source; the original wordings stay
in their own set. Writes data/mac/structured_s2ax/cases.jsonl (split "train"; mac:structured_s2ax:train).
"""
import collections
import hashlib
import json
import os
import sys

root = os.path.abspath(os.path.expanduser(sys.argv[1]))
src = f"{root}/data/mac/screen2ax_tree"
out_dir = f"{root}/data/mac/structured_s2ax"
by = collections.defaultdict(list)
for line in open(f"{src}/cases.jsonl"):
    c = json.loads(line)
    m = c.get("meta") or {}
    if c.get("bbox") and c.get("split") == "train" and m.get("label") and len(str(m["label"])) <= 40:
        by[c["image"]].append(c)


def words(c):
    m = c["meta"]
    label, role = str(m["label"]).strip(), str(m.get("role_word") or m.get("ax_role_description") or "").strip()
    return label if not role or label.lower().endswith(role.lower()) else f"{label} {role}"


os.makedirs(out_dir, exist_ok=True)
n = with_nb = 0
with open(f"{out_dir}/cases.jsonl", "w") as f:
    for image, cases in by.items():
        for c in cases:
            s = 1280 / max(c["width"], c["height"])
            x0, y0, x1, y1 = c["bbox"]
            left = right = None
            for o in cases:
                if o is c or o["bbox"] == c["bbox"] or words(o) == words(c):
                    continue
                b = o["bbox"]
                over = min(y1, b[3]) - max(y0, b[1])
                if over < 0.5 * min(y1 - y0, b[3] - b[1]):
                    continue
                if 0 <= (x0 - b[2]) * s <= 80 and (left is None or b[2] > left["bbox"][2]):
                    left = o
                if 0 <= (b[0] - x1) * s <= 80 and (right is None or b[0] < right["bbox"][0]):
                    right = o
            text = "the " + words(c)
            if left and right:
                text += f", between the {words(left)} and the {words(right)}"
            elif left:
                text += f", to the right of the {words(left)}"
            elif right:
                text += f", to the left of the {words(right)}"
            h = int(hashlib.sha1(c["id"].encode()).hexdigest(), 16)
            if h % 2:
                text = ("Click ", "Select ", "Press ")[h % 3] + text
            else:
                text = text[0].upper() + text[1:]
            n += 1; with_nb += bool(left or right)
            f.write(json.dumps(dict(c, id=c["id"] + "-struct", image=os.path.relpath(os.path.join(src, c["image"]), out_dir), instruction=text,
                                    meta=dict(c["meta"], structured=True))) + "\n")
print("data/mac/structured_s2ax: %d cases, %d of them name a neighbour (mac:structured_s2ax:train)" % (n, with_nb))
