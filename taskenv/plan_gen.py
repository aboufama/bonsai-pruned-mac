"""Planner training rows from the oracle, on the TRAINING apps only (see planmode.TRAIN_APPS).

    python -m taskenv.plan_gen --out /root/te-runs/planner_sim_s1 --singles 30 --pairs 2000 --triples 500 --workers 12
    python -m taskenv.plan_gen --out /root/te-runs/planner_sim_s1 --split held_out          # scoring rows, split "dev"

Every episode is played twice: once by the oracle, translated step by step into `next_step` answers, and once
again through the planner's own executor from the recorded answers. It is kept when the checker accepts both.
Output, in the folder format weightlab/planner.py reads: turns_sim_<split>.jsonl with one turn per line
(id, source, split, task, apps, front_app, window, done, controls [{n, role, name, value?}], answer) and
summary_<split>.json. Extra keys: meta (task ids, seed, step, of, kind, variant), state, hint, hidden.
"""
import argparse
import collections
import json
import multiprocessing
import os
import random
import sys
import time


def jobs(a):
    from . import planmode
    from .tasks import base
    sets = planmode.task_sets()
    out = []
    if a.split != "train":
        for tid in sets[a.split]:
            for seed in base.TEST_SEEDS:
                out.append(([tid], seed, "front"))
        return out
    rng = random.Random(f"plan_gen/{a.seed0}")
    for tid in sets["train"]:
        for s in range(a.singles):
            out.append(([tid], a.seed0 + s, rng.choices(["front", "closed", "behind"], [0.5, 0.3, 0.2])[0]))
    chainable = []                                           # act tasks without a drag: these can be chained
    for tid in sets["train"]:
        try:
            ep = base.build(tid, a.seed0)
        except Exception:
            continue
        if ep.kind == "act" and ep.steps and not any(type(s).__name__ == "Drag" for s in ep.steps):
            chainable.append(tid)
    app = lambda t: t.split(".")[0]
    for n, count in ((2, a.pairs), (3, a.triples)):
        k = 0
        while k < count and len({app(t) for t in chainable}) >= n:
            tids = rng.sample(chainable, n)
            if len({app(t) for t in tids}) == n:
                out.append((tids, a.seed0 + 1000 * n + k, "front"))
                k += 1
    return out


def worker(args):
    w, a, todo = args
    from . import planmode
    from .env import Env
    env = Env()
    path = os.path.join(a["out"], "parts", f"{a['split']}-{a['seed0']}-{w}.jsonl")
    done = collections.Counter()
    with open(path, "w", buffering=1) as f:
        for tids, seed, variant in todo:
            name = "+".join(tids)
            rng = random.Random(f"plan_gen/{name}/{seed}/{variant}")
            try:
                ep = planmode.build(tids, seed)
                if len(tids) == 1:
                    ep.request = planmode.rephrase(ep.request, rng)
                for use_open_url in (True, False):                # an address typed into the browser is open_url, when that replays
                    rng = random.Random(f"plan_gen/{name}/{seed}/{variant}/run")
                    rows, state, ok, why = planmode.oracle_rows(env, ep, rng, variant, drop_rate=a["drop"], use_open_url=use_open_url)
                    if ok:
                        ok, why = planmode.replay(env, ep, state, rows)
                    if ok or not any(r["answer"]["action"] == "open_url" for r in rows):
                        break
                if not ok:
                    f.write(json.dumps({"skipped": name, "seed": seed, "why": str(why)[:160]}) + "\n")
                    done["skipped"] += 1
                    continue
            except Exception as err:
                f.write(json.dumps({"skipped": name, "seed": seed, "why": f"{type(err).__name__}: {err}"[:160]}) + "\n")
                done["skipped"] += 1
                if not isinstance(err, (planmode.Untranslatable, AssertionError, LookupError)):
                    try:
                        env.close()
                    except Exception:
                        pass
                    env = Env()
                continue
            for k, row in enumerate(rows):
                row.update(id=f"sim-{name}-{seed}-{variant}-{k + 1}", source="taskenv-oracle", split="train" if a["split"] == "train" else "dev",
                           meta={"tasks": tids, "seed": seed, "step": k + 1, "of": len(rows), "kind": ep.kind, "category": ep.category, "variant": variant, "set": a["split"]})
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            done["episodes"] += 1
    env.close()
    return dict(done)


def merge(out, split):
    rows, skipped = {}, []
    parts = os.path.join(out, "parts")
    for name in sorted(os.listdir(parts)):
        if name.startswith(split + "-"):
            for line in open(os.path.join(parts, name)):
                d = json.loads(line)
                if "skipped" in d:
                    skipped.append(d)
                else:
                    rows[d["id"]] = d
    rows = [rows[k] for k in sorted(rows)]
    with open(os.path.join(out, f"turns_sim_{split}.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    eps = {(tuple(r["meta"]["tasks"]), r["meta"]["seed"], r["meta"]["variant"]): r["meta"] for r in rows}
    count = lambda xs: dict(sorted(collections.Counter(xs).items(), key=lambda kv: -kv[1]))
    summary = {"split": split, "turns": len(rows), "episodes": len(eps), "by_action": count(r["answer"]["action"] for r in rows), "episodes_by_length": dict(sorted(collections.Counter(m["of"] for m in eps.values()).items())),
               "episodes_by_tasks": count(len(k[0]) for k in eps), "episodes_by_kind": count(m["kind"] for m in eps.values()), "episodes_by_variant": count(m["variant"] for m in eps.values()),
               "episodes_by_app": count(k[0][0].split(".")[0] for k in eps), "templates": len({t for k in eps for t in k[0]}), "requests": len({r["task"] for r in rows}),
               "controls_per_turn": round(sum(len(r["controls"]) for r in rows) / max(1, len(rows)), 1), "skipped": len(skipped), "skipped_why": count(s["why"].split(":")[0][:60] for s in skipped),
               "skipped_tasks": count(s["skipped"] for s in skipped)}
    json.dump(summary, open(os.path.join(out, f"summary_{split}.json"), "w"), indent=1, ensure_ascii=False)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", choices=["train", "held_out"], default="train")
    ap.add_argument("--singles", type=int, default=20, help="seeds per training template")
    ap.add_argument("--pairs", type=int, default=0, help="chains of two tasks in different apps")
    ap.add_argument("--triples", type=int, default=0)
    ap.add_argument("--seed0", type=int, default=None)
    ap.add_argument("--drop", type=float, default=0.08, help="share of clicks answered with `look` because the control is left out of the list")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    from . import planmode
    a.seed0 = a.seed0 or planmode.TRAIN_SEED0
    assert a.split != "train" or a.seed0 >= planmode.TRAIN_SEED0, "training seeds start at 20001"
    out = os.path.expanduser(a.out)
    os.makedirs(os.path.join(out, "parts"), exist_ok=True)
    todo = jobs(a)
    if a.limit:
        todo = todo[::max(1, len(todo) // a.limit)][:a.limit]
    args = {"out": out, "split": a.split, "seed0": a.seed0, "drop": a.drop if a.split == "train" else 0.0}
    t = time.time()
    if a.workers == 1:
        got = [worker((0, args, todo))]
    else:
        with multiprocessing.get_context("spawn").Pool(a.workers) as pool:
            got = pool.map(worker, [(w, args, todo[w::a.workers]) for w in range(a.workers)])
    summary = merge(out, a.split)
    summary["last_run"] = {"jobs": len(todo), "episodes": sum(g.get("episodes", 0) for g in got), "seconds": round(time.time() - t, 1), "workers": a.workers}
    json.dump(summary, sys.stdout, indent=1, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
