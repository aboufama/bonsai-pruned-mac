"""Convert a Bonsai 2 MLX pack into a standard dense Qwen3.5 checkpoint for transformers.

usage: convert_to_hf.py <mlx-pack-dir> <qwen3.5-reference-dir> <out-dir>

Every packed (ternary, rotated) layer is folded into an ordinary dense matrix in the model's
original basis (see pack.py), so the result loads with the stock Qwen3_5ForConditionalGeneration
class and can be compared tensor-for-tensor and activation-for-activation with Qwen3.5-9B and
its fine-tunes. Dense weights are stored as float16. This checkpoint is for analysis and as a
teacher-comparison baseline; training works on the packed form (codes + scales), not on this.

The reference directory supplies config.json and the processor/tokenizer files.
"""
import json
import math
import os
import shutil
import sys

import numpy as np
import torch
from safetensors.torch import save_file

import pack

NORM_SUFFIXES = (".input_layernorm.weight", ".post_attention_layernorm.weight",
                 "model.norm.weight", ".q_norm.weight", ".k_norm.weight")
SHARD_BYTES = 4 * 1024**3
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def hf_name(key):
    if key.startswith("language_model.model."):
        return "model.language_model." + key[len("language_model.model."):]
    if key.startswith("language_model.lm_head."):
        return "lm_head." + key[len("language_model.lm_head."):]
    if key.startswith("vision_tower."):
        return "model.visual." + key[len("vision_tower."):]
    raise KeyError(key)


def fwht(x, block):
    shape = x.shape
    y = x.reshape(-1, block)
    h = 1
    while h < block:
        y = y.view(-1, block // (2 * h), 2, h)
        y = torch.stack((y[:, :, 0, :] + y[:, :, 1, :], y[:, :, 0, :] - y[:, :, 1, :]), dim=2)
        y = y.reshape(-1, block)
        h *= 2
    return (y / math.sqrt(block)).reshape(shape)


def fold_packed(path, header, start, base, block, chunk_rows=16384):
    """Dense float16 weight (rows, width) of one packed module, folded to the original basis."""
    words = pack.read_tensor(path, header, start, base + ".weight")
    scales = pack.read_tensor(path, header, start, base + ".scales")
    biases = pack.read_tensor(path, header, start, base + ".biases")
    signs = torch.from_numpy(np.array(pack.read_tensor(path, header, start, base + ".signs"))).to(DEV)
    shifts = (2 * torch.arange(pack.CODES_PER_WORD, device=DEV)).view(1, 1, -1)
    out = []
    for r in range(0, words.shape[0], chunk_rows):
        w = torch.from_numpy(np.array(words[r:r + chunk_rows]).astype(np.int64)).to(DEV)
        codes = ((w.unsqueeze(-1) >> shifts) & 3).reshape(w.shape[0], -1).float()
        s = torch.from_numpy(np.array(scales[r:r + chunk_rows])).to(DEV).float().repeat_interleave(pack.GROUP, dim=1)
        b = torch.from_numpy(np.array(biases[r:r + chunk_rows])).to(DEV).float().repeat_interleave(pack.GROUP, dim=1)
        dense = fwht(codes * s + b, block) * signs.unsqueeze(0)
        out.append(dense.half().cpu())
    return torch.cat(out)


def main():
    pack_dir, ref_dir, out_dir = sys.argv[1:4]
    os.makedirs(out_dir, exist_ok=True)
    cfg = json.load(open(f"{pack_dir}/config.json"))
    path = f"{pack_dir}/model.safetensors"
    header, start = pack.read_header(path)
    packed = {"language_model." + m["path"]: m["block"] for m in cfg["modules"]}

    shard, shard_bytes, shard_no, weight_map = {}, 0, 0, {}

    def flush():
        nonlocal shard, shard_bytes, shard_no
        if not shard:
            return
        name = f"model-{shard_no:05d}.safetensors"
        save_file(shard, f"{out_dir}/{name}", metadata={"format": "pt"})
        for k in shard:
            weight_map[k] = name
        print(f"wrote {name}: {len(shard)} tensors, {shard_bytes / 1e9:.2f} GB", flush=True)
        shard, shard_bytes, shard_no = {}, 0, shard_no + 1

    def add(name, tensor):
        nonlocal shard_bytes
        shard[name] = tensor.contiguous()
        shard_bytes += tensor.numel() * tensor.element_size()
        if shard_bytes >= SHARD_BYTES:
            flush()

    done = set()
    for base, block in sorted(packed.items()):
        add(hf_name(base + ".weight"), fold_packed(path, header, start, base, block))
        done.update(base + s for s in (".weight", ".scales", ".biases", ".signs"))
    for key in sorted(header):
        if key in done:
            continue
        t = torch.from_numpy(np.array(pack.read_tensor(path, header, start, key)))
        if any(key.endswith(s) for s in NORM_SUFFIXES):
            t = t - 1.0                      # pack stores 1 + w; transformers stores w
        elif key.endswith("conv1d.weight"):
            t = t.movedim(1, 2)              # (C, K, 1) -> (C, 1, K)
        elif key.endswith("patch_embed.proj.weight"):
            t = t.permute(0, 4, 1, 2, 3)     # (O, T, H, W, C) -> (O, C, T, H, W)
        add(hf_name(key), t.clone())
    flush()

    json.dump({"metadata": {"format": "pt"}, "weight_map": weight_map},
              open(f"{out_dir}/model.safetensors.index.json", "w"), indent=1)
    if not any(k.startswith("lm_head") for k in weight_map):
        print("no output head in the pack: the model ties it to the token embeddings")
    ref_cfg = json.load(open(f"{ref_dir}/config.json"))
    ref_cfg["text_config"]["mtp_num_hidden_layers"] = 0      # the pack ships no draft head
    json.dump(ref_cfg, open(f"{out_dir}/config.json", "w"), indent=1)
    for f in os.listdir(ref_dir):
        if f.endswith((".json", ".jinja", ".txt")) and f not in ("config.json", "model.safetensors.index.json"):
            shutil.copy(f"{ref_dir}/{f}", f"{out_dir}/{f}")
    print("tensors:", len(weight_map), "DONE")


main()
