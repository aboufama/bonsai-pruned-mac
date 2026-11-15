# Experiment 001: which parts of Bonsai, given the parent's full-precision weights, restore pointing?
# Run in the weight-lab session:  client.py run experiments/001_swap_sweep.py
# Teacher-forced score on 32 ScreenSpot-v2 screens at 1280 px, using the layer cache.
import json

d = lab.data("ssv2", n=32)
if "fB" not in globals():
    fB = lab.fast(d, "B")
LM = "model.language_model."
N = 32
results = []


def run(name, pred, first, source="P"):
    with lab.swap(pred, source) as n:
        r = fB.evaluate(first, tag=f"swap:{source}:{name}")
        fB.discard()
    r.update(name=name, source=source, weights=n)
    results.append(r)
    print("%-26s %s  swapped %5.2fB  p_hit %.3f  miss_nll %.3f  hundreds %.3f  tens %.3f  [%.1fs]" % (
        name, source, n / 1e9, r["p_hit"], r["miss_nll"], r["p_ok_hundreds"], r["p_ok_tens"], r["seconds"]), flush=True)
    return r


b = fB.baseline
print("Bonsai as is:              p_hit %.3f  miss_nll %.3f  hundreds %.3f  tens %.3f" % (
    b["p_hit"], b["miss_nll"], b["p_ok_hundreds"], b["p_ok_tens"]))

SMALL = ("layernorm.weight", "norm.weight", "A_log", "dt_bias", "conv1d.weight", "in_proj_a.weight", "in_proj_b.weight")
print("\n-- by kind of module (all layers)")
run("everything in the LM", lambda k: k.startswith(LM) or k == "lm_head.weight", 0)
run("full attention q,k,v,o", lambda k: ".self_attn." in k and "proj" in k, 3)
run("full attention q,k only", lambda k: ".self_attn.q_proj" in k or ".self_attn.k_proj" in k, 3)
run("full attention v,o only", lambda k: ".self_attn.v_proj" in k or ".self_attn.o_proj" in k, 3)
run("linear attention proj", lambda k: ".linear_attn." in k and k.endswith(("in_proj_qkv.weight", "in_proj_z.weight", "out_proj.weight")), 0)
run("MLPs", lambda k: ".mlp." in k, 0)
run("small full-precision parts", lambda k: k.startswith(LM) and k.endswith(SMALL), 0)
run("output head", lambda k: k == "lm_head.weight", N)

print("\n-- one layer at a time (all of that layer's tensors)")
for i in range(N):
    run(f"layer {i:2d} ({lab.B.config.text_config.layer_types[i][:4]})", lambda k, i=i: f"{LM}layers.{i}." in k, i)

print("\n-- bottom-up: layers 0..k from the parent")
for k_ in (3, 7, 11, 15, 19, 23, 27):
    run(f"layers 0..{k_}", lambda k, k_=k_: any(f"{LM}layers.{i}." in k for i in range(k_ + 1)), 0)

print("\n-- top-down: layers k..31 from the parent")
for k_ in (28, 24, 20, 16, 12, 8, 4):
    run(f"layers {k_}..31", lambda k, k_=k_: any(f"{LM}layers.{i}." in k for i in range(k_, N)), k_)

json.dump(results, open(f"{lab.dir}/exp001_swap_sweep.json", "w"), indent=1)
print("\nsaved", f"{lab.dir}/exp001_swap_sweep.json")
