"""Load a patch (the tensors that differ from PrismML's original pack) into the lab's Bonsai.

The inverse of weights/make_patch.py. A patch is how a trained state travels: to another
machine's lab (here), to the MLX runtime (playground/server.py) and to a GGUF
(weights/export_gguf.py). The original pack plus a patch of a few hundred MB is the whole model.
"""
import numpy as np
import torch
from safetensors import safe_open

from . import ternary

NORM_SUFFIXES = (".input_layernorm.weight", ".post_attention_layernorm.weight",
                 "model.norm.weight", ".q_norm.weight", ".k_norm.weight")


@torch.no_grad()
def apply_patch(lab, path):
    """Returns counts of what was replaced. The model must be loaded as "B" (lab.B)."""
    model = lab.B
    params = dict(model.named_parameters())
    n = {"multipliers": 0, "codes": 0, "small": 0}
    shifts = None
    with safe_open(path, "pt") as f:
        for k in f.keys():
            if k.endswith(".biases"):                     # always -scales; the lab derives it
                continue
            assert k.startswith("language_model."), k
            rest = k[len("language_model."):]
            base, leaf = rest.rsplit(".", 1)
            name = ternary.hf_module_name(base)
            t = f.get_tensor(k)
            if name in lab.tern and leaf == "scales":
                m = lab.tern[name]
                m.scales.data.copy_(t.float().to(m.scales.device)); m.invalidate(); n["multipliers"] += 1
            elif name in lab.tern and leaf == "weight":
                m = lab.tern[name]
                w = torch.from_numpy(t.numpy().astype(np.int64)).to(m.codes.device)
                if shifts is None or shifts.device != w.device:
                    shifts = (2 * torch.arange(16, device=w.device)).view(1, 1, -1)
                m.codes.copy_((((w.unsqueeze(-1) >> shifts) & 3) - 1).reshape(w.shape[0], -1).to(torch.int8)); m.invalidate(); n["codes"] += 1
            else:
                t = t.float()
                if any(k.endswith(s) for s in NORM_SUFFIXES):
                    t = t - 1.0                           # the pack stores 1 + w
                elif k.endswith("conv1d.weight"):
                    t = t.movedim(1, 2)                   # (C, K, 1) -> (C, 1, K)
                p = params[ternary.hf_module_name(base) + "." + leaf]
                assert p.shape == t.shape, (k, tuple(p.shape), tuple(t.shape))
                p.data.copy_(t.to(p.device, p.dtype)); n["small"] += 1
    torch.cuda.empty_cache()
    return n
