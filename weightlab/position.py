"""Screen position written into the image tokens where they enter the language model (test P1, 15 Nov).

For each image token: the centre of its screen square in normalised coordinates (x, y in 0..1), sine and
cosine at 32 frequencies per axis (128 numbers), one full-precision linear layer to the model width that
starts at zero (so the model is unchanged until it is trained). Normalised coordinates make it
independent of the image size. Installed with two hooks: one notes where the image tokens are and the
grid they form, the other adds the module's output to their vectors on the way into the language model.
"""
import torch
import torch.nn as nn
from safetensors.torch import load_file, save_file

from .head import fourier_position


class PositionInput(nn.Module):
    def __init__(self, model):
        super().__init__()
        d = model.config.text_config.hidden_size
        self.lin = nn.Linear(128, d)
        nn.init.zeros_(self.lin.weight); nn.init.zeros_(self.lin.bias)
        self.to(model.device).float()
        self.seen, self.hooks = None, []
        self.hooks.append(model.model.register_forward_pre_hook(self._note, with_kwargs=True))
        self.hooks.append(model.model.language_model.register_forward_pre_hook(self._add, with_kwargs=True))

    def _note(self, module, args, kwargs):
        mm, grid = kwargs.get("mm_token_type_ids"), kwargs.get("image_grid_thw")
        self.seen = None
        if mm is not None and grid is not None and grid.shape[0] == 1:
            _, gh, gw = grid[0].tolist()
            self.seen = ((mm[0] == 1).nonzero().squeeze(-1), gh // 2, gw // 2, mm.shape[1])

    def _add(self, module, args, kwargs):
        e = kwargs.get("inputs_embeds")
        if self.seen is None or e is None or e.shape[1] != self.seen[3]:
            return None                                   # later steps of a generation carry one token only
        img, rows, cols, _ = self.seen
        if img.numel() != rows * cols:
            return None
        ys, xs = torch.meshgrid(torch.arange(rows, device=e.device), torch.arange(cols, device=e.device), indexing="ij")
        c = torch.stack(((xs.flatten() + 0.5) / cols, (ys.flatten() + 0.5) / rows), dim=-1).float()
        add = torch.zeros_like(e)
        add[0, img] = self.lin(fourier_position(c)).to(e.dtype)
        kwargs["inputs_embeds"] = e + add
        return args, kwargs

    def save(self, path):
        save_file({"weight": self.lin.weight.detach().cpu(), "bias": self.lin.bias.detach().cpu()}, path)

    def remove(self):
        for h in self.hooks:
            h.remove()
        self.hooks = []
