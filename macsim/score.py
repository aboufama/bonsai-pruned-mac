"""macsim.score: the verifiable reward. Pure Python, no dependencies; runs on the Spark and the pods.

    python macsim/score.py --data ~/bonsai/benchdata/pointing/macsim_dev_s1 --answers answers.jsonl [--out scored.jsonl]

answers.jsonl has one line per case: {"id": ..., "point": [x, y]} in pixels of the saved image, or
{"id": ..., "grid": [x, y]} on the 1000 x 1000 grid, or {"id": ..., "raw": "<the model's text>"} (the first two
numbers are read as a grid point; --raw-space pixels reads them as pixels). A missing or [-1, -1] answer is "no_answer".

Per case the scorer returns hit or miss and the failure class:
    hit              inside the target (not on a child element inside it)
    child_element    on a control that sits inside the target (a tab's close button, an event chip in a day cell)
    same_name        on another element with the same name (the Search field of the wrong window)
    left_neighbour, right_neighbour, up_neighbour, down_neighbour     on the element next to the target on that side
    wrong_window     on another window or surface than the target's (a menu, the Dock, a window in front)
    near             within NEAR px of the target, on nothing else
    far              anywhere else; "distance" says how far (px of the image, and points of the screen)
For a multi-step task (macsim_steps_*) the verdict of the task is the state checker's: the oracle's path through the
task was checked by the checker when the data was made, and a click inside the target does what the oracle's click
did, so a task is "done" exactly when every pointing step of it is a hit.

In code:  from macsim.score import classify, reward
    classify(case, x, y) -> {"hit", "class", "distance", "distance_points", "on"}
    reward(case, x, y)   -> 1.0 for a hit; with shaped=True a miss on nothing earns up to 0.5 by closeness,
                            and a miss on a neighbour, a same-name element or another window earns 0
"""
import argparse
import collections
import json
import math
import os
import re
import sys

NEAR = 12
ORDER = ("hit", "child_element", "same_name", "left_neighbour", "right_neighbour", "up_neighbour", "down_neighbour", "wrong_window", "near", "far", "no_answer")


def _in(b, x, y):
    return b[0] <= x <= b[2] and b[1] <= y <= b[3]


def classify(case, x, y):
    m, b = case["meta"], case["bbox"]
    if x is None or y is None or x < 0 or y < 0:
        return {"hit": False, "class": "no_answer", "distance": None, "distance_points": None, "on": None}
    dx, dy = max(b[0] - x, 0, x - b[2]), max(b[1] - y, 0, y - b[3])
    dist = math.hypot(dx, dy)
    out = {"hit": False, "distance": round(dist, 1), "distance_points": round(dist / m["scale"], 1), "on": None}
    top = None
    for u in m["surfaces"]:                                  # back to front: the last one that holds the point is on top
        if _in(u["box"], x, y):
            top = u["name"]
    child = any(_in(h, x, y) for h in m["holes"])
    whole = _in(b, x, y) or (m["visible"] >= 0.99 and _in(m["full_box"], x, y))
    if whole and not child:
        return dict(out, hit=True, **{"class": "hit"}, distance=0.0, distance_points=0.0)
    if whole:
        return dict(out, **{"class": "child_element"})
    for s in m["same_name"]:
        if _in(s["box"], x, y):
            return dict(out, **{"class": "same_name"}, on=f"{s['role']} {s['name']} ({s['surface']})")
    if top == m["surface"] or top is None:
        for d in ("left", "right", "up", "down"):
            n = m["neighbours"].get(d)
            if n and _in(n["box"], x, y):
                return dict(out, **{"class": d + "_neighbour"}, on=f"{n['role']} {n['name']}")
    if top is not None and top != m["surface"]:
        return dict(out, **{"class": "wrong_window"}, on=top)
    return dict(out, **{"class": "near" if dist <= NEAR else "far"})


def reward(case, x, y, shaped=False):
    c = classify(case, x, y)
    if c["hit"]:
        return 1.0
    if shaped and c["class"] in ("near", "far"):
        return 0.5 * math.exp(-c["distance"] / 40.0)
    return 0.0


def read_point(a, case, raw_space="grid"):
    if a is None:
        return None, None
    w, h = case["width"], case["height"]
    if a.get("point"):
        return float(a["point"][0]), float(a["point"][1])
    if a.get("grid"):
        return a["grid"][0] * w / 1000.0, a["grid"][1] * h / 1000.0
    nums = re.findall(r"-?\d+(?:\.\d+)?", str(a.get("raw", "")))
    if len(nums) < 2:
        return None, None
    x, y = float(nums[0]), float(nums[1])
    return (x, y) if raw_space == "pixels" else (x * w / 1000.0, y * h / 1000.0)


def score(cases, answers, raw_space="grid"):
    """cases: list of case dicts; answers: {id: answer dict}. Returns (per-case rows, summary)."""
    rows = []
    for c in cases:
        x, y = read_point(answers.get(c["id"]), c, raw_space)
        r = classify(c, x, y)
        m = c["meta"]
        rows.append(dict(r, id=c["id"], kind=m["kind"], phrase=m["phrase"], tiny=m["tiny"], partial=m["partial"], app=m["app"], task=(m.get("task") or {}).get("id")))
    rate = lambda rs: {"n": len(rs), "hit": round(sum(r["hit"] for r in rs) / len(rs), 4)} if rs else {"n": 0, "hit": None}
    group = lambda key: {k: rate([r for r in rows if key(r) == k]) for k in sorted({key(r) for r in rows}, key=str)}
    summary = {"all": rate(rows), "by_kind": group(lambda r: r["kind"]), "by_phrase": group(lambda r: r["phrase"]), "tiny": rate([r for r in rows if r["tiny"]]), "partly_hidden": rate([r for r in rows if r["partial"]]),
               "by_app": group(lambda r: r["app"] or "desktop"), "classes": {k: v for k, v in sorted(collections.Counter(r["class"] for r in rows).items(), key=lambda kv: ORDER.index(kv[0]))}}
    tasks = collections.defaultdict(list)
    for r in rows:
        if r["task"]:
            tasks[r["task"]].append(r["hit"])
    if tasks:
        done = [all(v) for v in tasks.values()]
        summary["tasks"] = {"n": len(done), "done": round(sum(done) / len(done), 4), "note": "done = every pointing step of the task is a hit (the checker's verdict along the oracle's path)"}
    return rows, summary


def load(data):
    return [json.loads(l) for l in open(os.path.join(os.path.expanduser(data), "cases.jsonl"))]


def main():
    ap = argparse.ArgumentParser(description="Score a model's answers on a macsim set: hit or miss and the failure class per case.")
    ap.add_argument("--data", required=True, help="a macsim folder (with cases.jsonl)")
    ap.add_argument("--answers", required=True, help="jsonl: {id, point | grid | raw}")
    ap.add_argument("--out", help="write one scored line per case here")
    ap.add_argument("--raw-space", choices=["grid", "pixels"], default="grid")
    a = ap.parse_args()
    cases = load(a.data)
    answers = {}
    for l in open(os.path.expanduser(a.answers)):
        if l.strip():
            d = json.loads(l)
            answers[d["id"]] = d
    rows, summary = score(cases, answers, a.raw_space)
    if a.out:
        with open(os.path.expanduser(a.out), "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary["answered"] = sum(c["id"] in answers for c in cases)
    json.dump(summary, sys.stdout, indent=1, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
