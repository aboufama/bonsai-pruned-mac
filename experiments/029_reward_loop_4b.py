# Experiment 029: reward passes on pointing for the 4B pair (15 Nov 05:10; it does not wait for
# the simulator and uses the pools on disk). The pointer is the decoder on the jointly trained trunk.
#
# One pass:
#   1. score a fresh pool of POOL29 cases the run has not trained on (decoder's point inside the box =
#      reward 1), overall and by class: neighbour (another labelled box close beside it), small (smaller
#      side under 24 px at 1280, not a neighbour), other;
#   2. training slice: every miss with its box (neighbour misses twice), as many hits as anchors, and as
#      many ordinary mix cases again, so nothing else drifts;
#   3. STEPS29 joint steps (multipliers of layers 0..19 and the decoder), long sides 1280 / 896;
#   4. re-score the same misses (how many flipped), then report, select, the held-out neighbour slice,
#      held-out Mac windows, canary.
# The loop stops, and the last good state is put back, if report falls more than a point under the start
# or the canary goes under 0.90. A copy after every pass: lab/ckpt/joint018_<TAG29>_s<steps>.pt (the
# format tools/joint_export.py reads; base patch = the pair's trunk).
# Pools: Screen2AX-Tree, GroundCUA's neighbour cases, and the neighbour cases of the other Mac sets.
# Settings: PASSES29, POOL29, STEPS29, LRS29, LRH29, TAG29, SMOKE29, POOLSET29 (a generated set as the only pool,
# classes from its tags), MIX29 (mix cases per miss), DROP29 (how far report may fall before the loop stops). Needs HEAD29 (the decoder's file) and a
# fresh 4B session on the pair's trunk patch.
import collections
import copy
import json
import os
import random
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
import weightlab.head as headmod

SMOKE = globals().pop("SMOKE29", None)
PASSES, POOL, STEPS = (1, 40, 10) if SMOKE else (globals().get("PASSES29", 6), globals().get("POOL29", 3000), globals().get("STEPS29", 600))
LRS, LRH, TAG = globals().get("LRS29", 1e-4), globals().get("LRH29", 3e-4), globals().get("TAG29", "4b_reward") + ("_smoke" if SMOKE else "")
if "mix" not in globals() or "fS" not in globals():
    raise RuntimeError("run the prelude first")
rng = random.Random(29)
nb = set(json.load(open(f"{lab.root}/data/mac/neighbour_ids.json"))["ids"])
cands, seen = [], set()
for name, n in (("mac:screen2ax_tree:train", 27019), ("mac:neighbour_gcua:train", 34618), ("mac:os_atlas_mac:train", 13988),
                ("mac:scalecua_mac:train", 1398), ("mac:showui_desktop_mac:train", 1037), ("mac:fable_teacher:train", 4198)):
    if not os.path.exists(f"{lab.root}/data/mac/{name.split(':')[1]}/cases.jsonl"):
        continue
    for it in lab.data(name, n=n):
        if it["id"] not in seen and (name.split(":")[1] in ("screen2ax_tree", "neighbour_gcua") or it["id"] in nb):
            seen.add(it["id"]); cands.append(dict(it, kind=None))
CLASS = {}
if globals().get("POOLSET29"):                       # e.g. "gen:benchdata/pointing/macsim_train_s1": the pools come from this set alone,
    cands = [dict(it, kind=None) for it in lab.data(POOLSET29, n=globals().get("POOLSET_N29", 36484))]      # classes from its tags.challenge
    for _line in open(f"{lab.root}/{POOLSET29[4:]}/cases.jsonl"):
        _c = json.loads(_line)
        CLASS[_c["id"]] = (_c.get("tags") or {}).get("challenge") or "other"
rng.shuffle(cands)
cands = [it for it in cands if os.path.exists(it["path"])] if SMOKE is None else cands[:400]
print("029 %s: %d candidate cases for the pools (%d neighbour cases); %d passes of %d cases, %d steps each" % (
    TAG, len(cands), sum(it["id"] in nb for it in cands), PASSES, POOL, STEPS), flush=True)


def klass(it):
    if it["id"] in CLASS:
        return CLASS[it["id"]]
    if it["id"] in nb:
        return "neighbour"
    w, h = it["size"]
    b = it["bbox"]
    return "small" if min(b[2] - b[0], b[3] - b[1]) * 1280 / max(w, h) < 24 else "other"


# the decoder is built here, after the modules were reloaded: one built before a reload of weightlab.head is
# no longer an instance of its DecoderHead class, and the loss then takes the wrong branch (every pack skipped)
from safetensors.torch import load_file as _load
_head = headmod.DecoderHead((20,), d=lab.B.config.text_config.hidden_size, r=768, layers=2).to(lab.B.device).float()
_head.load_state_dict({k: v.to(lab.B.device) for k, v in _load(globals()["HEAD29"]).items()})
J = headmod.JointHeadTuner(lab, range(0, 20), kind="cross_dec:768:2", layer=20, key_layers=(20,), head=_head)
held = {"report": list(fR.samples), "select": list(fS.samples)}
if os.path.exists(f"{lab.root}/data/mac/neighbour_test/cases.jsonl"):
    held["neighbour slice"] = lab.data("mac:neighbour_test:test", n=600)
held["Mac windows"] = lab.data("mac:screen2ax_task:test", n=120)
if os.path.exists(f"{lab.root}/benchdata/pointing/macsim_dev_s1/cases.jsonl"):
    held["macsim dev"] = lab.data("gen:benchdata/pointing/macsim_dev_s1", n=600)
if SMOKE:
    held = {k: v[:10] for k, v in held.items()}
hit = lambda it: J.score([it])["hit"] >= 0.5


def held_out(label):
    t = time.time()
    row = {k: J.score(v) for k, v in held.items()}
    can = lab.canary(lab.B, tag=f"029:{TAG}:{label}")["all"]
    print("%-22s %s   canary %s   [%.0f s]" % (label, "   ".join("%s %.1f%% (within 20 px %.1f%%)" % (k, 100 * v["hit"], 100 * v.get("within20", 0)) for k, v in row.items()),
                                              can, time.time() - t), flush=True)
    return {"label": label, "canary": can, **{k: {"hit": v["hit"], "within20": v.get("within20")} for k, v in row.items()}}


def packs_of(items):
    by = collections.defaultdict(list)
    for it in items:
        by[it["path"]].append(it)
    out = []
    for v in by.values():
        side = rng.choice((1280, 896))
        out += [[dict(it, max_side=side) for it in v[i:i + 5]] for i in range(0, len(v), 5)]
    rng.shuffle(out)
    return out


out = {"tag": TAG, "passes": [], "pool": POOL, "steps": STEPS}
first = held_out("start")
out["start"] = first
good = None
anchors = list(mix); rng.shuffle(anchors)
for p in range(PASSES):
    t = time.time()
    pool = cands[p * POOL:(p + 1) * POOL]
    if len(pool) < POOL // 2:
        print("no fresh pool left", flush=True)
        break
    hits = {it["id"]: hit(it) for it in pool}
    by = collections.defaultdict(lambda: [0, 0])
    for it in pool:
        by[klass(it)][0] += 1; by[klass(it)][1] += hits[it["id"]]
    misses = [it for it in pool if not hits[it["id"]]]
    reward = 1 - len(misses) / len(pool)
    keep = [it for it in pool if hits[it["id"]]][:len(misses)]
    DOUBLE = ("neighbour", "position", "same_name")       # the neighbour-type classes count twice
    MIXX = globals().get("MIX29", 1)                     # ordinary mix cases per miss
    slice_ = misses + [it for it in misses if klass(it) in DOUBLE] + keep + anchors[p * MIXX * len(misses):(p + 1) * MIXX * len(misses)]
    print("pass %d: pool of %d fresh cases: reward %.1f%%   by class: %s   -> slice: %d misses (%d neighbour, counted twice), %d hits, %d mix cases   [%.0f s]" % (
        p + 1, len(pool), 100 * reward, "   ".join("%s %.1f%% of %d" % (k, 100 * v[1] / v[0], v[0]) for k, v in sorted(by.items())),
        len(misses), sum(klass(it) in DOUBLE for it in misses), len(keep), len(anchors[p * MIXX * len(misses):(p + 1) * MIXX * len(misses)]),
        time.time() - t), flush=True)
    res = J.train(packs_of(slice_), STEPS, total=STEPS * PASSES, lr_scales=LRS, lr_head=LRH, digits=0.0, seed=29 + p)
    flipped = sum(hit(it) for it in misses)
    row = held_out("after pass %d" % (p + 1))
    row.update({"pass": p + 1, "reward_before": reward, "by_class": {k: v[1] / v[0] for k, v in by.items()}, "misses": len(misses),
                "flipped": flipped, "reward_after_on_pool": (len(pool) - len(misses) + flipped) / len(pool)})
    out["passes"].append(row)
    print("pass %d: of its %d misses %d now hit (%.1f%%): reward on that pool %.1f%% -> %.1f%%" % (
        p + 1, len(misses), flipped, 100 * flipped / max(1, len(misses)), 100 * reward, 100 * row["reward_after_on_pool"]), flush=True)
    bad = row["report"]["hit"] < first["report"]["hit"] - globals().get("DROP29", 0.0101) or row["canary"]["tf_exact"] < 0.90
    if bad and not SMOKE:
        print("pass %d: report fell more than a point under the start or the canary is under 0.90: stopping%s" % (
            p + 1, "; the state after the last good pass is put back" if good else "; no good pass to go back to (the start pair's files are the last good state)"), flush=True)
        if good:
            for g, v in zip(J.gains, good["gains"]):
                g.data.copy_(v.to(g.device))
            J.head.load_state_dict(good["head"])
        break
    good = {"gains": [g.detach().cpu().clone() for g in J.gains], "head": copy.deepcopy(J.head.state_dict()), "pass": p + 1}
    if not SMOKE:
        torch.save({"spec": J.spec, "steps": J.steps, "head": J.head.state_dict(), "gains": [g.detach().cpu() for g in J.gains]},
                   f"{lab.dir}/ckpt/joint018_{TAG}_s{J.steps}.pt")
        json.dump(out, open(f"{lab.dir}/exp029_{TAG}.json", "w"), indent=1)
print("029 TABLE %s" % TAG)
print("  pass  reward before  after (same pool)  report  neighbour slice  Mac windows  canary   (macsim dev: %s)" % " -> ".join(
    "%.1f%%" % (100 * r["macsim dev"]["hit"]) for r in [first] + out["passes"] if "macsim dev" in r))
print("  start        -              -           %5.1f%%      %5.1f%%        %5.1f%%     %.2f" % (
    100 * first["report"]["hit"], 100 * first.get("neighbour slice", {"hit": 0})["hit"], 100 * first["Mac windows"]["hit"], first["canary"]["tf_exact"]))
for r in out["passes"]:
    print("  %4d     %5.1f%%         %5.1f%%         %5.1f%%      %5.1f%%        %5.1f%%     %.2f" % (
        r["pass"], 100 * r["reward_before"], 100 * r["reward_after_on_pool"], 100 * r["report"]["hit"],
        100 * r.get("neighbour slice", {"hit": 0})["hit"], 100 * r["Mac windows"]["hit"], r["canary"]["tf_exact"]), flush=True)
J.close()
print("029 done", flush=True)
