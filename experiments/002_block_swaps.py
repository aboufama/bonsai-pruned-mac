# Experiment 002: does a contiguous MIDDLE block of full-precision layers restore pointing?
# Experiment 001 showed: parent layers 0..19 + Bonsai layers 20..31 restores pointing fully,
# while single layers or single kinds of module do not. Here Bonsai keeps its own early and
# late layers and only a middle block comes from the parent (P) or from UI-Venus (V).
# A block of 8 layers stored at 4 bits instead of 2 would add about 0.43 GB.
import json

d = lab.data("ssv2", n=32)
if "fB" not in globals():
    fB = lab.fast(d, "B")
LM = "model.language_model."
results = []


def block(lo, hi, source):
    pred = lambda k: any(f"{LM}layers.{i}." in k for i in range(lo, hi + 1))
    with lab.swap(pred, source) as n:
        r = fB.evaluate(lo, tag=f"block:{source}:{lo}-{hi}")
        fB.discard()
    r.update(lo=lo, hi=hi, source=source, weights=n)
    results.append(r)
    extra_gb = n * 2 / 8 / 1e9          # going from 2 to 4 bits per weight
    print("layers %2d..%2d from %s  %4.2fB weights (+%.2f GB at 4 bits)  p_hit %.3f  miss_nll %.3f  hundreds %.3f  tens %.3f  [%.1fs]" % (
        lo, hi, source, n / 1e9, extra_gb, r["p_hit"], r["miss_nll"], r["p_ok_hundreds"], r["p_ok_tens"], r["seconds"]), flush=True)


b = fB.baseline
print("Bonsai as is: p_hit %.3f  miss_nll %.3f   (parent on the same screens: p_hit 0.707)" % (b["p_hit"], b["miss_nll"]))
BLOCKS = [(12, 19), (8, 19), (16, 19), (12, 15), (14, 19), (10, 17), (8, 15), (12, 23), (4, 19)]
for source in ("P", "V"):
    print(f"\n-- middle blocks from {'the parent' if source == 'P' else 'UI-Venus'}")
    for lo, hi in BLOCKS:
        block(lo, hi, source)

print("\n-- reference: every layer from UI-Venus (Bonsai embeddings kept)")
with lab.swap(lambda k: k.startswith(LM + "layers.") or k == LM + "norm.weight" or k == "lm_head.weight", "V") as n:
    r = fB.evaluate(0, tag="all:V")
    fB.discard()
print("all layers from V  p_hit %.3f  miss_nll %.3f  hundreds %.3f  tens %.3f" % (r["p_hit"], r["miss_nll"], r["p_ok_hundreds"], r["p_ok_tens"]))
results.append(dict(r, lo=0, hi=31, source="V-all"))
json.dump(results, open(f"{lab.dir}/exp002_block_swaps.json", "w"), indent=1)
