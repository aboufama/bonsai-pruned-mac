# Experiment 022, trial T4: coordinates written coarse to fine.
#
# Today the answer is "[x, y]": all of x, then all of y. Here it is six digit tokens: hundreds of
# x, hundreds of y, tens of x, tens of y, units of x, units of y (same 0..999 grid, no brackets
# or commas). Each pair of digits picks a cell of a 10 x 10 grid inside the previous cell, so
# every step is a small local choice in two dimensions. The prompt's format sentence asks for
# exactly this (weightlab/tune.py: C2F_PROMPT; the "[-1,-1] if infeasible" sentence is dropped
# with the brackets).
#
# Targets at each of the six positions, given the digits already written (the box centre's):
#   a) every digit for which some grid point of the box is still reachable, all equally
#      (the loss is -log of the probability mass on them, as tune.py does for "[x, y]")
#   b) the same digits, each weighted by the share of the box that lies in its cell: the exact
#      marginal of a uniform distribution over the box (the loss is the cross-entropy to it)
#
# Run, for each variant: from v3-gentle, lane 3's gentle recipe (multipliers and small parts, no
# codes, warm-up 100) over layers 4..31, 1,500 steps on the standard mix with the new format for
# every pointing sample. Every 500 steps: the probability of an acceptable digit at each of the
# six positions on select and report, and generated answers on report parsed back to (x, y).
# Reference in the usual format at the same point: lane 3b (the same recipe on "[x, y]") reached
# select 0.867 at step 1000.
exec(open(f"{lab.root}/experiments/022_extreme_common.py").read())
assert x22_base_score is not None, "run 022_extreme_t0_baseline_bias.py first"
import weightlab.core as core22
import weightlab.e2e as e2e22
import weightlab.tune as tune22

LO, HI = 4, 31
STEPS, EVERY = globals().get("STEPS22", 1500), globals().get("EVERY22", 500)
VARIANTS = globals().get("VARIANTS22", ("a", "b"))
PLACES = ("hundreds x", "hundreds y", "tens x", "tens y", "units x", "units y")
ck = f"{lab.dir}/ckpt"
_old_prompt = core22.PROMPT

_ids = lab.processor.tokenizer(tune22.c2f_text(x22_sel[0]), add_special_tokens=False)["input_ids"]
assert len(_ids) == 6 and all(15 <= i <= 24 for i in _ids), ("the six digits are not six digit tokens", _ids)


def c2f_on(weighted):
    core22.PROMPT = tune22.C2F_PROMPT                     # lab._inputs reads the module's PROMPT
    lab.answer_text = tune22.c2f_text
    e2e22.answer_targets = lambda it, tgt: tune22.answer_targets_c2f(it, tgt, weighted)
    e2e22.point_loss = tune22.point_loss_soft


def c2f_off():
    core22.PROMPT = _old_prompt
    lab.__dict__.pop("answer_text", None)
    e2e22.answer_targets, e2e22.point_loss = tune22.answer_targets, tune22.point_loss


@torch.no_grad()
def c2f_score(samples, E=None):
    """Teacher-forced on the box centre's six digits. Per position, the mean probability (over
    the ten digit tokens) of an acceptable digit; p_hit, the mean probability that all six are."""
    pos, hit = [0.0] * 6, 0.0
    for it in samples:
        if E is not None:
            logits = E.forward(it, hint_every=10 ** 6, use_hints=False)[1][0][0]
        else:
            inputs, n_prompt = lab._inputs(lab.B, it, tune22.c2f_text(it))
            logits = lab.B(**inputs).logits[0, n_prompt - 1:-1]
            lab.forward_passes += 1
        probs = torch.softmax(logits[:6].float()[:, 15:25], dim=-1)
        cells, p = tune22.c2f_cells(it), 1.0
        for k in range(6):
            good = sum(probs[k, d].item() for d in range(10) if cells[k][d] > 0)
            pos[k] += good
            p *= good
        hit += p
    n = len(samples)
    return {"p_hit": hit / n, "pos": [v / n for v in pos]}


@torch.inference_mode()
def c2f_generate(samples):
    points, texts = [], []
    for it in samples:
        inputs, n_prompt = lab._inputs(lab.B, it)
        out = lab.B.generate(**inputs, max_new_tokens=16, do_sample=False, eos_token_id=lab._stop_ids())
        lab.forward_passes += 1
        text = lab.processor.decode(out[0, n_prompt:], skip_special_tokens=True).strip()
        texts.append(text)
        points.append(tune22.c2f_point(text))
    return points, texts


def places(r):
    return "  ".join("%s %.3f" % (n, v) for n, v in zip(PLACES, r["pos"]))


# the baseline in its own format, per digit place (both coordinates together), for the comparison
if "t4_base" not in globals():
    t4_base = {"select": lab.digits(lab.B, x22_sel, tag="022x:T4:base:select"), "report": lab.digits(lab.B, x22_rep, tag="022x:T4:base:report")}
    print("v3-gentle in the usual format: " + "   ".join("%s p_hit %.3f hundreds %.3f tens %.3f units %.3f" % (
        k, v["p_hit"], v["p_ok_hundreds"], v["p_ok_tens"], v["p_ok_units"]) for k, v in t4_base.items()), flush=True)
    x22_notes.append({"T4_baseline_usual_format": t4_base}); x22_save()

t4_res = globals().get("t4_res", {})
for variant in VARIANTS:
    if variant in t4_res:
        continue
    t, out = time.time(), {"variant": variant, "rows": []}
    name = {"a": "all acceptable digits equal", "b": "digits weighted by box share"}[variant]
    c2f_on(weighted=(variant == "b"))
    try:
        E = BlockTrainer(lab, LO, HI, teacher=None)
        E.open(lr_codes=2e-3, lr_scales=1e-4, lr_fp=2e-5, codes=False)
        a = c2f_score(x22_sel, E)
        print("T4%s (%s): before any step, new format: select p_hit %.3f   %s" % (variant, name, a["p_hit"], places(a)), flush=True)
        out["rows"].append({"step": 0, "select": a})
        for r in range(0, STEPS, EVERY):
            res = E.train(x22_packs, min(EVERY, STEPS - r), total_steps=STEPS, task=1.0, hint=0.0, warmup=100, final=0.2,
                          seed=10, report_every=100)
            a, b = c2f_score(x22_sel, E), c2f_score(x22_rep, E)
            x22_light_save(f"{ck}/x22_t4{variant}_step{E.steps_done}.safetensors", range(LO, HI + 1), E)
            out["rows"].append({"step": E.steps_done, "select": a, "report": b, "train": res})
            print("T4%s step %4d: select %.3f (%s)\n               report %.3f (%s)   train loss %.2f / %.2f  [%.0f min]" % (
                variant, E.steps_done, a["p_hit"], places(a), b["p_hit"], places(b), res["first_question"], res["later_questions"],
                (time.time() - t) / 60), flush=True)
        E.close()
        del E
        torch.cuda.empty_cache()
        # generated answers per checkpoint, with the block closed (ordinary ternary layers)
        for row in out["rows"][1:]:
            x22_light_restore(f"{ck}/x22_t4{variant}_step{row['step']}.safetensors")
            pts, texts = c2f_generate(x22_rep)
            row["gen_hits"], row["gen_n"], row["gen_answers"] = x22_hits(pts, x22_rep), len(x22_rep), texts
            row["unparsed"] = sum(p is None for p in pts)
            c = lab.canary(lab.B, tag=f"022x:T4{variant}:{row['step']}")["all"]
            row["canary_exact"], row["canary_nll"] = c["tf_exact"], c["nll"]
            closed = c2f_score(x22_sel)
            print("T4%s step %4d, block closed: select %.3f   generated on report %d/%d (%.1f%%), %d answers not six digits   canary %.2f / %.3f" % (
                variant, row["step"], closed["p_hit"], row["gen_hits"], row["gen_n"], 100 * row["gen_hits"] / row["gen_n"], row["unparsed"],
                row["canary_exact"], row["canary_nll"]), flush=True)
            x22_rows.append({"trial": "T4", "setting": "coarse-to-fine, %s, step %d" % (name, row["step"]), "select": row["select"]["p_hit"],
                             "report": row["report"]["p_hit"], "gen_hits": row["gen_hits"], "gen_n": row["gen_n"], "gen_answers": texts,
                             "canary_exact": row["canary_exact"], "canary_nll": row["canary_nll"], "positions_select": row["select"]["pos"],
                             "positions_report": row["report"]["pos"], "minutes": round((time.time() - t) / 60, 1)})
        t4_res[variant] = out
        x22_notes.append({"T4": out}); x22_save()
    finally:
        c2f_off()
        if getattr(globals().get("E"), "training", False):
            E.close()
    x22_back_to_baseline(f"after T4{variant}")
print("T4 done", flush=True)
