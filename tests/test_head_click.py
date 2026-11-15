"""CrossHead's click output: shapes, and that it reads the state at the last prompt position.
CPU only, no model needed:  python3 tests/test_head_click.py"""
import os, sys
import torch
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from weightlab import head

torch.manual_seed(0)
d, r, rows, cols = 64, 16, 5, 7
N, Q = rows * cols, 3
ys, xs = torch.meshgrid(torch.arange(rows), torch.arange(cols), indexing="ij")
centres = torch.stack(((xs.flatten() + 0.5) / cols * 1000, (ys.flatten() + 0.5) / rows * 1000), dim=-1).float()
cell = torch.tensor([1000 / cols, 1000 / rows])

# question tokens laid out the way HeadBench.features does: ranges of different lengths, left-aligned
states = torch.randn(40, d)
lens, ranges, a = [4, 9, 6], [], 5
for n in lens:
    ranges.append((a, a + n)); a += n + 2
T = max(lens)
qtok = torch.zeros(Q, T, d); mask = torch.ones(Q, T, dtype=torch.bool)
for i, (x0, x1) in enumerate(ranges):
    qtok[i, :x1 - x0] = states[x0:x1]; mask[i, :x1 - x0] = False
keys = {0: torch.randn(N, d), 12: torch.randn(N, d)}
feats = (qtok, mask, keys, centres, cell, (rows, cols))
boxes = torch.tensor([[100., 100, 300, 300], [500, 500, 700, 800], [0, 0, 0, 0]])
present = torch.tensor([1., 1, 0])

for mode in ("query", "attention"):
    h = head.CrossHead((0, 12), d=d, r=r, click=mode)
    s, pt, click, est = h(*feats)
    assert s.shape == (Q, N) and pt.shape == (Q, 2) and click.shape == (Q,) and est.shape == (Q, N, 2)
    loss = head.head_loss(h, feats, boxes, present)
    loss.backward()
    assert torch.isfinite(loss)
    print(f"click={mode}: shapes ok, loss {loss.item():.3f}, {sum(p.numel() for p in h.parameters())} parameters")

h = head.CrossHead((0, 12), d=d, r=r, click="query")
last = torch.stack([states[b - 1] for _, b in ranges])          # what PointHead is given as q
want = h.click(h.cp(h.cn(last))).squeeze(-1)
got = h(*feats)[2]
assert torch.allclose(want, got, atol=1e-6), (want, got)
print("the click output reads the last prompt position")

h.zero_grad(); h(*feats)[2].sum().backward()
assert h.cp.weight.grad.abs().sum() > 0
assert not any(p.grad is not None and p.grad.abs().sum() > 0 for p in h.blocks.parameters())
print("the click loss trains only its own path, not the attention layers")

one = h(qtok[:1, :lens[0]], mask[:1, :lens[0]], keys, centres, cell, (rows, cols))     # scoring: one question
assert one[2].shape == (1,) and one[1].shape == (1, 2)
old = head.CrossHead((0, 12), d=d, r=r)                                               # the default
assert old.click[0].in_features == 2 * r and not hasattr(old, "cp")                    # heads saved before the change load here
p = head.PointHead(d=d, r=r)(last, keys[0], centres, cell)
g = head.RegressHead(d=d)(last, keys[0], centres, cell)
assert p[1].shape == (Q, 2) and p[2].shape == (Q,) and g[1].shape == (Q, 2) and g[2].shape == (Q,)
print("ok")
