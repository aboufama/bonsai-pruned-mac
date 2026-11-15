# Experiment 022 (extreme trials): what the four trials share. One way of measuring, an exact
# restore of the baseline, and the block trainer stretched over all 32 layers.
#
# Baseline: the original pack plus the v3-gentle patch. Every trial is measured with
#   select / report   teacher-forced p_hit on the two fixed eighths of ScreenSpot-v2 (1280 px)
#   generated         answers written by the model on the report set (1280 px, standard prompt), hits
#   canary            50 short text questions (tf_exact, nll)
# and, where asked (EXTRA), the same at 896 px and on 200 Mac app windows (Screen2AX, reserved apps).
# Rows are appended to lab/exp022_extreme.json as they are measured.
import json
import os
import re
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab import mixes, state
from weightlab.core import Tensors
from weightlab.distill import _Stop, _cast
from weightlab.e2e import BlockTrainer
from weightlab.ternary import GROUP, fwht

X22_PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-gentle.patch.safetensors"
X22_OUT = f"{lab.dir}/exp022_extreme.json"
X22_SKIP = (".scales", ".gate", ".latent", ".log_gain")


@torch.no_grad()
def x22_snapshot(codes=False):
    """Everything a trial may change: the multipliers of every ternary matrix, the small
    full-precision parts of the language model, the vision tower and its merger."""
    snap = {"scales": {n: m.scales.data.clone() for n, m in lab.tern.items()}, "codes": {},
            "params": {n: p.data.clone() for n, p in lab.B.named_parameters()
                       if not n.endswith(X22_SKIP) and "embed_tokens" not in n}}
    if codes:
        snap["codes"] = {n: m.codes.clone() for n, m in lab.tern.items()}
    return snap


@torch.no_grad()
def x22_restore(snap):
    params = dict(lab.B.named_parameters())
    for n, m in lab.tern.items():
        m.scales.data.copy_(snap["scales"][n])
        if n in snap["codes"]:
            m.codes.copy_(snap["codes"][n])
        m.invalidate()
    for n, v in snap["params"].items():
        params[n].data.copy_(v.to(params[n].dtype))
    torch.cuda.empty_cache()


def x22_save():
    json.dump({"rows": x22_rows, "notes": x22_notes}, open(X22_OUT, "w"), indent=1)


def x22_points(answers):
    out = []
    for text in answers:
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
        out.append((nums[0], nums[1]) if len(nums) >= 2 else None)
    return out


def x22_hits(points, samples):
    return sum(p is not None and it["box1000"][0] <= p[0] <= it["box1000"][2] and it["box1000"][1] <= p[1] <= it["box1000"][3]
               for p, it in zip(points, samples))


def x22_measure(trial, setting, started=None, extra=False, keep=True):
    """One row of the table for the model as it is now. `started`: time.time() when the trial's
    work for this setting began (the row's minutes include the measuring)."""
    t, B = time.time(), lab.B
    tag = f"022x:{trial}:{setting}"
    row = {"trial": trial, "setting": setting, "stack": list(lab.stack)}
    row["select"] = lab.digits(B, x22_sel, tag=tag + ":select")["p_hit"]
    row["report"] = lab.digits(B, x22_rep, tag=tag + ":report")["p_hit"]
    g = lab.score(B, x22_rep, tag=tag + ":generated")
    row["gen_hits"], row["gen_n"], row["gen_answers"] = x22_hits(x22_points(g["answers"]), x22_rep), len(x22_rep), g["answers"]
    c = lab.canary(B, tag=tag)["all"]
    row["canary_exact"], row["canary_nll"] = c["tf_exact"], c["nll"]
    line = "%-4s %-44s select %.3f  report %.3f  generated %d/%d (%.1f%%)  canary %.2f / %.3f" % (
        trial, setting, row["select"], row["report"], row["gen_hits"], row["gen_n"], 100 * row["gen_hits"] / row["gen_n"],
        row["canary_exact"], row["canary_nll"])
    if extra:
        row["select_896"] = lab.digits(B, x22_sel896, tag=tag + ":select896")["p_hit"]
        row["report_896"] = lab.digits(B, x22_rep896, tag=tag + ":report896")["p_hit"]
        g = lab.score(B, x22_rep896, tag=tag + ":generated896")
        row["gen_hits_896"] = x22_hits(x22_points(g["answers"]), x22_rep896)
        row["mac"] = lab.digits(B, x22_mac, tag=tag + ":mac")["p_hit"]
        g = lab.score(B, x22_mac, tag=tag + ":generated_mac")
        row["mac_gen_hits"], row["mac_n"] = x22_hits(x22_points(g["answers"]), x22_mac), len(x22_mac)
        line += "\n     896 px: select %.3f  report %.3f  generated %d/%d   Mac windows: %.3f, generated %d/%d" % (
            row["select_896"], row["report_896"], row["gen_hits_896"], row["gen_n"], row["mac"], row["mac_gen_hits"], row["mac_n"])
    row["minutes"] = round((time.time() - (started or t)) / 60, 1)
    print(line + "   [%.1f min]" % row["minutes"], flush=True)
    if keep:
        x22_rows.append(row)
        x22_save()
    return row


def x22_back_to_baseline(label=""):
    """Restore the baseline and check that the teacher-forced numbers are the baseline's again."""
    x22_restore(x22_base)
    lab.stack[:] = [f"patch:{os.path.basename(X22_PATCH)}"]
    a = lab.digits(lab.B, x22_sel, tag="022x:restore:select")["p_hit"]
    b = lab.digits(lab.B, x22_rep, tag="022x:restore:report")["p_hit"]
    ok = abs(a - x22_base_score[0]) < 5e-4 and abs(b - x22_base_score[1]) < 5e-4
    print("baseline restored %s: select %.4f  report %.4f  (baseline %.4f / %.4f)  %s" % (
        label, a, b, x22_base_score[0], x22_base_score[1], "OK" if ok else "MISMATCH"), flush=True)
    x22_notes.append({"restore": label, "select": a, "report": b, "ok": ok})
    x22_save()
    if not ok:
        raise RuntimeError("the baseline did not come back; restart the session")


# ---------------------------------------------------------------------------------------------
class X22Trainer(BlockTrainer):
    """The block trainer with a block that may start at layer 0, and with a path for gradients
    down to the vision tower.

    The stock trainer reads the arguments each layer type needs off the frozen layers below the
    block (run without gradients), so it cannot start at layer 0 and nothing below the block can
    learn. Here one pass runs the model up to the first full-attention layer with layers 0..2
    switched to pass-through: it yields the state entering layer 0 and both layer types'
    arguments at the cost of the vision tower only. Layers 0..lo-1 then run frozen. With `vision`
    (a list of trainable vision parameters) both steps keep their graph, so the task loss
    reaches the vision tower through the frozen layers below the block."""

    def __init__(self, lab, lo=0, hi=None, vision=None):
        super().__init__(lab, lo, len(lab.B.model.language_model.layers) - 1 if hi is None else hi, teacher=None)
        self.vision = vision
        self.first_full = self.types.index("full_attention")
        self.D.states = self._states

    def _states(self, it, upto=None, text_weight=1.0):
        items = it if isinstance(it, (list, tuple)) else [it]
        inputs, spans = self.lab._inputs_multi(self.B, items)
        self.D.last = (inputs, spans)
        kw, grabbed, was = {}, {}, torch.is_grad_enabled()

        def first(module, args, kwargs):
            kw.setdefault(self.types[0], dict(kwargs))
            grabbed["h"] = args[0]

        def stop(module, args, kwargs):
            kw.setdefault(self.types[self.first_full], dict(kwargs))
            raise _Stop()

        hooks = [self.layers[0].register_forward_pre_hook(first, with_kwargs=True),
                 self.layers[self.first_full].register_forward_pre_hook(stop, with_kwargs=True)]
        for i in range(self.first_full):
            self.layers[i].forward = lambda hidden_states, *a, **k: hidden_states
        torch.set_grad_enabled(was and bool(self.vision) and self.training)
        try:
            try:
                self.B(**inputs, use_cache=False)
            except _Stop:
                pass
            finally:
                for h in hooks:
                    h.remove()
                for i in range(self.first_full):
                    del self.layers[i].forward
            assert len(kw) == len(set(self.types)), kw.keys()
            x = grabbed["h"]
            for i in range(self.lo):                       # frozen layers below the block
                x = self.layers[i](x, **kw[self.types[i]])
        finally:
            torch.set_grad_enabled(was)
        self.lab.forward_passes += 1
        return kw, [x], torch.ones(x.shape[:2], device=x.device)


@torch.no_grad()
def x22_light_save(path, layer_ids, E=None):
    """Multipliers and small full-precision parts of these layers (codes never change in these
    trials, so they are left out: a few hundred MB instead of several GB). With `E` (an open
    trainer) the values are what closing the block now would write."""
    from safetensors.torch import save_file
    os.makedirs(os.path.dirname(path), exist_ok=True)
    t = {}
    for i in layer_ids:
        prefix = f"model.language_model.layers.{i}."
        for n, m in lab.tern.items():
            if n.startswith(prefix):
                t[n + ".scales"] = m.live_scales().float().cpu()
        for n, p in lab.B.model.language_model.layers[i].named_parameters():
            if not n.endswith(("latent", "log_gain", "scales", "gate")):
                t[prefix + n] = p.data.to(torch.bfloat16).cpu()
    save_file(t, path)
    return path


@torch.no_grad()
def x22_light_restore(path):
    """Load a file written by x22_light_save (or vision tensors saved under their own names)."""
    from safetensors.torch import load_file
    params = dict(lab.B.named_parameters())
    for key, v in load_file(path).items():
        if key.endswith(".scales"):
            m = lab.tern[key[:-7]]
            m.scales.data.copy_(v.to(m.scales.device))
            m.invalidate()
        else:
            params[key].data.copy_(v.to(params[key].device, params[key].dtype))
    torch.cuda.empty_cache()


def x22_tune(steps=400, warmup=100, lr_scales=1e-4, lr_fp=2e-5, tag="tune", every=200):
    """Lane 3's recipe (multipliers and small full-precision parts, no codes, task signal only,
    warm-up, cosine to 0.2) over layers 0..31, on the standard training mix. Leaves the result
    in the model as ordinary ternary layers."""
    t = time.time()
    E = X22Trainer(lab)
    E.open(lr_codes=2e-3, lr_scales=lr_scales, lr_fp=lr_fp, codes=False)
    s0 = E.score(x22_sel)["p_hit"]
    print(f"{tag}: block 0..31 open, select before any step {s0:.3f}", flush=True)
    for r in range(0, steps, every):
        res = E.train(x22_packs, min(every, steps - r), total_steps=steps, task=1.0, hint=0.0, warmup=warmup, final=0.2,
                      seed=10, report_every=100)
        print("%s: step %d  select %.3f  train loss first question %.2f, later %.2f  [%.1f min]" % (
            tag, E.steps_done, E.score(x22_sel)["p_hit"], res["first_question"], res["later_questions"], (time.time() - t) / 60), flush=True)
    E.close()
    lab.stack[-1] = f"022x:{tag}:{steps}"
    del E
    torch.cuda.empty_cache()


# ---------------------------------------------------------------------------------------------
if not globals().get("x22_ready"):
    t0 = time.time()
    lab.B
    x22_orig = x22_snapshot(codes=True)                      # PrismML's pack as shipped
    print("patch applied:", state.apply_patch(lab, X22_PATCH), os.path.basename(X22_PATCH), flush=True)
    lab.stack[:] = [f"patch:{os.path.basename(X22_PATCH)}"]
    for _m in lab.tern.values():
        # every matrix is folded afresh from its codes and multipliers. The matrices the patch does
        # not touch otherwise keep the dense copy from the converted checkpoint, which differs in
        # the last bfloat16 bit and moves the scores by 0.0006: enough to hide whether a restore
        # really brought the baseline back.
        _m.invalidate()
    x22_base = x22_snapshot(codes=True)
    for _n in list(x22_base["codes"]):                       # keep codes only where the patch changed them
        if torch.equal(x22_base["codes"][_n], x22_orig["codes"][_n]):
            del x22_base["codes"][_n], x22_orig["codes"][_n]
    print("matrices whose codes the patch changed:", len(x22_base["codes"]), "of", len(lab.tern), flush=True)
    torch.cuda.empty_cache()
    x22_sel, x22_rep = lab.data("ssv2", mod=(8, 1)), lab.data("ssv2", mod=(8, 5))
    x22_sel896, x22_rep896 = lab.data("ssv2", mod=(8, 1), max_side=896), lab.data("ssv2", mod=(8, 5), max_side=896)
    x22_mac = lab.data("mac:screen2ax_task:test", n=200)
    _, x22_packs, x22_counts = mixes.build(lab)
    x22_rows, x22_notes = [], []
    if os.path.exists(X22_OUT):
        _old = json.load(open(X22_OUT))
        x22_rows, x22_notes = _old["rows"], _old["notes"]
    x22_base_score = None
    x22_ready = True
    print("022 extreme trials ready: %d select, %d report, %d Mac windows, training mix %s in %d packs  [%.0f s]" % (
        len(x22_sel), len(x22_rep), len(x22_mac), x22_counts, len(x22_packs), time.time() - t0), flush=True)

# every trial file starts from the baseline, whatever the job before it left behind
if x22_base_score is not None:
    if getattr(globals().get("E"), "training", False):
        E.close()
    lab.__dict__.pop("answer_text", None)
    x22_back_to_baseline("at the start of a trial file")
