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
# GEN27, SMOKE27 (N updates, tiny score sets, nothing saved), PATCHNAME27.
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
tool_cases = [json.loads(l) for l in open(f"{lab.root}/benchdata/toolcall/train_s11/cases.jsonl")]
tools27 = [s for s in (chat.tool_case(c) for c in tool_cases) if s]
n_point = round((len(step_train) + 900) / 3)             # a quarter of the whole
train27 = (point_items[:n_point] + [s for s in tools27 if s["kind"] == "tool_call"][:600]
           + [s for s in tools27 if s["kind"] == "no_call"][:300] + step_train)
train27 = [sized(s) for s in train27]
rng.shuffle(train27)
print("training samples:", dict(collections.Counter(s.get("kind", "point") for s in train27)), flush=True)

dev_cases = [json.loads(l) for l in open(f"{lab.root}/bench/toolcall/runs/dev_20261114/cases.jsonl")]
tool_dev = [s for s in (chat.tool_case(c) for c in dev_cases) if s]
if SMOKE:
    tool_dev = tool_dev[:8]
rows = []
out = {"tag": TAG, "updates": UPDATES, "every": EVERY, "lr": LR, "accumulate": ACC, "sizes": list(SIZES), "thought": THOUGHT,
       "train": dict(collections.Counter(s.get("kind", "point") for s in train27)), "state": list(lab.stack), "rows": rows}


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
    can = lab.canary(lab.B, tag=f"027:{TAG}:{label}")["all"]
    row = {"label": label, "select": a, "report": b, "tools": tc, "steps_tf": st, "steps_generated": sg, "pointer_own_words": p_own,
           "pointer_dataset_words": p_ref, "pointer_n": n_own, "canary": can, "examples": answers[:3], "seconds": time.time() - t}
    rows.append(row)
    pct = lambda v: "  n/a" if v is None else "%5.1f%%" % (100 * v)
    by = sg["by_action"]
    print("%s  [%.0f s]" % (label, time.time() - t))
    print("   steps, reserved         generated (%d): fully right %s   action right %s   call parsed %s   mean target overlap %s   |   teacher-forced: every token right %.1f%% of %d" % (
        sg["n"], pct(sg["correct"]), pct(sg["action"]), pct(sg["parsed"]), sg["mean_target_overlap"], 100 * st.get("tf_exact", 0), st.get("n_tool", 0)))
    print("   steps by action         " + "   ".join("%s %s of %d" % (k, pct(v["correct"]), v["n"]) for k, v in by.items()) + ("   | misses: %s" % sg["why"] if sg["why"] else ""))
    print("   pointer on its targets  within 24 px with the model's own words %s, with the dataset's words %s (%d targets; this model as the pointer)" % (pct(p_own), pct(p_ref), n_own))
    print("   plain pointing          select %.3f   report %.3f" % (a["p_hit"], b["p_hit"]))
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
first = measure("start")
best = {"label": "start", "step": 0, "score": first["steps_generated"]["correct"] or 0.0}
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
    if row["select"]["p_hit"] >= floor and (row["steps_generated"]["correct"] or 0.0) > best["score"]:
        best = {"label": row["label"], "step": done, "score": row["steps_generated"]["correct"]}
        mark = "  <- best so far"
        if PATCHNAME:
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
    print("027 done: best %s (generated steps fully right %.1f%%); the last round's multipliers are in memory, each round's in lab/ckpt/tune_%s_u*.pt" % (
        best["label"], 100 * best["score"], TAG), flush=True)
