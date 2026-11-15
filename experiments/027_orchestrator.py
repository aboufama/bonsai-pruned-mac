# Experiment 027: the 9B as orchestrator. It reads a screenshot, the goal and the last steps, and answers
# with ONE call of `next_step`: the action and its target in plain words, no coordinates
# (docs/ACTION_FORMAT.md "Orchestrator steps", weightlab/actions.py). A pointer then finds the target.
#
# Recipe: experiment 014/023's (only the multipliers of layers 4..31 and the output head move, gentle).
# Training samples: orchestrator steps (most of the mix), the tool benchmark's training calls with its
# no-call cases, and a quarter plain pointing so the model keeps pointing. Screenshots get a long side
# of 1280 or 896, half each. Rounds of EVERY27 updates on one schedule; after each round:
#   steps, reserved (trajectories no pointing run trained on): teacher-forced, and generated answers
#     judged by actions.score_steps (action right; target words overlapping; text, keys, direction exact)
#   pointer test: the target words the model wrote are handed, with the same screenshot, to the model
#     itself as a plain pointing request; a hit is within 24 px of the recorded point (step_points).
#     The same with the dataset's own words gives the line the pointer reaches with a perfect description.
#     (The model under training is its own pointer here: one set of weights for both, as the plan wants,
#     and no second 9B has to fit on the GPU.)
#   plain pointing on select and report, the tool benchmark's dev split, the canary.
# Best round = most generated steps fully right among rounds whose plain pointing on select is not more
# than 0.03 under the start. Every new best is written out as a patch at once (PATCHNAME27-u<step>).
# Step cases come from data/mac/agentnet/step_pick.json (tools/step_images.py).
# Settings: UPDATES27, EVERY27, LR27, ACC27, TAG27, STEPS27 (training step cases), THOUGHT27, SIZES27,
# GEN27, SMOKE27 (N updates, tiny score sets, nothing saved), PATCHNAME27, POINT_SHARE27, NEIGHBOUR27 (the
# PLANNER27 (folders of planner turns in format v1, text only; with them the best round is the dev turns
# fully right plus the neighbour slice), PLANNER_N27, PLANNER_DEV27; pointing part draws neighbour cases three times as often; the best round is then steps fully right plus
# the held-out neighbour slice), NB_N27. Every round also scores generated answers on the held-out
# neighbour slice and Mac windows when those sets are on the machine.
import collections
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab import chat, ternary
importlib.reload(chat)
from weightlab import actions
importlib.reload(actions)
actions.install()
from weightlab.distill import BlockDistiller
from weightlab.tune import TaskTuner

SMOKE = globals().pop("SMOKE27", None)
UPDATES = SMOKE or globals().get("UPDATES27", 3000)
EVERY = min(UPDATES, globals().get("EVERY27", 500))
LR = globals().get("LR27", 2e-4)
ACC = globals().get("ACC27", 2)
TAG = globals().get("TAG27", "orchestrator") + ("_smoke" if SMOKE else "")
N_STEPS = globals().get("STEPS27", 3600)
THOUGHT = globals().get("THOUGHT27", False)
SIZES = globals().get("SIZES27", (1280, 896))
N_SCORE = 8 if SMOKE else 200
N_GEN = 6 if SMOKE else globals().get("GEN27", 120)
PATCHNAME = None if SMOKE else globals().get("PATCHNAME27", None)
POINT_SHARE = globals().get("POINT_SHARE27", 0.25)   # share of the training samples that are plain pointing
NEIGHBOUR = globals().get("NEIGHBOUR27", False)      # pointing list: neighbour cases 3x, Apple's apps 2x again, Fable and GroundCUA neighbours added
ROLL_SHARE = globals().get("ROLL_SHARE27")          # e.g. 0.5: this share of every batch is rollout rows (states the planner reached, the oracle's step)
ROLL_DISAGREE = globals().get("ROLL_DISAGREE27", False)   # rollout rows only from states where the planner's own step differed from the oracle's
QUICK = globals().get("QUICK27", False)             # score only the planner dev turns, report and select (teacher-forced) and the tool dev cases
EXPORT_ALL = globals().get("EXPORT_ALL27", False)   # write a patch at every scored step, not only at a best
NB_N = 12 if SMOKE else globals().get("NB_N27", 150)  # cases of the held-out neighbour slice scored per round (generated answers)
LAYERS = list(range(4, 32))
rng = random.Random(27)
if "mix" not in globals() or "fS" not in globals():
    raise RuntimeError("run the prelude first: it builds the pointing mix and the two score sets")

adir = f"{lab.root}/data/mac/agentnet"
pick27 = json.load(open(f"{adir}/step_pick.json"))
want = {"train": set(pick27["train"]), "reserved": set(pick27["reserved"])}
cases27, missing = {"train": [], "reserved": []}, collections.Counter()
for line in open(f"{adir}/cases_steps.jsonl"):
    c = json.loads(line)
    for part in ("train", "reserved"):
        if c["id"] in want[part]:
            if os.path.exists(os.path.normpath(os.path.join(adir, c["image"]))):
                cases27[part].append(c)
            else:
                missing[part] += 1
if missing:
    print("screenshots not on this machine, cases left out:", dict(missing))
for part in cases27:
    order = {i: k for k, i in enumerate(pick27[part])}
    cases27[part].sort(key=lambda c: order[c["id"]])
train_cases = cases27["train"][:N_STEPS]
if len(train_cases) < min(50, N_STEPS) or not cases27["reserved"]:
    raise RuntimeError(f"too few step cases on this machine: {len(train_cases)} for training, {len(cases27['reserved'])} reserved")
step_train = [actions.step_case(c, base=adir, thought=THOUGHT) for c in train_cases]
step_test = [actions.step_case(c, base=adir, thought=THOUGHT) for c in cases27["reserved"][:N_SCORE]]
step_gen = step_test[:N_GEN]
# ---- planner turns in format v1 (text only: a list of controls instead of a screenshot; weightlab/planner.py)
plan_train, plan_dev = [], []
for _dir in globals().get("PLANNER27", ()):
    _name, _dir = os.path.basename(_dir), f"{lab.root}/{_dir}"
    if os.path.exists(_dir):
        from weightlab import planner as planner27
        importlib.reload(planner27)
        plan_train += planner27.load(_dir, "train")
        _d = planner27.load(_dir, "dev")                 # the dev turns of each folder are scored on their own
        random.Random(272).shuffle(_d)
        plan_dev += [dict(x, dev_set=_name) for x in _d[:8 if SMOKE else globals().get("PLANNER_DEV27", 150)]]
_first = [x for x in plan_train if str(x["id"]).startswith("roll")]          # rollout turns (DAgger) are always kept
plan_train = [x for x in plan_train if not str(x["id"]).startswith("roll")]
random.Random(271).shuffle(plan_train)
plan_train = _first + plan_train[:max(0, globals().get("PLANNER_N27", 6000) - len(_first))]
if plan_train:
    print("planner turns (format v1): %d for training %s, %d of the dev split for scoring" % (
        len(plan_train), dict(collections.Counter(s["category"].split(":")[1] for s in plan_train)), len(plan_dev)), flush=True)
print("step cases: training", dict(collections.Counter(c["step"]["action"] for c in train_cases)),
      "  reserved:", dict(collections.Counter(s["case"]["step"]["action"] for s in step_test)), "  thoughts:", THOUGHT)


def sized(sample):
    side = rng.choice(SIZES)
    if sample.get("kind") in ("point_call", actions.KIND, actions.STEP_KIND):
        return dict(sample, item=dict(sample["item"], max_side=side))
    if sample.get("kind"):
        return sample
    return dict(sample, max_side=side)


point_items = list(mix)
rng.shuffle(point_items)
if NEIGHBOUR:
    _nb = set(json.load(open(f"{lab.root}/data/mac/neighbour_ids.json"))["ids"])
    _apple = ("calendar", "ical", "finder", "mail", "notes", "reminders", "safari", "system_preferences", "systempreferences",
              "system settings", "system_settings", "systemsettings", "messages", "mobilesms")
    _pool = list(mix)
    for _name, _n in (("mac:fable_teacher:train", 4198), ("mac:neighbour_gcua:train", 3000), ("mac:structured_s2ax:train", 6000)):
        if os.path.exists(f"{lab.root}/data/mac/{_name.split(':')[1]}/cases.jsonl"):
            _pool += [it for it in lab.data(_name, n=_n) if os.path.exists(it["path"])]
    _pool = [dict(it, kind=None) for it in _pool]        # plain pointing cases: the Fable cases carry a kind (direct / intent / next) that the tuner would read as a chat sample
    _w = [(3 if it["id"] in _nb else 1) * (2 if it["id"] in _nb and any(k in str(it.get("group", "")).lower() for k in _apple) else 1) for it in _pool]
    print("pointing pool: %d cases, %d of them neighbour cases (drawn three times as often; Apple's apps twice again)" % (
        len(_pool), sum(it["id"] in _nb for it in _pool)), flush=True)
tool_cases = [json.loads(l) for l in open(f"{lab.root}/benchdata/toolcall/train_s11/cases.jsonl")]
tools27 = [s for s in (chat.tool_case(c) for c in tool_cases) if s]
n_point = round((len(step_train) + len(plan_train) + 900) * POINT_SHARE / (1 - POINT_SHARE))
if NEIGHBOUR:
    # about half of the pointing targets are small: smaller side under 24 px with the long side at 1280
    _small = [min(it["bbox"][2] - it["bbox"][0], it["bbox"][3] - it["bbox"][1]) * 1280 / max(it["size"]) < 24 for it in _pool]
    _a = [(it, w) for it, w, sm in zip(_pool, _w, _small) if sm]
    _b = [(it, w) for it, w, sm in zip(_pool, _w, _small) if not sm]
    point_items = (rng.choices([x[0] for x in _a], weights=[x[1] for x in _a], k=n_point // 2)
                   + rng.choices([x[0] for x in _b], weights=[x[1] for x in _b], k=n_point - n_point // 2))
    print("pointing part: %d cases, half of them with a target under 24 px (the pool has %d such cases of %d); structured descriptions: %d" % (
        n_point, len(_a), len(_pool), sum(str(it["id"]).endswith("-struct") for it in point_items)), flush=True)
train27 = (point_items[:n_point] + [s for s in tools27 if s["kind"] == "tool_call"][:600]
           + [s for s in tools27 if s["kind"] == "no_call"][:300] + step_train + plan_train)
train27 = [sized(s) for s in train27]
rng.shuffle(train27)
if ROLL_SHARE and plan_train:
    _roll = [x for x in plan_train if str(x["id"]).startswith("roll")]
    if ROLL_DISAGREE:
        _roll = [x for x in _roll if not ((x["turn"].get("meta") or {}).get("agrees"))]
    _rest = [x for x in plan_train if not str(x["id"]).startswith("roll")]
    _n = UPDATES * ACC
    _nr = round(_n * ROLL_SHARE)
    _np = round((_n - _nr) * 0.7); _npt = round((_n - _nr) * 0.2); _nt = _n - _nr - _np - _npt
    rng.shuffle(_rest)
    _tools = [x for x in tools27 if x["kind"] == "tool_call"][:600] + [x for x in tools27 if x["kind"] == "no_call"][:300]
    _rw = None
    if globals().get("ROLL_WEIGHT27"):                   # two kinds of states three times as often: the planner said done and the
        def _hard(x):                                    # oracle did not; the last step had no effect
            t = x["turn"]; ma = (t.get("meta") or {}).get("model_answer")
            early = isinstance(ma, dict) and ma.get("action") == "done" and t["answer"].get("action") != "done"
            stuck = bool(t.get("done")) and ("(nothing changed)" in t["done"][-1] or "(not carried out" in t["done"][-1])
            return early or stuck
        _rw = [3 if _hard(x) else 1 for x in _roll]
        print("rollout pool: %d states, %d of them drawn three times as often (done said too early, or after a step with no effect)" % (len(_roll), sum(w == 3 for w in _rw)), flush=True)
    train27 = (rng.choices(_roll, weights=_rw, k=_nr) + _rest[:_np] + [sized(x) for x in rng.choices(point_items, k=_npt)] + rng.choices(_tools, k=_nt))
    rng.shuffle(train27)
    print("batches: %d samples = %d rollout rows (%.0f%%; drawn from %d states%s) + %d oracle, rule and verified turns + %d pointing + %d tool cases" % (
        _n, _nr, 100 * _nr / _n, len(_roll), ", only those where the planner differed from the oracle" if ROLL_DISAGREE else "", _np, _npt, _nt), flush=True)
print("training samples:", dict(collections.Counter(s.get("kind", "point") for s in train27)), flush=True)

dev_cases = [json.loads(l) for l in open(f"{lab.root}/bench/toolcall/runs/dev_20261114/cases.jsonl")]
tool_dev = [s for s in (chat.tool_case(c) for c in dev_cases) if s]
if SMOKE:
    tool_dev = tool_dev[:8]
rows = []
out = {"tag": TAG, "updates": UPDATES, "every": EVERY, "lr": LR, "accumulate": ACC, "sizes": list(SIZES), "thought": THOUGHT,
       "train": dict(collections.Counter(s.get("kind", "point") for s in train27)), "state": list(lab.stack), "rows": rows}


held27 = {}
if os.path.exists(f"{lab.root}/data/mac/neighbour_test/cases.jsonl"):
    _all = lab.data("mac:neighbour_test:test", n=600)
    held27["neighbour slice"] = _all[::max(1, len(_all) // NB_N)][:NB_N]
if os.path.exists(f"{lab.root}/data/mac/screen2ax_task/cases.jsonl"):
    held27["Mac windows"] = lab.data("mac:screen2ax_task:test", n=8 if SMOKE else 60)


def _point_item(case, words, point):
    w, h = case["width"], case["height"]
    tol = actions.TOL_PX
    box = [point[0] - tol, point[1] - tol, point[0] + tol, point[1] + tol]
    b1000 = [1000 * box[0] / w, 1000 * box[1] / h, 1000 * box[2] / w, 1000 * box[3] / h]
    return {"id": case["id"] + ":" + words[:20], "path": os.path.normpath(os.path.join(adir, case["image"])), "bbox": box,
            "instruction": words, "group": "step", "ui_type": "point", "size": (w, h), "max_side": 1280, "box1000": b1000,
            "target": (round(1000 * point[0] / w), round(1000 * point[1] / h)), "_point": point}


def pointer_test(items, tag):
    """Share of pointing items the model's written point lands within TOL_PX of the recorded point."""
    if not items:
        return None, 0
    answers = lab.score(lab.B, items, tag=tag)["answers"]
    ok = 0
    for it, text in zip(items, answers):
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
        if len(nums) >= 2:
            w, h = it["size"]
            ok += math.hypot(nums[0] * w / 1000 - it["_point"][0], nums[1] * h / 1000 - it["_point"][1]) <= actions.TOL_PX
    return ok / len(items), len(items)


def measure(label):
    t = time.time()
    actions.install()
    if QUICK:
        a, b = fS.evaluate(4, tag=f"027:{TAG}:{label}:select"), fR.evaluate(4, tag=f"027:{TAG}:{label}:report")
        fS.discard(); fR.discard()
        tc = chat.score(lab, lab.B, tool_dev[:150], tag=f"027:{TAG}:{label}:tools")
        _r = [planner27.score(x, chat.generate(lab, lab.B, x, max_new_tokens=96)[0]) for x in plan_dev]
        pl = {"n": len(_r), "ok": sum(r["ok"] for r in _r) / len(_r), "action": sum(r["action"] for r in _r) / len(_r), "parsed": sum(r["parsed"] for r in _r) / len(_r), "by_set": {}}
        for _n2 in sorted({x["dev_set"] for x in plan_dev}):
            _q = [r for x, r in zip(plan_dev, _r) if x["dev_set"] == _n2]
            pl["by_set"][_n2] = {"n": len(_q), "ok": sum(r["ok"] for r in _q) / len(_q), "action": sum(r["action"] for r in _q) / len(_q)}
        row = {"label": label, "select": a, "report": b, "tools": tc, "planner_dev": pl, "held_out_pointing": {}, "steps_generated": {"correct": 0.0}, "seconds": time.time() - t}
        rows.append(row)
        print("%s  [%.0f s]   planner dev (%d): fully right %5.1f%%   action right %5.1f%%   | %s   | select %.3f report %.3f   tools %.1f%% holds back %.1f%%" % (
            label, time.time() - t, pl["n"], 100 * pl["ok"], 100 * pl["action"],
            "   ".join("%s: %.1f%% of %d" % (k, 100 * v["ok"], v["n"]) for k, v in pl["by_set"].items()), a["p_hit"], b["p_hit"],
            100 * tc.get("tf_exact", 0), 100 * tc.get("holds_back", 0)), flush=True)
        return row
    a, b = fS.evaluate(4, tag=f"027:{TAG}:{label}:select"), fR.evaluate(4, tag=f"027:{TAG}:{label}:report")
    fS.discard(); fR.discard()
    tc = chat.score(lab, lab.B, tool_dev, tag=f"027:{TAG}:{label}:tools")
    st = chat.score(lab, lab.B, step_test, tag=f"027:{TAG}:{label}:steps")
    answers = [chat.generate(lab, lab.B, s, max_new_tokens=160 if THOUGHT else 96)[0] for s in step_gen]
    sg = actions.score_steps([s["case"] for s in step_gen], answers)
    own, ref = [], []
    for s, text in zip(step_gen, answers):
        case, got = s["case"], actions.parse_step(text) or {}
        for key, (words, point) in zip(("target", "target_end"), [(case["step"].get("target"), case.get("point")), (case["step"].get("target_end"), case.get("point_end"))]):
            if words and point:
                ref.append(_point_item(case, words, point))
                own.append(_point_item(case, got.get(key) or "(no target written)", point))
    actions.install()
    p_own, n_own = pointer_test(own, f"027:{TAG}:{label}:pointer_own")
    p_ref, _ = pointer_test(ref, f"027:{TAG}:{label}:pointer_ref")
    pl = None
    if plan_dev:                                         # planner turns of the dev split, generated
        _r = [planner27.score(s, chat.generate(lab, lab.B, s, max_new_tokens=96)[0]) for s in plan_dev]
        pl = {"n": len(_r), "ok": sum(r["ok"] for r in _r) / len(_r), "action": sum(r["action"] for r in _r) / len(_r),
              "parsed": sum(r["parsed"] for r in _r) / len(_r)}
        pl["by_set"] = {}
        for _n in sorted({x["dev_set"] for x in plan_dev}):
            _q = [r for x, r in zip(plan_dev, _r) if x["dev_set"] == _n]
            pl["by_set"][_n] = {"n": len(_q), "ok": sum(r["ok"] for r in _q) / len(_q), "action": sum(r["action"] for r in _q) / len(_q)}
        print("   planner turns, dev      generated (%d): fully right %5.1f%%   action right %5.1f%%   call parsed %5.1f%%   | %s" % (
            pl["n"], 100 * pl["ok"], 100 * pl["action"], 100 * pl["parsed"],
            "   ".join("%s: fully right %.1f%%, action right %.1f%% of %d" % (k, 100 * v["ok"], 100 * v["action"], v["n"]) for k, v in pl["by_set"].items())), flush=True)
    extra = {}
    for key, items in held27.items():                    # generated answers on the held-out pointing sets
        ans = lab.score(lab.B, items, tag=f"027:{TAG}:{label}:{key}")["answers"]
        ok = 0
        for it, text in zip(items, ans):
            nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
            bx = it["box1000"]
            ok += len(nums) >= 2 and bx[0] <= nums[0] <= bx[2] and bx[1] <= nums[1] <= bx[3]
        extra[key] = ok / len(items)
    can = lab.canary(lab.B, tag=f"027:{TAG}:{label}")["all"]
    row = {"label": label, "select": a, "report": b, "tools": tc, "steps_tf": st, "steps_generated": sg, "pointer_own_words": p_own,
           "pointer_dataset_words": p_ref, "pointer_n": n_own, "canary": can, "held_out_pointing": extra, "planner_dev": pl, "examples": answers[:3], "seconds": time.time() - t}
    rows.append(row)
    pct = lambda v: "  n/a" if v is None else "%5.1f%%" % (100 * v)
    by = sg["by_action"]
    print("%s  [%.0f s]" % (label, time.time() - t))
    print("   steps, reserved         generated (%d): fully right %s   action right %s   call parsed %s   mean target overlap %s   |   teacher-forced: every token right %.1f%% of %d" % (
        sg["n"], pct(sg["correct"]), pct(sg["action"]), pct(sg["parsed"]), sg["mean_target_overlap"], 100 * st.get("tf_exact", 0), st.get("n_tool", 0)))
    print("   steps by action         " + "   ".join("%s %s of %d" % (k, pct(v["correct"]), v["n"]) for k, v in by.items()) + ("   | misses: %s" % sg["why"] if sg["why"] else ""))
    print("   pointer on its targets  within 24 px with the model's own words %s, with the dataset's words %s (%d targets; this model as the pointer)" % (pct(p_own), pct(p_ref), n_own))
    print("   plain pointing          select %.3f   report %.3f" % (a["p_hit"], b["p_hit"])
          + "".join("   %s %.1f%% of %d on target (generated)" % (k, 100 * v, len(held27[k])) for k, v in extra.items()))
    print("   tool benchmark (dev)    every token right on %.1f%% of %d calls   holds back on %.1f%% of %d no-call cases   canary %s" % (
        100 * tc.get("tf_exact", 0), tc.get("n_tool", 0), 100 * tc.get("holds_back", 0), tc.get("n_no_call", 0), can), flush=True)
    return row


def export27(label, step):
    name = f"{PATCHNAME}-u{step}"
    _tmp = f"{lab.root}/export/tmp_{name}_pack"
    ternary.export_pack(lab.tern, lab.paths["pack"], _tmp)
    _ck = BlockDistiller(lab, 4, 31, teacher=None).save(range(4, 32), f"{lab.dir}/ckpt/{name}_L4-31.safetensors")
    _out = f"{lab.root}/export/patches/{name}.patch.safetensors"
    _r = subprocess.run([sys.executable, f"{lab.root}/weights/make_patch.py", lab.paths["pack"], _out, "--pack", _tmp, "--ckpt", _ck,
                         "--note", f"orchestrator steps, tools and pointing (experiment 027, {TAG}, {label}); started from {out['state']}"],
                        capture_output=True, text=True)
    print(_r.stdout.strip() or "(no output)", _r.stderr.strip()[-1500:], flush=True)
    shutil.rmtree(_tmp, ignore_errors=True)
    os.remove(_ck)
    if _r.returncode:
        print("make_patch.py FAILED; the round's multipliers are in lab/ckpt", flush=True)


T27 = TaskTuner(lab, LAYERS, scales=True, head=True)
snap27 = T27.snapshot()
if globals().get("NOSTART27"):                       # the start state was scored by the run that made it: go straight to training
    first, best, floor = None, {"label": "start", "step": 0, "score": globals().get("NOSTART27") if isinstance(globals().get("NOSTART27"), float) else -1.0}, 0.0
    _score = lambda r: ((r["planner_dev"]["ok"] if r.get("planner_dev") else (r["steps_generated"]["correct"] or 0.0))
                        + (r["held_out_pointing"].get("neighbour slice", 0.0) if NEIGHBOUR else 0.0))
else:
    first = measure("start")
    _score = lambda r: ((r["planner_dev"]["ok"] if r.get("planner_dev") else (r["steps_generated"]["correct"] or 0.0))
                        + (r["held_out_pointing"].get("neighbour slice", 0.0) if NEIGHBOUR else 0.0))
    best = {"label": "start", "step": 0, "score": _score(first)}
    floor = first["select"]["p_hit"] - 0.03
per_round, done = EVERY * ACC, 0
while done < UPDATES:
    n = min(EVERY, UPDATES - done)
    k = (done // EVERY) * per_round
    chunk = [train27[(k + i) % len(train27)] for i in range(n * ACC)]
    actions.install()
    r = T27.train(chunk, n, lr_scales=LR, warmup=40, accumulate=ACC, ema=0.98, seed=27 + done, report_every=50,
                  offset=done, total=UPDATES, rewarm=25)
    done += n
    row = measure(f"step {done}")
    row["train"] = r
    mark = ""
    if not SMOKE:
        torch.save(T27.snapshot(), f"{lab.dir}/ckpt/tune_{TAG}_u{done}.pt")      # every scored round is kept
    if row["select"]["p_hit"] >= floor and _score(row) > best["score"]:
        best = {"label": row["label"], "step": done, "score": _score(row)}
        mark = "  <- best so far"
        if PATCHNAME and not EXPORT_ALL:
            export27(row["label"], done)
    if PATCHNAME and EXPORT_ALL:
        export27(row["label"], done)
    print("   training loss %.3f -> %.3f%s" % (r["loss_start"], r["loss_end"], mark), flush=True)
    if not SMOKE:
        json.dump(out, open(f"{lab.dir}/exp027_{TAG}.json", "w"), indent=1)
if SMOKE:
    T27.restore(snap27)
    print("smoke run finished: %d updates, every part ran; the starting multipliers are back and nothing was saved" % UPDATES)
else:
    out["kept"] = best
    json.dump(out, open(f"{lab.dir}/exp027_{TAG}.json", "w"), indent=1)
    print("027 done: best %s (score %.1f: steps fully right, plus the neighbour slice when NEIGHBOUR27 is set); the last round's multipliers are in memory, each round's in lab/ckpt/tune_%s_u*.pt" % (
        best["label"], 100 * best["score"], TAG), flush=True)
