# Smoke test of the end-to-end block trainer, starting from the multipliers tuned in 005.
import time
import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab.e2e import BlockTrainer

train2 = lab.data("gen:benchdata/pointing/train_s202", n=6000)
print("train_s202:", len(train2), "cases on", len({t["path"] for t in train2}), "screens")
E = BlockTrainer(lab, 4, 19, teacher="V")
state005 = E.D.save(range(4, 20), f"{lab.dir}/ckpt/tune005_L4-19.safetensors")
r = fB.evaluate(4); fB.discard(); print("start (005 state): dev p_hit %.4f" % r["p_hit"])
print("score() with the block closed:", {k: round(v, 3) for k, v in E.score(dev[:6]).items()})
E.open(lr_codes=4e-3)
print("opened; GPU %.1f GB" % (torch.cuda.memory_allocated() / 1e9))
print(E.train(train2[:8], 8, total_steps=600, report_every=4))
print("score() with the block open:  ", {k: round(v, 3) for k, v in E.score(dev[:6]).items()})
print(E.close())
r = fB.evaluate(4); fB.discard(); print("after 8 steps, written back: dev p_hit %.4f" % r["p_hit"])
E.D.restore(state005)
lab.stack.pop()
r = fB.evaluate(4); fB.discard(); print("restored to the 005 state: dev p_hit %.4f" % r["p_hit"])
print("GPU %.1f GB allocated, %.1f GB reserved" % (torch.cuda.memory_allocated() / 1e9, torch.cuda.memory_reserved() / 1e9))
