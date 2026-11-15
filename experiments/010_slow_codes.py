# Experiment 010: slow retraining of the ternary values in layers 4..19 (weightlab/e2e.py).
#
# What experiments 005-008 established: tuning multipliers alone takes Bonsai from 0.33 to about
# 0.67 on real screens (parent 0.85, UI-Venus 0.93); restarts must be gentle; 32 screens are too
# few to steer by. Here the ternary codes of the damaged block are opened as well, with a low
# learning rate so that a code only flips after its gradient has pointed the same way for
# hundreds of screens. Multipliers and small parts move slowly alongside. The signal is the task
# only (answer digits that land in the box), through Bonsai's own frozen top layers.
#
# Training screens: generated ones plus real macOS data with boxes; AgentNet (click points, the
# pointer is often visible near the target) is kept to a minority share. ScreenSpot-v2 is only
# used to measure, and the cases that overlap public Mac training data are excluded.
#
# Settings: STEPS10, EVERY10, LR_CODES10, LR_SCALES10, LR_FP10, WARM10, MIX10, TAG10, LO10, HI10, CODES10,
# KEEP10 (experiment 022's JSON: Mac cases UI-Venus points outside the box are left out), TEACHER10 and
# TEACH10 (experiment 022's digit distributions and the weight of the cross-entropy to them),
# SIZES10 (train each screenshot at a random long side from this list), SIZE_SCORES10 (also score
# select and report at these long sides, before and at every checkpoint; the best checkpoint is
# then the one with the highest mean select score over those sizes), MAC_SIZES10 (of those long sides,
# the ones at which the Mac app windows are scored too; 1280 always is). A long side repeated in
# SIZES10 is drawn that much more often.
# DROP10 (a JSON list of case ids left out of the Mac folders of the mix), EXTRA10 (extra Mac sets
# added to the training packs: [(lab.data name, cases or None for all, cap per app or None, repeats)];
# their packs are always full, KMAX questions per screenshot), EXTRA_SHARE10 (the share of training
# steps the extra packs get; the usual packs are cut down to fit; None = whatever their number gives),
# EMPH10 (True: cases with a small target or a button role are drawn three times as often),
# EXTRA_SCORES10 ({label: lab.data name}: scored before training and at every checkpoint, split by
# the cases' kind when they carry one).
import json
import os
import random
import shutil
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab.e2e import BlockTrainer

LO, HI = globals().get("LO10", 4), globals().get("HI10", 19)
STEPS = globals().get("STEPS10", 3000)
EVERY = globals().get("EVERY10", 250)
LR_CODES = globals().get("LR_CODES10", 2e-3)
LR_SCALES = globals().get("LR_SCALES10", 1e-4)
LR_FP = globals().get("LR_FP10", 2e-5)
WARM = globals().get("WARM10", 100)
TAG = globals().get("TAG10", f"codes_lr{LR_CODES:g}_s{STEPS}")
SCORE_N = globals().get("SCORE_N10", None)          # score on the first N select screens only (pre-flight runs)
KMAX = globals().get("KMAX10", 5)                   # at most this many questions per screenshot in one step
SIZES = globals().get("SIZES10", None)              # e.g. (640, 768, 896, 1024, 1280); None = always 1280
SIZE_SCORES = globals().get("SIZE_SCORES10", None)  # e.g. (1280, 896, 640)
MAC_SIZES = globals().get("MAC_SIZES10", None)      # e.g. (896,)
SIDE_RANK = globals().get("SIDE_RANK10", None)      # low-rank full-precision side paths beside the block's ternary matrices (weightlab/sidepath.py)
SIDE_LR = globals().get("SIDE_LR10", 1e-4)
if globals().get("side10") is not None:              # side paths left by an earlier run in this session
    side10.remove()
side10 = None
TEACHER = globals().get("TEACHER10", None)          # lab/venus_teacher.npz (experiment 022): UI-Venus's digit distributions per case
TEACH = globals().get("TEACH10", 0.0)               # weight of the cross-entropy to them (cases where its point is inside the box)
KEEP = globals().get("KEEP10", None)                # lab/venus_clean.json (experiment 022): Mac cases UI-Venus puts outside their box are left out
DROP = globals().get("DROP10", None)                # JSON list of case ids to leave out of the Mac folders
EXTRA = globals().get("EXTRA10", None)              # [(name, cases, cap, repeats)]
EXTRA_SHARE = globals().get("EXTRA_SHARE10", None)  # e.g. 0.5
EXTRA_SCORES = globals().get("EXTRA_SCORES10", None)  # e.g. {"fable test": "mac:fable_teacher:test"}
MIX = globals().get("MIX10", [                      # (lab.data name, cases, cap per app)
    ("gen:benchdata/pointing/train_s303", 9000, None),
    ("gen:benchdata/pointing/train_s202", 3000, None),
    ("mac:os_atlas_mac:train", 6000, None),
    ("mac:screen2ax_tree:train", 6000, 400),
    ("mac:scalecua_mac:train", 1400, None),
    ("mac:showui_desktop_mac:train", 1037, None),
    ("mac:agentnet:train", 1500, None),
])

# ---- free what this run does not need: the old 32-screen sets, the teacher block, layer-0 caches
for name in ("fB", "fH"):
    globals().pop(name, None)
for key in [k for k in lab.models if k not in ("B",)]:
    del lab.models[key]
for obj in list(globals().values()):                 # older trainer objects still hold the teacher's layers
    for holder in (obj, getattr(obj, "D", None)):
        if hasattr(holder, "t_layers") and not isinstance(holder, type):
            holder.t_layers = {}
excl = lab.excluded()
for f in (fS, fR):
    n = f.drop(excl)
    for c in f.cache:
        if LO > 0:                                   # a block that starts at layer 0 restarts from the layer-0 boundary
            c["hidden"].pop(0, None)
    if n:
        print(f"dropped {n} ScreenSpot-v2 cases that overlap public Mac training data; {len(f.samples)} left")
import gc
gc.collect(); torch.cuda.empty_cache()

# ---- training mix
def usable(text):
    """Drop labels that are not instructions a person could follow: icon-font glyphs (private-use
    characters), no letters at all, or absurd lengths. Mostly raw accessibility labels."""
    return (2 <= len(text) <= 200 and any(c.isalpha() for c in text)
            and not any(0xE000 <= ord(c) <= 0xF8FF for c in text))


mix, counts = [], {}
for name, n, cap in MIX:
    base = name.split(":")[1] if name.startswith("gen:") else f"data/mac/{name.split(':')[1]}"
    if not os.path.exists(f"{lab.root}/{base}/cases.jsonl"):
        print("not on disk yet, skipped:", name)
        continue
    items = lab.data(name, n=int(n * (3 if cap else 1.3)))
    if cap:
        per, kept = {}, []
        for it in items:
            per[it["group"]] = per.get(it["group"], 0) + 1
            if per[it["group"]] <= cap:
                kept.append(it)
        items = kept
    seen, uniq = set(), []
    for it in items:                               # evenly spaced selection can repeat on small sets
        if it["id"] not in seen and usable(it["instruction"]):
            seen.add(it["id"]); uniq.append(it)
    uniq = uniq[:n]
    if DROP and name.startswith("mac:"):
        if "drop10" not in globals() or drop10[0] != DROP:
            drop10 = (DROP, set(json.load(open(DROP))))
        before = len(uniq)
        uniq = [it for it in uniq if it["id"] not in drop10[1]]
        print("  %-34s %d of %d cases left out (on the list of %d bad source cases)" % (name, before - len(uniq), before, len(drop10[1])))
    if KEEP and name.startswith("mac:"):           # generator cases have exact boxes and always stay
        if "keep10" not in globals() or keep10[0] != KEEP:
            keep10 = (KEEP, json.load(open(KEEP)))
        before = len(uniq)
        uniq = [it for it in uniq if keep10[1].get(f"{name}|{it['id']}", {"in": True})["in"]]
        print("  %-34s %d of %d cases left out (UI-Venus points outside the labelled box), %d not judged" % (
            name, before - len(uniq), before, sum(f"{name}|{it['id']}" not in keep10[1] for it in uniq)))
    if TEACHER and TEACH > 0:
        if "teach10" not in globals() or teach10[0] != TEACHER:
            import numpy as np
            _z = np.load(TEACHER, allow_pickle=False)
            _marks = json.load(open(TEACHER[:-4] + ".json"))
            teach10 = (TEACHER, {k: p for k, p in zip(_z["keys"].tolist(), _z["p"])}, _marks)
        with_teacher = 0
        for i, it in enumerate(uniq):
            key = f"{name}|{it['id']}"
            mark = teach10[2].get(key)
            if mark and mark.get("in") and mark.get("x") and key in teach10[1]:
                # a copy: the sets other experiments share stay without the teacher's numbers
                uniq[i] = dict(it, teacher={"x": mark["x"], "y": mark["y"], "p": teach10[1][key].astype("float32")})
                with_teacher += 1
        print("  %-34s %d of %d cases carry UI-Venus's digit distributions" % (name, with_teacher, len(uniq)))
    counts[name] = len(uniq)
    mix += uniq
# several questions about one screenshot go into one step (one conversation), 1 to KMAX of them
rng = random.Random(10)
by_image = {}
for it in mix:
    by_image.setdefault(it["path"], []).append(it)
packs = []
for items in by_image.values():
    rng.shuffle(items)
    i = 0
    while i < len(items):
        k = rng.randint(1, KMAX)
        packs.append(items[i:i + k])
        i += k
rng.shuffle(packs)
# ---- extra sets (EXTRA10): their own packs, always KMAX questions on a screenshot, added to the list
# the trainer draws from. The usual packs (`packs`, which other experiments share) are not changed.
extra_packs, extra_counts = [], {}
for name, n, cap, repeats in (EXTRA or ()):
    if not os.path.exists(f"{lab.root}/data/mac/{name.split(':')[1]}/cases.jsonl"):
        print("not on disk, skipped:", name)
        continue
    seen, uniq, per, missing = set(), [], {}, 0
    for it in lab.data(name, n=n or 20000):
        if it["id"] in seen or not usable(it["instruction"]):
            continue
        seen.add(it["id"])
        if not os.path.exists(it["path"]):
            missing += 1
            continue
        per[it["group"]] = per.get(it["group"], 0) + 1
        if cap and per[it["group"]] > cap:
            continue
        uniq.append(dict(it, path=os.path.normpath(it["path"])))      # a copy; the same screenshot gets one path
    if n:
        uniq = uniq[:n]
    extra_counts[name] = len(uniq)
    re10 = random.Random(1011)
    for _ in range(repeats or 1):
        by_extra = {}
        for it in uniq:
            by_extra.setdefault(it["path"], []).append(it)
        for items in by_extra.values():
            re10.shuffle(items)
            extra_packs += [items[i:i + KMAX] for i in range(0, len(items), KMAX)]
    print("extra set %-28s %d cases on %d screenshots, %d time(s) -> %d packs so far%s" % (
        name, len(uniq), len({it["path"] for it in uniq}), repeats or 1, len(extra_packs),
        "   (%d cases left out: screenshot not on this machine)" % missing if missing else ""), flush=True)
train_list = packs
if extra_packs:
    base_packs = packs
    if EXTRA_SHARE:
        base_packs = packs[:min(len(packs), round(len(extra_packs) * (1 - EXTRA_SHARE) / EXTRA_SHARE))]
    train_list = base_packs + extra_packs
    print("training list: %d usual packs + %d extra packs; the extra ones get %.0f%% of the steps, so in %d steps each extra case is seen about %.2f times" % (
        len(base_packs), len(extra_packs), 100 * len(extra_packs) / len(train_list), STEPS,
        STEPS * len(extra_packs) / len(train_list) * (sum(len(p) for p in extra_packs) / len(extra_packs)) / max(1, sum(extra_counts.values()))), flush=True)
if globals().get("EMPH10"):                          # small targets and buttons three times as often (lanes/_emphasis.py)
    exec(open(f"{lab.root}/experiments/lanes/" + globals().get("EMPH_FILE10", "_emphasis.py")).read())
    train_list = emphasise(train_list)
train_packs = train_list
if SIZES:
    # one long side per pack (a pack is one screenshot, seen once per run); copies, so the sets
    # other experiments share stay at 1280
    rs = random.Random(1010)
    train_packs = [[dict(it, max_side=side) for it in pack] for pack in train_list for side in [rs.choice(SIZES)]]
    print("training long sides:", {side: sum(p[0]["max_side"] == side for p in train_packs) for side in sorted(set(SIZES))})
print("training mix:", counts, "total", len(mix), "cases on", len(by_image), "screenshots, in", len(packs),
      "steps' worth of packs (%.1f questions per step on average)" % (len(mix) / len(packs)))

out = {"tag": TAG, "steps": STEPS, "lr_codes": LR_CODES, "lr_scales": LR_SCALES, "lr_fp": LR_FP, "mix": counts,
       "extra": extra_counts, "extra_packs": len(extra_packs),
       "packs": len(packs), "kmax": KMAX, "sizes": list(SIZES or []), "rows": []}


def fast_line(label):
    a, b = fS.evaluate(LO, tag=f"010:{TAG}:{label}:select"), fR.evaluate(LO, tag=f"010:{TAG}:{label}:report")
    fS.discard(); fR.discard()
    out["rows"].append({"label": label, "select": a, "report": b})
    print("%-40s select %.3f (hundreds %.3f tens %.3f)   report %.3f (hundreds %.3f tens %.3f)" % (
        label, a["p_hit"], a["p_ok_hundreds"], a["p_ok_tens"], b["p_hit"], b["p_ok_hundreds"], b["p_ok_tens"]), flush=True)
    return a["p_hit"]


start_score = fast_line("start")
E = BlockTrainer(lab, LO, HI, teacher=None)
ck = f"{lab.dir}/ckpt"
start_path = E.D.save(range(LO, HI + 1), f"{ck}/qat010_{TAG}_start.safetensors")
best_path, last_path = f"{ck}/qat010_{TAG}_best.safetensors", f"{ck}/qat010_{TAG}_last.safetensors"
E.open(lr_codes=LR_CODES, lr_scales=LR_SCALES, lr_fp=LR_FP, codes=globals().get("CODES10", True))
if SIDE_RANK:
    from weightlab.sidepath import SidePaths
    side10 = SidePaths(lab, range(LO, HI + 1), rank=SIDE_RANK)
    E.opt.add_param_group({"params": side10.params(), "lr": SIDE_LR})
    E.base["groups"].append(SIDE_LR)
    print("side paths: rank %d beside %d ternary matrices of layers %d..%d: %.1f million parameters, %.0f MB in float32 (%.0f MB in float16)" % (
        SIDE_RANK, len(side10.A), LO, HI, side10.count() / 1e6, side10.count() * 4 / 1e6, side10.count() * 2 / 1e6), flush=True)
score_set = fS.samples[:SCORE_N] if SCORE_N else fS.samples
mac_set = lab.data("mac:screen2ax_task:test", n=globals().get("MAC_N10", 80))[:SCORE_N or None]   # real Mac app windows, reserved apps
# the two yardsticks at other long sides (same screens, shrunk further)
size_sets = {side: (lab.data("ssv2", mod=(8, 1), max_side=side)[:SCORE_N or None],
                    lab.data("ssv2", mod=(8, 5), max_side=side)[:SCORE_N or None]) for side in (SIZE_SCORES or ())}


mac_size_sets = {side: lab.data("mac:screen2ax_task:test", n=globals().get("MAC_N10", 80), max_side=side)[:SCORE_N or None]
                 for side in (MAC_SIZES or ()) if side in size_sets}


def size_table(label, select_1280=None):
    """Written-answer score on select and report at every long side, with the block as it is now.
    `select_1280`: the select score at 1280 if it was just measured (the same screens)."""
    t, row = time.time(), {}
    for side, (a_set, b_set) in size_sets.items():
        row[side] = {"select": select_1280 if (side == 1280 and select_1280 is not None) else E.score(a_set),
                     "report": E.score(b_set)}
    for side, m_set in mac_size_sets.items():
        row[side]["mac"] = E.score(m_set)
    print("%-11s by long side:  " % label + "   ".join("%d px select %.3f report %.3f" % (
        side, r["select"]["p_hit"], r["report"]["p_hit"]) for side, r in row.items())
          + "".join("   Mac windows at %d px %.3f" % (side, row[side]["mac"]["p_hit"]) for side in mac_size_sets)
          + "   [%.0f s]" % (time.time() - t), flush=True)
    return row


def size_mean(row):
    return sum(r["select"]["p_hit"] for r in row.values()) / len(row)


# ---- extra score sets (EXTRA_SCORES10), split by the cases' kind
extra_sets = {}
for label10, name in (EXTRA_SCORES or {}).items():
    if not os.path.exists(f"{lab.root}/data/mac/{name.split(':')[1]}/cases.jsonl"):
        print("not on disk, not scored:", name)
        continue
    seen, by_kind = set(), {}
    for it in lab.data(name, n=20000):
        if it["id"] not in seen and os.path.exists(it["path"]):
            seen.add(it["id"])
            by_kind.setdefault(it.get("kind") or "all", []).append(it)
    extra_sets[label10] = {k: v[:SCORE_N or None] for k, v in sorted(by_kind.items())}


def extra_table(label):
    """Written-answer score on every extra set, per kind, with the block as it is now."""
    row = {}
    for name, by_kind in extra_sets.items():
        t = time.time()
        row[name] = {k: dict(E.score(v), n=len(v)) for k, v in by_kind.items()}
        n_all = sum(r["n"] for r in row[name].values())
        row[name]["_all"] = {"p_hit": sum(r["p_hit"] * r["n"] for r in row[name].values()) / n_all, "n": n_all}
        print("%-11s %s:  " % (label, name) + "   ".join("%s %.3f (%d)" % (k, r["p_hit"], r["n"]) for k, r in row[name].items() if k != "_all")
              + "   all %.3f (%d)   [%.0f s]" % (row[name]["_all"]["p_hit"], n_all, time.time() - t), flush=True)
    return row


s0 = E.score(score_set)
m0 = E.score(mac_set)
print("Mac app windows (%d cases) before any step: %.3f" % (len(mac_set), m0["p_hit"]), flush=True)
print("block open, before any step: select %.3f on %d screens (the closed block scored %.3f on all %d)" % (
    s0["p_hit"], len(score_set), start_score, len(fS.samples)), flush=True)
out["before"] = {"select": s0, "mac": m0}
sz0 = size_table("before", s0) if size_sets else None
if sz0:
    out["rows"].append({"label": "before, by long side", "sizes": sz0})
    out["before"]["sizes"] = sz0
if extra_sets:
    out["before"]["extra"] = extra_table("before")
best, best_step, low = (size_mean(sz0) if sz0 else s0["p_hit"]), 0, 0
started = time.time()
for r in range(0, STEPS, EVERY):
    res = E.train(train_packs, min(EVERY, STEPS - r), total_steps=STEPS, task=1.0, hint=0.0, warmup=WARM, final=0.2, seed=10, report_every=50, teach=TEACH)
    if TEACH > 0:
        print("  teacher term on %d of %d answers this round (%d digit positions)" % (res["taught_answers"], res["answers"], res["taught_positions"]), flush=True)
    a = E.score(score_set)
    mac = E.score(mac_set)
    flips = E.flips()
    if flips > 0:                                    # where the flipped codes are, by group of four layers
        try:
            _names = {id(m): n for n, m in lab.tern.items()}
            _grp = {}
            for m in E.mods:
                if m.latent is None:
                    continue
                g = int(_names[id(m)].split("layers.")[1].split(".")[0]) // 4
                c = _grp.setdefault(g, [0, 0])
                c[0] += int((m.hard_codes().to(torch.int8) != m.codes).sum()); c[1] += m.codes.numel()
            print("   codes flipped by layers: " + "   ".join("%d-%d %.3f%%" % (4 * g, 4 * g + 3, 100 * a / b) for g, (a, b) in sorted(_grp.items())), flush=True)
        except Exception as e:
            print("   (codes by layer group not available: %s)" % e, flush=True)
    E.checkpoint(last_path)
    if side10 is not None:
        side10.save(last_path.replace(".safetensors", "_side.safetensors"))
    sizes = size_table(f"step {E.steps_done}", a) if size_sets else None
    crit = size_mean(sizes) if sizes else a["p_hit"]
    mark = ""
    if crit > best:
        best, best_step, mark = crit, E.steps_done, "  <- best so far"
        shutil.copyfile(last_path, best_path)
        if side10 is not None:
            shutil.copyfile(last_path.replace(".safetensors", "_side.safetensors"), best_path.replace(".safetensors", "_side.safetensors"))
    out["rows"].append({"label": f"step {E.steps_done}", "step": E.steps_done, "select": a, "mac": mac, "flips": flips, "train": res})
    if sizes:
        out["rows"][-1]["sizes"] = sizes
    if extra_sets:
        out["rows"][-1]["extra"] = extra_table(f"step {E.steps_done}")
    print("step %5d: select %.3f (hundreds %.3f tens %.3f)   Mac windows %.3f   codes flipped %.3f%%   train loss: first question %.2f, later ones %.2f   [%.0f min]%s" % (
        E.steps_done, a["p_hit"], a["p_ok_hundreds"], a["p_ok_tens"], mac["p_hit"], 100 * flips, res["first_question"], res["later_questions"],
        (time.time() - started) / 60, mark), flush=True)
    json.dump(out, open(f"{lab.dir}/exp010_{TAG}.json", "w"), indent=1)
    low = low + 1 if a["p_hit"] < s0["p_hit"] - 0.05 else 0
    if low >= 2 and E.steps_done >= globals().get("STOPMIN10", 750):
        print("two checkpoints in a row more than 0.05 below the start: stopping early", flush=True)
        break
closed = E.close()
out["closed"] = closed
print("at the end: %.3f%% of the block's codes differ from the start" % (100 * closed["codes_changed_share"]))
E.D.restore(best_path if best_step else start_path)
if side10 is not None:
    side10.load(best_path.replace(".safetensors", "_side.safetensors")) if best_step else side10.zero()
lab.stack[-1] = f"qat010:{TAG}:best@{best_step}"
print(f"loaded the best checkpoint (step {best_step})")
fast_line(f"best checkpoint (step {best_step})")
out["best_step"] = best_step
out["best"] = dict(next((r for r in out["rows"] if r.get("step") == best_step), out["before"]), report=out["rows"][-1]["report"])
if size_sets:
    # generated answers (one look, the way experiment 013 measures) with the best checkpoint
    out["generated"] = {}
    for side, (a_set, b_set) in size_sets.items():
        g = lab.score(lab.B, b_set, tag=f"010:{TAG}:generated:report:{side}")
        out["generated"][side] = {k: v for k, v in g.items() if k != "answers"}
        print("generated answers, report set at %4d px: %5.1f%% of %d on target   median distance %.0f" % (
            side, 100 * g["acc"], len(b_set), g["median_dist"] or -1), flush=True)
out["canary"] = lab.canary(lab.B, tag=f"010:{TAG}")
print("canary:", out["canary"]["all"], "(original Bonsai: tf_exact 0.86, nll 0.074)")
json.dump(out, open(f"{lab.dir}/exp010_{TAG}.json", "w"), indent=1)
