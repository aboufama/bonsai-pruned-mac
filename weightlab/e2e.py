"""Train the whole damaged block at once, staying ternary, on two signals.

`BlockDistiller` teaches each layer separately and `TaskTuner` only moves multipliers. This
trainer opens everything in layers lo..hi (ternary codes, multipliers, small full-precision
parts) and runs the block as a chain, so the layers learn to work together:

    hint   after every `hint_every` layers and at the end of the block, Bonsai's state should
           match the state the teacher's layers produce from the same input (relative squared
           error, measured against how far the teacher moved the state since the block began)
    task   the block's output goes through Bonsai's own frozen top layers and output head; at
           each answer digit the probability mass on digits that keep the point inside the
           target box should be high (the lab's `miss_nll`, see tune.py)

Forward pass for one sample:
    Bonsai layers 0..lo-1 (frozen)  ->  X
    teacher layers lo..hi from X    ->  teacher states            (no gradient)
    Bonsai layers lo..hi from X     ->  student states            (trained)
    Bonsai layers hi+1..31, head    ->  answer logits             (frozen, gradients pass through)

Memory: the codes are trained through latents that each layer updates itself during the
backward pass (see TernaryLinear.start_training, `lean`), 8 bytes per weight, so all 16 layers
fit at once: about 28 GB for latents and optimiser state plus 7 GB of working weights.
"""
import math
import random
import time
import collections

import torch

from .core import mem_available_gb, need_memory
from .distill import BlockDistiller, _cast, _cast_layer
from .ternary import TernaryLinear
from .tune import answer_targets, point_loss, teacher_loss


class BlockTrainer:
    def __init__(self, lab, lo, hi, teacher="V"):
        self.lab, self.lo, self.hi = lab, lo, hi
        self.B = lab.B
        self.text = self.B.model.language_model
        self.layers = list(self.text.layers)
        self.types = list(self.B.config.text_config.layer_types)
        self.D = BlockDistiller(lab, lo, hi, teacher)
        self.mods, self.training = [], False
        self.hist = []

    # ------------------------------------------------------------------ one sample
    def forward(self, it, hint_every=4, text_weight=1.0, want_logits=True, use_hints=True):
        """Returns (hint losses, answers). `it` is one sample or a list of samples on the same
        screenshot (asked one after the other in one conversation); answers holds, per sample,
        (logits at its answer positions, its answer token ids). Call under no_grad to score.
        With use_hints=False the teacher's layers are not run at all."""
        kw, xs, w = self.D.states(it, upto=self.hi if use_hints else self.lo - 1, text_weight=text_weight)
        inputs, spans = self.D.last
        block_dtype = torch.float32 if self.training else torch.bfloat16
        kwb = {k: _cast(v, block_dtype) for k, v in kw.items()}
        x0 = xs[0].float()
        s = xs[0].to(block_dtype)
        hints = []
        for i in range(self.lo, self.hi + 1):
            s = self.layers[i](s, **kwb[self.types[i]])
            j = i + 1 - self.lo
            if use_hints and (j % hint_every == 0 or i == self.hi):
                y = xs[j].float()
                num = ((s.float() - y).pow(2).mean(-1) * w).sum()
                den = ((y - x0).pow(2).mean(-1) * w).sum().clamp_min(1e-8)
                hints.append(num / den)
        answers = []
        if want_logits:
            h = s.to(torch.bfloat16)
            for i in range(self.hi + 1, len(self.layers)):
                h = self.layers[i](h, **kw[self.types[i]])
            # the head only runs on the positions that predict answer tokens
            idx = torch.cat([torch.arange(a - 1, a - 1 + n, device=h.device) for a, n in spans])
            logits = self.B.lm_head(self.text.norm(h)[0, idx])
            ids, off = inputs["input_ids"][0], 0
            for a, n in spans:
                answers.append((logits[off:off + n], ids[a:a + n]))
                off += n
        return hints, answers

    # ------------------------------------------------------------------ open / close
    def open(self, lr_codes=1e-2, lr_scales=1e-3, lr_fp=1e-4, codes=True, scales=True, fp=True):
        """Put layers lo..hi into training form. Returns nothing; call close() to write back."""
        assert not self.training
        n = self.hi - self.lo + 1
        # per layer: latents and two moments (1.73 GB), working weights (0.43 GB), minus the folded
        # cache that is released while the layer trains (0.43 GB); plus activations and transients
        need_memory(n * (1.73 if codes else 0.1) + 5, f"training {n} layers end to end")
        gains, small = [], []
        self.mods = []
        for i in range(self.lo, self.hi + 1):
            layer = self.layers[i]
            _cast_layer(layer, torch.float32)
            for m in layer.modules():
                if isinstance(m, TernaryLinear):
                    gains += m.start_training(codes=codes, scales=scales, keep_hard=True,
                                              compute_dtype=torch.bfloat16, lean={"lr": lr_codes} if codes else None)
                    self.mods.append(m)
            if fp:
                small += [p for nme, p in layer.named_parameters() if not nme.endswith(("latent", "log_gain", "scales", "gate"))]
        for p in small:
            p.requires_grad_(True)
        groups = [g for g in ({"params": gains, "lr": lr_scales}, {"params": small, "lr": lr_fp}) if g["params"]]
        self.opt = torch.optim.Adam(groups, betas=(0.9, 0.99), eps=1e-8) if groups else None
        self.base = dict(codes=lr_codes, groups=[g["lr"] for g in groups])
        self.small, self.training, self.steps_done = small, True, 0

    def close(self):
        """Write latents and gains back into codes and multipliers; the block is ordinary again."""
        assert self.training
        changed = sum(m.bake() for m in self.mods)
        total = sum(m.codes.numel() for m in self.mods)
        for p in self.small:
            p.requires_grad_(False)
            p.grad = None
        for i in range(self.lo, self.hi + 1):
            _cast_layer(self.layers[i], torch.bfloat16)
        self.opt, self.training = None, False
        torch.cuda.empty_cache()
        self.lab.stack.append(f"e2e:L{self.lo}-{self.hi}:{self.steps_done}")
        return {"codes_changed": changed, "codes_changed_share": changed / total}

    # ------------------------------------------------------------------ training
    def train(self, samples, steps, total_steps=None, task=1.0, hint=1.0, hint_every=4, text_weight=4.0,
              seed=0, report_every=25, warmup=0, final=0.1, teach=0.0):
        """`steps` more steps (one sample each). `total_steps` sets the length of the cosine
        learning-rate schedule when training is split over several calls. `warmup` steps of
        linear rise from zero come first (needed when starting from a tuned state); the
        schedule ends at `final` times the starting rate. `teach` > 0 adds, for samples that carry
        a teacher's digit distributions (it["teacher"], see tune.teacher_targets), `teach` times the
        cross-entropy to them; samples without one are trained on the label loss alone."""
        assert self.training, "call open() first"
        total_steps = total_steps or steps
        rng = random.Random(seed + self.steps_done)
        order = list(range(len(samples)))
        rng.shuffle(order)
        hist, started = [], time.time()
        first, later = [], []                  # loss of the first question on a screenshot / of later ones
        taught = [0, 0]                        # answers and digit positions that got the teacher term
        for k in range(steps):
            t = self.steps_done
            warm = min(1.0, (t + 1) / warmup) if warmup else 1.0
            factor = warm * (final + (1 - final) * 0.5 * (1 + math.cos(math.pi * min(t, total_steps) / total_steps)))
            for m in self.mods:
                if m.lean is not None:
                    m.lean["lr"] = self.base["codes"] * factor
            if self.opt is not None:
                for g, lr in zip(self.opt.param_groups, self.base["groups"]):
                    g["lr"] = lr * factor
                self.opt.zero_grad(set_to_none=True)
            it = samples[order[k % len(samples)]]
            items = it if isinstance(it, (list, tuple)) else [it]
            try:
                hints, answers = self.forward(it, hint_every, text_weight, want_logits=task > 0, use_hints=hint > 0)
                self.lab.forward_passes += 1
                per = [point_loss(lg, answer_targets(one, tgt)) for one, (lg, tgt) in zip(items, answers)]
                if teach > 0:
                    for i, (one, (lg, tgt)) in enumerate(zip(items, answers)):
                        extra, n_pos = teacher_loss(lg, one)
                        if n_pos:
                            per[i] = per[i] + teach * extra
                            taught[0] += 1; taught[1] += n_pos
                tl = torch.stack(per).mean() if per else torch.zeros((), device=self.B.device)
                h = torch.stack(hints).mean() if hints else torch.zeros((), device=tl.device)
                (task * tl + hint * h).backward()
            except torch.OutOfMemoryError:
                raise
            except Exception as e:             # one unusable sample must not end an hours-long run
                self.skipped = getattr(self, "skipped", 0) + 1
                print(f"  skipped a sample ({items[0]['id']}): {type(e).__name__}: {str(e)[:120]}", flush=True)
                for m in self.mods:
                    m.after_step()
                if self.skipped > 25:
                    raise RuntimeError("more than 25 samples failed; stopping") from e
                continue
            if per:
                first.append(per[0].item())
                later += [p.item() for p in per[1:]]
            if self.opt is not None:
                torch.nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"]], 1.0)
                self.opt.step()
            for m in self.mods:
                m.after_step()
            self.steps_done += 1
            hist.append((tl.item(), h.item(), hints[-1].item() if hints else float("nan")))
            if step_report(k, report_every):
                r = hist[-report_every:]
                print(f"  step {self.steps_done}  task {sum(x[0] for x in r) / len(r):.3f}  hint {sum(x[1] for x in r) / len(r):.3f}"
                      f"  block output {sum(x[2] for x in r) / len(r):.3f}"
                      f"  [{(time.time() - started) / (k + 1):.2f}s/step, {torch.cuda.max_memory_allocated() / 1e9:.0f} GB peak]", flush=True)
            if k % 10 == 0 and mem_available_gb() < 14:
                print(f"  stopping: only {mem_available_gb():.0f} GB of memory left on the machine", flush=True)
                break
        self.hist += hist
        n = max(1, min(25, len(hist)))
        return {"task_start": sum(x[0] for x in hist[:n]) / n, "task_end": sum(x[0] for x in hist[-n:]) / n,
                "hint_start": sum(x[1] for x in hist[:n]) / n, "hint_end": sum(x[1] for x in hist[-n:]) / n,
                "first_question": sum(first) / max(1, len(first)), "later_questions": sum(later) / max(1, len(later)),
                "answers": len(first) + len(later), "taught_answers": taught[0], "taught_positions": taught[1]}

    # ------------------------------------------------------------------ checkpoints while open
    @torch.no_grad()
    def checkpoint(self, path):
        """Write the block as it would be if closed now (rounded codes, current multipliers,
        small parts), without closing it. Same file format as BlockDistiller.save()."""
        from safetensors.torch import save_file
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        t = {}
        for i in range(self.lo, self.hi + 1):
            tern, small = self.D._named(i)
            for n, m in tern.items():
                t[n + ".codes"] = m.hard_codes().to(torch.int8).cpu()
                t[n + ".scales"] = m.live_scales().float().cpu()
            for n, p in small.items():
                t[n] = p.data.to(torch.bfloat16).cpu()
        save_file(t, path)
        return path

    @torch.no_grad()
    def flips(self):
        """Share of the block's codes that currently differ from the stored ones."""
        changed = sum(int((m.hard_codes().to(torch.int8) != m.codes).sum()) for m in self.mods if m.latent is not None)
        total = sum(m.codes.numel() for m in self.mods)
        return changed / total

    # ------------------------------------------------------------------ scoring while open
    @torch.no_grad()
    def score(self, samples, use_hints=False):
        """The lab's digit score with the block in its current (possibly open) state. With
        use_hints=True also the block-output error against the teacher. One pass per sample."""
        nll, ok, out_err = [], collections.defaultdict(list), []
        for it in samples:
            hints, answers = self.forward(it, hint_every=10**6, use_hints=use_hints)
            logits, tgt = answers[0]
            self.lab._digit_stats(torch.log_softmax(logits.float(), dim=-1), tgt, it, nll, ok)
            if hints:
                out_err.append(hints[-1].item())
        r = self.lab._digit_summary(nll, ok)
        if out_err:
            r["block_output_error"] = sum(out_err) / len(out_err)
        return r


def step_report(k, every):
    return every and (k + 1) % every == 0
