"""How far is each Bonsai tensor (dense, original basis) from the same tensor in the parent?

usage: compare_weights.py <bonsai-dense-dir> <parent-dir> [--out FILE.tsv]

For every tensor both checkpoints have, prints relative error ||B - P|| / ||P|| and cosine
similarity, grouped by kind (averaged over layers) and, for the packed kinds, per layer.
Tells which parts PrismML left untouched (error about 0), which they retrained in full
precision, and how the ternary error is distributed over depth.
"""
import argparse
import collections
import json
import re

import torch
from safetensors import safe_open


def index(d):
    return json.load(open(f"{d}/model.safetensors.index.json"))["weight_map"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bonsai")
    ap.add_argument("parent")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    bi, pi = index(args.bonsai), index(args.parent)
    keys = sorted(set(bi) & set(pi))
    print(f"tensors in both: {len(keys)}; only in parent: {len(set(pi) - set(bi))}; only in bonsai: {len(set(bi) - set(pi))}")
    handles = {}

    def get(d, idx, k):
        path = f"{d}/{idx[k]}"
        if path not in handles:
            handles[path] = safe_open(path, framework="pt")
        return handles[path].get_tensor(k)

    rows = []
    for k in keys:
        b = get(args.bonsai, bi, k).to("cuda", torch.float32)
        p = get(args.parent, pi, k).to("cuda", torch.float32)
        if b.shape != p.shape:
            print("shape mismatch", k, tuple(b.shape), tuple(p.shape))
            continue
        rel = ((b - p).norm() / p.norm().clamp_min(1e-12)).item()
        cos = torch.nn.functional.cosine_similarity(b.flatten(), p.flatten(), dim=0).item()
        rows.append((k, rel, cos, p.numel()))
    if args.out:
        with open(args.out, "w") as f:
            f.write("tensor\trel_err\tcosine\tnumel\n")
            for r in rows:
                f.write("%s\t%.6f\t%.6f\t%d\n" % r)

    kinds = collections.defaultdict(list)
    for k, rel, cos, n in rows:
        kinds[re.sub(r"\.\d+\.", ".N.", k)].append((rel, cos))
    print("\nkind                                                              n   rel_err  cosine")
    for kind, v in sorted(kinds.items()):
        if "visual.blocks" in kind:
            continue
        print(f"{kind[:64]:64s} {len(v):3d}  {sum(x[0] for x in v) / len(v):7.4f}  {sum(x[1] for x in v) / len(v):6.4f}")
    vis = [(rel, cos) for k, rel, cos, n in rows if k.startswith("model.visual.")]
    if vis:
        print(f"{'model.visual.* (all)':64s} {len(vis):3d}  {sum(x[0] for x in vis) / len(vis):7.4f}  {sum(x[1] for x in vis) / len(vis):6.4f}"
              f"   max rel_err {max(x[0] for x in vis):.6f}")

    print("\nper-layer relative error of the large projections (mean over the layer's packed tensors)")
    per = collections.defaultdict(list)
    for k, rel, cos, n in rows:
        m = re.search(r"layers\.(\d+)\.(mlp|self_attn|linear_attn)\.\w+_?proj\w*\.weight$", k)
        if m and n > 1_000_000:
            per[int(m.group(1))].append(rel)
    print(" ".join(f"L{i}:{sum(v) / len(v):.3f}" for i, v in sorted(per.items())))


main()
