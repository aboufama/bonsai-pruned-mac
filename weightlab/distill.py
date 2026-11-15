"""Teach a block of Bonsai's layers to reproduce the parent's layers, staying ternary.

What the swap experiments established (FINDINGS.md, section 6):
  - Bonsai's first 4 layers hand a usable state to the parent's layers.
  - Bonsai's last 12 layers decode the parent's state correctly.
  - With the parent's layers 4..19 in between, pointing is back (p_hit 0.692, parent 0.707).

So layers 4..19 have a precise, label-free target: given the state Bonsai's own early layers
produce, compute what the parent's layers 4..19 would compute. `BlockDistiller` trains each
layer of the block on exactly that:

    target  Y_l   the state the parent's layer l produces (parent block run from Bonsai's input)
    input         inputs="teacher": the parent's state entering layer l (layers learn independently)
                  inputs="student": what Bonsai's own (already trained) layers below produce, so
                                    each layer also learns to absorb the errors made below it
    loss    | student_layer(input) - Y_l |^2  /  | Y_l - X_l |^2     (error relative to what the
                                                                      parent's layer adds)

Only ternary codes (through a straight-through estimator), the per-group multipliers and the
layer's small full-precision parts are trained. After training the layer is an ordinary Bonsai
layer again: same file format, same size, same speed.

Any screenshot with any instruction is training material; no answer labels are needed.
"""
import gc
import math
import os
import random
import time

import torch

from .core import mem_available_gb, need_memory
from .ternary import TernaryLinear


class _Stop(Exception):
    pass


def _cast(obj, dtype):
    if torch.is_tensor(obj):
        return obj.to(dtype) if obj.is_floating_point() else obj
    if isinstance(obj, (tuple, list)):
        return type(obj)(_cast(o, dtype) for o in obj)
    if isinstance(obj, dict):
        return {k: _cast(v, dtype) for k, v in obj.items()}
    return obj


def _cast_layer(layer, dtype):
    """Change the working precision of a layer's full-precision parts. Ternary modules keep
    their float32 multipliers and signs; only the dtype they emit changes."""
    for mod in layer.modules():
        if isinstance(mod, TernaryLinear):
            mod.out_dtype = dtype
            mod.invalidate()
            continue
        for p in mod._parameters.values():
            if p is not None and p.is_floating_point():
                p.data = p.data.to(dtype)
        for name, b in mod._buffers.items():
            if b is not None and b.is_floating_point():
                mod._buffers[name] = b.to(dtype)


def _rel(out, x, y, w):
    """Weighted squared error of `out` against `y`, relative to the size of the step x -> y."""
    num = ((out - y).pow(2).mean(-1) * w).sum()
    den = ((y - x).pow(2).mean(-1) * w).sum().clamp_min(1e-8)
    return num / den


def teacher_block(lab, which, lo, hi):
    """Layers lo..hi of a teacher model as {index: layer}. If the teacher was not already loaded,
    the rest of it is released again, so only the block stays in memory (7 GB for 16 layers
    instead of 18 GB for the whole model)."""
    key = f"{which}[{lo}..{hi}]"
    if key not in lab.models:
        had = which in lab.models
        layers = lab.load(which).model.language_model.layers
        lab.models[key] = {i: layers[i] for i in range(lo, hi + 1)}
        if not had:
            del lab.models[which], layers
            gc.collect()
            torch.cuda.empty_cache()
    return lab.models[key]


class BlockDistiller:
    def __init__(self, lab, lo, hi, teacher="P"):
        self.lab, self.lo, self.hi = lab, lo, hi
        self.B = lab.B
        self.b_layers = list(self.B.model.language_model.layers)
        self.t_layers = teacher_block(lab, teacher, lo, hi) if teacher else {}     # None: no teacher needed
        self.types = list(self.B.config.text_config.layer_types)
        self.log = []

    # ------------------------------------------------------------------ teacher states
    @torch.no_grad()
    def states(self, it, upto=None, text_weight=1.0):
        """Run Bonsai up to layer `lo`, then the teacher's layers lo..upto from that state.

        Returns (kwargs per layer type, [X_lo, ..., X_upto+1], per-position weights). The sample
        is the prompt plus the teacher-forced answer. Positions that are not image tokens get
        weight `text_weight`.
        """
        upto = self.hi if upto is None else upto
        items = it if isinstance(it, (list, tuple)) else [it]        # several questions on one screenshot
        inputs, spans = self.lab._inputs_multi(self.B, items)
        self.last = (inputs, spans)
        kw, grabbed, hooks = {}, {}, []

        def kw_hook(i):
            def hook(module, args, kwargs):
                kw.setdefault(self.types[i], dict(kwargs))
            return hook

        def stop_hook(module, args, kwargs):
            kw.setdefault(self.types[self.lo], dict(kwargs))
            grabbed["h"] = args[0]
            raise _Stop()

        for i in range(self.lo):
            hooks.append(self.b_layers[i].register_forward_pre_hook(kw_hook(i), with_kwargs=True))
        hooks.append(self.b_layers[self.lo].register_forward_pre_hook(stop_hook, with_kwargs=True))
        try:
            self.B(**inputs, use_cache=False)
        except _Stop:
            pass
        finally:
            for h in hooks:
                h.remove()
        self.lab.forward_passes += 1
        missing = set(self.types) - set(kw)
        assert not missing, f"no layer of type {missing} below layer {self.lo}; choose lo >= 4"
        xs = [grabbed["h"]]
        for i in range(self.lo, upto + 1):
            xs.append(self.t_layers[i](xs[-1], **kw[self.types[i]]))
        w = torch.ones(xs[0].shape[:2], device=xs[0].device)
        kinds = inputs.get("mm_token_type_ids")
        if text_weight != 1.0 and kinds is not None:
            w = torch.where(kinds == 0, torch.full_like(w, text_weight), w)
        return kw, xs, w

    @torch.no_grad()
    def _student_state(self, xs, kw, upto):
        """Bonsai's own state entering layer `upto`, starting from the shared state at `lo`."""
        s = xs[0]
        for i in range(self.lo, upto):
            s = self.b_layers[i](s, **kw[self.types[i]])
        return s

    # ------------------------------------------------------------------ training
    def train(self, layer_ids, samples, steps=None, inputs="teacher", chain=False, text_weight=1.0,
              lr_codes=3e-3, lr_scales=2e-3, lr_fp=2e-4, codes=True, scales=True, fp=True,
              seed=0, report_every=50):
        """Train consecutive layers `layer_ids` (a subset of lo..hi) at once.

        One step = one sample. inputs="teacher": every layer gets the parent's state as input.
        inputs="student": the first layer gets what Bonsai's layers below it produce; with
        chain=True each further layer gets the output of the one before it and gradients flow
        through the whole group, otherwise further layers get the parent's state.
        Learning rates fall along a cosine to a tenth of their starting value.
        Returns, per layer, the loss at the start and end and how many codes changed.
        """
        layer_ids = list(layer_ids)
        assert layer_ids == list(range(layer_ids[0], layer_ids[-1] + 1)) and self.lo <= layer_ids[0] and layer_ids[-1] <= self.hi
        need_memory((4.0 if codes else 0.5) * len(layer_ids) + 2, f"training {len(layer_ids)} layers")
        rng = random.Random(seed)
        groups, tern = [], {}
        for i in layer_ids:
            layer = self.b_layers[i]
            _cast_layer(layer, torch.float32)
            mods = [m for m in layer.modules() if isinstance(m, TernaryLinear)]
            tern[i] = mods
            latents, gains = [], []
            for m in mods:
                for p in m.start_training(codes=codes, scales=scales, keep_hard=True, compute_dtype=torch.bfloat16):
                    (latents if p is m.latent else gains).append(p)
            if latents:
                groups.append({"params": latents, "lr": lr_codes})
            if gains:
                groups.append({"params": gains, "lr": lr_scales})
            if fp:
                small = [p for n, p in layer.named_parameters() if not n.endswith(("latent", "log_gain", "scales"))]
                for p in small:
                    p.requires_grad_(True)
                groups.append({"params": small, "lr": lr_fp})
        opt = torch.optim.Adam(groups, betas=(0.9, 0.99))
        base_lrs = [g["lr"] for g in groups]
        steps = steps or len(samples)
        order = list(range(len(samples)))
        rng.shuffle(order)
        hist = {i: [] for i in layer_ids}
        first, last = layer_ids[0], layer_ids[-1]
        started = time.time()
        for step in range(steps):
            factor = 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * step / steps))
            for g, lr in zip(opt.param_groups, base_lrs):
                g["lr"] = lr * factor
            it = samples[order[step % len(samples)]]
            kw, xs, w = self.states(it, upto=last, text_weight=text_weight)
            kw32 = {k: _cast(v, torch.float32) for k, v in kw.items()}
            opt.zero_grad(set_to_none=True)
            s = self._student_state(xs, kw, first).float() if inputs == "student" else None
            total = 0.0
            for i in layer_ids:
                x = xs[i - self.lo].float()
                y = xs[i - self.lo + 1].float()
                feed = s if (s is not None and (chain or i == first)) else x
                out = self.b_layers[i](feed, **kw32[self.types[i]])
                loss = _rel(out, x, y, w)
                hist[i].append(loss.item())
                if chain:
                    total = total + loss
                    s = out
                else:
                    loss.backward()
            if chain:
                total.backward()
            opt.step()
            for mods in tern.values():
                for m in mods:
                    m.after_step()
            if step % 10 == 0 and mem_available_gb() < 14:
                print(f"  stopping at step {step}: only {mem_available_gb():.0f} GB of memory left on the machine", flush=True)
                break
            if report_every and (step + 1) % report_every == 0:
                recent = {i: sum(h[-report_every:]) / report_every for i, h in hist.items()}
                print(f"  step {step + 1}/{steps}  " + "  ".join(f"L{i}:{v:.3f}" for i, v in recent.items())
                      + f"  [{(time.time() - started) / (step + 1):.2f}s/step, "
                      + f"{torch.cuda.max_memory_allocated() / 1e9:.0f} GB peak]", flush=True)
        del opt
        # write the result back into ordinary ternary layers
        out = {}
        for i in layer_ids:
            changed = sum(m.bake() for m in tern[i])
            total_codes = sum(m.codes.numel() for m in tern[i])
            layer = self.b_layers[i]
            for p in layer.parameters():
                p.requires_grad_(False)
                p.grad = None
            _cast_layer(layer, torch.bfloat16)
            k = min(20, len(hist[i]))
            out[i] = {"loss_start": sum(hist[i][:k]) / k, "loss_end": sum(hist[i][-k:]) / k,
                      "codes_changed": changed, "codes_changed_share": changed / total_codes}
        torch.cuda.empty_cache()
        self.log.append({"layers": layer_ids, "steps": steps, "inputs": inputs, "chain": chain, "result": out})
        self.lab.stack.append(f"distill:L{first}-{last}:{inputs}{':chain' if chain else ''}:{steps}")
        return out

    @torch.no_grad()
    def local_error(self, samples, inputs="teacher"):
        """Per layer, the relative error against the parent's output, without training.
        inputs="teacher": each layer is fed the parent's state (how good is the layer alone).
        inputs="student": the layers are run as a chain (how far has the block drifted by layer l)."""
        tot = {i: 0.0 for i in range(self.lo, self.hi + 1)}
        for it in samples:
            kw, xs, w = self.states(it)
            s = xs[0]
            for i in tot:
                x, y = xs[i - self.lo], xs[i - self.lo + 1]
                out = self.b_layers[i](s if inputs == "student" else x, **kw[self.types[i]])
                s = out
                tot[i] += _rel(out.float(), x.float(), y.float(), w).item()
        return {i: v / len(samples) for i, v in tot.items()}

    # ------------------------------------------------------------------ checkpoints
    def _named(self, i):
        prefix = f"model.language_model.layers.{i}."
        tern = {n: m for n, m in self.lab.tern.items() if n.startswith(prefix)}
        small = {prefix + n: p for n, p in self.b_layers[i].named_parameters()
                 if not n.endswith(("latent", "log_gain", "scales", "gate"))}
        return tern, small

    @torch.no_grad()
    def save(self, layer_ids, path):
        """Write the current codes, multipliers and small full-precision parts of these layers."""
        from safetensors.torch import save_file
        os.makedirs(os.path.dirname(path), exist_ok=True)
        t = {}
        for i in layer_ids:
            tern, small = self._named(i)
            for n, m in tern.items():
                t[n + ".codes"], t[n + ".scales"] = m.codes.cpu(), m.scales.data.float().cpu()
            for n, p in small.items():
                t[n] = p.data.cpu()
        save_file(t, path)
        return path

    @torch.no_grad()
    def restore(self, path):
        """Load a checkpoint written by save() back into Bonsai. Returns the layers touched."""
        from safetensors.torch import load_file
        t = load_file(path)
        params = dict(self.B.named_parameters())
        touched = set()
        for key, v in t.items():
            if key.endswith(".codes"):
                m = self.lab.tern[key[:-6]]
                m.codes.copy_(v.to(m.codes.device))
                m.scales.data.copy_(t[key[:-6] + ".scales"].to(m.scales.device))
                m.invalidate()
            elif not key.endswith(".scales"):
                params[key].data.copy_(v.to(params[key].device, params[key].dtype))
            touched.add(int(key.split("layers.")[1].split(".")[0]))
        torch.cuda.empty_cache()
        return sorted(touched)
