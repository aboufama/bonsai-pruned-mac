"""The memory-light training path must give the same gradients as plain autograd."""
import os, sys
import torch
import torch.nn.functional as F
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from weightlab.ternary import TernaryLinear, fwht, GROUP

torch.manual_seed(0)
rows, width, block = 24, 512, 256
codes = torch.randint(-1, 2, (rows, width), dtype=torch.int8)
scales = torch.rand(rows, width // GROUP) * 0.1 + 0.01
signs = torch.where(torch.rand(width) > 0.5, 1.0, -1.0)
m = TernaryLinear(codes, scales, signs, block, out_dtype=torch.float32)
x = torch.randn(3, 7, width, requires_grad=True)
target = torch.randn(3, 7, rows)

from weightlab.ternary import rotate
probe = torch.randn(5, 3, width)
err = (rotate(probe, block) - fwht(probe, block)).abs().max().item()
print(f"one-product rotation vs staged transform: {err:.2e}")
assert err < 1e-4

# folded and rotated modes agree before any training
y_folded = m(x)
m.mode = "rotated"
err = (m(x) - y_folded).abs().max().item()
print(f"untrained: folded vs rotated output differs by {err:.2e}")
assert err < 1e-4
m.start_training(codes=True, scales=True)
with torch.no_grad():
    m.latent.add_(torch.randn_like(m.latent) * 0.3)      # move latents off the grid
    m.log_gain.add_(torch.randn_like(m.log_gain) * 0.1)

loss = (m(x) - target).pow(2).sum()
g_new = torch.autograd.grad(loss, [x, m.latent, m.log_gain])

xr = fwht(x * m.signs, block)
loss_ref = (F.linear(xr, m.rotated_weight()) - target).pow(2).sum()
g_ref = torch.autograd.grad(loss_ref, [x, m.latent, m.log_gain])
for name, a, b in zip(("input", "latent", "log_gain"), g_new, g_ref):
    err = (a - b).abs().max().item() / b.abs().max().item()
    print(f"{name:9s} max relative difference {err:.2e}")
    assert err < 1e-4, name
assert abs(loss.item() - loss_ref.item()) < 1e-3 * abs(loss_ref.item())

# the fast path (big products in bfloat16) stays close to the exact gradients
m.compute_dtype = torch.bfloat16
g_fast = torch.autograd.grad((m(x) - target).pow(2).sum(), [x, m.latent, m.log_gain])
for name, a, b in zip(("input", "latent", "log_gain"), g_fast, g_ref):
    cos = torch.nn.functional.cosine_similarity(a.flatten(), b.flatten(), dim=0).item()
    print(f"{name:9s} bfloat16 products: cosine to exact gradient {cos:.5f}")
    assert cos > 0.999, name
m.compute_dtype = None

# the built-in optimiser for the latents follows torch's Adam
def run(lean):
    torch.manual_seed(1)
    mm = TernaryLinear(codes.clone(), scales.clone(), signs, block, out_dtype=torch.float32)
    ps = mm.start_training(codes=True, scales=False, lean=dict(lr=0.01, b2=0.95, state=torch.float32) if lean else None)
    opt = None if lean else torch.optim.Adam(ps, lr=0.01, betas=(0.9, 0.95), eps=1e-12)
    xx = torch.randn(4, 9, width)
    goal = torch.randn(4, 9, rows)
    for _ in range(5):
        loss = (mm(xx) - goal).pow(2).sum()
        if opt:
            opt.zero_grad(); loss.backward(); opt.step(); mm.after_step()
        else:
            loss.backward(); mm.after_step()
    return mm.latent.detach().clone()

a_, b_ = run(True), run(False)
err = (a_ - b_).abs().max().item()
moved = (b_ - codes.float()).abs().max().item()
print(f"built-in latent optimiser vs torch Adam after 5 steps: max difference {err:.2e} (latents moved up to {moved:.3f})")
assert err < 2e-3 and moved > 0.02

# baking writes the trained state back and the folded matrix matches the trained forward
y_train = m(x).detach()
changed = m.bake()
assert m.latent is None and m.log_gain is None and m.mode == "folded"
err = (m(x) - y_train).abs().max().item()
print(f"codes changed {changed}; folded output after bake differs by {err:.2e}")
assert err < 1e-4
print("OK")
