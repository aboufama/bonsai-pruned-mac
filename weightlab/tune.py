"""Train parts of Bonsai on the pointing task itself, staying ternary.

`BlockDistiller` (distill.py) teaches layers to imitate a teacher's layers. `TaskTuner` instead
optimises the thing we measure: the probability that the answer lands inside the target box.
The whole model runs forward, the loss is read at the answer positions, and gradients reach
whichever parts were opened for training:

    scales   the per-group multipliers of the ternary matrices (1 per 128 weights; cheap, safe)
    codes    the ternary codes themselves, through latents (3.5 GB per layer while training)
    fp       the small full-precision parts of the chosen layers

The loss for one sample, with the box centre teacher-forced as the answer "[x, y]":
    at a digit position      -log( probability mass on digits that keep the point in the box )
    at any other position    -log( probability of the expected token )      (keeps the format)
This is the differentiable form of the lab's `miss_nll` score. Labels come free with generated
screens, so this needs no teacher model; an optional teacher adds a second term that pulls the
digit distributions toward the teacher's.
"""
import collections
import math
import random
import time

import torch

from . import chat
from .core import mem_available_gb, need_memory
from .ternary import TernaryLinear

DIGIT0 = 15                      # token ids 15..24 are the digits 0..9


def answer_targets(it, tgt):
    """For each answer position, the token ids that count as correct.

    Digits: every digit for which some completion of the lower digits lands inside the box
    (more significant digits taken from the box centre). Everything else: the expected token.
    """
    allowed = [[int(t)] for t in tgt.tolist()]
    pos = 1                                                # skip '['
    for axis, lo, hi in ((0, it["box1000"][0], it["box1000"][2]), (1, it["box1000"][1], it["box1000"][3])):
        s = str(it["target"][axis])
        for d in range(len(s)):
            ok = []
            for digit in range(10):
                head = s[:d] + str(digit)
                low, high = int(head + "0" * (len(s) - d - 1)), int(head + "9" * (len(s) - d - 1))
                if high >= lo and low <= hi:
                    ok.append(DIGIT0 + digit)
            allowed[pos + d] = ok or allowed[pos + d]
        pos += len(s) + 2
    return allowed


def teacher_targets(it):
    """Where a teacher's digit distributions apply to the label answer of `it`, and what they are.

    `it["teacher"]` = {"x": "448", "y": "381", "p": 6 x 10 probabilities}: the teacher's own greedy
    point as digit strings and, for each of its digits in written order (rows 0..2 for x, 3..5 for
    y), its probability over the ten digit tokens, read while it wrote that answer. The student is
    teacher-forced on the LABEL answer (the box centre), so a teacher row is used only where both
    models are conditioned on the same digits: the coordinate has the same number of digits in both
    answers and the teacher's digits before that place equal the label's. The first digit of a
    coordinate therefore always qualifies when the lengths match; later digits only while the two
    answers agree. (For y the earlier x digits may differ; the teacher's point is inside the box, so
    its x is an acceptable x.) Returns [(answer position, ten probabilities)]; the positions follow
    the "[x, y]" layout that `answer_targets` uses."""
    t = it.get("teacher")
    if not t:
        return []
    out, pos = [], 1                                       # skip '['
    for axis, key in ((0, "x"), (1, "y")):
        s, ts = str(it["target"][axis]), t[key]
        if len(ts) == len(s):
            for d in range(len(s)):
                if ts[:d] == s[:d]:
                    out.append((pos + d, t["p"][3 * axis + d]))
        pos += len(s) + 2
    return out


def teacher_loss(logits, it):
    """Cross-entropy between the teacher's digit distributions and the student's at the positions
    `teacher_targets` gives: -sum(w * log p) over the ten digit tokens, summed over positions
    (the same scale as `point_loss`). Returns (loss, number of positions); (0, 0) without a teacher."""
    slots = teacher_targets(it)
    if not slots:
        return 0.0, 0
    logp = torch.log_softmax(logits.float(), dim=-1)
    total = 0.0
    for p, w in slots:
        w = torch.as_tensor(w, device=logp.device, dtype=logp.dtype)
        total = total - (w / w.sum().clamp_min(1e-6) * logp[p, DIGIT0:DIGIT0 + 10]).sum()
    return total, len(slots)


def point_loss(logits, allowed):
    """Sum over answer positions of -log(probability mass on the allowed tokens)."""
    logp = torch.log_softmax(logits.float(), dim=-1)
    total = 0.0
    for p, ids in enumerate(allowed):
        if isinstance(ids, tuple) and ids[0] == "not":      # anything but this token
            total = total - torch.log1p(-logp[p, ids[1]].exp().clamp(max=1 - 1e-6))
        else:
            total = total - torch.logsumexp(logp[p, ids], dim=0)
    return total


# ---- coarse-to-fine coordinates (experiment 022, trial T4) -------------------------------------
# The answer is six digit tokens: hundreds of x, hundreds of y, tens of x, tens of y, units of x,
# units of y, on the same 0..999 grid. Each pair of digits picks a cell of a 10 x 10 grid inside
# the cell picked so far, so every step is a small local choice in two dimensions.
C2F_PROMPT = (
    "Output the center point of the position corresponding to the following instruction: \n"
    "{instruction}. \n\n"
    "The output should just be six digits: the hundreds digit of x, the hundreds digit of y, "
    "then the tens digits, then the units digits."
)
C2F_ORDER = ((0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2))      # (axis, digit place from the left) per position


def c2f_digits(it):
    """The box centre as two zero-padded three-digit strings (x, y), clamped to 0..999."""
    return tuple("%03d" % min(999, max(0, int(it["target"][a]))) for a in (0, 1))


def c2f_text(it):
    """The teacher-forced answer in coarse-to-fine order, e.g. centre (437, 582) -> '453872'."""
    s = c2f_digits(it)
    return "".join(s[a][d] for a, d in C2F_ORDER)


def c2f_point(text):
    """Six digits back to (x, y); None if the text holds fewer than six digits."""
    d = [c for c in text if c.isdigit()][:6]
    if len(d) < 6:
        return None
    return float(d[0] + d[2] + d[4]), float(d[1] + d[3] + d[5])


def c2f_cells(it):
    """Per answer position, for each of the ten digits: how many grid points of the target box
    are still reachable if that digit is written after the centre's digits so far. A digit is
    acceptable when the count is above zero; the counts, normalised, are the exact marginal of a
    uniform distribution over the box's grid points given what is already written."""
    out = []
    for axis, d in C2F_ORDER:
        s = c2f_digits(it)[axis]
        lo, hi = math.ceil(it["box1000"][axis] - 1e-9), math.floor(it["box1000"][axis + 2] + 1e-9)   # grid points inside the box
        lo, hi = max(lo, 0), min(hi, 999)
        width = 10 ** (2 - d)
        counts = []
        for digit in range(10):
            low = int(s[:d] + str(digit) + "0" * (2 - d))
            counts.append(max(0, min(hi, low + width - 1) - max(lo, low) + 1))
        out.append(counts)
    return out


def answer_targets_c2f(it, tgt, weighted=False):
    """`answer_targets` for the coarse-to-fine format (six digit tokens, see c2f_text).

    weighted=False: per position, the token ids of every acceptable digit (all count equally, as
    in `answer_targets`). weighted=True: per position ("soft", ids, weights) with the weight of a
    digit the share of the box that lies in its cell; use with `point_loss_soft`. A position with
    no acceptable digit (a box holding no grid point) falls back to the expected token."""
    allowed = [[int(t)] for t in tgt.tolist()]
    for p, counts in enumerate(c2f_cells(it)[:len(allowed)]):
        ids = [DIGIT0 + digit for digit in range(10) if counts[digit] > 0]
        if not ids:
            continue
        if weighted:
            total = float(sum(counts))
            allowed[p] = ("soft", ids, [counts[i - DIGIT0] / total for i in ids])
        else:
            allowed[p] = ids
    return allowed


def point_loss_soft(logits, allowed):
    """`point_loss`, plus positions given as ("soft", ids, weights): there the loss is the
    cross-entropy against the weights, -sum(w * log p), an exact target distribution instead of
    a set of equally good tokens."""
    logp = torch.log_softmax(logits.float(), dim=-1)
    total = 0.0
    for p, ids in enumerate(allowed):
        if isinstance(ids, tuple) and ids[0] == "soft":
            w = torch.tensor(ids[2], device=logp.device, dtype=logp.dtype)
            total = total - (w * logp[p, ids[1]]).sum()
        elif isinstance(ids, tuple) and ids[0] == "not":
            total = total - torch.log1p(-logp[p, ids[1]].exp().clamp(max=1 - 1e-6))
        else:
            total = total - torch.logsumexp(logp[p, ids], dim=0)
    return total


class TaskTuner:
    def __init__(self, lab, layers, scales=True, codes=False, fp=False, head=False, teacher=None):
        """layers: indices of language-model layers to open. head=True also opens the output head."""
        self.lab, self.B = lab, lab.B
        self.layer_ids = sorted(layers)
        self.opts = dict(scales=scales, codes=codes, fp=fp, head=head)
        self.T = lab.load(teacher) if teacher else None
        self.layers = list(self.B.model.language_model.layers)
        self.first = self.layer_ids[0] if self.layer_ids else len(self.layers)
        self.hist = []

    def _modules(self):
        mods = []
        for i in self.layer_ids:
            mods += [m for m in self.layers[i].modules() if isinstance(m, TernaryLinear)]
        if self.opts["head"]:
            mods.append(self.B.lm_head)
        return mods

    def train(self, samples, steps, lr_scales=1e-3, lr_codes=2e-3, lr_fp=1e-4, kd=0.0, seed=0, report_every=25,
              accumulate=1, warmup=0, ema=0.0, final=0.1, offset=0, total=None, rewarm=0):
        """`steps` optimiser updates, each on `accumulate` samples. Returns the mean loss over
        the first and last 25 updates and the number of codes changed.

        kd > 0     adds KL(teacher || student) over the ten digit tokens.
        warmup     updates over which the learning rate rises linearly from zero. Use it when
                   continuing from an already tuned state: Adam's first updates are full-sized
                   whatever the gradient, which knocks a tuned model about.
        final      share of the learning rate left at the end of the cosine schedule.
        ema        if > 0, the multipliers written back are an exponential average over the
                   run (that decay per update) rather than the last, noisiest values.
        offset, total   for a run split over several calls (to score in between): this call is
                   updates offset..offset+steps of `total`, and warm-up and cosine follow that one
                   schedule. Each call still starts a fresh optimiser, so give `rewarm` updates of
                   linear rise at the start of every later call. Pass each call its own samples.
        """
        rng = random.Random(seed)
        mods = self._modules()
        weights = sum(m.codes.numel() for m in mods) / 1e9
        need_memory(weights * (2 + (16 if self.opts["codes"] else 0)) + 4, "task tuning")
        latents, gains = [], []
        for m in mods:
            for p in m.start_training(codes=self.opts["codes"], scales=self.opts["scales"], keep_hard=True,
                                      compute_dtype=torch.bfloat16):
                (latents if p is m.latent else gains).append(p)
        small = self._small()
        for p in small:
            p.requires_grad_(True)
        groups = [g for g in ({"params": gains, "lr": lr_scales}, {"params": latents, "lr": lr_codes},
                              {"params": small, "lr": lr_fp}) if g["params"]]
        groups += [dict(g) for g in getattr(self, "extra_groups", [])]      # extra full-precision parameters trained alongside
        opt = torch.optim.Adam(groups, betas=(0.9, 0.99), eps=1e-6)
        base = [g["lr"] for g in groups]
        order = list(range(len(samples)))
        rng.shuffle(order)
        hist, started = [], time.time()
        avg = [torch.zeros_like(g) for g in gains] if ema else None
        done = 0
        kinds = collections.defaultdict(list)          # loss per kind of sample, for the report
        for step in range(steps):
            g_step, g_total = step + offset, total or steps
            warm = min(1.0, (g_step + 1) / warmup) if warmup else 1.0
            if rewarm and offset:
                warm *= min(1.0, (step + 1) / rewarm)
            factor = warm * (final + (1 - final) * 0.5 * (1 + math.cos(math.pi * min(g_step, g_total) / g_total)))
            for g, lr in zip(opt.param_groups, base):
                g["lr"] = lr * factor
            opt.zero_grad(set_to_none=True)
            total = 0.0
            for a in range(accumulate):
                it = samples[order[(step * accumulate + a) % len(samples)]]
                if it.get("kind"):                       # a chat sample: pointing or tool calling as a tool call
                    inputs, spans, allowed, _ = chat.supervise(self.lab, self.B, it)
                    n_prompt, n_ans = spans[0]
                    tgt = inputs["input_ids"][0, n_prompt:]
                    logits = chat.answer_logits(self.B, inputs, n_prompt, n_ans)
                    loss = point_loss(logits, allowed)
                    if it["kind"] == "tool_call":        # long answers: keep the scale of a ten-token answer
                        loss = loss * (10.0 / n_ans)
                    elif it["kind"] == "no_call":        # one position stands for a whole reply
                        loss = loss * 4.0
                    kinds[it["kind"]].append(loss.item())
                else:
                    inputs, n_prompt = self.lab._inputs(self.B, it, self.lab.answer_text(it))
                    tgt = inputs["input_ids"][0, n_prompt:]
                    logits = chat.answer_logits(self.B, inputs, n_prompt, tgt.shape[0])
                    loss = point_loss(logits, answer_targets(it, tgt))
                    kinds["point"].append(loss.item())
                self.lab.forward_passes += 1
                if kd and self.T is not None and not it.get("kind"):
                    with torch.no_grad():
                        t = self.T(**inputs, use_cache=False).logits[0, n_prompt - 1:-1, DIGIT0:DIGIT0 + 10].float()
                    is_digit = (tgt >= DIGIT0) & (tgt < DIGIT0 + 10)
                    sl = torch.log_softmax(logits[is_digit, DIGIT0:DIGIT0 + 10].float(), dim=-1)
                    loss = loss + kd * torch.nn.functional.kl_div(sl, torch.softmax(t[is_digit], dim=-1), reduction="sum")
                (loss / accumulate).backward()
                total += loss.item() / accumulate
            torch.nn.utils.clip_grad_norm_([p for g in groups for p in g["params"]], 1.0)
            opt.step()
            for m in mods:
                m.after_step()
            done += 1
            if avg is not None:
                for e, g in zip(avg, gains):
                    e.mul_(ema).add_(g.data, alpha=1 - ema)
            hist.append(total)
            if step % 10 == 0 and mem_available_gb() < 14:
                print(f"  stopping at step {step}: only {mem_available_gb():.0f} GB of memory left on the machine", flush=True)
                break
            if report_every and (step + 1) % report_every == 0:
                by = "  ".join(f"{k} {sum(v[-40:]) / len(v[-40:]):.2f}" for k, v in sorted(kinds.items()))
                print(f"  step {step + 1}/{steps}  loss {sum(hist[-report_every:]) / report_every:.3f}  ({by})"
                      f"  [{(time.time() - started) / (step + 1):.2f}s/step, {torch.cuda.max_memory_allocated() / 1e9:.0f} GB peak]",
                      flush=True)
        del opt
        if avg is not None and done:
            for e, g in zip(avg, gains):
                g.data.copy_(e / (1 - ema ** done))
        changed = sum(m.bake() for m in mods)
        for p in small:
            p.requires_grad_(False)
            p.grad = None
        torch.cuda.empty_cache()
        k = min(25, len(hist))
        self.hist += hist
        tag = "+".join(k_ for k_, v in self.opts.items() if v)
        self.lab.stack.append(f"tune:{tag}:L{self.first}-{self.layer_ids[-1] if self.layer_ids else 'head'}:{steps}")
        return {"loss_start": sum(hist[:k]) / k, "loss_end": sum(hist[-k:]) / k, "codes_changed": changed}

    def _small(self):
        out = []
        if self.opts["fp"]:
            for i in self.layer_ids:
                out += [p for n, p in self.layers[i].named_parameters()
                        if not n.endswith(("latent", "log_gain", "scales", "gate"))]
        return out

    @torch.no_grad()
    def snapshot(self):
        """Everything this tuner may change (multipliers; codes and small parts if opened), on the CPU."""
        return {"tern": [(m.scales.data.clone().cpu(), m.codes.clone().cpu() if self.opts["codes"] else None)
                         for m in self._modules()],
                "small": [p.data.clone().cpu() for p in self._small()]}

    @torch.no_grad()
    def restore(self, snap):
        for m, (s, c) in zip(self._modules(), snap["tern"]):
            m.scales.data.copy_(s.to(m.scales.device))
            if c is not None:
                m.codes.copy_(c.to(m.codes.device))
            m.invalidate()
        for p, v in zip(self._small(), snap["small"]):
            p.data.copy_(v.to(p.device))
