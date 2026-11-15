"""Low-rank full-precision side paths beside ternary matrices (design L, 15 Nov).

For a ternary matrix W the layer computes y = W x; a side path adds B (A x) with A (rank x inputs) small
and random and B (outputs x rank) zero at the start, so the model is unchanged until training moves B.
The ternary codes and multipliers are not touched; the side paths are extra full-precision tensors
kept in their own safetensors file (names: <module name>.A, <module name>.B).
"""
import torch
import torch.nn.functional as F
from safetensors.torch import load_file, save_file


class SidePaths:
    def __init__(self, lab, layers, rank=16, seed=0):
        g = torch.Generator().manual_seed(seed)
        want = {f"layers.{i}." for i in layers}
        self.rank, self.A, self.B, self.hooks = rank, {}, {}, []
        for name, mod in lab.tern.items():
            if not any(w in name for w in want):
                continue
            rows, cols = mod.codes.shape
            dev = mod.codes.device
            A = torch.nn.Parameter((torch.randn(rank, cols, generator=g) / cols ** 0.5).to(dev))
            B = torch.nn.Parameter(torch.zeros(rows, rank, device=dev))
            self.A[name], self.B[name] = A, B
            self.hooks.append(mod.register_forward_hook(self._hook(A, B)))

    @staticmethod
    def _hook(A, B):
        def hook(mod, inputs, out):
            x = inputs[0]
            return out + F.linear(F.linear(x.to(A.dtype), A), B).to(out.dtype)
        return hook

    def params(self):
        return list(self.A.values()) + list(self.B.values())

    def count(self):
        return sum(p.numel() for p in self.params())

    def save(self, path):
        t = {n + ".A": p.detach().cpu() for n, p in self.A.items()}
        t.update({n + ".B": p.detach().cpu() for n, p in self.B.items()})
        save_file(t, path, metadata={"rank": str(self.rank)})
        return path

    @torch.no_grad()
    def load(self, path):
        t = load_file(path)
        for n in self.A:
            self.A[n].copy_(t[n + ".A"].to(self.A[n].device)); self.B[n].copy_(t[n + ".B"].to(self.B[n].device))

    @torch.no_grad()
    def zero(self):
        for b in self.B.values():
            b.zero_()

    def remove(self):
        for h in self.hooks:
            h.remove()
        self.hooks = []
