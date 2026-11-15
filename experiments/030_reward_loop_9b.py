# Experiment 030: reward passes on pointing for the 9B's WRITTEN answers (15 Nov;
# the model that feeds the app). The twin of 029 for a model that points by writing "[x, y]".
#
# One pass: (1) score a fresh pool of POOL30 simulator cases with generated answers (reward 1 = inside the
# box), overall and by the simulator's class; (2) slice = every miss with its box (position and same_name
# misses twice), as many hits, and MIX30 ordinary mix cases per miss, plus planner turns and tool calls as
# anchors when the start model is a planner (ANCHORS30), so planning does not drift; (3) UPD30 updates of
# the 014 recipe (multipliers of layers 4..31 and the head) at a gentle rate; (4) re-score the same misses,
# then macsim_dev, report, the neighbour slice, Mac windows (generated), select teacher-forced, the tool
# benchmark and the canary. The loop stops and puts the last good state back if report falls more than
# DROP30 under the start or the canary is under 0.90. A snapshot after every pass:
# lab/ckpt/tune_<TAG30>_p<pass>.pt; with PATCHNAME30 a patch after every pass that holds.
# Settings: PASSES30, POOL30, UPD30, LR30, MIX30, DROP30, TAG30, PATCHNAME30, ANCHORS30, SMOKE30.
import collections
import json
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
from weightlab.distill import BlockDistiller
from weightlab.tune import TaskTuner

SMOKE = globals().pop("SMOKE30", None)
PASSES, POOL, UPD = (1, 16, 6) if SMOKE else (globals().get("PASSES30", 4), globals().get("POOL30", 1200), globals().get("UPD30", 300))
LR, ACC, MIXX, DROP = globals().get("LR30", 5e-5), 2, globals().get("MIX30", 2), globals().get("DROP30", 0.0101)
TAG, PATCHNAME = globals().get("TAG30", "9b_reward_macsim") + ("_smoke" if SMOKE else ""), None if SMOKE else globals().get("PATCHNAME30")
if "mix" not in globals() or "fS" not in globals():
    raise RuntimeError("run the prelude first")
rng = random.Random(30)
SET = "gen:benchdata/pointing/macsim_train_s1"
cands = [dict(it, kind=None) for it in lab.data(SET, n=36484)]
CLASS = {}
for _line in open(f"{lab.root}/{SET[4:]}/cases.jsonl"):
    _c = json.loads(_line)
    CLASS[_c["id"]] = (_c.get("tags") or {}).get("challenge") or "other"
rng.shuffle(cands)
held = {"macsim dev": lab.data("gen:benchdata/pointing/macsim_dev_s1", n=300), "report": list(fR.samples)}
if os.path.exists(f"{lab.root}/data/mac/neighbour_test/cases.jsonl"):
    held["neighbour slice"] = lab.data("mac:neighbour_test:test", n=600)[::4][:150]
held["Mac windows"] = lab.data("mac:screen2ax_task:test", n=60)
if SMOKE:
    held = {k: v[:6] for k, v in held.items()}
_dev = [json.loads(l) for l in open(f"{lab.root}/bench/toolcall/runs/dev_20261114/cases.jsonl")]
tool_dev = [x for x in (chat.tool_case(c) for c in _dev) if x][:8 if SMOKE else 150]
anchors_extra = []
for _dir in globals().get("ANCHORS30", ()):              # planner turns, so a planner stays a planner
    if os.path.exists(f"{lab.root}/{_dir}"):
        from weightlab import planner as planner30
        anchors_extra += planner30.load(f"{lab.root}/{_dir}", "train")
rng.shuffle(anchors_extra)
_tools = [x for x in (chat.tool_case(json.loads(l)) for l in open(f"{lab.root}/benchdata/toolcall/train_s11/cases.jsonl")) if x]
anchors_extra += [x for x in _tools if x["kind"] == "tool_call"][:300]
rng.shuffle(anchors_extra)
mix_anchors = [dict(it, kind=None) for it in mix]
rng.shuffle(mix_anchors)


def inside(it, text):
    v = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text)]
    b = it["box1000"]
    return len(v) >= 2 and b[0] <= v[0] <= b[2] and b[1] <= v[1] <= b[3]


def hits_of(items, tag):
    return [inside(it, a) for it, a in zip(items, lab.score(lab.B, items, tag=tag)["answers"])]


def held_out(label):
    t = time.time()
    row = {k: sum(hits_of(v, f"030:{TAG}:{label}:{k}")) / len(v) for k, v in held.items()}
    a = fS.evaluate(4, tag=f"030:{TAG}:{label}:select"); fS.discard()
    tc = chat.score(lab, lab.B, tool_dev, tag=f"030:{TAG}:{label}:tools")
    can = lab.canary(lab.B, tag=f"030:{TAG}:{label}")["all"]
    row.update({"label": label, "select_tf": a["p_hit"], "tools": tc.get("tf_exact"), "holds_back": tc.get("holds_back"), "canary": can})
    print("%-16s %s   select (teacher-forced) %.3f   tools %.1f%%   canary %s   [%.0f s]" % (
        label, "   ".join("%s %.1f%%" % (k, 100 * row[k]) for k in held), a["p_hit"], 100 * (tc.get("tf_exact") or 0), can, time.time() - t), flush=True)
    return row


T30 = TaskTuner(lab, list(range(4, 32)), scales=True, head=True)
good, out = T30.snapshot(), {"tag": TAG, "passes": [], "pool": POOL, "updates": UPD, "lr": LR}
first = held_out("start")
out["start"] = first
for p in range(PASSES):
    t = time.time()
    pool = cands[p * POOL:(p + 1) * POOL]
    hit = hits_of(pool, f"030:{TAG}:pass{p + 1}:pool")
    by = collections.defaultdict(lambda: [0, 0])
    for it, h in zip(pool, hit):
        by[CLASS.get(it["id"], "other")][0] += 1; by[CLASS.get(it["id"], "other")][1] += h
    misses = [it for it, h in zip(pool, hit) if not h]
    keep = [it for it, h in zip(pool, hit) if h][:len(misses)]
    reward = 1 - len(misses) / len(pool)
    n_extra = min(len(anchors_extra), len(misses))
    train = (misses + [it for it in misses if CLASS.get(it["id"]) in ("position", "same_name")] + keep
             + mix_anchors[p * MIXX * len(misses):(p + 1) * MIXX * len(misses)] + anchors_extra[:n_extra])
    train = [dict(s, max_side=rng.choice((1280, 896))) if not s.get("kind") else s for s in train]
    rng.shuffle(train)
    print("pass %d: pool of %d fresh simulator cases: reward %.1f%%   by class: %s   -> slice: %d misses, %d hits, %d mix cases, %d planner and tool anchors   [%.0f s]" % (
        p + 1, len(pool), 100 * reward, "   ".join("%s %.1f%% of %d" % (k, 100 * v[1] / v[0], v[0]) for k, v in sorted(by.items())),
        len(misses), len(keep), MIXX * len(misses), n_extra, time.time() - t), flush=True)
    T30.train([train[i % len(train)] for i in range(UPD * ACC)], UPD, lr_scales=LR, warmup=20, accumulate=ACC, ema=0.98, seed=30 + p,
              report_every=50, offset=p * UPD, total=PASSES * UPD, rewarm=15)
    flipped = sum(hits_of(misses, f"030:{TAG}:pass{p + 1}:misses"))
    row = held_out("after pass %d" % (p + 1))
    row.update({"pass": p + 1, "reward_before": reward, "by_class": {k: v[1] / v[0] for k, v in by.items()}, "misses": len(misses), "flipped": flipped,
                "reward_after_on_pool": (len(pool) - len(misses) + flipped) / len(pool)})
    out["passes"].append(row)
    print("pass %d: of its %d misses %d now hit (%.1f%%): reward on that pool %.1f%% -> %.1f%%" % (
        p + 1, len(misses), flipped, 100 * flipped / max(1, len(misses)), 100 * reward, 100 * row["reward_after_on_pool"]), flush=True)
    if (row["report"] < first["report"] - DROP or row["canary"]["tf_exact"] < 0.90) and not SMOKE:
        print("pass %d: report fell more than %.1f points under the start or the canary is under 0.90: stopping; the last good state is put back" % (p + 1, 100 * DROP), flush=True)
        T30.restore(good)
        break
    good = T30.snapshot()
    if not SMOKE:
        torch.save(good, f"{lab.dir}/ckpt/tune_{TAG}_p{p + 1}.pt")
        json.dump(out, open(f"{lab.dir}/exp030_{TAG}.json", "w"), indent=1)
        if PATCHNAME:
            name = f"{PATCHNAME}-p{p + 1}"
            _tmp = f"{lab.root}/export/tmp_{name}_pack"
            ternary.export_pack(lab.tern, lab.paths["pack"], _tmp)
            _ck = BlockDistiller(lab, 4, 31, teacher=None).save(range(4, 32), f"{lab.dir}/ckpt/{name}_L4-31.safetensors")
            _r = subprocess.run([sys.executable, f"{lab.root}/weights/make_patch.py", lab.paths["pack"], f"{lab.root}/export/patches/{name}.patch.safetensors",
                                 "--pack", _tmp, "--ckpt", _ck, "--note", f"reward pass {p + 1} on simulator pointing (experiment 030, {TAG})"], capture_output=True, text=True)
            print(_r.stdout.strip() or "(no output)", _r.stderr.strip()[-600:], flush=True)
            shutil.rmtree(_tmp, ignore_errors=True); os.remove(_ck)
if SMOKE:
    T30.restore(good)
print("030 TABLE %s" % TAG)
print("  pass  reward before  after (same pool)  macsim dev  report  neighbour slice  Mac windows  tools  canary")
print("  start        -              -             %5.1f%%   %5.1f%%      %5.1f%%        %5.1f%%   %5.1f%%   %.2f" % (
    100 * first["macsim dev"], 100 * first["report"], 100 * first.get("neighbour slice", 0), 100 * first["Mac windows"], 100 * (first["tools"] or 0), first["canary"]["tf_exact"]))
for r in out["passes"]:
    print("  %4d     %5.1f%%         %5.1f%%           %5.1f%%   %5.1f%%      %5.1f%%        %5.1f%%   %5.1f%%   %.2f" % (
        r["pass"], 100 * r["reward_before"], 100 * r["reward_after_on_pool"], 100 * r["macsim dev"], 100 * r["report"],
        100 * r.get("neighbour slice", 0), 100 * r["Mac windows"], 100 * (r["tools"] or 0), r["canary"]["tf_exact"]), flush=True)
print("030 done", flush=True)
