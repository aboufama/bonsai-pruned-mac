"""Make every table of docs/BENCHMARK.md from the per-case files, and the summary JSON files.

    python3 bench/report.py --runs ~/Bonsai-demo/benchruns                   # print the tables
    python3 bench/report.py --runs ~/Bonsai-demo/benchruns --write           # also bench/results/*.json and docs/BENCHMARK.md
    python3 bench/report.py --runs ... --only ssv2                           # one table

--runs is a folder of <model>[@tag]/<job>*.jsonl written by bench/run.py (copied
from the machine that ran them). --new names the run folder shown as "the new model"
(default bonsai9b-new); other folders of the same model are listed by their tag.

docs/BENCHMARK.md keeps its hand-written text; only the blocks between
<!-- begin:NAME --> and <!-- end:NAME --> are replaced.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bench import stats  # noqa: E402
from bench.models import MODELS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["bonsai9b-new", "bonsai9b-orig", "qwen35-9b", "venus2-9b", "qwen35-4b-q4", "bonsai4b-new", "bonsai4b-orig",
         "bonsai9b-new-gguf", "bonsai9b-orig-gguf"]
EXPECTED = {"ssv2": 1272, "sspro": 1581, "osworld_g": 564, "osworld_g_refined": 564, "mac": 2106, "mac_agentnet": 504, "gen": 413,
            "toolcall": 400, "canary": 50}
INPUT_NAME = {"native": "full resolution", "s448": "448 px", "s640": "640 px", "s896": "896 px", "s1280": "1280 px", "s1920": "1920 px"}
SUMMARY = {}


# ------------------------------------------------------------------ loading
def load(runs_dir):
    """{run name: {job: {case id: record}}}; shards of one job are merged."""
    runs = collections.defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(os.path.expanduser(runs_dir), "*", "*.jsonl"))):
        name = os.path.basename(os.path.dirname(path))
        job = re.sub(r"\.shard\d+of\d+$", "", os.path.basename(path)[:-len(".jsonl")])
        recs = runs[name].setdefault(job, {})
        for line in open(path):
            try:
                r = json.loads(line)
                recs[r["id"]] = r
            except ValueError:
                pass
    return runs


def title(name, new):
    key, _, tag = name.partition("@")
    t = MODELS.get(key, {}).get("title", key)
    if key == "bonsai9b-new" and not tag:
        tag = "v2"
    return t + (f" [{tag}]" if tag else "")


def names(runs, new, want=None):
    """Run folders in table order: the new model first, then the registry order, then other tags."""
    def rank(n):
        key = n.partition("@")[0]
        return (0 if n == new else 1, ORDER.index(key) if key in ORDER else 99, n)
    return sorted((n for n in runs if want is None or n.partition("@")[0] in want or n in want), key=rank)


def acc(recs, keep=None, cluster=False):
    rows = [r for r in recs.values() if keep is None or keep(r)]
    a = stats.accuracy([bool(r["hit"]) for r in rows], clusters=[r.get("cluster") for r in rows] if cluster and rows else None)
    a["unparseable"] = sum(r.get("parse") == "unparseable" for r in rows)
    a["refusals"] = sum(r.get("parse") == "refusal" for r in rows)
    return a


def ci(a, digits=1):
    if not a or not a.get("n"):
        return "–"
    return f"{a['acc']:.{digits}f} ({a['lo']:.{digits}f}–{a['hi']:.{digits}f})"


def pt(a, digits=1):
    return "–" if not a or not a.get("n") else f"{a['acc']:.{digits}f}"


def partial(recs, set_name):
    want = EXPECTED.get(set_name)
    return f" †{len(recs)}/{want}" if want and len(recs) < want else ""


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def jobs_of(runs, name, set_name, looks=1, subsets=False):
    """[(input, job)] of a pointing set for one run. Subset jobs (":n500") are left out unless
    `subsets`; then they are listed after the full job of the same input and looked up as
    (input + ":n500", job)."""
    out = []
    for job in runs[name]:
        p = job.split(":")
        if p[0] != set_name:
            continue
        sub = next((x for x in p[1:] if x.startswith("n") and x[1:].isdigit()), None)
        if (sub and not subsets) or ("looks2" in p) != (looks == 2):
            continue
        inp = next((x for x in p[1:] if x in INPUT_NAME), "s1280")
        out.append((inp + (":" + sub if sub else ""), job))
    order = list(INPUT_NAME)
    return sorted(out, key=lambda t: (order.index(t[0].split(":")[0]), t[0]))


def in_name(inp):
    base, _, sub = inp.partition(":")
    return INPUT_NAME[base] + (f", {sub[1:]} evenly spaced cases" if sub else "")


# ------------------------------------------------------------------ tables
def t_ssv2(runs, new):
    cells = [("mobile", "text"), ("mobile", "icon"), ("desktop", "text"), ("desktop", "icon"), ("web", "text"), ("web", "icon")]
    rows, rows3, js = [], [], []
    for name in names(runs, new):
        for inp, job in jobs_of(runs, name, "ssv2"):
            if inp not in ("native", "s1280"):
                continue
            recs = runs[name][job]
            a = acc(recs)
            parts = [acc(recs, lambda r, g=g, u=u: r["group"] == g and r["ui_type"] == u) for g, u in cells]
            no8 = acc(recs, lambda r: not r["flags"]["overlap"])
            nosel = acc(recs, lambda r: not r["flags"]["select"] and not r["flags"]["overlap"])
            rows.append([title(name, new) + partial(recs, "ssv2"), INPUT_NAME[inp], ci(a)] + [pt(p) for p in parts] + [a["unparseable"], a["refusals"]])
            rows3.append([title(name, new), INPUT_NAME[inp], f"{ci(a)}, n={a['n']}", f"{ci(no8)}, n={no8['n']}", f"{ci(nosel)}, n={nosel['n']}"])
            js.append({"run": name, "input": inp, "all": a, "without_overlap": no8, "without_overlap_and_select": nosel,
                       "cells": {f"{g}_{u}": p for (g, u), p in zip(cells, parts)}})
    SUMMARY["ssv2"] = js
    a = table(["Model", "Input", "All 1,272 (95% interval)", "Mobile text", "Mobile icon", "Desktop text", "Desktop icon", "Web text", "Web icon",
               "Unreadable answers", "Refusals"], rows)
    b = table(["Model", "Input", "All cases", "Without the 8 overlap cases", "Also without the eighth used to choose checkpoints"], rows3)
    return {"ssv2": a, "ssv2_three_ways": b}


def t_sspro(runs, new):
    groups = ["Dev", "Creative", "CAD", "Scientific", "Office", "OS"]
    rows, js = [], []
    for name in names(runs, new):
        for looks in (1, 2):
            for inp, job in jobs_of(runs, name, "sspro", looks):
                recs = runs[name][job]
                a = acc(recs)
                tx, ic = acc(recs, lambda r: r["ui_type"] == "text"), acc(recs, lambda r: r["ui_type"] == "icon")
                gs = [acc(recs, lambda r, g=g: r["group"] == g) for g in groups]
                rows.append([title(name, new) + partial(recs, "sspro"), INPUT_NAME[inp] + (", two looks" if looks == 2 else ""), ci(a), pt(tx), pt(ic)]
                            + [pt(g) for g in gs] + [a["unparseable"]])
                js.append({"run": name, "input": inp, "looks": looks, "all": a, "text": tx, "icon": ic,
                           "groups": dict(zip(groups, gs))})
    SUMMARY["sspro"] = js
    return {"sspro": table(["Model", "Input", "All 1,581 (95% interval)", "Text", "Icon"] + groups + ["Unreadable answers"], rows)}


def t_osworld(runs, new):
    out = {}
    for set_name, label in (("osworld_g_refined", "refined instructions"), ("osworld_g", "original instructions")):
        rows, js = [], []
        for name in names(runs, new):
            for inp, job in jobs_of(runs, name, set_name):
                recs = runs[name][job]
                a = acc(recs)
                tgt, ref = acc(recs, lambda r: r["target_type"] != "absent"), acc(recs, lambda r: r["target_type"] == "absent")
                false_ref = sum(r.get("parse") == "refusal" and r["target_type"] != "absent" for r in recs.values())
                rows.append([title(name, new) + partial(recs, set_name), INPUT_NAME[inp], ci(a), ci(tgt), f"{ref['hits']}/{ref['n']}", false_ref, a["unparseable"]])
                js.append({"run": name, "input": inp, "all": a, "with_target": tgt, "absent_target": ref, "refused_a_real_target": false_ref})
        SUMMARY[set_name] = js
        out[set_name] = table(["Model", "Input", f"All 564, {label} (95% interval)", "The 510 with a target", "Refused correctly (of 54 with no target)",
                               "Refused a real target", "Unreadable answers"], rows)
    return out


def t_mac(runs, new):
    rows, js = [], []
    for name in names(runs, new):
        for looks in (1, 2):
            for inp, job in jobs_of(runs, name, "mac", looks, subsets=True):
                recs = runs[name][job]
                a = acc(recs, cluster=True)
                rows.append([title(name, new) + ("" if ":" in inp else partial(recs, "mac")), in_name(inp) + (", two looks" if looks == 2 else ""), ci(a),
                             f"{a['lo_cluster']:.1f}–{a['hi_cluster']:.1f}", a["unparseable"], a["refusals"]])
                js.append({"run": name, "input": inp, "looks": looks, "all": a})
    SUMMARY["mac"] = js
    return {"mac": table(["Model", "Input", "All 2,106 unless noted (95% interval over cases)", "Interval over screenshots", "Unreadable answers", "Refusals"], rows)}


def t_mac_verified(runs, new):
    """The reserved Mac set restricted to cases whose label was checked by eye (bench/mac_verified.json)."""
    path = os.path.join(HERE, "mac_verified.json")
    if not os.path.exists(path):
        return {"mac_verified": "Not checked yet."}
    v = json.load(open(path))
    ok = {r["id"] for r in v["cases"] if r["verdict"] == "ok"}
    looked = {r["id"] for r in v["cases"]}
    rows, js = [], []
    for name in names(runs, new):
        got = dict(jobs_of(runs, name, "mac"))
        if "s1280" not in got:
            continue
        recs = runs[name][got["s1280"]]
        a_all = acc(recs, lambda r: r["id"] in looked)
        a_ok = acc(recs, lambda r: r["id"] in ok)
        a_bad = acc(recs, lambda r: r["id"] in looked and r["id"] not in ok)
        rows.append([title(name, new) + partial(recs, "mac"), f"{ci(a_all)}, n={a_all['n']}", f"{ci(a_ok)}, n={a_ok['n']}", f"{a_bad['hits']}/{a_bad['n']}"])
        js.append({"run": name, "looked_at": a_all, "label_ok": a_ok, "label_not_ok": a_bad})
    SUMMARY["mac_verified"] = js
    return {"mac_verified": table(["Model, 1280 px", "The cases looked at", "Those whose label is right", "Hits on the cases with a wrong or unclear label"], rows)}


def t_mac_agentnet(runs, new):
    rows, js = [], []
    for name in names(runs, new):
        for inp, job in jobs_of(runs, name, "mac_agentnet"):
            recs = runs[name][job]
            a = acc(recs)
            rows.append([title(name, new) + partial(recs, "mac_agentnet"), INPUT_NAME[inp], ci(a), a["unparseable"]])
            js.append({"run": name, "input": inp, "all": a})
    SUMMARY["mac_agentnet"] = js
    return {"mac_agentnet": table(["Model", "Input", "All 504 (95% interval)", "Unreadable answers"], rows) if rows else "Not run."}


def t_gen(runs, new):
    kinds = [("text", "direct"), ("text", "functional"), ("icon", "direct"), ("icon", "functional")]
    sizes = ["l", "m", "s", "xs"]
    rows, js = [], []
    for name in names(runs, new):
        for looks in (1, 2):
            for inp, job in jobs_of(runs, name, "gen", looks):
                recs = runs[name][job]
                a = acc(recs, cluster=True)
                ks = [acc(recs, lambda r, u=u, k=k: r["ui_type"] == u and r["flags"].get("kind") == k) for u, k in kinds]
                ss = [acc(recs, lambda r, s=s: r["flags"].get("size") == s) for s in sizes]
                rows.append([title(name, new) + partial(recs, "gen"), INPUT_NAME[inp] + (", two looks" if looks == 2 else ""), ci(a)]
                            + [pt(k) for k in ks] + [" / ".join(pt(s) for s in ss)])
                js.append({"run": name, "input": inp, "looks": looks, "all": a, "kinds": {f"{u}_{k}": v for (u, k), v in zip(kinds, ks)},
                           "sizes": dict(zip(sizes, ss))})
    SUMMARY["gen"] = js
    return {"gen": table(["Model", "Input", "All 413 (95% interval)", "Text, named", "Text, by function", "Icon, named", "Icon, by function",
                          "Target large / medium / small / very small"], rows)}


def t_grouped(runs, new, job_prefix, key, label, group_names=None):
    rows, js, groups = [], [], group_names
    for name in names(runs, new):
        for job in sorted(runs[name]):
            if job.split(":")[0] != job_prefix:
                continue
            recs = runs[name][job]
            if groups is None:
                groups = sorted({r["group"] for r in recs.values()})
            a = acc(recs)
            gs = [acc(recs, lambda r, g=g: r["group"] == g) for g in groups]
            rows.append([title(name, new) + partial(recs, job_prefix), f"{ci(a)}, n={a['n']}"] + [f"{g['hits']}/{g['n']}" for g in gs])
            js.append({"run": name, "job": job, "all": a, "groups": dict(zip(groups, gs))})
    SUMMARY[key] = js
    return {key: table(["Model", label] + list(groups or []), rows) if rows else "Not run yet."}


def t_general(runs, new):
    rows, js = [], []
    for name in names(runs, new):
        r = runs[name]
        can = next((r[j] for j in r if j.split(":")[0] == "canary"), None)
        mm = next((r[j] for j in sorted(r) if j.split(":")[0] == "mmlu"), None)
        ch = next((r[j] for j in sorted(r) if j.split(":")[0] == "chartqa"), None)
        if not (can or mm or ch):
            continue
        row, j = [title(name, new)], {"run": name}
        if can:
            a = acc(can)
            nll = sum(x["nll"] for x in can.values()) / max(1, sum(x["tokens"] for x in can.values()))
            row += [f"{a['hits']}/{a['n']}", f"{nll:.3f}"]
            j["canary"] = dict(a, nll_per_token=round(nll, 4))
        else:
            row += ["–", "–"]
        for recs, k in ((mm, "mmlu"), (ch, "chartqa")):
            if recs:
                a = acc(recs)
                row.append(f"{ci(a)}, n={a['n']}")
                j[k] = a
            else:
                row.append("–")
        rows.append(row)
        js.append(j)
    SUMMARY["general"] = js
    return {"general": table(["Model", "Canary: all answer tokens top-ranked (of 50)", "Canary: negative log-probability per answer token",
                              "MMLU (95% interval)", "ChartQA, relaxed accuracy (95% interval)"], rows) if rows else "Not run yet."}


def t_sizes(runs, new):
    sizes = ["s448", "s640", "s896", "s1280", "s1920", "native"]
    out = {}
    for set_name in ("ssv2", "mac"):
        rows, js = [], []
        for name in names(runs, new):
            got = dict(jobs_of(runs, name, set_name))
            if len([s for s in sizes if s in got]) < 3:
                continue
            cells_, j = [], {"run": name}
            for s in sizes:
                if s in got:
                    recs = runs[name][got[s]]
                    a = acc(recs)
                    tok = sum(r["prompt_tokens"] or 0 for r in recs.values()) / max(1, len(recs))
                    cells_.append(f"{pt(a)} ({tok:.0f}){partial(recs, set_name)}")
                    j[s] = dict(a, prompt_tokens_mean=round(tok))
                else:
                    cells_.append("–")
            rows.append([title(name, new)] + cells_)
            js.append(j)
        SUMMARY[f"sizes_{set_name}"] = js
        out[f"sizes_{set_name}"] = table(["Model"] + [INPUT_NAME[s] for s in sizes], rows) if rows else "Not run yet."
    return out


def t_looks(runs, new):
    rows, js = [], []
    for set_name in ("ssv2", "sspro", "mac", "gen", "osworld_g_refined"):
        for name in names(runs, new):
            two = dict(jobs_of(runs, name, set_name, 2, subsets=True))
            one = dict(jobs_of(runs, name, set_name, 1))
            for inp_sub in two:
                inp = inp_sub.split(":")[0]
                if inp not in one:
                    continue
                r1, r2 = runs[name][one[inp]], runs[name][two[inp_sub]]
                ids = sorted(set(r1) & set(r2))
                if not ids:
                    continue
                p = stats.paired([bool(r2[i]["hit"]) for i in ids], [bool(r1[i]["hit"]) for i in ids])
                t1 = sum(r1[i]["prompt_tokens"] or 0 for i in ids) / len(ids)
                t2 = sum(r2[i]["prompt_tokens"] or 0 for i in ids) / len(ids)
                rows.append([set_name, title(name, new), INPUT_NAME[inp], f"{p['acc_b']:.1f}", f"{p['acc_a']:.1f}",
                             f"{p['diff']:+.1f} ({p['lo']:+.1f} to {p['hi']:+.1f})", f"{t1:.0f}", f"{t2:.0f}", p["n"]])
                js.append({"set": set_name, "run": name, "input": inp_sub, "paired": p, "tokens_one": round(t1), "tokens_two": round(t2)})
    SUMMARY["looks"] = js
    return {"looks": table(["Set", "Model", "First look", "One look", "Two looks", "Difference (95% interval)", "Tokens read, one look",
                            "Tokens read, two looks", "Cases"], rows) if rows else "Not run yet."}


def t_paired(runs, new):
    pairs = [("bonsai9b-orig", "s1280", "original Bonsai, 1280 px"), ("qwen35-9b", "s1280", "parent, 1280 px"),
             ("qwen35-9b", "native", "parent, full resolution"), ("venus2-9b", "s1280", "UI-Venus, 1280 px"),
             ("venus2-9b", "native", "UI-Venus, full resolution"), ("qwen35-4b-q4", "s1280", "Qwen3.5-4B 4-bit, 1280 px")]
    rows, js = [], []
    if new not in runs:
        return {"paired": "Not run yet."}
    for set_name in ("ssv2", "sspro", "osworld_g_refined", "mac", "gen"):
        mine = dict(jobs_of(runs, new, set_name))
        if "s1280" not in mine:
            continue
        a = runs[new][mine["s1280"]]
        for other, inp, label in pairs:
            if other not in runs:
                continue
            theirs = dict(jobs_of(runs, other, set_name))
            if inp not in theirs:
                continue
            b = runs[other][theirs[inp]]
            ids = sorted(set(a) & set(b))
            if set_name == "ssv2":
                ids = [i for i in ids if not a[i]["flags"]["overlap"]]
            if not ids:
                continue
            p = stats.paired([bool(a[i]["hit"]) for i in ids], [bool(b[i]["hit"]) for i in ids],
                             clusters=[a[i]["cluster"] for i in ids] if set_name in ("mac", "gen") else None)
            rows.append([set_name, label, p["n"], f"{p['acc_a']:.1f}", f"{p['acc_b']:.1f}", f"{p['diff']:+.1f} ({p['lo']:+.1f} to {p['hi']:+.1f})",
                         p["only_a"], p["only_b"], stats.fmt_p(p["p_mcnemar"])])
            js.append({"set": set_name, "against": other, "against_input": inp, **p})
    SUMMARY["paired"] = js
    return {"paired": table(["Set", "New model at 1280 px against", "Cases both answered", "New", "Other", "Difference in points (95% interval)",
                             "Only the new model right", "Only the other right", "McNemar exact p"], rows) if rows else "Not run yet."}


def t_cost(runs, new):
    rows, js = [], []
    for name in names(runs, new):
        recs = runs[name].get("cost")
        if not recs:
            continue
        c = recs["cost"]
        size = sum(c["file_bytes"].values())
        parts = ", ".join(f"{k} {v / 1e9:.2f}" for k, v in c["file_bytes"].items())
        rows.append([title(name, new), f"{size / 1e9:.2f} ({parts})", c.get("gpu_memory_gb"), c.get("point_seconds_median"),
                     c.get("point_prompt_tokens_mean"), c.get("prompt_tokens_per_second"), c.get("generation_tokens_per_second")])
        js.append(dict(c, run=name, total_file_bytes=size))
    SUMMARY["cost"] = js
    return {"cost": table(["Model", "Files, GB", "Peak GPU memory, GB", "Seconds per pointing answer (median, 1280 px)", "Prompt tokens per answer",
                           "Prompt tokens per second", "Generation tokens per second"], rows) if rows else "Not run yet."}


def t_runtime(runs, new):
    """The exported GGUF in llama.cpp against the same model read from the pack in PyTorch."""
    rows, js = [], []
    for gguf, torch_name in (("bonsai9b-new-gguf", new), ("bonsai9b-orig-gguf", "bonsai9b-orig")):
        for name in [n for n in runs if n.partition("@")[0] == gguf]:
            for job, recs in sorted(runs[name].items()):
                set_name = job.split(":")[0]
                other = runs.get(torch_name, {}).get(job) or runs.get(torch_name, {}).get(":".join(p for p in job.split(":") if not (p.startswith("n") and p[1:].isdigit())))
                if not other or "hit" not in next(iter(recs.values())):
                    continue
                ids = sorted(set(recs) & set(other))
                if not ids:
                    continue
                p = stats.paired([bool(recs[i]["hit"]) for i in ids], [bool(other[i]["hit"]) for i in ids])
                same = sum(recs[i].get("point") == other[i].get("point") for i in ids)
                near = sum(1 for i in ids if recs[i].get("point") and other[i].get("point")
                           and abs(recs[i]["point"][0] - other[i]["point"][0]) <= 5 and abs(recs[i]["point"][1] - other[i]["point"][1]) <= 5)
                rows.append([title(name, new), job, p["n"], f"{p['acc_a']:.1f}", f"{p['acc_b']:.1f}", f"{p['diff']:+.1f} ({p['lo']:+.1f} to {p['hi']:+.1f})",
                             f"{100 * same / len(ids):.1f}%", f"{100 * near / len(ids):.1f}%"])
                js.append({"run": name, "job": job, "paired": p, "identical_answers": same, "within_5_units": near})
    SUMMARY["runtime"] = js
    return {"runtime": table(["File and runtime", "Job", "Cases", "llama.cpp (GGUF)", "PyTorch (pack)", "Difference (95% interval)", "Identical answers",
                              "Answers within 5 of 1000 units"], rows) if rows else "Not run yet."}


def t_headline(runs, new):
    def one(name, set_name, inp, looks=1):
        if name not in runs:
            return "not run"
        got = dict(jobs_of(runs, name, set_name, looks))
        if inp not in got:
            return "not run"
        recs = runs[name][got[inp]]
        return pt(acc(recs)) + partial(recs, set_name)

    def task(name, prefix):
        if name not in runs:
            return "not run"
        job = next((j for j in sorted(runs[name]) if j.split(":")[0] == prefix), None)
        return pt(acc(runs[name][job])) + partial(runs[name][job], prefix) if job else "not run"

    rows = []
    for name in names(runs, new):
        key = name.partition("@")[0]
        if key.endswith("-gguf"):
            continue
        rows.append([title(name, new), one(name, "ssv2", "s1280"), one(name, "ssv2", "native"), one(name, "sspro", "s1280"), one(name, "sspro", "native"),
                     one(name, "osworld_g_refined", "native") if key in ("qwen35-9b", "venus2-9b", "qwen35-4b-q4") else one(name, "osworld_g_refined", "s1280"),
                     one(name, "mac", "s1280"), one(name, "gen", "s1280"), task(name, "toolcall"), task(name, "bfcl")])
    SUMMARY["headline"] = rows
    return {"headline": table(["Model", "ScreenSpot-v2, 1280 px", "ScreenSpot-v2, full resolution", "ScreenSpot-Pro, 1280 px", "ScreenSpot-Pro, full resolution",
                               "OSWorld-G refined", "macOS app windows, 1280 px", "Our generated screens, 1280 px", "Tool calls (ours)", "BFCL v3 subset"], rows)}


def t_published(runs, new):
    path = os.path.join(HERE, "published.json")
    if not os.path.exists(path):
        return {"published": "Not collected yet."}
    rows = [[r["model"], r.get("ssv2", "–"), r.get("sspro", "–"), r.get("osworld_g", "–"), r.get("osworld_g_refined", "–"),
             f"[{r['source_name']}]({r['url']})", r.get("note", "")] for r in json.load(open(path))["rows"]]
    return {"published": table(["Model (as reported)", "ScreenSpot-v2", "ScreenSpot-Pro", "OSWorld-G", "OSWorld-G refined", "Source", "Setting"], rows)}


def t_env(runs, new, runs_dir=None):
    """What produced the numbers: one row per run folder, from the .meta.json files."""
    rows, js = [], []
    for name in names(runs, new):
        metas = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(RUNS_DIR, name, "*.meta.json")))]
        if not metas:
            continue
        env = [m["environment"] for m in metas]
        files = metas[0]["model_files"]
        one = lambda key: ", ".join(sorted({str(e.get(key)) for e in env if e.get(key)}))
        commits = ", ".join(sorted({(e.get("git_commit") or "?")[:7] + ("+" if "+" in (e.get("git_commit") or "") else "") for e in env}))
        what = os.path.basename(files.get("source") or "")
        if files.get("patch"):
            what += " + " + os.path.basename(files["patch"]) + f" (sha256 {files.get('patch_sha256', '')[:8]})"
        rows.append([title(name, new), what, len(metas), commits, one("torch"), one("transformers"), one("gpu").split(",")[0]])
        js.append({"run": name, "files": what, "jobs": len(metas), "commits": commits, "torch": one("torch"), "transformers": one("transformers"),
                   "gpu": one("gpu"), "hosts": one("host")})
    SUMMARY["environment"] = js
    return {"environment": table(["Model", "Files", "Jobs", "Code (git commit)", "torch", "transformers", "GPU"], rows) if rows else "Not run yet."}


RUNS_DIR = ""
TABLES = [t_headline, t_ssv2, t_sspro, t_osworld, t_mac, t_mac_verified, t_mac_agentnet, t_gen,
          lambda r, n: t_grouped(r, n, "toolcall", "toolcall", "All 400 (95% interval)"),
          lambda r, n: t_grouped(r, n, "bfcl", "bfcl", "All (95% interval)", ["simple", "multiple", "parallel", "parallel_multiple", "irrelevance"]),
          t_general, t_sizes, t_looks, t_paired, t_cost, t_runtime, t_env, t_published]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--new", default="bonsai9b-new")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--doc", default=os.path.join(HERE, "..", "docs", "BENCHMARK.md"))
    args = ap.parse_args()
    global RUNS_DIR
    RUNS_DIR = os.path.expanduser(args.runs)
    runs = load(args.runs)
    blocks = {}
    for fn in TABLES:
        blocks.update(fn(runs, args.new))
    for name, text in blocks.items():
        if args.only and args.only not in name:
            continue
        print(f"\n### {name}\n{text}")
    if args.write:
        os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
        for key, value in SUMMARY.items():
            json.dump(value, open(os.path.join(HERE, "results", f"{key}.json"), "w"), indent=1)
        json.dump({"runs": {n: {j: len(r) for j, r in sorted(jobs.items())} for n, jobs in sorted(runs.items())}, "new": args.new},
                  open(os.path.join(HERE, "results", "runs.json"), "w"), indent=1)
        if os.path.exists(args.doc):
            doc = open(args.doc).read()
            for name, text in blocks.items():
                doc = re.sub(rf"(<!-- begin:{name} -->\n).*?(\n<!-- end:{name} -->)", lambda m: m.group(1) + text + m.group(2), doc, flags=re.S)
            open(args.doc, "w").write(doc)
            print(f"\nwrote {args.doc} and bench/results/*.json")


if __name__ == "__main__":
    main()
