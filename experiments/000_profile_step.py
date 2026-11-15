# Where does a training step spend its time? (task tuner, multipliers of layers 4..19)
import time
import torch
from weightlab.tune import TaskTuner, point_loss, answer_targets

train = lab.data("gen:benchdata/pointing/train_s101", n=3000)
B = lab.B


def sync():
    torch.cuda.synchronize()
    return time.time()


it = train[3]
inputs, n_prompt = lab._inputs(B, it, lab.answer_text(it))
print("tokens", inputs["input_ids"].shape[1])
with torch.no_grad():
    for label in ("forward, folded, no grad", "again"):
        t = sync(); B(**inputs, use_cache=False); print("%-46s %.2fs" % (label, sync() - t))
T = TaskTuner(lab, list(range(4, 20)))
mods = T._modules()
for m in mods:
    m.start_training(codes=False, scales=True, keep_hard=True, compute_dtype=torch.bfloat16)
with torch.no_grad():
    t = sync(); B(**inputs, use_cache=False); print("%-46s %.2fs" % ("forward, rotated 4..19, builds the weights", sync() - t))
    t = sync(); B(**inputs, use_cache=False); print("%-46s %.2fs" % ("forward, rotated 4..19, weights kept", sync() - t))
t = sync(); logits = B(**inputs, use_cache=False).logits[0, n_prompt - 1:-1]; print("%-46s %.2fs" % ("forward with graph", sync() - t))
loss = point_loss(logits, answer_targets(it, inputs["input_ids"][0, n_prompt:]))
t = sync(); loss.backward(); print("%-46s %.2fs" % ("backward", sync() - t))
for m in mods:
    m.after_step()
with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA]) as prof:
    logits = B(**inputs, use_cache=False).logits[0, n_prompt - 1:-1]
    loss = point_loss(logits, answer_targets(it, inputs["input_ids"][0, n_prompt:]))
    loss.backward()
    torch.cuda.synchronize()
print(prof.key_averages().table(sort_by="self_cuda_time_total", row_limit=22, max_name_column_width=44)[:6000])
print(prof.key_averages().table(sort_by="self_cpu_time_total", row_limit=12, max_name_column_width=44)[:3500])
for m in mods:
    m.log_gain = None
    m.bake()
torch.cuda.empty_cache()
