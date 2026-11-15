#!/usr/bin/env python
"""Write the vision file ("mmproj") that llama.cpp needs for images, from the vision tower inside the MLX pack.

    export_mmproj.py --pack ~/Bonsai-demo/models/Ternary-Bonsai-2-9B-mlx-2bit --out Ternary-Bonsai-2-9B-mmproj-F16.gguf

PrismML publishes this file next to their GGUFs. This script is for a machine that has the pack but not
that file: the pack carries the same vision tower (27 blocks and the merger, float16, about 0.9 GB), and the
file is the same for the original and for every edited language model.

It follows conversion/qwen3vl.py of PrismML's llama.cpp fork as run with --outtype f16: matrices keep the
pack's float16 values, vectors and the position table are float32, and the two time slices of the patch
convolution become two tensors. Needs the fork's gguf-py (--gguf-py).
"""
import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pack  # noqa: E402

BLOCK = {"attn.qkv": "attn_qkv", "attn.proj": "attn_out", "norm1": "ln1", "norm2": "ln2",
         "mlp.linear_fc1": "ffn_up", "mlp.linear_fc2": "ffn_down"}
FIXED = {"merger.linear_fc1": "mm.0", "merger.linear_fc2": "mm.2", "merger.norm": "v.post_ln",
         "pos_embed": "v.position_embd", "patch_embed.proj": "v.patch_embd"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pack", required=True, help="folder of the MLX pack (config.json, preprocessor_config.json, model.safetensors)")
    ap.add_argument("--out", required=True, help="the GGUF file to write (about 0.9 GB for the 9B)")
    ap.add_argument("--gguf-py", default=os.path.expanduser("~/Bonsai-demo/llama.cpp/gguf-py"), help="gguf-py folder of the fork")
    args = ap.parse_args()
    sys.path.insert(0, args.gguf_py)
    import gguf

    cfg = json.load(open(os.path.join(args.pack, "config.json")))
    pre = json.load(open(os.path.join(args.pack, "preprocessor_config.json")))
    vision, text = cfg["vision_config"], cfg["text_config"]
    if vision.get("deepstack_visual_indexes") or vision.get("temporal_patch_size", 2) != 2:
        sys.exit("export_mmproj: this vision tower has parts the script does not write")
    path = os.path.join(args.pack, "model.safetensors")
    header, start = pack.read_header(path)

    w = gguf.GGUFWriter(args.out, arch="clip")
    w.add_type(gguf.GGUFType.MMPROJ)
    w.add_name(f"{os.path.basename(os.path.normpath(args.pack))} vision tower")
    w.add_file_type(gguf.LlamaFileType.MOSTLY_F16)
    w.add_clip_has_vision_encoder(True)
    w.add_vision_projection_dim(text["hidden_size"])
    w.add_vision_image_size(int(vision["num_position_embeddings"] ** 0.5 * vision["patch_size"]))
    w.add_vision_patch_size(vision["patch_size"])
    w.add_vision_embedding_length(vision["hidden_size"])
    w.add_vision_feed_forward_length(vision["intermediate_size"])
    w.add_vision_block_count(vision["depth"])
    w.add_vision_head_count(vision["num_heads"])
    w.add_vision_image_mean(pre["image_mean"])
    w.add_vision_image_std(pre["image_std"])
    w.add_clip_projector_type(gguf.VisionProjectorType.QWEN3VL)
    w.add_vision_use_gelu(True)
    w.add_vision_spatial_merge_size(int(vision["spatial_merge_size"]))
    w.add_vision_attention_layernorm_eps(text.get("rms_norm_eps", 1e-6))
    w.add_vision_is_deepstack_layers([False] * vision["depth"])

    count = 0

    def add(name, arr):
        nonlocal count
        arr = np.asarray(arr)
        plain = arr.ndim <= 1 or name == "v.position_embd.weight"        # the converter keeps these float32
        w.add_tensor(name, np.ascontiguousarray(arr.astype(np.float32 if plain else np.float16)))
        count += 1

    for name in sorted(n for n in header if n.startswith("vision_tower.")):
        module, _, leaf = name[len("vision_tower."):].rpartition(".")
        arr = pack.read_tensor(path, header, start, name)
        m = re.fullmatch(r"blocks\.(\d+)\.(.+)", module)
        if m:
            add(f"v.blk.{m.group(1)}.{BLOCK[m.group(2)]}.{leaf}", arr)
        elif module == "patch_embed.proj" and leaf == "weight":
            a = np.asarray(arr).transpose(0, 4, 1, 2, 3)                 # MLX (out, t, h, w, in) -> (out, in, t, h, w)
            add("v.patch_embd.weight", a[:, :, 0])
            add("v.patch_embd.weight.1", a[:, :, 1])
        else:
            add(f"{FIXED[module]}.{leaf}", arr)
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()
    print(f"wrote {args.out}: {count} tensors, {os.path.getsize(args.out) / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
