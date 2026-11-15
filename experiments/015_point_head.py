# Experiment 015: a "System 1" pointing head (weightlab/head.py).
#
# Instead of writing "[x, y]" digit by digit, a small head reads the model's internal state once
# the screenshot and the instruction have been processed and returns three numbers directly:
# x, y and a click-or-not logit. The backbone stays frozen (and ternary); the head is about 2.4
# million ordinary parameters. Several heads are trained at once from the same forward passes:
#   pointer heads   score every image cell against the query state, at different layers
#   regress heads   an MLP from the query state alone (the literal three-number idea), as control
# The layer choice matters for speed: a head that reads layer 20 means layers 21..32 never run.
# Training data: the Mac-plus-synthetic mix of experiment 010 (several questions per screenshot).
# Scored the way it would be used: one instruction per screenshot, no earlier answers in context.
# Settings: STEPS15, ROUND15, TAG15.
import json
import os
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
import weightlab.head as headmod
importlib.reload(headmod)

STEPS = globals().get("STEPS15", 4000)
ROUND = globals().get("ROUND15", 1000)
TAG = globals().get("TAG15", "v1")

# ---- 0. finish experiment 010 if it was interrupted: close the block, keep the better checkpoint
if "E" in globals() and getattr(E, "training", False):
    c = E.close()
    lab.stack.pop()
    print("experiment 010 stopped at step %d; %.4f%% of the block's codes had flipped" % (E.steps_done, 100 * c["codes_changed_share"]))
if "chosen010" not in globals():
    cand = {}
    for label, path in (("step 1000 (best on the select set)", best_path), ("last saved checkpoint", last_path)):
        if not os.path.exists(path):
            continue
        E.D.restore(path)
        a, b = fS.evaluate(4), fR.evaluate(4)
        fS.discard(); fR.discard()
        cand[label] = (path, a["p_hit"], b["p_hit"])
        print("%-36s select %.3f   report %.3f" % (label, a["p_hit"], b["p_hit"]), flush=True)
    chosen010 = max(cand, key=lambda k: cand[k][1] + cand[k][2])
    E.D.restore(cand[chosen010][0])
    lab.stack[:] = ["tune:scales:L4-19:400", "tune:scales:L4-19:300", "tune:scales:L4-31+head:400", f"qat010:{chosen010}"]
    json.dump({k: v[1:] for k, v in cand.items()}, open(f"{lab.dir}/exp010_choice.json", "w"), indent=1)
    print("using:", chosen010, flush=True)
import gc
gc.collect(); torch.cuda.empty_cache()

# ---- 1. heads
SPECS = [("pointer q32 k32", "pointer", 32, 32), ("pointer q32 k20", "pointer", 32, 20), ("pointer q24 k20", "pointer", 24, 20),
         ("pointer q20 k20", "pointer", 20, 20), ("pointer q20 k12", "pointer", 20, 12), ("pointer q16 k16", "pointer", 16, 16),
         ("regress q32", "regress", 32, 32), ("regress q20", "regress", 20, 20)]
HB = headmod.HeadBench(lab, SPECS)
sets = {"select": fS.samples, "report": fR.samples,
        "fresh ScreenSpot-v2": lab.data("ssv2", mod=(8, 3)),
        "Mac app windows": lab.data("mac:screen2ax_task:test", n=120)}
out = {"specs": SPECS, "state": list(lab.stack), "rounds": []}


def table(name, r):
    print(f"  {name}:")
    for n, v in r.items():
        print("    %-18s on target %5.1f%%   median distance %5.1f   click decision right %5.1f%%" % (
            n, 100 * v["hit"], v["median_dist"], 100 * v["click_acc"]), flush=True)


t0 = time.time()
for r0 in range(0, STEPS, ROUND):
    losses = HB.train(packs, min(ROUND, STEPS - r0), total=STEPS, seed=15)
    s = HB.score(sets["select"])
    out["rounds"].append({"steps": HB.steps, "select": s, "losses": losses})
    print("after %d steps  [%.0f min]" % (HB.steps, (time.time() - t0) / 60))
    table("select (159 real screens)", s)
    HB.save(f"{lab.dir}/ckpt/heads015_{TAG}.pt")
    json.dump(out, open(f"{lab.dir}/exp015_{TAG}.json", "w"), indent=1)
print("final, all sets:")
out["final"] = {}
for name, data in sets.items():
    out["final"][name] = HB.score(data)
    table(f"{name} ({len(data)})", out["final"][name])
json.dump(out, open(f"{lab.dir}/exp015_{TAG}.json", "w"), indent=1)
print("heads saved to", f"{lab.dir}/ckpt/heads015_{TAG}.pt")
