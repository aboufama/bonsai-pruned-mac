"""Turn the lab's state into a patch for PrismML's original Bonsai 2 pack.

usage: make_patch.py <original-pack-dir> <out.patch.safetensors> [--base-patch <patch>] [--pack <exported-pack-dir>] [--ckpt <lab checkpoint>.safetensors ...]

A patch is a safetensors file holding only the tensors that differ from the original pack, under
the pack's own names, so a runtime can load the original model and replace just those tensors
(`playground/server.py` does this in memory; `weights/export_gguf.py` writes them into a GGUF).

Sources, applied in order (later ones win):
  --base-patch  an existing patch for the same original pack: all of its tensors. Use it when a
           checkpoint covers only some layers of a state that was itself built on a patch (for
           example a block checkpoint of layers 4..19 trained from the v2 patch)
  --pack   a pack written by weightlab.ternary.export_pack: its multipliers and codes
  --ckpt   a checkpoint written by BlockDistiller.save / BlockTrainer.checkpoint: codes,
           multipliers and the small full-precision parts of the layers it covers

Only what actually differs from the original is written:
  <module>.scales, <module>.biases   float16; biases are -scales, as the pack stores them
  <module>.weight                    uint32 words of 16 two-bit codes, only for modules whose codes changed
  small full-precision tensors       float32, mapped back to the pack's conventions
                                     (norm weights are stored as 1 + w, conv1d as (C, K, 1))
"""
import argparse
import os
import sys

import numpy as np
from safetensors import safe_open
from safetensors.numpy import save_file

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pack  # noqa: E402

NORM_SUFFIXES = (".input_layernorm.weight", ".post_attention_layernorm.weight",
                 "model.norm.weight", ".q_norm.weight", ".k_norm.weight")


def pack_name(hf):
    """'model.language_model.layers.5.mlp.up_proj' -> 'language_model.model.layers.5.mlp.up_proj'."""
    if hf.startswith("lm_head"):
        return "language_model." + hf
    assert hf.startswith("model.language_model."), hf
    return "language_model.model." + hf[len("model.language_model."):]


def words_from_codes(codes):
    """int8 codes in {-1, 0, 1}, shape (rows, inputs) -> uint32 words, 16 codes each, lowest bits first."""
    c = (codes.astype(np.int64) + 1).reshape(codes.shape[0], -1, pack.CODES_PER_WORD)
    shifts = (2 * np.arange(pack.CODES_PER_WORD, dtype=np.int64)).reshape(1, 1, -1)
    return (c << shifts).sum(-1).astype(np.uint32)


def codes_from_words(words):
    shifts = (2 * np.arange(pack.CODES_PER_WORD, dtype=np.int64)).reshape(1, 1, -1)
    return (((words.astype(np.int64)[..., None] >> shifts) & 3) - 1).reshape(words.shape[0], -1).astype(np.int8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("original")
    ap.add_argument("out")
    ap.add_argument("--base-patch")
    ap.add_argument("--pack")
    ap.add_argument("--ckpt", action="append", default=[])
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    src = f"{args.original}/model.safetensors"
    hs, ss = pack.read_header(src)
    orig = lambda k: np.array(pack.read_tensor(src, hs, ss, k))
    patch, stats = {}, {"scales": 0, "codes": 0, "codes_changed": 0, "small": 0}

    def put_scales(base, scales):
        s16 = scales.astype(np.float16)
        if s16.tobytes() != orig(base + ".scales").tobytes():
            patch[base + ".scales"], patch[base + ".biases"] = s16, (-s16).astype(np.float16)
        else:
            patch.pop(base + ".scales", None); patch.pop(base + ".biases", None)

    def put_codes(base, codes):
        words = words_from_codes(codes)
        o = orig(base + ".weight")
        if words.tobytes() != o.tobytes():
            patch[base + ".weight"] = words
            stats["codes_changed"] += int((codes != codes_from_words(o)).sum())
        else:
            patch.pop(base + ".weight", None)

    if args.base_patch:
        with safe_open(args.base_patch, "np") as f:
            for k in f.keys():
                assert k in hs, f"{k} of the base patch is not in the original pack"
                patch[k] = f.get_tensor(k)

    if args.pack:
        new = f"{args.pack}/model.safetensors"
        hn, sn = pack.read_header(new)
        for k in sorted(hs):
            if k.endswith(".scales"):
                put_scales(k[:-7], np.array(pack.read_tensor(new, hn, sn, k)))
            elif k.endswith(".weight") and (k[:-7] + ".scales") in hs:
                w = np.array(pack.read_tensor(new, hn, sn, k))
                if w.tobytes() != orig(k).tobytes():
                    patch[k] = w
                    stats["codes_changed"] += int((codes_from_words(w) != codes_from_words(orig(k))).sum())

    if args.ckpt:
        import torch                              # only checkpoints need it (bfloat16)
    for path in args.ckpt:
        with safe_open(path, "pt") as f:                  # torch reader: the lab stores small parts in bfloat16
            get = lambda key: (lambda t: t.float().numpy() if t.is_floating_point() else t.numpy())(f.get_tensor(key))
            keys = list(f.keys())
            for k in keys:
                if k.endswith(".codes"):
                    base = pack_name(k[:-6])
                    put_codes(base, get(k))
                    put_scales(base, get(k[:-6] + ".scales"))
                elif not k.endswith(".scales"):
                    name = pack_name(k)
                    v = get(k).astype(np.float32)        # the value as the lab holds it
                    o = orig(name)
                    if any(name.endswith(s) for s in NORM_SUFFIXES):
                        t, o_lab = v + 1.0, o.astype(np.float32) - 1.0          # the pack stores 1 + w
                    elif name.endswith("conv1d.weight"):
                        t, o_lab = np.moveaxis(v, 2, 1), np.moveaxis(o.astype(np.float32), 1, 2)   # (C, 1, K) <-> (C, K, 1)
                    else:
                        t, o_lab = v, o.astype(np.float32)
                    assert o.shape == t.shape, (name, o.shape, t.shape)
                    # The lab holds these in bfloat16. An untouched tensor is exactly the original rounded
                    # to bfloat16; anything else was trained and is written. (Until 15 Nov a tensor was
                    # written only if it had moved by more than 4e-3 of its largest value, which dropped
                    # most trained small tensors: 122 of 165 on the 4B, select 0.700 -> 0.654.)
                    if np.array_equal(v, torch.from_numpy(np.ascontiguousarray(o_lab)).to(torch.bfloat16).float().numpy()):
                        patch.pop(name, None)
                    else:
                        patch[name] = t.astype(o.dtype)
    stats["scales"] = sum(k.endswith(".scales") for k in patch)
    stats["codes"] = sum(k.endswith(".weight") and (k[:-7] + ".scales") in hs for k in patch)
    stats["small"] = len(patch) - 2 * stats["scales"] - stats["codes"]
    layers = sorted({int(k.split("layers.")[1].split(".")[0]) for k in patch if "layers." in k})
    save_file(patch, args.out, metadata={"base": "prism-ml/" + os.path.basename(os.path.normpath(args.original)), "note": args.note,
                                         "stats": str(stats)})
    print(f"{args.out}: {len(patch)} tensors, {os.path.getsize(args.out) / 1e6:.0f} MB; "
          f"multipliers of {stats['scales']} matrices, codes of {stats['codes']} matrices "
          f"({stats['codes_changed']} individual codes changed), {stats['small']} small tensors; "
          f"layers {layers[0] if layers else '-'}..{layers[-1] if layers else '-'}, head {'yes' if any('lm_head' in k for k in patch) else 'no'}")


if __name__ == "__main__":
    main()
