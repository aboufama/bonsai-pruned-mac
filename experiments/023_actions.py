# Experiment 023: one set of weights that points, calls tools and acts (the computer_use tool).
#
# The loop we want: the model reads a screenshot, emits ONE action as a tool call, the harness runs
# it, repeat (docs/ACTION_FORMAT.md, weightlab/actions.py). This is experiment 014's recipe (only
# multipliers of layers 4..31 and the output head move, gentle) with AgentNet macOS action cases
# added to the mix:
#   point        the plain "[x, y]" grounding format
#   point_call   screenshot + request -> point(x, y)
#   tool_call    text request + tools -> the expected calls;  no_call: must not start a call
#   action_call  screenshot + goal + previous actions -> one computer_use call
# Every training screenshot gets one long side from SIZES23 (896-weighted by default).
# The run is split into rounds of EVERY23 updates on one learning-rate schedule; after each round:
# plain pointing (select, report), pointing as a tool call, the tool benchmark's dev split, and the
# action cases of trajectories no training pool has seen (reserved, never_trained): teacher-forced,
# and generated answers judged by actions.score_answers (action name right; click within 24 px;
# both ends for a drag; exact text for type and key).
# Best round = highest share of generated actions fully right, among rounds whose plain pointing on
# select is not more than 0.03 under the start (if none qualifies, the round with the best select).
# Its multipliers are restored at the end and written out as a patch.
#
# Action cases come from data/mac/agentnet/action_pick.json, written by tools/action_images.py on
# the machine that has the screenshots, so both sides use the same cases by construction.
# Settings: UPDATES23, EVERY23, LR23, ACC23, TAG23, HEAD23 (False on the 4B), ACTIONS23, KINDS23
# (action names; None = every kind in the pick file), SIZES23, SCORE_ACTIONS23 (teacher-forced
# cases per round), GEN_ACTIONS23 (generated answers per round), SMOKE23 (N updates, tiny score
# sets, nothing saved), PATCHNAME23 (file name of the patch, without extension; None = no export).
import collections
import json
import os
import random
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

SMOKE = globals().pop("SMOKE23", None)                 # applies to the run that sets it only
UPDATES = SMOKE or globals().get("UPDATES23", 3000)
EVERY = min(UPDATES, globals().get("EVERY23", 500))
LR = globals().get("LR23", 2e-4)
ACC = globals().get("ACC23", 2)
TAG = globals().get("TAG23", f"actions_u{UPDATES}") + ("_smoke" if SMOKE else "")
HEAD = globals().get("HEAD23", True)
N_ACTIONS = globals().get("ACTIONS23", 3000)
KINDS = globals().get("KINDS23", actions.CLICKS + actions.SCROLLS)
SIZES = globals().get("SIZES23", (896, 896, 896, 896, 640, 768, 1024, 1280))
N_SCORE = 8 if SMOKE else globals().get("SCORE_ACTIONS23", 200)
N_GEN = 4 if SMOKE else globals().get("GEN_ACTIONS23", 120)
PATCHNAME = None if SMOKE else globals().get("PATCHNAME23", None)
LAYERS = list(range(4, 32))
rng = random.Random(23)

if "mix" not in globals() or "fS" not in globals():
    raise RuntimeError("run the prelude first: it builds the pointing mix and the two score sets")

# ---- action cases: the ids chosen by tools/action_images.py, read from the cases on this machine
adir = f"{lab.root}/data/mac/agentnet"
if not os.path.exists(f"{adir}/action_pick.json") or not os.path.exists(f"{adir}/cases_actions.jsonl"):
    raise RuntimeError("data/mac/agentnet/action_pick.json or cases_actions.jsonl is missing: run tools/action_images.py "
                       "where the screenshots are and copy the files it lists to this machine")
pick23 = json.load(open(f"{adir}/action_pick.json"))
want = {"train": set(pick23["train"]), "reserved": set(pick23["reserved"])}
cases23, missing = {"train": [], "reserved": []}, collections.Counter()
for line in open(f"{adir}/cases_actions.jsonl"):
    c = json.loads(line)
    for part in ("train", "reserved"):
        if c["id"] in want[part]:
            if KINDS is not None and c["action"]["name"] not in KINDS:
                continue
            if os.path.exists(os.path.normpath(os.path.join(adir, c["image"]))):
                cases23[part].append(c)
            else:
                missing[part] += 1
if missing:
    print("screenshots not on this machine, cases left out:", dict(missing))
for part in cases23:                                     # the pick file's order, so a smaller ACTIONS23 is a prefix
    order = {i: k for k, i in enumerate(pick23[part])}
    cases23[part].sort(key=lambda c: order[c["id"]])
train_cases = cases23["train"][:N_ACTIONS]
if len(train_cases) < min(50, N_ACTIONS) or not cases23["reserved"]:
    raise RuntimeError(f"too few action cases on this machine: {len(train_cases)} for training, {len(cases23['reserved'])} reserved")
act_train = [actions.action_case(c, base=adir) for c in train_cases]
act_test = [actions.action_case(c, base=adir) for c in cases23["reserved"][:N_SCORE]]
act_gen = act_test[:N_GEN]
print("action cases: training", dict(collections.Counter(c["action"]["name"] for c in train_cases)),
      "  reserved, never trained on:", dict(collections.Counter(s["case"]["action"]["name"] for s in act_test)))


def sized(sample):
    """A copy of a training sample whose screenshot has one of the long sides of SIZES."""
    if not SIZES:
        return sample
    side = rng.choice(SIZES)
    if sample.get("kind") in ("point_call", actions.KIND):
        return dict(sample, item=dict(sample["item"], max_side=side))
    if sample.get("kind"):                               # tool_call / no_call: no screenshot
        return sample
    return dict(sample, max_side=side)


# ---- training samples (014's mix plus the action cases)
point_items = list(mix)
rng.shuffle(point_items)
tool_cases = [json.loads(l) for l in open(f"{lab.root}/benchdata/toolcall/train_s11/cases.jsonl")]
tools23 = [s for s in (chat.tool_case(c) for c in tool_cases) if s]
train23 = ([chat.point_call(it) for it in point_items[:2600]] + point_items[2600:4000]
           + [s for s in tools23 if s["kind"] == "tool_call"][:3000] + [s for s in tools23 if s["kind"] == "no_call"][:1000]
           + act_train)
train23 = [sized(s) for s in train23]
rng.shuffle(train23)
print("training samples:", dict(collections.Counter(s.get("kind", "point") for s in train23)),
      "  long sides:", dict(sorted(collections.Counter(
          (s.get("item") or s).get("max_side") for s in train23 if s.get("kind") in (None, "point_call", actions.KIND)).items())) if SIZES else "1280")

# ---- measurements
dev_cases = [json.loads(l) for l in open(f"{lab.root}/bench/toolcall/runs/dev_20261114/cases.jsonl")]
tool_dev = [s for s in (chat.tool_case(c) for c in dev_cases) if s]
point_dev = [chat.point_call(it) for it in fS.samples]
if SMOKE:
    tool_dev, point_dev = tool_dev[:8], point_dev[:8]
rows = []
out = {"tag": TAG, "updates": UPDATES, "every": EVERY, "lr": LR, "accumulate": ACC, "head": HEAD, "sizes": list(SIZES or []),
       "kinds": list(KINDS) if KINDS is not None else None, "train": dict(collections.Counter(s.get("kind", "point") for s in train23)),
       "state": list(lab.stack), "rows": rows}


def measure(label):
    t = time.time()
    actions.install()
    a, b = fS.evaluate(4, tag=f"023:{TAG}:{label}:select"), fR.evaluate(4, tag=f"023:{TAG}:{label}:report")
    fS.discard(); fR.discard()
    pc = chat.score(lab, lab.B, point_dev, tag=f"023:{TAG}:{label}:point_call")
    tc = chat.score(lab, lab.B, tool_dev, tag=f"023:{TAG}:{label}:tools")
    at = chat.score(lab, lab.B, act_test, tag=f"023:{TAG}:{label}:actions")
    answers = [actions.generate(lab, lab.B, s)[0] for s in act_gen]
    ag = actions.score_answers([s["case"] for s in act_gen], answers)
    by = ag["by_action"]
    clicks = [v for k, v in by.items() if k in actions.CLICKS]
    click_ok = sum(v["correct"] * v["n"] for v in clicks) / max(1, sum(v["n"] for v in clicks)) if clicks else None
    row = {"label": label, "select": a, "report": b, "point_call": pc, "tools": tc, "actions_tf": at, "actions_generated": ag,
           "click_within_24px": click_ok, "examples": answers[:3], "seconds": time.time() - t}
    rows.append(row)
    pct = lambda v: "  n/a" if v is None else "%5.1f%%" % (100 * v)
    print("%s  [%.0f s]" % (label, time.time() - t))
    print("   plain pointing          select %.3f   report %.3f" % (a["p_hit"], b["p_hit"]))
    print("   pointing as a tool call select %.3f   (call written correctly %.0f%%)" % (pc["p_hit"], 100 * pc["format"]))
    print("   tool benchmark (dev)    every token right on %.1f%% of %d calls   holds back on %.1f%% of %d no-call cases" % (
        100 * tc.get("tf_exact", 0), tc.get("n_tool", 0), 100 * tc.get("holds_back", 0), tc.get("n_no_call", 0)))
    print("   actions, reserved       teacher-forced: every token right on %.1f%% of %d   |   generated (%d): fully right %s   action name right %s   click within 24 px %s   median distance %s px" % (
        100 * at["tf_exact"], at["n_tool"], ag["n"], pct(ag["correct"]), pct(ag["name"]), pct(click_ok), ag["median_dist_px"]))
    print("   actions by kind         " + "   ".join("%s %s of %d" % (k, pct(v["correct"]), v["n"]) for k, v in by.items())
          + ("   | misses: %s" % ag["why"] if ag["why"] else ""), flush=True)
    return row


T23 = TaskTuner(lab, LAYERS, scales=True, head=HEAD)
snap23 = T23.snapshot()                                   # the state this run started from
first = measure("start")
best = {"label": "start", "step": 0, "score": first["actions_generated"]["correct"] or 0.0, "snap": None}
floor = first["select"]["p_hit"] - 0.03
fallback = {"label": "start", "step": 0, "select": first["select"]["p_hit"], "snap": None}
per_round = EVERY * ACC
done = 0
while done < UPDATES:
    n = min(EVERY, UPDATES - done)
    k = (done // EVERY) * per_round
    chunk = [train23[(k + i) % len(train23)] for i in range(n * ACC)]       # each round its own stretch of the shuffled mix
    actions.install()
    r = T23.train(chunk, n, lr_scales=LR, warmup=40, accumulate=ACC, ema=0.98, seed=23 + done, report_every=50,
                  offset=done, total=UPDATES, rewarm=25)
    done += n
    row = measure(f"step {done}")
    row["train"] = r
    snap = T23.snapshot()
    mark = ""
    if row["select"]["p_hit"] >= floor and (row["actions_generated"]["correct"] or 0.0) > best["score"]:
        best = {"label": row["label"], "step": done, "score": row["actions_generated"]["correct"], "snap": snap}
        mark = "  <- best so far"
        if not SMOKE:
            torch.save(snap, f"{lab.dir}/ckpt/tune_{TAG}_best.pt")
    if row["select"]["p_hit"] > fallback["select"] and done:
        fallback = {"label": row["label"], "step": done, "select": row["select"]["p_hit"], "snap": snap}
    print("   training loss %.3f -> %.3f%s" % (r["loss_start"], r["loss_end"], mark), flush=True)
    if not SMOKE:
        json.dump(out, open(f"{lab.dir}/exp023_{TAG}.json", "w"), indent=1)

if SMOKE:
    T23.restore(snap23)
    print("smoke run finished: %d updates, every part ran; the starting multipliers are back and nothing was saved" % UPDATES)
else:
    chosen = best if best["snap"] is not None else fallback
    if chosen["snap"] is None:
        T23.restore(snap23)
        print("no round beat the start; the starting multipliers are back")
    else:
        T23.restore(chosen["snap"])
        if chosen is fallback:
            torch.save(chosen["snap"], f"{lab.dir}/ckpt/tune_{TAG}_best.pt")
        print("kept: %s (%s)" % (chosen["label"], "most actions fully right with plain pointing held" if chosen is best
                                 else "no round held plain pointing within 0.03 and beat the start on actions; this one has the best select"))
    out["kept"] = {"label": chosen["label"], "step": chosen["step"]}
    final = measure("kept")
    out["canary"] = lab.canary(lab.B, tag=f"023:{TAG}")
    print("   canary                  %s" % out["canary"]["all"])
    json.dump(out, open(f"{lab.dir}/exp023_{TAG}.json", "w"), indent=1)
    if PATCHNAME and chosen["snap"] is not None:
        _tmp = f"{lab.root}/export/tmp_{PATCHNAME}_pack"
        ternary.export_pack(lab.tern, lab.paths["pack"], _tmp)
        _ck = BlockDistiller(lab, 4, 31, teacher=None).save(range(4, 32), f"{lab.dir}/ckpt/{PATCHNAME}_L4-31.safetensors")
        _out = f"{lab.root}/export/patches/{PATCHNAME}.patch.safetensors"
        _r = subprocess.run([sys.executable, f"{lab.root}/weights/make_patch.py", lab.paths["pack"], _out, "--pack", _tmp, "--ckpt", _ck,
                             "--note", f"pointing, tools and computer_use actions (experiment 023, {TAG}, {chosen['label']}); started from {out['state']}"],
                            capture_output=True, text=True)
        print(_r.stdout.strip() or "(no output)", _r.stderr.strip()[-1500:], flush=True)
        shutil.rmtree(_tmp, ignore_errors=True)
        if _r.returncode:
            raise RuntimeError("make_patch.py failed")
    print("kept in memory; T23.restore(snap23) puts the starting multipliers back")
