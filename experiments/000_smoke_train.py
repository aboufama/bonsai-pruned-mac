# Smoke test of both trainers: a few steps each, then everything is put back and checked.
import time
import torch
from weightlab.distill import BlockDistiller
from weightlab.tune import TaskTuner

dev = lab.data("ssv2", n=32)
held = lab.data("ssv2", n=32, offset=23)
train = lab.data("gen:benchdata/pointing/train_s101", n=3000)
print("training cases", len(train), "screens", len({t["path"] for t in train}), "example:", train[0]["instruction"], train[0]["size"], lab.image(train[0]).size)
fB = lab.fast(dev, "B", every=4)
fH = lab.fast(held, "B", every=4)
t = time.time(); c = lab.canary(lab.B, tag="baseline"); print("canary baseline (%.1fs):" % (time.time() - t), c)

print("-- task tuner: multipliers of layers 4..19, 6 steps")
T = TaskTuner(lab, list(range(4, 20)))
snap = T.snapshot()
print(T.train(train[:6], 6, report_every=2))
r = fB.evaluate(4); fB.discard(); print("after 6 steps p_hit %.3f" % r["p_hit"])
T.restore(snap)
r = fB.evaluate(4); fB.discard(); print("restored p_hit %.4f, baseline %.4f" % (r["p_hit"], fB.baseline["p_hit"]))

print("-- block distiller: layers 4..5 toward UI-Venus, 6 steps")
D = BlockDistiller(lab, 4, 19, teacher="V")
print("GPU memory with teacher block %.1f GB" % (torch.cuda.memory_allocated() / 1e9))
orig = D.save(range(4, 20), f"{lab.dir}/ckpt/orig_L4-19.safetensors")
e = D.local_error(train[:2]); print("layer error (teacher inputs):", " ".join(f"{i}:{v:.2f}" for i, v in e.items()))
print(D.train([4, 5], train[:6], steps=6, report_every=2))
r = fB.evaluate(4); fB.discard(); print("after 6 steps p_hit %.3f" % r["p_hit"])
D.restore(orig)
r = fB.evaluate(4); fB.discard(); print("restored p_hit %.4f, baseline %.4f" % (r["p_hit"], fB.baseline["p_hit"]))
lab.stack.clear()
print("GPU memory %.1f GB allocated, %.1f GB reserved" % (torch.cuda.memory_allocated() / 1e9, torch.cuda.memory_reserved() / 1e9))
