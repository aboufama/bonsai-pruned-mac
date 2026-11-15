"""macsim.gen: make the sets. Run on the Mac mini (system font, Apple's symbol and icon renders).

    python -m macsim.gen make  --out ~/bonsai/macsim/macsim_train_s1 --split train --start 0 --n 3000 --workers 8
    python -m macsim.gen make  --out ~/bonsai/macsim/macsim_dev_s1   --split dev   --start 0 --n 300
    python -m macsim.gen make  --out ~/bonsai/macsim/macsim_steps_s1 --split steps --start 0 --n 600
    python -m macsim.gen sheet --data ~/bonsai/macsim/macsim_train_s1 --out sheet.png      # boxes drawn, for looking only
    python -m macsim.gen self  --data ~/bonsai/macsim/macsim_train_s1                      # the scorer on the oracle's own answers

A folder is in the loader's format ("gen:" in weightlab/core.py): cases.jsonl, screens.jsonl, images/, and
summary.json with the counts. `make` can be run again with a later --start; it appends and rebuilds the summary.
A steps folder also holds actions.jsonl (every step as one computer_use action, typing, keys and the final
"terminate" included) and tasks.jsonl (one line per task).
"""
import argparse
import collections
import json
import multiprocessing
import os
import random
import sys
import time

ICONS = "~/bonsai/icon_render"


def screen_job(sim, split, seed, out):
    from . import cases, sim as simlib, world
    state, post = world.build(seed, split)
    r = random.Random(f"macsim/cases/{split}/{seed}")
    sim.boot(state)
    sim.post(post, r)
    image, scale = sim.shot()
    els, surf, front = sim.elements()
    errors = sim.errors()
    if errors:
        return None, [], f"seed {seed}: {errors[:2]}"
    simlib.to_image(els, surf, scale)
    sid = f"macsim-{split}-{seed:06d}"
    screen = {"id": sid, "image": f"images/{sid}.png", "width": image.width, "height": image.height, "split": split, "seed": seed, "points": state["screen"], "scale": round(scale, 5), "theme": "dark" if state["dark"] else "light"}
    chosen, by_i = cases.make(els, surf, r)
    rows = [cases.record(c, by_i, surf, screen, k) for k, c in enumerate(chosen)]
    image.save(os.path.join(out, screen["image"]), compress_level=4)
    line = dict(screen, accent=state["accent"], wallpaper=state["wallpaper"], apps=[w["app"] for w in state["windows"]], front=front, overlay=[p[0] for p in post] + (["spotlight"] if state["spot"]["open"] else []) +
                (["alert"] if any(s["ui"].get("alert") for s in state["apps"].values()) else []), surfaces=surf, elements=[cases.public(e) for e in els])
    return line, rows, None


def steps_job(sim, seed, out):
    from . import cases, steps
    traj, why = steps.run(sim, seed)
    if not traj:
        return None, why
    tid = f"macsim-steps-{seed:06d}"
    st = traj["state"]
    lines, rows, acts, ids = [], [], [], []
    for rec in traj["steps"]:
        k, image = rec["k"], rec["image"]
        sid = f"{tid}-{k + 1}"
        screen = {"id": sid, "image": f"images/{sid}.png", "width": image.width, "height": image.height, "split": "steps", "seed": seed, "points": st["screen"], "scale": round(rec["scale"], 5), "theme": "dark" if st["dark"] else "light"}
        image.save(os.path.join(out, screen["image"]), compress_level=4)
        task = {"id": tid, "name": traj["task"], "request": traj["request"], "step": k + 1, "of": len(traj["steps"]), "history": rec["history"]}
        act = {"id": sid, "image": screen["image"], "width": image.width, "height": image.height, "goal": traj["request"], "history": rec["history"], "split": "train", "app": traj["app"] or "desktop", "meta": {"task": tid, "step": k + 1, "of": len(traj["steps"])}}
        if "e" in rec:
            verb = {"click": "Click", "double": "Double-click", "right": "Right-click"}[rec["do"]]
            c = {"e": rec["e"], "kind": "step", "phrase": "step", "instruction": f"{verb} {rec['say']}", "detail": rec["do"], "tiny": min(rec["e"]["box"][2] - rec["e"]["box"][0], rec["e"]["box"][3] - rec["e"]["box"][1]) <= cases.TINY, "partial": rec["e"]["vis"] < 0.75}
            row = cases.record(c, rec["by_i"], rec["surf"], screen, 0)
            row["id"], row["meta"]["task"] = sid, task
            rows.append(row)
            name = {"click": "left_click", "double": "double_click", "right": "right_click"}[rec["do"]]
            act.update(action={"name": name, "arguments": {"coordinate": rec["point"]}}, step={"action": {"click": "click", "double": "double_click", "right": "right_click"}[rec["do"]], "target": rec["say"]})
            act["meta"]["bbox"] = rec["e"]["box"]
        elif rec["do"] == "type":
            act.update(action={"name": "type", "arguments": {"text": rec["text"]}}, step={"action": "type", "text": rec["text"]})
        else:
            keys = [k.lower().replace("meta", "cmd") for k in rec["keys"].split("+")]
            act.update(action={"name": "key", "arguments": {"keys": keys}}, step={"action": "key", "keys": keys})
        acts.append(act)
        ids.append(sid)
        lines.append(dict(screen, task=tid, surfaces=rec["surf"], elements=[cases.public(e) for e in rec["els"]]))
    fid = f"{tid}-end"
    traj["final"].save(os.path.join(out, f"images/{fid}.png"), compress_level=4)
    acts.append({"id": fid, "image": f"images/{fid}.png", "width": traj["final"].width, "height": traj["final"].height, "goal": traj["request"], "history": traj["history"], "split": "train", "app": traj["app"] or "desktop",
                 "action": {"name": "terminate", "arguments": {"status": "success"}}, "step": {"action": "done"}, "meta": {"task": tid, "step": len(traj["steps"]) + 1, "of": len(traj["steps"])}})
    return {"lines": lines, "rows": rows, "acts": acts, "task": {"id": tid, "name": traj["task"], "app": traj["app"], "request": traj["request"], "steps": ids, "final": f"images/{fid}.png", "verdict": "done", "seed": seed}}, "ok"


def worker(args):
    w, a = args
    from .sim import Sim
    out = os.path.expanduser(a["out"])
    sim = Sim(a["icons"])
    seeds = [s for s in range(a["start"], a["start"] + a["n"]) if s % a["workers"] == w]
    files = {k: open(os.path.join(out, "parts", f"{k}-{a['start']}-{w}.jsonl"), "w", buffering=1) for k in ("cases", "screens", "actions", "tasks", "skipped")}
    put = lambda k, d: files[k].write(json.dumps(d, ensure_ascii=False) + "\n")
    done = 0
    for seed in seeds:
        try:
            if a["split"] == "steps":
                res, why = steps_job(sim, seed, out)
                if not res:
                    put("skipped", {"seed": seed, "why": why})
                    continue
                for l in res["lines"]:
                    put("screens", l)
                for r in res["rows"]:
                    put("cases", r)
                for x in res["acts"]:
                    put("actions", x)
                put("tasks", res["task"])
            else:
                line, rows, err = screen_job(sim, a["split"], seed, out)
                if err:
                    put("skipped", {"seed": seed, "why": err})
                    continue
                put("screens", line)
                for r in rows:
                    put("cases", r)
            done += 1
        except Exception as err:                              # one bad screen must not end the run; it is counted
            put("skipped", {"seed": seed, "why": f"{type(err).__name__}: {err}"[:300]})
            try:
                sim.close()
            except Exception:
                pass
            sim = Sim(a["icons"])
    for f in files.values():
        f.close()
    sim.close()
    return done


def merge(out):
    """Parts -> cases.jsonl, screens.jsonl (and actions.jsonl, tasks.jsonl), sorted by id; and the summary."""
    parts, got = os.path.join(out, "parts"), {}
    for kind in ("cases", "screens", "actions", "tasks", "skipped"):
        rows = {}
        for f in sorted(os.listdir(parts)):
            if f.startswith(kind + "-"):
                for l in open(os.path.join(parts, f)):
                    d = json.loads(l)
                    rows[d.get("id", d.get("seed"))] = l
        got[kind] = [rows[k] for k in sorted(rows, key=str)]
        if rows and kind != "skipped":
            with open(os.path.join(out, kind + ".jsonl"), "w") as f:
                f.writelines(got[kind])
    cs = [json.loads(l) for l in got["cases"]]
    count = lambda key: dict(sorted(collections.Counter(key(c) for c in cs).items(), key=lambda kv: -kv[1]))
    summary = {"screens": len(got["screens"]), "cases": len(cs), "by_challenge": count(lambda c: c["meta"]["kind"]), "by_phrase": count(lambda c: c["meta"]["phrase"]), "tiny": sum(c["meta"]["tiny"] for c in cs), "partly_hidden": sum(c["meta"]["partial"] for c in cs),
               "calendar_nav": sum(c["meta"].get("must") == "calendar_nav" for c in cs), "by_app": count(lambda c: c["meta"]["app"] or c["meta"]["where"]), "by_role": count(lambda c: c["meta"]["role"]), "by_surface": count(lambda c: c["meta"]["where"]),
               "by_theme": count(lambda c: c["meta"]["theme"]), "by_screen": count(lambda c: "x".join(map(str, c["meta"]["points"]))), "skipped": len(got["skipped"]),
               "skipped_why": dict(collections.Counter(json.loads(l)["why"].split(":")[0] for l in got["skipped"]).most_common(12))}
    if got["tasks"]:
        ts = [json.loads(l) for l in got["tasks"]]
        summary.update(tasks=len(ts), by_task=dict(sorted(collections.Counter(t["name"] for t in ts).items())), actions=len(got["actions"]), steps_per_task=round(sum(len(t["steps"]) for t in ts) / len(ts), 2))
    return summary


def make(a):
    out = os.path.expanduser(a.out)
    os.makedirs(os.path.join(out, "images"), exist_ok=True)
    os.makedirs(os.path.join(out, "parts"), exist_ok=True)
    args = {"out": out, "icons": a.icons, "split": a.split, "start": a.start, "n": a.n, "workers": a.workers}
    t = time.time()
    if a.workers == 1:
        done = [worker((0, args))]
    else:
        with multiprocessing.get_context("spawn").Pool(a.workers) as pool:
            done = pool.map(worker, [(w, args) for w in range(a.workers)])
    secs = time.time() - t
    summary = merge(out)
    summary["last_run"] = {"split": a.split, "start": a.start, "n": a.n, "made": sum(done), "seconds": round(secs, 1), "per_second": round(sum(done) / secs, 2), "workers": a.workers}
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(summary, sys.stdout, indent=1, ensure_ascii=False)
    print()


def sheet(a):
    """A contact sheet: some screens with every case's box drawn and numbered, the instructions beside. For looking only."""
    from PIL import Image, ImageDraw, ImageFont
    data = os.path.expanduser(a.data)
    by = collections.defaultdict(list)
    for l in open(os.path.join(data, "cases.jsonl")):
        c = json.loads(l)
        by[c["image"]].append(c)
    names = sorted(by)
    if a.pick:
        keep = {json.loads(l)["image"] for l in open(os.path.join(data, "screens.jsonl")) if a.pick in l[l.index('"apps"'):l.index('"surfaces"')]}
        names = [n for n in names if n in keep]
    r = random.Random(a.seed)
    names = r.sample(names, min(a.n, len(names)))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
    except Exception:
        font = ImageFont.load_default()
    tiles = []
    for n in names:
        im = Image.open(os.path.join(data, n)).convert("RGB")
        d = ImageDraw.Draw(im)
        side = Image.new("RGB", (620, im.height), "white")
        sd = ImageDraw.Draw(side)
        sd.text((8, 4), n.split("/")[-1], fill="black", font=font)
        for k, c in enumerate(by[n]):
            b = c["bbox"]
            d.rectangle([b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2], outline=(255, 0, 80), width=2)
            d.text((b[2] + 4, b[1] - 6), str(k), fill=(255, 0, 80), font=font, stroke_width=3, stroke_fill="white")
            m = c["meta"]
            sd.text((8, 28 + k * 44), f"{k} [{m['kind']}/{m['phrase']}{' tiny' if m['tiny'] else ''}{' part' if m['partial'] else ''}] {m['role']}: {m['name'][:40]}", fill=(120, 0, 40), font=font)
            sd.text((8, 46 + k * 44), c["instruction"][:86], fill="black", font=font)
        tile = Image.new("RGB", (im.width + 620, im.height), "white")
        tile.paste(im, (0, 0))
        tile.paste(side, (im.width, 0))
        tiles.append(tile)
        if a.tiles:
            tile.save(os.path.expanduser(a.out).replace(".png", f"-{len(tiles) - 1}.png"))
    w, h = max(t.width for t in tiles), sum(t.height + 8 for t in tiles)
    big = Image.new("RGB", (w, h), (40, 40, 40))
    y = 0
    for t in tiles:
        big.paste(t, (0, y))
        y += t.height + 8
    big.save(os.path.expanduser(a.out))
    print(a.out, big.size, len(tiles), "screens")


def self_test(a):
    """The scorer on answers whose truth is known: the oracle's point must be a hit, a point on each neighbour must
    be that neighbour's class, a point on a same-name element must be "same_name"."""
    from . import score
    cs = score.load(a.data)
    mid = lambda b: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    bad = collections.Counter()
    n = collections.Counter()
    for c in cs:
        m = c["meta"]
        n["oracle"] += 1
        if not score.classify(c, *mid(c["bbox"]))["hit"]:
            bad["oracle point is not a hit"] += 1
        for d, nb in m["neighbours"].items():
            if any(score._in(h, *mid(nb["box"])) for h in m["holes"]) or score._in(c["bbox"], *mid(nb["box"])):
                continue
            n["neighbour"] += 1
            got = score.classify(c, *mid(nb["box"]))
            if got["hit"] or got["class"] not in (d + "_neighbour", "same_name", "wrong_window"):
                bad[f"point on the {d} neighbour scored {got['class']}"] += 1
        for s in m["same_name"]:
            n["same_name"] += 1
            got = score.classify(c, *mid(s["box"]))
            if got["hit"] or got["class"] not in ("same_name", "wrong_window", "child_element"):
                bad[f"point on a same-name element scored {got['class']}"] += 1
    print(json.dumps({"checked": dict(n), "wrong": dict(bad)}, indent=1))
    return not bad


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--out", required=True)
    m.add_argument("--split", choices=["train", "dev", "steps"], required=True)
    m.add_argument("--start", type=int, default=0)
    m.add_argument("--n", type=int, default=100)
    m.add_argument("--workers", type=int, default=6)
    m.add_argument("--icons", default=ICONS)
    s = sub.add_parser("sheet")
    s.add_argument("--data", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--n", type=int, default=6)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--tiles", action="store_true", help="also save each screen of the sheet as its own file")
    s.add_argument("--pick", help="only screens whose apps or overlay hold this word (reads screens.jsonl)")
    t = sub.add_parser("self")
    t.add_argument("--data", required=True)
    g = sub.add_parser("merge")
    g.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "make":
        make(a)
    elif a.cmd == "sheet":
        sheet(a)
    elif a.cmd == "self":
        sys.exit(0 if self_test(a) else 1)
    else:
        print(json.dumps(merge(os.path.expanduser(a.out)), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
