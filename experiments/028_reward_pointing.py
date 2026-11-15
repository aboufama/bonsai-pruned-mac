# Experiment 028 (the research pod, 15 Nov 04:56): reward fine-tuning
# of the 9B's WRITTEN pointing answers, against plain supervised training on the same cases.
#
# Reward arm, per round: for each case of a fresh pool the model writes K28 answers at temperature TEMP28.
# Reward of an answer: 1 inside the box, else exp(-distance / SIGMA28) with the distance to the box in
# pixels of the screenshot at a 1280 px long side (so a near miss still earns something). The update
# goes toward the rewarded samples: the training target of the case is the best sample itself when it is
# inside the box (the model's own way of hitting it), and otherwise that sample pulled into the box (the
# nearest point of the box shrunk by 15% per side), with the case counted twice. Then UPD28 updates of
# the 014 recipe (multipliers of layers 4..31 and the head) on those targets plus as many ordinary mix
# cases as anchors.
# Supervised arm: the model is put back to the start and trained on the same cases, the same number of
# times, with the usual target (the box centre) and the same anchors.
# After every round, both arms: generated answers on report (158), on the held-out neighbour slice (150),
# on a fixed probe of 200 training-distribution cases, select teacher-forced, canary.
# Settings: K28, TEMP28, SIGMA28, CASES28 (pool per round), ROUNDS28, UPD28, LR28, TAG28, SMOKE28.
import json
import math
import os
import random
import re
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab.tune import TaskTuner

SMOKE = globals().pop("SMOKE28", None)
K, TEMP, SIGMA = globals().get("K28", 3), globals().get("TEMP28", 0.8), globals().get("SIGMA28", 30.0)
CASES, ROUNDS, UPD = (12, 1, 6) if SMOKE else (globals().get("CASES28", 300), globals().get("ROUNDS28", 4), globals().get("UPD28", 250))
LR, ACC, TAG = globals().get("LR28", 1e-4), 2, globals().get("TAG28", "reward_9b") + ("_smoke" if SMOKE else "")
if "mix" not in globals() or "fS" not in globals():
    raise RuntimeError("run the prelude first")
rng = random.Random(28)
pool = [it for it in mix]
rng.shuffle(pool)
probe, pool = pool[:16 if SMOKE else 200], pool[200:]
held = {"report": list(fR.samples)[:8 if SMOKE else None], "probe (training kind)": probe}
if os.path.exists(f"{lab.root}/data/mac/neighbour_test/cases.jsonl"):
    _all = lab.data("mac:neighbour_test:test", n=600)
    held["neighbour slice"] = _all[::4][:8 if SMOKE else 150]
nums = lambda text: [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)][:2]


def reward(it, p):
    if len(p) < 2:
        return 0.0
    w, h = it["size"]
    k = 1280 / max(w, h)
    b = it["box1000"]
    d = math.hypot(max(b[0] - p[0], 0, p[0] - b[2]) * w * k / 1000, max(b[1] - p[1], 0, p[1] - b[3]) * h * k / 1000)
    return 1.0 if d == 0 else math.exp(-d / SIGMA)


@torch.inference_mode()
def samples_of(it):
    inputs, n_prompt = lab._inputs(lab.B, it)
    out = []
    for _ in range(K):
        o = lab.B.generate(**inputs, max_new_tokens=16, do_sample=True, temperature=TEMP, top_p=1.0, top_k=0, eos_token_id=lab._stop_ids())
        out.append(nums(lab.processor.decode(o[0, n_prompt:], skip_special_tokens=True)))
    return out


def measure(label):
    t, row = time.time(), {"label": label}
    for key, items in held.items():
        row[key] = lab.score(lab.B, items, tag=f"028:{TAG}:{label}:{key}")["acc"]
    a = fS.evaluate(4, tag=f"028:{TAG}:{label}:select"); fS.discard()
    row["select_tf"] = a["p_hit"]
    row["canary"] = lab.canary(lab.B, tag=f"028:{TAG}:{label}")["all"]
    print("%-26s generated on target: %s   select (teacher-forced) %.3f   canary %s   [%.0f s]" % (
        label, "   ".join("%s %.1f%%" % (k, 100 * row[k]) for k in held), a["p_hit"], row["canary"], time.time() - t), flush=True)
    return row


T28 = TaskTuner(lab, list(range(4, 32)), scales=True, head=True)
start28 = T28.snapshot()
out = {"tag": TAG, "k": K, "temperature": TEMP, "sigma": SIGMA, "cases": CASES, "rounds": ROUNDS, "updates": UPD, "lr": LR, "rows": []}
out["rows"].append(measure("start"))
plan = []                                                # per round: (cases with multiplicity, reward targets, anchors)
for r in range(ROUNDS):                                  # ---- reward arm
    cases = pool[r * CASES:(r + 1) * CASES]
    anchors = pool[ROUNDS * CASES + r * CASES:ROUNDS * CASES + (r + 1) * CASES]
    t, items_r, mult, rs, inside = time.time(), [], [], [], 0
    for it in cases:
        ss = samples_of(it)
        best = max(ss, key=lambda p: reward(it, p))
        rb = reward(it, best)
        rs.append(sum(reward(it, p) for p in ss) / K)
        b = it["box1000"]
        if rb == 1.0:
            inside += 1
            tgt, m = (round(best[0]), round(best[1])), 1
        else:
            if len(best) < 2:
                best = list(it["target"])
            mx, my = 0.15 * (b[2] - b[0]), 0.15 * (b[3] - b[1])
            tgt, m = (round(min(max(best[0], b[0] + mx), b[2] - mx)), round(min(max(best[1], b[1] + my), b[3] - my))), 2
        items_r += [dict(it, target=tgt)] * m
        mult.append(m)
    plan.append((cases, mult, anchors))
    print("reward round %d: %d cases, %d answers each at temperature %.1f: mean reward %.3f, a sample inside the box for %.1f%% of cases   [%.0f s]" % (
        r + 1, len(cases), K, TEMP, sum(rs) / len(rs), 100 * inside / len(cases), time.time() - t), flush=True)
    train = items_r + list(anchors)
    rng.shuffle(train)
    T28.train([train[i % len(train)] for i in range(UPD * ACC)], UPD, lr_scales=LR, warmup=20, accumulate=ACC, ema=0.98, seed=28 + r,
              report_every=50, offset=r * UPD, total=ROUNDS * UPD, rewarm=15)
    row = measure("reward arm, round %d" % (r + 1)); row["mean_reward"] = sum(rs) / len(rs); row["inside"] = inside / len(cases)
    out["rows"].append(row)
    if not SMOKE:
        torch.save(T28.snapshot(), f"{lab.dir}/ckpt/tune_{TAG}_reward_r{r + 1}.pt")
        json.dump(out, open(f"{lab.dir}/exp028_{TAG}.json", "w"), indent=1)
T28.restore(start28)                                     # ---- supervised arm: same cases, same counts, box centres
rs2 = random.Random(2828)
for r, (cases, mult, anchors) in enumerate(plan):
    train = [it for it, m in zip(cases, mult) for _ in range(m)] + list(anchors)
    rs2.shuffle(train)
    T28.train([train[i % len(train)] for i in range(UPD * ACC)], UPD, lr_scales=LR, warmup=20, accumulate=ACC, ema=0.98, seed=28 + r,
              report_every=50, offset=r * UPD, total=ROUNDS * UPD, rewarm=15)
    out["rows"].append(measure("supervised arm, round %d" % (r + 1)))
    if not SMOKE:
        torch.save(T28.snapshot(), f"{lab.dir}/ckpt/tune_{TAG}_supervised_r{r + 1}.pt")
        json.dump(out, open(f"{lab.dir}/exp028_{TAG}.json", "w"), indent=1)
if SMOKE:
    T28.restore(start28)
print("028 done%s" % (" (smoke: nothing saved, start state back)" if SMOKE else ""), flush=True)
