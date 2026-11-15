# Experiment 016: "System 1" pointing heads, second design (weightlab/head.py). Experiment 015 was the
# first attempt; its loss was badly scaled and it was stopped after 400 steps.
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
# Settings: STEPS16, ROUND16, TAG16, SEED16 (data order), HEADSEED16 (head start), SPECS16, LR16,
# ALLSETS16 (score all four sets after every round, not only select), RESUME16 (a heads file to
# continue from: heads with the same name get their saved weights and the step count carries on).
import json
import os
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
import weightlab.head as headmod
importlib.reload(headmod)

STEPS = globals().get("STEPS16", 4000)
ROUND = globals().get("ROUND16", 1000)
TAG = globals().get("TAG16", "v2")
SEED = globals().get("SEED16", 16)
# these two apply to the run that sets them only (variables persist in the lab session)
ALLSETS = globals().pop("ALLSETS16", False)
RESUME = globals().pop("RESUME16", None)
SIZES = globals().pop("SIZES16", None)               # train each screenshot at a random long side from this list
SCORE_SIZES = globals().pop("SCORE_SIZES16", None)   # extra long sides for the final scores, e.g. (896,)
EXTRA_TRAIN = globals().pop("EXTRA16", None)         # extra training sets (lab.data names), five questions per screenshot
EXTRA_SETS = globals().pop("EXTRA_SETS16", None)     # extra score sets {label: list of samples}

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

# ---- 1. heads (second design; see weightlab/head.py)
SPECS = globals().get("SPECS16") or [
    ("cross q32 k0+12+20", "cross", 32, (0, 12, 20)), ("cross q20 k0+12+20", "cross", 20, (0, 12, 20)),
    ("cross q32 k32", "cross", 32, (32,)), ("cross q20 k20", "cross", 20, (20,)), ("cross q12 k0+12", "cross", 12, (0, 12)),
    ("pointer q32 k32", "pointer", 32, 32), ("pointer q20 k20", "pointer", 20, 20), ("regress q32", "regress", 32, 32)]
HB = headmod.HeadBench(lab, SPECS, seed=globals().get("HEADSEED16", 0), lr=globals().get("LR16", 5e-4))
sets = {"select": fS.samples, "report": fR.samples,
        "fresh ScreenSpot-v2": lab.data("ssv2", mod=(8, 3)),
        "Mac app windows": lab.data("mac:screen2ax_task:test", n=120)}
out = {"specs": SPECS, "state": list(lab.stack), "rounds": [], "params": getattr(HB, "params", {})}
print("parameters: " + "   ".join("%s %.1f M" % (n, c / 1e6) for n, c in out["params"].items()), flush=True)
train_packs = packs
if EXTRA_TRAIN:
    import random as _random
    _re = _random.Random(1617)
    train_packs = list(packs)
    for _name in EXTRA_TRAIN:
        _by = {}
        _okp = {}
        for _it in lab.data(_name, n=10 ** 6):               # evenly spaced picks repeat cases: keep each once
            if _it["path"] not in _okp:
                _okp[_it["path"]] = os.path.exists(_it["path"])    # one look per screenshot (the volume is slow)
            if _okp[_it["path"]]:
                _by.setdefault(_it["path"], {})[_it["id"]] = _it
        _n0 = len(train_packs)
        for _items in _by.values():
            _items = list(_items.values()); _re.shuffle(_items)
            train_packs += [_items[i:i + 5] for i in range(0, len(_items), 5)]
        print("extra training set %s: %d cases on %d screenshots, %d packs" % (_name, sum(len(v) for v in _by.values()), len(_by), len(train_packs) - _n0), flush=True)
    _re.shuffle(train_packs)
if EXTRA_SETS:
    sets.update(EXTRA_SETS)
_only = globals().pop("ONLYSETS16", None)             # score only these sets (names as printed)
if SIZES:
    import random as _random
    _rs = _random.Random(1616)
    train_packs = [[dict(it, max_side=side) for it in pack] for pack in train_packs for side in [_rs.choice(SIZES)]]
    print("training long sides:", {side: sum(p[0]["max_side"] == side for p in train_packs) for side in sorted(set(SIZES))})
for _side in (SCORE_SIZES or ()):
    sets.update({"select at %d px" % _side: lab.data("ssv2", mod=(8, 1), max_side=_side), "report at %d px" % _side: lab.data("ssv2", mod=(8, 5), max_side=_side),
                 "fresh ScreenSpot-v2 at %d px" % _side: lab.data("ssv2", mod=(8, 3), max_side=_side),
                 "Mac app windows at %d px" % _side: lab.data("mac:screen2ax_task:test", n=120, max_side=_side)})
if _only:
    sets = {k: v for k, v in sets.items() if k in _only}


def table(name, r):
    print(f"  {name}:")
    for n, v in r.items():
        print("    %-20s on target %5.1f%%   median distance %5.1f   click decision right %5.1f%%   within 20 px %5.1f%%" % (
            n, 100 * v["hit"], v["median_dist"], 100 * v["click_acc"], 100 * v.get("within20", 0)), flush=True)


t0 = time.time()
if RESUME:
    HB.load_as = globals().pop("RESUME_AS16", None)      # {head name here: head name in the file}
    got16 = HB.load(RESUME)
    out["resumed"] = {"file": RESUME, "steps": HB.steps, "heads": got16}
    print("continuing from %s at step %d: %s; fresh: %s" % (os.path.basename(RESUME), HB.steps, got16, [n for n in HB.heads if n not in got16]), flush=True)
for r0 in range(HB.steps, STEPS, ROUND):
    losses = HB.train(train_packs, min(ROUND, STEPS - r0), total=STEPS, seed=SEED)
    s = HB.score(sets["select"])
    row = {"steps": HB.steps, "select": s, "losses": losses}
    out["rounds"].append(row)
    print("after %d steps  [%.0f min]" % (HB.steps, (time.time() - t0) / 60))
    table("select (159 real screens)", s)
    if ALLSETS:
        for name, data in sets.items():
            if name != "select":
                row[name] = HB.score(data)
                table(f"{name} ({len(data)})", row[name])
    HB.save(f"{lab.dir}/ckpt/heads016_{TAG}.pt")
    if globals().get("KEEP_ROUNDS16"):                # a copy at every scored step, so no round is lost
        HB.save(f"{lab.dir}/ckpt/heads016_{TAG}_s{HB.steps}.pt")
    json.dump(out, open(f"{lab.dir}/exp016_{TAG}.json", "w"), indent=1)
print("final, all sets:")
out["final"] = {}
last_row = out["rounds"][-1] if out["rounds"] else {}
for name, data in sets.items():
    # the heads have not changed since the last round's scoring, and scoring is deterministic
    out["final"][name] = last_row[name] if name in last_row else HB.score(data)
    table(f"{name} ({len(data)})", out["final"][name])
json.dump(out, open(f"{lab.dir}/exp016_{TAG}.json", "w"), indent=1)
if hasattr(HB, "time_heads"):
    out["ms"] = HB.time_heads(sets["report"][0])
    print("milliseconds per answer (head alone, given the model's states): " + "   ".join("%s %.1f" % (n, v) for n, v in out["ms"].items()), flush=True)
    json.dump(out, open(f"{lab.dir}/exp016_{TAG}.json", "w"), indent=1)
print("heads saved to", f"{lab.dir}/ckpt/heads016_{TAG}.pt")
