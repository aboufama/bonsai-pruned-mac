"""Pointing test sets of the benchmark, one loader each.

Every loader returns a list of cases sorted by id. A case is a dict:

    id           unique within the set
    image        absolute path of the screenshot
    instruction  what to point at
    target       {"type": "box", "box": [x1, y1, x2, y2]}        pixels of the original screenshot
                 {"type": "polygon", "points": [x1, y1, x2, y2, ...]}
                 {"type": "absent"}                              nothing to point at: the right answer is a refusal
    group        platform / application group, used for the per-group rows
    ui_type      "text" or "icon" where the set says so
    cluster      the screenshot, for intervals that resample screenshots instead of cases
    flags        set-specific booleans (see each loader)

Sources are checked in docs/BENCHMARK.md. Nothing here is downloaded; `bench/README.md` says
where each set has to be.
"""
import glob
import json
import os


def root():
    return os.path.expanduser(os.environ.get("BONSAI_ROOT", "~/bonsai"))


def ssv2(R=None):
    """ScreenSpot-v2 (OS-Copilot/ScreenSpot-v2), all 1,272 cases.

    flags: overlap  one of the 8 cases whose screen also occurs in public macOS training data
                    (ssv2/excluded_overlap.json, docs/MAC_DATA.md)
           select   the eighth (position 1 modulo 8 after sorting by id) that was used to choose
                    between training runs
           report   the eighth (position 5 modulo 8) quoted during development
    """
    R = R or root()
    items = []
    for split in ("desktop", "mobile", "web"):
        for i, it in enumerate(json.load(open(f"{R}/ssv2/screenspot_{split}_v2.json"))):
            x, y, w, h = it["bbox"]
            items.append({"id": f"{split}_{i:04d}", "image": f"{R}/ssv2/screenspotv2_image/{it['img_filename']}",
                          "instruction": it["instruction"], "target": {"type": "box", "box": [x, y, x + w, y + h]},
                          "group": split, "ui_type": it["data_type"], "cluster": it["img_filename"]})
    items.sort(key=lambda c: c["id"])
    path = f"{R}/ssv2/excluded_overlap.json"
    overlap = {f"{e['split']}_{int(e['index']):04d}" for e in json.load(open(path))} if os.path.exists(path) else set()
    for pos, it in enumerate(items):
        it["flags"] = {"overlap": it["id"] in overlap, "select": pos % 8 == 1, "report": pos % 8 == 5}
    return items


def sspro(R=None):
    """ScreenSpot-Pro (likaixin/ScreenSpot-Pro), 1,581 cases on high-resolution professional software."""
    R = R or root()
    items = []
    for path in sorted(glob.glob(f"{R}/sspro/annotations/*.json")):
        for it in json.load(open(path)):
            items.append({"id": it["id"], "image": f"{R}/sspro/images/{it['img_filename']}",
                          "instruction": it["instruction"], "target": {"type": "box", "box": list(it["bbox"])},
                          "group": it["group"], "ui_type": it["ui_type"], "cluster": it["img_filename"],
                          "flags": {"app": it.get("application"), "platform": it.get("platform")}})
    items.sort(key=lambda c: c["id"])
    return items


def _osworld_g(R, name):
    base = f"{R}/pub/osworld-g-repo/benchmark"
    items = []
    for it in json.load(open(f"{base}/{name}.json")):
        c = it["box_coordinates"]
        if it["box_type"] == "bbox":
            target = {"type": "box", "box": [c[0], c[1], c[0] + c[2], c[1] + c[3]]}
        elif it["box_type"] == "polygon":
            target = {"type": "polygon", "points": list(c)}
        else:
            target = {"type": "absent"}
        items.append({"id": it["id"], "image": f"{base}/images/{it['image_path']}", "instruction": it["instruction"],
                      "target": target, "group": it["box_type"], "ui_type": None, "cluster": it["image_path"],
                      "flags": {"gui_types": it.get("GUI_types")}})
    items.sort(key=lambda c: c["id"])
    return items


def osworld_g(R=None):
    """OSWorld-G (github.com/xlang-ai/OSWorld-G, benchmark/OSWorld-G.json), 564 cases, original
    instructions. 54 of them have no target: the right answer is a refusal."""
    return _osworld_g(R or root(), "OSWorld-G")


def osworld_g_refined(R=None):
    """The same 564 cases with the refined instructions (benchmark/OSWorld-G_refined.json)."""
    return _osworld_g(R or root(), "OSWorld-G_refined")


def mac(R=None):
    """Screen2AX-Task, the app keys reserved for testing (docs/MAC_DATA.md): 2,106 cases on 134
    macOS app-window screenshots. No training run used a screenshot or an app of this set."""
    R = R or root()
    base = f"{R}/data/mac/screen2ax_task"
    items = []
    for line in open(f"{base}/cases.jsonl"):
        it = json.loads(line)
        if it.get("split") != "test":
            continue
        items.append({"id": it["id"], "image": f"{base}/{it['image']}", "instruction": it["instruction"],
                      "target": {"type": "box", "box": list(it["bbox"])}, "group": it["meta"].get("app_key") or it.get("app"),
                      "ui_type": None, "cluster": it["image"], "flags": {"small": bool(it["meta"].get("small"))}})
    items.sort(key=lambda c: c["id"])
    return items


def neighbour(R=None):
    """The neighbour slice (tools/neighbour_cases.py): 600 held-out macOS cases whose target is a small
    control with other controls close by. Same format and folder layout as the other Mac sets."""
    R = R or root()
    base = f"{R}/data/mac/neighbour_test"
    items = []
    for line in open(f"{base}/cases.jsonl"):
        it = json.loads(line)
        if it.get("split") not in (None, "test"):
            continue
        items.append({"id": it["id"], "image": f"{base}/{it['image']}", "instruction": it["instruction"],
                      "target": {"type": "box", "box": list(it["bbox"])}, "group": (it.get("meta") or {}).get("app_key") or it.get("app") or "mac",
                      "ui_type": None, "cluster": it["image"], "flags": {}})
    items.sort(key=lambda c: c["id"])
    return items


def mac_agentnet(R=None):
    """AgentNet macOS, held-out recording sessions: 504 human click points. There is no box, so a
    square of +-1.2% of the image width is put around the click (as the lab does)."""
    R = R or root()
    base = f"{R}/data/mac/agentnet"
    items = []
    for line in open(f"{base}/cases.jsonl"):
        it = json.loads(line)
        if it.get("split") != "test":
            continue
        x, y = it["point"]
        tol = 0.012 * it["width"]
        items.append({"id": it["id"], "image": f"{base}/{it['image']}", "instruction": it["instruction"],
                      "target": {"type": "box", "box": [x - tol, y - tol, x + tol, y + tol]}, "group": it.get("app") or "mac",
                      "ui_type": None, "cluster": it["image"], "flags": {"point_only": True}})
    items.sort(key=lambda c: c["id"])
    return items


def gen(R=None, name="benchdata/pointing/dev_20261114"):
    """Our generated benchmark (bench/pointing/generate.py, dev split, seed 20261114): 413 cases
    on 52 rendered screens with exact boxes. It has no absent-target cases."""
    R = R or root()
    base = f"{R}/{name}"
    items = []
    for line in open(f"{base}/cases.jsonl"):
        it = json.loads(line)
        tags = it.get("tags", {})
        items.append({"id": it["id"], "image": f"{base}/{it['image']}", "instruction": it["instruction"],
                      "target": {"type": "box", "box": list(it["bbox"])}, "group": it["meta"].get("archetype", "gen"),
                      "ui_type": it["element"].get("ui_type", "text"), "cluster": it["image"],
                      "flags": {"kind": tags.get("instruction_kind"), "size": tags.get("size")}})
    items.sort(key=lambda c: c["id"])
    return items


POINTING = {"ssv2": ssv2, "sspro": sspro, "osworld_g": osworld_g, "osworld_g_refined": osworld_g_refined,
            "mac": mac, "neighbour": neighbour, "mac_agentnet": mac_agentnet, "gen": gen}


def pick(items, limit=0, shard=None):
    """An evenly spaced subset of `limit` cases (0 = all), then shard k of n (every n-th case)."""
    if limit and limit < len(items):
        step = len(items) / limit
        items = [items[int(i * step)] for i in range(limit)]
    if shard:
        k, n = shard
        items = [it for i, it in enumerate(items) if i % n == k]
    return items


def hit(point_px, target):
    """Is the point (pixels of the original screenshot, or None for a refusal) a correct answer?"""
    if target["type"] == "absent":
        return point_px is None
    if point_px is None:
        return False
    x, y = point_px
    if target["type"] == "box":
        b = target["box"]
        return b[0] <= x <= b[2] and b[1] <= y <= b[3]
    p = target["points"]                                   # polygon: the rule of OSWorld-G's eval.py
    n, inside, j = len(p) // 2, False, len(p) // 2 - 1
    for i in range(n):
        xi, yi, xj, yj = p[2 * i], p[2 * i + 1], p[2 * j], p[2 * j + 1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside
