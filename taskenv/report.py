"""Tables from the runs.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    python -m taskenv.report --runs ~/Bonsai-demo/taskenv-runs [--seeds test] [--out taskenv/results]

Reads every <runs>/<name>/{meta.json, episodes.jsonl}. Writes summary.md and summary.json to
--out (and prints the markdown). The 95% intervals are bootstrap intervals over tasks (2,000
resamples of whole tasks, so that the seeds of one task stay together); with the oracle at 100%
by construction they say how far a rate could move with another draw of tasks of the same kind.
"""
import argparse
import collections
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from taskenv.tasks.base import CATEGORIES, DEV_SEEDS, TEST_SEEDS  # noqa: E402

BINS = [("0", 0, 0), ("1", 1, 1), ("2-3", 2, 3), ("4-5", 4, 5), ("6+", 6, 99)]
CAT_LABEL = {"single": "One click", "chain": "Chain", "typing": "Typing", "drag": "Drag", "scroll": "Scroll to find", "menu": "Menus",
             "shortcut": "Shortcut", "already_done": "Already done", "infeasible": "Cannot be done"}


def load_runs(root, seeds=None):
    runs = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not (os.path.isfile(os.path.join(d, "meta.json")) and os.path.isfile(os.path.join(d, "episodes.jsonl"))):
            continue
        meta = json.load(open(os.path.join(d, "meta.json")))
        eps = {}
        for line in open(os.path.join(d, "episodes.jsonl")):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if seeds is None or r["seed"] in seeds:
                eps[(r["task"], r["seed"])] = r
        if eps:
            # a run may be extended seed by seed: only seeds that are finished count; a run with none finished is "still running"
            per = collections.Counter(s for _, s in eps)
            full = {s for s, n in per.items() if n >= (meta.get("tasks") or max(per.values()))}
            kept = [e for (t, s), e in eps.items() if s in full]
            runs.append({"name": name, "meta": meta, "episodes": kept or list(eps.values()), "complete": bool(kept)})
    return runs


def interval(eps, n_boot=2000, seed=7):
    """Bootstrap 95% interval of the success rate, resampling tasks."""
    by_task = collections.defaultdict(list)
    for e in eps:
        by_task[e["task"]].append(1.0 if e["success"] else 0.0)
    tasks = list(by_task.values())
    if not tasks:
        return (0.0, 0.0)
    rng, rates = random.Random(seed), []
    for _ in range(n_boot):
        s = n = 0
        for _ in tasks:
            t = tasks[rng.randrange(len(tasks))]
            s += sum(t)
            n += len(t)
        rates.append(s / n)
    rates.sort()
    return rates[int(0.025 * n_boot)], rates[int(0.975 * n_boot) - 1]


def _mean(v):
    return sum(v) / len(v) if v else float("nan")


def rate(eps):
    return sum(e["success"] for e in eps) / len(eps) if eps else float("nan")


def pct(v):
    return "n/a" if v != v else f"{100 * v:.0f}%"


def summarise(run):
    eps, meta = run["episodes"], run["meta"]
    steps = [s for e in eps for s in e["steps"]]
    model_steps = [s for s in steps if not s.get("scripted")]
    acts = [e for e in eps if e["kind"] == "act"]
    lo, hi = interval(eps)
    pts = [i for s in model_steps for i in s.get("inside", [])]
    secs = [s.get("model_seconds", s["seconds"]) for s in model_steps if s.get("model_seconds", s["seconds"]) > 0]
    out = {"name": run["name"], "complete": run.get("complete", True), "agent": meta.get("agent"), "model": meta.get("model"), "tag": meta.get("tag") or "", "patch": meta.get("patch"),
           "input": meta.get("input"), "ask": meta.get("ask"), "prompt": meta.get("prompt"), "n": len(eps), "tasks": len({e["task"] for e in eps}),
           "seeds": sorted({e["seed"] for e in eps}), "success": rate(eps), "lo": lo, "hi": hi,
           "success_act": rate(acts), "n_act": len(acts),
           "mean_steps": sum(e["n_steps"] for e in eps) / len(eps), "mean_needed": sum((e.get("needed") or 0) for e in eps) / len(eps),
           "seconds_per_step": sum(secs) / len(secs) if secs else float("nan"),
           "invalid": sum(1 for s in model_steps if s["action"] is None), "model_steps": len(model_steps),
           "stopped": sum(1 for e in eps if e["stopped"]) / len(eps),
           "strict": sum(1 for e in eps if e["success"] and e["stopped"]) / len(eps),
           "stuck": sum(1 for e in eps if e.get("stuck")) / len(eps),
           "point_inside": sum(pts) / len(pts) if pts else float("nan"), "n_points": len(pts),
           "snap": bool(meta.get("snap")), "check": ("ask" if meta.get("check") is True else meta.get("check") or ""), "v1": bool((meta.get("snap") or meta.get("check")) and not meta.get("aids_version")), "mlx": str(meta.get("model") or "").startswith("mlx-"),
           "snapped": sum(1 for s in model_steps for v in s.get("snapped", []) if v),
           "checks_no": sum(1 for s in model_steps if s.get("check") is False), "retries": sum(1 for s in model_steps if s.get("retry")),
           "prompt_tokens": _mean([s["prompt_tokens"] for s in model_steps if s.get("prompt_tokens") and "inside" in s]),
           "sec_point": _mean([s["model_seconds"] / max(1, len(s["inside"])) for s in model_steps if "inside" in s and not s.get("retry") and s.get("model_seconds")]),
           "sec_step": (sum(s.get("model_seconds") or 0 for s in model_steps) / max(1, sum(1 for s in model_steps if "inside" in s and not s.get("retry")))),
           "peak_gb": max([s.get("peak_memory_gb") or 0 for s in model_steps] or [0]),
           "thinking": bool(meta.get("thinking")), "shard": meta.get("shard") or "", "orch": bool(meta.get("orchestrated")),
           "planner_sec": _mean([s["planner_seconds"] for s in model_steps if s.get("planner_seconds")]),
           "pointer_sec": _mean([s["pointer_seconds"] for s in model_steps if s.get("pointer_seconds")]),
           "think_tokens": _mean([s.get("think_tokens") or 0 for s in model_steps]) if meta.get("thinking") else 0.0,
           "by_category": {c: [sum(e["success"] for e in eps if e["category"] == c), sum(1 for e in eps if e["category"] == c)] for c in CATEGORIES},
           "by_needed": {b: [sum(e["success"] for e in eps if lo_ <= (e.get("needed") or 0) <= hi_), sum(1 for e in eps if lo_ <= (e.get("needed") or 0) <= hi_)]
                         for b, lo_, hi_ in BINS},
           "by_app": {}}
    for e in eps:
        k = out["by_app"].setdefault(e["app"], [0, 0])
        k[0] += e["success"]
        k[1] += 1
    return out


NAMES = {"qwen35-9b": "Qwen3.5-9B (parent, full precision)", "venus2-9b": "UI-Venus-2-9B (full precision)", "bonsai9b-orig": "Bonsai 2 9B, original",
         "bonsai4b-orig": "Bonsai 2 4B, original", "9b-v3-gentle": "Bonsai 2 9B, repaired (v3-gentle)", "9b-v2": "Bonsai 2 9B, repaired (v2)",
         "9b-v3-tools": "Bonsai 2 9B, repaired + tool calls (v3-tools)", "4b-v2-mixed": "Bonsai 2 4B, repaired (v2-mixed)", "4b-v1": "Bonsai 2 4B, repaired (v1)",
         "4b-tools": "Bonsai 2 4B, repaired + tool calls (tools-v1)", "9b-orig": "Bonsai 2 9B, original", "4b-orig": "Bonsai 2 4B, original",
         "4b-v3-mixed": "Bonsai 2 4B, repaired (v3-mixed)", "4b-head": "Bonsai 2 4B v2-mixed, pointing decoder on 20 layers (s6000), no written answer",
         "4b-joint-head": "Bonsai 2 4B joint trunk + pointing decoder on 20 layers (s4000), no written answer", "9b-v3-mixed896": "Bonsai 2 9B, repaired (v3-mixed896)"}


def label(s):
    if s["agent"] in ("oracle", "noop", "random"):
        return {"oracle": "Scripted oracle (solves through the page)", "noop": "Does nothing, says done", "random": "Random clicks"}[s["agent"]]
    tag = s["tag"] or s["model"] or "?"
    if tag.startswith("4b-joint-head-s"):
        return f"Bonsai 2 4B joint trunk + pointing decoder on 20 layers ({tag.rsplit('-', 1)[1]}), no written answer"
    if tag == "9b-v3-mixed896":
        return "Bonsai 2 9B, repaired (v3-mixed896)"
    if "+" in tag:                                     # orchestrator + pointer, e.g. 9b-orch-u500+4b-joint-s7500
        o, p = tag.split("+", 1)
        return f"Orchestrator Bonsai 2 {o.split('-')[0].upper()} ({o.split('-', 1)[1]}) says the step, pointer {p} finds it"
    if "orch" in tag:
        return f"Orchestrator Bonsai 2 {tag.split('-')[0].upper()} ({tag.split('-', 1)[1]}) says the step and points itself"
    if "actions" in tag:                               # e.g. 4b-actions-u1000
        size, _, rest = tag.partition("-actions-")
        return f"Bonsai 2 {size.upper()}, action-trained (v1, update {rest.lstrip('u')})"
    return NAMES.get(tag, tag)


def row_name(s):
    if not s["model"]:
        return label(s)
    aids = "".join((["+snap"] if s.get("snap") else []) + (["+" + ("check" if s["check"] == "ask" else "second look")] if s.get("check") else [])) + (" (first version)" if s.get("v1") else "")
    return f"{label(s)}, {s['agent']}{aids}, {s['input'][1:]} px{', MLX' if s.get('mlx') else ''}{', thinking on' if s.get('thinking') else ''}{', every fifth task' if s.get('shard') else ''}"


def cell(k):
    return "n/a" if not k[1] else f"{100 * k[0] / k[1]:.0f}% ({k[0]}/{k[1]})"


def tables(summaries, extra=None):
    md = []
    running = [s for s in summaries if not s.get("complete", True)]
    summaries = [s for s in summaries if s.get("complete", True)]
    order = {"agent": 0, "guided": 1, "oracle": 2, "noop": 3, "random": 4}
    S = sorted(summaries, key=lambda s: (order.get(s["agent"], 9), not s.get("mlx"), -s["success"]))
    for mode, title, note in (("agent", "Agent mode: the model chooses every action", ""),
                              ("guided", "Guided mode: each step is given in words, the model only points",
                               "Tasks with nothing to do (already done, cannot be done) are not part of guided mode.")):
        rows = [s for s in S if s["agent"] == mode]
        if not rows:
            continue
        md += [f"### {title}", ""]
        if note:
            md += [note, ""]
        if mode == "agent":
            md += ["| Model | Input | Tasks done | 95% interval | Done and said so | Episodes | Steps used (needed) | Seconds per step | Unreadable or invalid actions | Stopped by itself | Cut as stuck |", "|---|---|---|---|---|---|---|---|---|---|---|"]
            for s in rows:
                who = label(s) + (", MLX on the Mac mini" if s["mlx"] else "") + (", thinking on (%.0f tokens per step)" % s["think_tokens"] if s["thinking"] else "") + (", every fifth task" if s["shard"] else "")
                md.append(f"| {who} | {s['input'][1:]} px | **{pct(s['success'])}** | {pct(s['lo'])} to {pct(s['hi'])} | {pct(s['strict'])} | {s['n']} | {s['mean_steps']:.1f} ({s['mean_needed']:.1f}) | "
                          f"{s['seconds_per_step']:.1f} | {s['invalid']} of {s['model_steps']} ({pct(s['invalid'] / max(1, s['model_steps']))}) | {pct(s['stopped'])} | {pct(s['stuck'])} |")
        else:
            md += ["| Model | Runs on | Input | Aids | Tasks done | 95% interval | Episodes | Points inside the element | No point in the answer | Model seconds per point | Model seconds per step, all asks | Tokens read per look | Peak memory |",
                   "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
            for s in rows:
                aids = " + ".join((["snap to element"] if s["snap"] else []) + ([{"ask": "yes/no check", "effect": "second look when nothing changed"}[s["check"]]] if s["check"] else [])) or ("none" if s["ask"] != "tool" else "none (point tool call)")
                if s["v1"]:
                    aids += ", first version"
                if s["check"]:
                    aids += f" ({s['checks_no']} no, {s['retries']} retries)"
                if s["snap"]:
                    aids += f" ({s['snapped']} points moved)"
                md.append(f"| {label(s)} | {'Mac mini M6, MLX' if s['mlx'] else 'pod, PyTorch'} | {s['input'][1:]} px | {aids} | **{pct(s['success'])}** | {pct(s['lo'])} to {pct(s['hi'])} | {s['n']} | "
                          f"{pct(s['point_inside'])} of {s['n_points']} | {s['invalid']} | {s['sec_point']:.2f} | {s['sec_step']:.2f} | {s['prompt_tokens']:.0f} | {(str(s['peak_gb']) + ' GB') if s['peak_gb'] else 'n/a'} |")
        md.append("")
    four = [s for s in S if s["agent"] == "guided" and s.get("mlx") and "4B" in label(s)]
    if four:
        t = extra or {}
        md += ["### The 4B on the tasks: written answers and the pointing decoder side by side", "",
               "Guided mode on the Mac mini in MLX, seed 9101, 75 tasks. \"Written\" means the model generates \"[x, y]\" with all 32 layers; "
               "\"decoder\" means the small pointing decoder reads the state after layer 20 and no token is generated. "
               + (f"On a screenshot that has already been read through layer 20, one more request costs the decoder {t['decoder_ms']:.0f} ms at 1280 px "
                  f"({t['decoder_ms_896']:.0f} ms at 896 px); reading the screenshot that far takes {t['read20_ms']:.0f} ms plus {t['vision_ms']:.0f} ms for the vision part "
                  f"({t['read20_ms_896']:.0f} + {t['vision_ms_896']:.0f} ms at 896 px). " if t else ""), "",
               "| Weights | Pointer | Input | Aids | Tasks done | 95% interval | Points inside the element | Model seconds per step, all asks |", "|---|---|---|---|---|---|---|---|"]
        for s in sorted(four, key=lambda s: -s["success"]):
            aids = " + ".join((["snap"] if s["snap"] else []) + ([{"ask": "yes/no check", "effect": "second look"}[s["check"]]] if s["check"] else [])) or "none"
            md.append(f"| {label(s).replace('Bonsai 2 4B', '').strip(' ,')} | {'decoder' if 'decoder' in label(s) else 'written'} | {s['input'][1:]} px | {aids}{', first version' if s['v1'] else ''} | "
                      f"**{round(s['success'] * s['n'])} of {s['n']} ({pct(s['success'])})** | {pct(s['lo'])} to {pct(s['hi'])} | {pct(s['point_inside'])} | {s['sec_step']:.2f} |")
        md.append("")
    floors = [s for s in S if s["agent"] in ("oracle", "noop", "random")]
    if floors:
        md += ["### Reference agents", "", "| Agent | Tasks done | Episodes |", "|---|---|---|"]
        md += [f"| {label(s)} | {pct(s['success'])} | {s['n']} |" for s in floors] + [""]
    md += ["### By kind of task", "", "| Run | " + " | ".join(CAT_LABEL[c] for c in CATEGORIES) + " |", "|---|" + "---|" * len(CATEGORIES)]
    for s in S:
        md.append(f"| {row_name(s)} | " + " | ".join(cell(s["by_category"][c]) for c in CATEGORIES) + " |")
    md += ["", "### By number of steps the task needs", "", "| Run | " + " | ".join(b for b, _, _ in BINS) + " |", "|---|" + "---|" * len(BINS)]
    for s in S:
        md.append(f"| {row_name(s)} | " + " | ".join(cell(s["by_needed"][b]) for b, _, _ in BINS) + " |")
    apps = sorted({a for s in S for a in s["by_app"]})
    md += ["", "### By app", "", "| Run | " + " | ".join(apps) + " |", "|---|" + "---|" * len(apps)]
    for s in S:
        md.append(f"| {row_name(s)} | " + " | ".join(cell(s["by_app"].get(a, [0, 0])) for a in apps) + " |")
    if running:
        md += ["", "Still running or stopped early (not in the tables): " + "; ".join(f"{row_name(s)}: {round(s['success'] * s['n'])} of {s['n']} so far" for s in running) + "."]
    return "\n".join(md) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--seeds", default="test", help="test | dev | all")
    ap.add_argument("--out")
    args = ap.parse_args()
    seeds = {"test": set(TEST_SEEDS), "dev": set(DEV_SEEDS), "all": None}[args.seeds]
    summaries = [summarise(r) for r in load_runs(args.runs, seeds)]
    md = tables(summaries)
    print(md)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        open(os.path.join(args.out, "summary.md"), "w").write(md)
        json.dump(summaries, open(os.path.join(args.out, "summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
