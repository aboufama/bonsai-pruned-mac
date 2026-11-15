# Experiment 021: skip the blank areas of a screenshot (weightlab/sparse.py).
#
# On the target Mac the cost of an answer is the number of tokens the language model reads
# (about 105 per second), and a 1280 px screenshot is about 1,000 image tokens, one per 32x32 px
# cell. Here the tokens of flat cells are removed before the language model runs, every other
# token keeping its position, and three things are measured for each flatness rule and threshold:
# the share of image tokens dropped, the teacher-forced p_hit, and the seconds per pass.
#
# Stages, run in the order listed in STAGES21 (arguments after a colon, comma separated):
#   check              nothing dropped == the normal forward pass; greedy loop == model.generate
#   sweep:RULES        every threshold of each rule on select, report and Mac app windows
#   generate:SETS      generated answers (hits) for the settings in GEN21 on those sets
#   controls           same number of tokens dropped at random; positions not passed
#   timing             seconds per pass of the language model, each setting in TIME21 run back to
#                      back with nothing dropped on the same case, so drift cancels
#   adapt:RULE@THR     tune only the multipliers (TaskTuner, the usual loss) with that rule dropping
#                      tokens during training, measure again, then put the weights back
#   macshare           how much each rule removes on real Mac screenshots (data/mac/*); needs no
#                      model, only the processor, so it also runs outside the lab session
# Settings: STAGES21, THRS21, GEN21, CTRL21, NMAC21, UPDATES21, LR21, LAYERS21.
# Run experiments/_prelude.py first.
import importlib
import json
import os
import random
import time

import torch
import weightlab.sparse as sparse

importlib.reload(sparse)

STAGES = globals().get("STAGES21", ("check", "sweep:win3,win5", "generate:report", "controls", "sweep:cell,nbr",
                                    "generate:select,mac", "macshare"))
THRS = globals().get("THRS21", (1, 4, 8, 16, 32, 64))
GEN = globals().get("GEN21", (("none", 0), ("win3", 1), ("win3", 8), ("win3", 16), ("win3", 32), ("win3", 64),
                              ("win5", 8), ("win5", 32), ("cell", 8), ("nbr", 8)))
CTRL = globals().get("CTRL21", (("win3", 8), ("win3", 32)))
TIME = globals().get("TIME21", (("win3", 1), ("win3", 8), ("win3", 32), ("win5", 1), ("win5", 8), ("win5", 32),
                                ("cell", 8), ("bands", 8)))
NMAC = globals().get("NMAC21", 250)   # screenshots per folder of data/mac for `macshare`
UPDATES = globals().get("UPDATES21", 400)            # `adapt`: optimiser updates of two cases each
LR = globals().get("LR21", 2e-4)
LAYERS = globals().get("LAYERS21", list(range(0, 32)))
MAC_TPS = 105.0                       # prompt tokens per second measured on the M4 MacBook
OUT = globals().get("OUT21", f"{lab.dir}/exp021_skip_blank.json")
R21 = globals().get("R21") or {"sweep": {}, "controls": {}, "generate": {}, "adapted": {}}
P21 = globals().get("P21") or {}
NEED_MODEL = any(s.split(":")[0] != "macshare" for s in STAGES)


def save():
    json.dump(R21, open(OUT, "w"), indent=1)


# ---------------------------------------------------------------- every sample, prepared once
if NEED_MODEL:
    model = lab.B
    sets21 = {"select": fS.samples, "report": fR.samples, "mac": lab.data("mac:screen2ax_task:test", n=120)}
    with torch.inference_mode():
        for name, samples in sets21.items():
            if name not in P21:
                t0 = time.time()
                P21[name] = [sparse.prepare(lab, model, it) for it in samples]
                n_img = [p.img_idx.numel() for p in P21[name]]
                vis = [p.vision_seconds for p in P21[name][3:]]
                print("%-7s %3d cases prepared in %.0f s: %.0f image tokens on average (%d to %d), sequence %.0f, "
                      "vision tower %.3f s" % (name, len(samples), time.time() - t0, sum(n_img) / len(n_img), min(n_img),
                                               max(n_img), sum(p.emb.shape[1] for p in P21[name]) / len(samples),
                                               sum(vis) / len(vis)), flush=True)
                R21.setdefault("sets", {})[name] = {"n": len(samples), "image_tokens": sum(n_img) / len(n_img),
                                                    "sequence": sum(p.emb.shape[1] for p in P21[name]) / len(samples),
                                                    "vision_seconds": sum(vis) / len(vis)}


def keeps_for(name, rule, thr):
    return [sparse.keep_mask(p, thr, rule) if rule != "none" else None for p in P21[name]]


def measure(rule, thr, positions="original", keeps=None, label=None):
    """One setting on all three sets; prints one line and returns {set: result}."""
    row = {}
    for name, samples in sets21.items():
        row[name] = sparse.score(lab, model, samples, P21[name], (keeps or {}).get(name) or keeps_for(name, rule, thr), positions)
    base = R21["sweep"].get("none@0")
    parts = []
    for name in sets21:
        r = row[name]
        if base:                                      # paired difference to nothing dropped, with its standard error
            d = torch.tensor(r["per_sample"]["p"]) - torch.tensor(base[name]["per_sample"]["p"])
            r["delta"], r["delta_se"] = d.mean().item(), (d.std() / len(d) ** 0.5).item()
            r["speedup"] = base[name]["seconds"] / r["seconds"]
        parts.append("%s %.3f%s" % (name, r["p_hit"], (" (%+.3f +-%.3f)" % (r["delta"], r["delta_se"])) if base else ""))
    allr = list(row.values())
    n = sum(r["n"] for r in allr)
    drop = sum(r["dropped"] * r["n"] for r in allr) / n
    secs = sum(r["seconds"] * r["n"] for r in allr) / n
    toks = sum(r["tokens"] * r["n"] for r in allr) / n
    print("%-14s dropped %4.1f%% (%2.0f..%3.0f)  %s  | %.4f s/pass  %4.0f tokens  ~%.1f s on the Mac" % (
        label or f"{rule}@{thr}", 100 * drop, 100 * min(r["dropped_min"] for r in allr), 100 * max(r["dropped_max"] for r in allr),
        "  ".join(parts), secs, toks, toks / MAC_TPS + 0.4), flush=True)
    return row


# ---------------------------------------------------------------- 1. correctness
def stage_check():
    with torch.inference_mode():
        worst = {"use_cache=False": 0.0, "default": 0.0}
        top_same, n_pos = 0, 0
        cases = sets21["select"][:16] + sets21["report"][:8] + sets21["mac"][:8]
        for it in cases:
            inputs, n_prompt = lab._inputs(model, it, lab.answer_text(it))
            prep = sparse.prepare_inputs(model, inputs, n_prompt)
            mine, idx = sparse.logits(model, prep)
            mine = mine[0].float()
            assert idx.numel() == inputs["input_ids"].shape[1]
            for label, kw in (("use_cache=False", {"use_cache": False}), ("default", {})):
                ref = model(**inputs, **kw).logits[0].float()
                worst[label] = max(worst[label], (mine - ref).abs().max().item())
            top_same += int((mine.argmax(-1) == ref.argmax(-1)).sum()); n_pos += mine.shape[0]
        print("nothing dropped vs the normal forward pass, %d cases, logits at every position:" % len(cases))
        for label, v in worst.items():
            print("   largest absolute difference (reference called with %s): %g" % (label, v))
        print("   same top token at %d of %d positions" % (top_same, n_pos))
        R21["check"] = {"cases": len(cases), "max_abs_diff": worst, "top_same": top_same, "positions": n_pos}

        # the greedy loop against model.generate, nothing dropped
        same, n = 0, 0
        for it, prep in list(zip(sets21["select"], P21["select"]))[:40]:
            inputs, n_prompt = lab._inputs(model, it)
            out = model.generate(**inputs, max_new_tokens=16, do_sample=False, eos_token_id=lab._stop_ids())
            ref = lab.processor.decode(out[0, n_prompt:], skip_special_tokens=True)
            mine = sparse.generate(lab, model, prep)
            same += ref.strip() == mine.strip(); n += 1
            if ref.strip() != mine.strip():
                print("   differs:", repr(ref), "vs", repr(mine))
        print("greedy loop, nothing dropped: same text as model.generate on %d of %d cases" % (same, n), flush=True)
        R21["check"]["generate_same"] = [same, n]


# ---------------------------------------------------------------- 2. the sweep
def stage_sweep(rules):
    with torch.inference_mode():
        for p in P21["select"][:8]:                   # warm the GPU before anything is timed
            sparse.answer_logits(model, p)
    R21["sweep"]["none@0"] = measure("none", 0)
    print("   (the lab's own caches say select %.3f, report %.3f)" % (fS.baseline["p_hit"], fR.baseline["p_hit"]))
    for rule in rules:
        for thr in THRS:
            R21["sweep"][f"{rule}@{thr}"] = measure(rule, thr)
        save()
    R21["sweep"]["none@0 (again)"] = measure("none", 0, label="none (again)")


# ---------------------------------------------------------------- 3. controls
def stage_controls():
    for rule, thr in CTRL:
        rng = random.Random(21)
        rand = {}
        for name in sets21:
            rand[name] = []
            for k in keeps_for(name, rule, thr):
                flat = torch.ones(k.numel(), dtype=torch.bool, device=k.device)
                gone = rng.sample(range(k.numel()), int((~k).sum()))
                flat[torch.tensor(gone, dtype=torch.long, device=k.device)] = False
                rand[name].append(flat.view_as(k))
        R21["controls"][f"random like {rule}@{thr}"] = measure(rule, thr, keeps=rand, label=f"random~{rule}@{thr}")
        R21["controls"][f"{rule}@{thr} sequential positions"] = measure(rule, thr, positions="sequential", label=f"{rule}@{thr} seq.pos")
    R21["controls"]["none, sequential positions"] = measure("none", 0, positions="sequential", label="none seq.pos")


# ---------------------------------------------------------------- 4. generated answers
def generated(rule, thr, names, row=None, label=None):
    """Greedy answers for one setting on the named sets; prints one line."""
    row = {} if row is None else row
    for name in names:
        samples = sets21[name]
        hits, first, total, answers = 0, [], [], []
        with torch.inference_mode():
            for it, prep, keep in zip(samples, P21[name], keeps_for(name, rule, thr)):
                text, a, b = sparse.generate(lab, model, prep, keep, timed=True)
                hits += sparse.hit(it, text); first.append(a); total.append(b); answers.append(text.strip())
        row[name] = {"acc": hits / len(samples), "hits": hits, "n": len(samples), "prompt_seconds": sum(first) / len(first),
                     "answer_seconds": sum(total) / len(total), "answers": answers}
    print("%-14s generated answers on target: %s   | prompt %.3f s, whole answer %.3f s" % (
        label or f"{rule}@{thr}", "  ".join("%s %d/%d = %.1f%%" % (n, row[n]["hits"], row[n]["n"], 100 * row[n]["acc"]) for n in names),
        sum(row[n]["prompt_seconds"] for n in names) / len(names), sum(row[n]["answer_seconds"] for n in names) / len(names)), flush=True)
    return row


def stage_generate(names):
    for rule, thr in GEN:
        generated(rule, thr, names, R21["generate"].setdefault(f"{rule}@{thr}", {}))
        save()


# ---------------------------------------------------------------- 4a. timing
def stage_timing():
    """Per case: one pass with nothing dropped, then one per setting, timed on the GPU with a
    synchronise before and after. Reported: mean seconds and the ratio of the totals."""
    settings = [("none", 0)] + list(TIME)
    out = R21.setdefault("timing", {})
    with torch.inference_mode():
        for p in P21["select"][:8]:
            sparse.answer_logits(model, p)
        for name in sets21:
            keeps = {s: keeps_for(name, *s) for s in settings}
            secs, toks = {s: [] for s in settings}, {s: [] for s in settings}
            for k, prep in enumerate(P21[name]):
                for s in settings:
                    _, n, dt = sparse.answer_logits(model, prep, keeps[s][k], timed=True)
                    secs[s].append(dt); toks[s].append(n)
            base = sum(secs[("none", 0)])
            for s in settings:
                out.setdefault(f"{s[0]}@{s[1]}", {})[name] = {"seconds": sum(secs[s]) / len(secs[s]), "tokens": sum(toks[s]) / len(toks[s]),
                                                              "speedup": base / sum(secs[s])}
    for s in settings:
        row = out[f"{s[0]}@{s[1]}"]
        print("%-10s %s" % (f"{s[0]}@{s[1]}", "   ".join("%s %.4f s (x%.2f, %4.0f tokens)" % (n, row[n]["seconds"], row[n]["speedup"], row[n]["tokens"]) for n in sets21)), flush=True)


# ---------------------------------------------------------------- 4b. a short adaptation
def stage_adapt(arg):
    """Multipliers only, the usual pointing loss, but the model reads the reduced sequence while
    it trains. Scores afterwards are printed against the untrained model with nothing dropped.
    The tuned multipliers are saved and the session's weights are put back as they were."""
    from weightlab.tune import TaskTuner
    rule, thr = arg.split("@")
    thr = int(thr)
    key = f"{rule}@{thr}"
    T = TaskTuner(lab, LAYERS, scales=True)
    snap0 = T.snapshot()
    t0 = time.time()
    try:
        with sparse.dropping(thr, rule):
            r = T.train(mix, UPDATES, lr_scales=LR, warmup=30, accumulate=2, ema=0.98, seed=21, report_every=50)
        minutes = (time.time() - t0) / 60
        print("adapted with %s dropped: %d updates of 2 cases, layers %d..%d, lr %g, loss %.3f -> %.3f  [%.1f min]" % (
            key, UPDATES, LAYERS[0], LAYERS[-1], LR, r["loss_start"], r["loss_end"], minutes), flush=True)
        torch.save(T.snapshot(), f"{lab.dir}/ckpt/exp021_drop_{rule}{thr}.pt")
        out = R21.setdefault("adapted", {}).setdefault(key, {})
        out.update(train=r, minutes=minutes, updates=UPDATES, lr=LR, layers=[LAYERS[0], LAYERS[-1]], rows={}, generate={})
        for rr, tt in [("none", 0), (rule, thr)] + [(rule, t) for t in (1, 8, 16, 32) if t != thr] + [("cell", 8)]:
            out["rows"][f"{rr}@{tt}"] = measure(rr, tt, label=f"[A] {rr}@{tt}")
            save()
        for rr, tt in (("none", 0), (rule, thr)):
            out["generate"][f"{rr}@{tt}"] = generated(rr, tt, ["report"], label=f"[A] {rr}@{tt}")
            save()
    finally:
        T.restore(snap0)
        if lab.stack and lab.stack[-1].startswith("tune:"):
            lab.stack.pop()
        print("weights put back; active edits:", lab.stack, flush=True)


# ---------------------------------------------------------------- 5. real Mac screenshots
def stage_macshare():
    """Share of image tokens each rule removes on screenshots from every folder of data/mac
    (shown at 1280 px like everything else). Only the processor is used."""
    if lab.processor is None:
        from transformers import AutoProcessor
        lab.processor = AutoProcessor.from_pretrained(lab.paths["B"])

    class Cpu:
        device = "cpu"

    out = R21.setdefault("macshare", {})
    settings = [(rule, thr) for rule in sparse.RULES for thr in THRS]
    for folder in sorted(os.listdir(f"{lab.root}/data/mac")):
        if not os.path.exists(f"{lab.root}/data/mac/{folder}/cases.jsonl"):
            continue
        seen, items = set(), []
        for it in lab.data(f"mac:{folder}", n=8 * NMAC):
            if it["path"] not in seen:
                seen.add(it["path"]); items.append(it)
        items = items[::max(1, len(items) // NMAC)][:NMAC]
        shares, n_img, t0 = {s: [] for s in settings}, [], time.time()
        for it in items:
            inputs, _ = lab._inputs(Cpu, it)
            lo, hi = sparse.cell_minmax(inputs)
            n_img.append(lo.shape[0] * lo.shape[1])
            for rule, thr in settings:
                shares[(rule, thr)].append(sparse.blank(lo, hi, thr, rule).float().mean().item())
        row = {"screenshots": len(items), "image_tokens": sum(n_img) / len(n_img)}
        for (rule, thr), v in shares.items():
            v = sorted(v)
            row[f"{rule}@{thr}"] = {"mean": sum(v) / len(v), "median": v[len(v) // 2], "p10": v[len(v) // 10], "p90": v[(9 * len(v)) // 10]}
        out[folder] = row
        print("%-20s %3d screenshots, %4.0f image tokens  [%.0f s]" % (folder, len(items), row["image_tokens"], time.time() - t0))
        for rule in ("win3", "win5", "cell", "bands"):
            print("   %-5s removes  %s" % (rule, "   ".join("thr %d: %2.0f%% (%2.0f..%2.0f)" % (
                thr, 100 * row[f"{rule}@{thr}"]["mean"], 100 * row[f"{rule}@{thr}"]["p10"], 100 * row[f"{rule}@{thr}"]["p90"]) for thr in THRS)), flush=True)
        save()


for stage in STAGES:
    kind, _, arg = stage.partition(":")
    t0 = time.time()
    if kind == "check":
        stage_check()
    elif kind == "sweep":
        stage_sweep(arg.split(",") if arg else list(sparse.RULES))
    elif kind == "controls":
        stage_controls()
    elif kind == "generate":
        stage_generate(arg.split(",") if arg else list(sets21))
    elif kind == "timing":
        stage_timing()
    elif kind == "adapt":
        stage_adapt(arg)
    elif kind == "macshare":
        stage_macshare()
    else:
        raise ValueError(stage)
    save()
    print("--- %s done in %.0f s" % (stage, time.time() - t0), flush=True)
print("021 done:", OUT)
