"""Bonsai's packed layers as PyTorch modules that stay ternary.

A TernaryLinear holds the real representation of a Bonsai layer:
  codes   int8 (rows, width) in {-1, 0, +1}
  scales  float32 (rows, width/128), one per group of 128 inputs
  signs   +1/-1 (width,) and a rotation block size
and computes  y = (codes * scales) . H(signs * x), exactly as the runtimes do.

Two forward modes with the same result:
  "folded"   uses a cached dense matrix in the original basis (fast; for analysis and scoring)
  "rotated"  rotates the activations and multiplies by codes * scales (for training: gradients
             reach `scales` and, if enabled, the deletion logits `gate`)

Anything changed through `codes`, `scales` or `gate` can be written back as a ternary file.
"""
import json
import math
import os
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "weights"))
import pack  # noqa: E402

GROUP = pack.GROUP


def fwht(x, block):
    """Normalised Walsh-Hadamard transform over consecutive blocks of the last dimension."""
    shape = x.shape
    y = x.reshape(-1, block)
    h = 1
    while h < block:
        y = y.view(-1, block // (2 * h), 2, h)
        y = torch.stack((y[:, :, 0, :] + y[:, :, 1, :], y[:, :, 0, :] - y[:, :, 1, :]), dim=2)
        y = y.reshape(-1, block)
        h *= 2
    return (y / math.sqrt(block)).reshape(shape)


_HADAMARD = {}


def hadamard(block, device, dtype):
    """The +1/-1 Walsh-Hadamard matrix of size `block` (natural ordering), cached."""
    key = (block, str(device), dtype)
    if key not in _HADAMARD:
        h = torch.ones(1, 1, device=device)
        while h.shape[0] < block:
            h = torch.cat([torch.cat([h, h], dim=1), torch.cat([h, -h], dim=1)], dim=0)
        _HADAMARD[key] = h.to(dtype)
    return _HADAMARD[key]


def rotate(x, block):
    """The same transform as `fwht`, done as one matrix product per call.

    `fwht` runs 12 small stages for a block of 4096; with autograd that is thousands of tiny
    GPU operations per training step, each of which stalls when the GPU is shared. One product
    with the 4096 x 4096 sign matrix costs little next to the layer's own product."""
    shape = x.shape
    y = x.reshape(*shape[:-1], -1, block) @ hadamard(block, x.device, x.dtype)
    return (y * (1.0 / math.sqrt(block))).reshape(shape)


class _RotatedProduct(torch.autograd.Function):
    """y = xr . W^T with W = codes * multipliers, for training without keeping W in the graph.

    A plain autograd graph would hold three weight-sized float tensors per matrix until the
    backward pass. Here only the (small) input is saved; W is rebuilt for the backward pass and
    the gradients for the latent codes and the log-gains are formed directly:
        dL/dlatent   = G * multiplier              (straight-through: d code / d latent = 1)
        dL/dlog_gain = sum over the group of (G * code) * multiplier
    with G = dL/dW = grad_y^T . xr.
    """

    @staticmethod
    def forward(ctx, mod, xr, *params):
        ctx.mod = mod
        ctx.save_for_backward(xr)
        return F.linear(xr, mod.hard_weight(xr.dtype))

    @staticmethod
    def backward(ctx, g):
        mod = ctx.mod
        (xr,) = ctx.saved_tensors
        out = [None, g @ mod.hard_weight(g.dtype)]
        if mod.latent is not None or mod.log_gain is not None:
            # G = dL/dW, formed in the working precision (bfloat16 on the GPU, several times
            # faster than float32)
            G = g.reshape(-1, g.shape[-1]).t() @ xr.reshape(-1, xr.shape[-1])
            if mod.lean is not None:
                # everything stays in the working precision and nothing weight-sized is stored
                if mod.log_gain is not None:        # sum over each group of G * code * multiplier
                    out.append((G * mod.hard_weight(g.dtype)).view(G.shape[0], -1, GROUP).sum(-1, dtype=torch.float32))
                mod.lean_update(G)                  # Adam ignores the per-group multiplier, so G is enough
            else:
                G = G.float()
                scales = mod.live_scales()
                if mod.latent is not None and mod.latent.requires_grad:
                    out.append(G * scales.repeat_interleave(GROUP, dim=1))
                if mod.log_gain is not None:
                    out.append((G * mod.hard_codes()).view(G.shape[0], -1, GROUP).sum(-1) * scales)
        return tuple(out)


class TernaryLinear(nn.Module):
    def __init__(self, codes, scales, signs, block, folded=None, out_dtype=torch.bfloat16):
        super().__init__()
        self.register_buffer("codes", codes, persistent=False)        # int8, {-1, 0, 1}
        self.register_buffer("signs", signs.float(), persistent=False)
        self.scales = nn.Parameter(scales.float(), requires_grad=False)
        self.gate = None             # optional deletion logits, same shape as codes
        self.gate_sharpness = 1.0
        self.latent = None           # optional trainable real-valued codes (see start_training)
        self.log_gain = None         # optional trainable log-multiplier on the scales
        self.keep_hard = False       # keep the rotated weight between forward and backward
        self.compute_dtype = None    # precision of the big products while training (None: the input's)
        self.lean = None             # settings of the built-in optimiser for the latents (see start_training)
        self._m = self._v = None
        self._hard = None
        self.block = block
        self.mode = "folded"
        self.out_dtype = out_dtype
        self._folded = folded
        self.out_features, self.in_features = codes.shape

    # ---- weights -------------------------------------------------------------------------
    def keep_mask(self):
        if self.gate is None:
            return None
        if self.training:
            return torch.sigmoid(self.gate * self.gate_sharpness)
        return (self.gate > 0).to(self.scales.dtype)

    def rotated_weight(self):
        """codes * scales (and the deletion mask), in the rotated basis the file stores."""
        if self.latent is None:
            codes = self.codes.to(self.scales.dtype)
        else:
            # straight-through: forward uses the ternary value, backward treats it as the latent
            hard = torch.sign(self.latent) * (self.latent.abs() > 0.5)
            codes = self.latent + (hard - self.latent).detach()
        scales = self.scales if self.log_gain is None else self.scales * torch.exp(self.log_gain)
        w = codes * scales.repeat_interleave(GROUP, dim=1)
        mask = self.keep_mask()
        return w if mask is None else w * mask

    @torch.no_grad()
    def hard_codes(self):
        """Current codes as float32: the stored ones, or the rounded latents while training."""
        if self.latent is None:
            return self.codes.float()
        return self.latent.clamp(-1, 1).round_()      # -1, 0 or +1; exactly 0.5 rounds to 0

    @torch.no_grad()
    def live_scales(self):
        return self.scales if self.log_gain is None else self.scales * torch.exp(self.log_gain)

    @torch.no_grad()
    def hard_weight(self, dtype):
        """codes * multipliers in the rotated basis, detached, in `dtype`.

        With `keep_hard` set, the matrix is kept until `after_step()` so that the forward and
        the backward pass of one training step share it."""
        if self._hard is not None and self._hard.dtype == dtype:
            return self._hard
        if self.latent is None:      # codes are fixed: go straight to the working precision
            w = self.codes.to(dtype) * self.live_scales().to(dtype).repeat_interleave(GROUP, dim=1)
        else:
            w = self.hard_codes().to(dtype)
            w *= self.live_scales().to(dtype).repeat_interleave(GROUP, dim=1)
        if self.keep_hard:
            self._hard = w
        return w

    @torch.no_grad()
    def after_step(self):
        """Call after every optimiser step: keeps latents in range and drops the kept matrix."""
        if self.latent is not None and self.lean is None:
            self.latent.clamp_(-1.5, 1.5)
        self._hard = None

    # ---- training ------------------------------------------------------------------------
    def start_training(self, codes=True, scales=True, keep_hard=False, compute_dtype=None, lean=None):
        """Make this layer trainable while staying ternary.

        codes:  a real-valued latent per weight, initialised at the current code; the forward
                pass rounds it to -1, 0 or +1 (threshold 0.5) and gradients pass straight through.
        scales: a log-multiplier per group, initialised at 0 (no change).
        lean:   {"lr": ..., "b1": 0.9, "b2": 0.95} makes the layer update its own latents during
                the backward pass with Adam whose two moments are kept in bfloat16. Memory per
                weight is then 4 + 2 + 2 bytes instead of 16, which is what lets all 16 middle
                layers train at once. The latent is not returned as a parameter in this mode;
                change `self.lean["lr"]` to schedule it.
        Call bake() afterwards to write the result back into codes and scales.
        """
        self.latent = nn.Parameter(self.codes.float().clone(), requires_grad=lean is None) if codes else None
        self.lean = {"b1": 0.9, "b2": 0.95, "eps": 1e-12, "t": 0, "state": torch.bfloat16, **lean} if (lean and codes) else None
        if self.lean is not None:
            self._m = torch.zeros_like(self.latent, dtype=self.lean["state"])
            self._v = torch.zeros_like(self.latent, dtype=self.lean["state"])
        self.log_gain = nn.Parameter(torch.zeros_like(self.scales)) if scales else None
        self.mode = "rotated"
        self._folded = self._hard = None
        self.keep_hard = keep_hard
        self.compute_dtype = compute_dtype
        return [p for p in (self.latent, self.log_gain) if p is not None and p.requires_grad]

    @torch.no_grad()
    def lean_update(self, G):
        """One Adam step on the latents from dL/dW (same shape; consumed). The straight-through
        gradient for a latent is dL/dW times its group's multiplier, a per-group constant that
        Adam's normalisation removes, so dL/dW is used as is."""
        o = self.lean
        o["t"] += 1
        G = G.to(o["state"])
        self._m.mul_(o["b1"]).add_(G, alpha=1 - o["b1"])
        self._v.mul_(o["b2"]).addcmul_(G, G, value=1 - o["b2"])
        bc1, bc2 = 1 - o["b1"] ** o["t"], 1 - o["b2"] ** o["t"]
        torch.sqrt(self._v, out=G).add_(o["eps"] * math.sqrt(bc2))          # reuse G as the denominator
        G.reciprocal_().mul_(self._m)
        self.latent.data.add_(G, alpha=-o["lr"] * math.sqrt(bc2) / bc1)
        if o["t"] % 8 == 0:
            self.latent.data.clamp_(-1.5, 1.5)

    @torch.no_grad()
    def bake(self):
        """Fold the trained latents and gains back into codes and scales; return codes changed."""
        changed = 0
        if self.latent is not None:
            new = self.hard_codes().to(torch.int8)
            changed = int((new != self.codes).sum())
            self.codes.copy_(new)
            self.latent = None
        if self.log_gain is not None:
            self.scales.data.mul_(torch.exp(self.log_gain.data))
            self.log_gain = None
        self.mode = "folded"
        self._folded = self._hard = None
        self.keep_hard, self.compute_dtype = False, None
        self.lean = self._m = self._v = None
        return changed

    def folded_weight(self):
        """The same layer as an ordinary dense matrix in the model's original basis (cached)."""
        if self._folded is None:
            with torch.no_grad():
                self._folded = (fwht(self.rotated_weight().float(), self.block) * self.signs).to(self.out_dtype)
        return self._folded

    def invalidate(self):
        """Call after changing codes, scales or gate."""
        self._folded = None

    @property
    def weight(self):
        return self.folded_weight()

    # ---- forward -------------------------------------------------------------------------
    def forward(self, x):
        if self.mode == "folded":
            w = self.folded_weight()
            if torch.is_grad_enabled() and w.is_inference():
                # the cache was built during scoring (inference mode); autograd needs an ordinary tensor
                self._folded = w = w.clone()
            return F.linear(x, w.to(x.dtype))
        if self.gate is not None:
            xr = fwht((x * self.signs.to(x.dtype)).float(), self.block).to(x.dtype)
            return F.linear(xr, self.rotated_weight().to(x.dtype))
        cd = self.compute_dtype or x.dtype        # precision of the big products
        xr = rotate((x * self.signs.to(x.dtype)).to(cd), self.block)
        params = [p for p in (self.latent, self.log_gain) if p is not None and p.requires_grad]
        if self.lean is not None and not params and not xr.requires_grad and torch.is_grad_enabled():
            xr = xr.requires_grad_()          # so backward still reaches this layer's own update
        return _RotatedProduct.apply(self, xr, *params).to(x.dtype)

    def extra_repr(self):
        return f"in={self.in_features}, out={self.out_features}, block={self.block}, mode={self.mode}"

    # ---- file format ---------------------------------------------------------------------
    @torch.no_grad()
    def packed(self):
        """Return (weight uint32, scales float16, biases float16) as the pack stores them."""
        codes = self.codes
        mask = self.keep_mask()
        if mask is not None:
            codes = codes * (mask > 0.5).to(codes.dtype)
        c = (codes.to(torch.int64) + 1).reshape(codes.shape[0], -1, pack.CODES_PER_WORD)
        shifts = (2 * torch.arange(pack.CODES_PER_WORD, device=c.device)).view(1, 1, -1)
        words = (c << shifts).sum(-1).cpu().numpy().astype(np.uint32)
        s = self.scales.detach().to(torch.float16).cpu().numpy()
        return words, s, (-s).astype(np.float16)


@torch.no_grad()
def read_packed(path, header, start, base, device, chunk_rows=16384):
    """codes (int8), scales (float32), signs (float32) of one packed module, on `device`."""
    words = pack.read_tensor(path, header, start, base + ".weight")
    shifts = (2 * torch.arange(pack.CODES_PER_WORD, device=device)).view(1, 1, -1)
    out = []
    for r in range(0, words.shape[0], chunk_rows):
        w = torch.from_numpy(np.array(words[r:r + chunk_rows]).astype(np.int64)).to(device)
        out.append((((w.unsqueeze(-1) >> shifts) & 3) - 1).reshape(w.shape[0], -1).to(torch.int8))
    scales = torch.from_numpy(np.array(pack.read_tensor(path, header, start, base + ".scales"))).to(device).float()
    signs = torch.from_numpy(np.array(pack.read_tensor(path, header, start, base + ".signs"))).to(device)
    return torch.cat(out), scales, signs


def hf_module_name(pack_path):
    """'model.layers.3.mlp.up_proj' -> 'model.language_model.layers.3.mlp.up_proj'."""
    return "lm_head" if pack_path == "lm_head" else "model.language_model." + pack_path[len("model."):]


@torch.no_grad()
def attach_ternary(model, pack_dir, skip=("model.embed_tokens",)):
    """Replace the dense linears of a converted Bonsai checkpoint by TernaryLinear modules.

    `model` is the dense checkpoint written by weights/convert_to_hf.py, already loaded. Its dense
    matrices are reused as the folded caches, so nothing is recomputed. Returns {hf name: module}.
    """
    cfg = json.load(open(f"{pack_dir}/config.json"))
    path = f"{pack_dir}/model.safetensors"
    header, start = pack.read_header(path)
    modules = dict(model.named_modules())
    out = {}
    for rec in cfg["modules"]:
        if rec["path"] in skip:
            continue
        name = hf_module_name(rec["path"])
        old = modules[name]
        codes, scales, signs = read_packed(path, header, start, "language_model." + rec["path"], old.weight.device)
        new = TernaryLinear(codes, scales, signs, rec["block"], folded=old.weight.data, out_dtype=old.weight.dtype)
        parent = modules[name.rsplit(".", 1)[0]] if "." in name else model
        setattr(parent, name.rsplit(".", 1)[-1], new)
        out[name] = new
    return out


def export_pack(ternary_modules, src_pack_dir, out_dir):
    """Write a new MLX pack: the source pack with every TernaryLinear's current state written back.

    Full-precision tensors are copied unchanged from the source pack (editing those is not
    exported yet).
    """
    from safetensors.numpy import save_file
    import shutil
    os.makedirs(out_dir, exist_ok=True)
    src = f"{src_pack_dir}/model.safetensors"
    header, start = pack.read_header(src)
    tensors = {k: np.array(pack.read_tensor(src, header, start, k)) for k in header}
    for name, mod in ternary_modules.items():
        base = "language_model.lm_head" if name == "lm_head" else "language_model.model." + name[len("model.language_model."):]
        words, scales, biases = mod.packed()
        assert tensors[base + ".weight"].shape == words.shape, name
        tensors[base + ".weight"], tensors[base + ".scales"], tensors[base + ".biases"] = words, scales, biases
    save_file(tensors, f"{out_dir}/model.safetensors", metadata={"format": "mlx"})
    for f in os.listdir(src_pack_dir):
        if f != "model.safetensors" and os.path.isfile(f"{src_pack_dir}/{f}"):
            shutil.copy(f"{src_pack_dir}/{f}", f"{out_dir}/{f}")
