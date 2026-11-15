"""Which parts of Bonsai, restored to the parent's full-precision weights, restore pointing?

usage: swap_eval.py <bonsai-dense-dir> <parent-dir> [--n 50] [--max-side 1280]
                    [--configs none,all,lm_head,...] [--out FILE.jsonl]

Bonsai (converted to a dense checkpoint, see convert_to_hf.py) and its parent Qwen3.5-9B have
identical shapes and live in the same basis, so any subset of Bonsai's tensors can be replaced
by the parent's. For each named subset this script swaps those tensors in, scores pointing on
the same ScreenSpot-v2 samples, and swaps them back. A subset whose swap restores accuracy is
where the ternary conversion did its damage.

Greedy decoding, thinking off, screenshots downscaled to --max-side on the long side.
"""
import argparse
import collections
import glob
import json
import os
import re
import time

import torch
from PIL import Image
from safetensors import safe_open
from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

ROOT = os.path.expanduser("~/bonsai")
PROMPT = (
    "Output the center point of the position corresponding to the following instruction: \n"
    "{instruction}. \n\n"
    "The output should just be the coordinates of a point, in the format [x,y]. "
    "Additionally, if the task is infeasible (e.g., the task is not related to the image), "
    "the output should be [-1,-1]."
)
LM = "model.language_model."


def in_layers(lo, hi):
    return lambda k: (m := re.match(r"model\.language_model\.layers\.(\d+)\.", k)) is not None and lo <= int(m.group(1)) <= hi


SMALL_FP = ("layernorm.weight", "norm.weight", "A_log", "dt_bias", "conv1d.weight", "in_proj_a.weight", "in_proj_b.weight")
CONFIGS = collections.OrderedDict([
    ("none", lambda k: False),
    ("all", lambda k: True),
    ("language_model", lambda k: k.startswith(LM) or k == "lm_head.weight"),
    ("vision", lambda k: k.startswith("model.visual.")),
    ("lm_head", lambda k: k == "lm_head.weight"),
    ("embed", lambda k: k == LM + "embed_tokens.weight"),
    ("head+embed", lambda k: k in ("lm_head.weight", LM + "embed_tokens.weight")),
    ("small_fp", lambda k: k.startswith(LM) and k.endswith(SMALL_FP)),
    ("layers_0-7", in_layers(0, 7)),
    ("layers_8-15", in_layers(8, 15)),
    ("layers_16-23", in_layers(16, 23)),
    ("layers_24-31", in_layers(24, 31)),
    ("full_attn", lambda k: ".self_attn." in k and k.startswith(LM)),
    ("linear_attn", lambda k: ".linear_attn." in k),
    ("mlp", lambda k: ".mlp." in k and k.startswith(LM)),
])


def load_samples(n, max_side):
    items = []
    for split in ("desktop", "mobile", "web"):
        for i, it in enumerate(json.load(open(f"{ROOT}/ssv2/screenspot_{split}_v2.json"))):
            x, y, w, h = it["bbox"]
            items.append({"id": f"{split}_{i:04d}", "path": f"{ROOT}/ssv2/screenspotv2_image/{it['img_filename']}",
                          "bbox": [x, y, x + w, y + h], "instruction": it["instruction"], "group": split})
    items.sort(key=lambda x: x["id"])
    step = len(items) / n
    out = []
    for it in (items[int(i * step)] for i in range(n)):
        im = Image.open(it["path"]).convert("RGB")
        it["size"] = im.size
        scale = max_side / max(im.size) if max_side else 1
        if scale < 1:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        it["image"] = im
        out.append(it)
    return out


class Tensors:
    """Lazy access to a sharded safetensors checkpoint by tensor name."""

    def __init__(self, d):
        self.d = d
        self.map = json.load(open(f"{d}/model.safetensors.index.json"))["weight_map"]
        self.handles = {}

    def get(self, k):
        path = f"{self.d}/{self.map[k]}"
        if path not in self.handles:
            self.handles[path] = safe_open(path, framework="pt")
        return self.handles[path].get_tensor(k)


@torch.inference_mode()
def score(model, processor, samples):
    hits, dist, digits, per_group = 0, [], collections.Counter(), collections.defaultdict(list)
    for it in samples:
        messages = [{"role": "user", "content": [
            {"type": "image", "image": it["image"]},
            {"type": "text", "text": PROMPT.format(instruction=it["instruction"].rstrip("."))}]}]
        inputs = processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True,
            return_tensors="pt", enable_thinking=False).to(model.device)
        out = model.generate(**inputs, max_new_tokens=16, do_sample=False)
        text = processor.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
        hit = False
        if len(nums) >= 2:
            w, h = it["size"]
            b = it["bbox"]
            px, py = nums[0] * w / 1000, nums[1] * h / 1000
            hit = b[0] <= px <= b[2] and b[1] <= py <= b[3]
            cx, cy = 1000 * (b[0] + b[2]) / 2 / w, 1000 * (b[1] + b[3]) / 2 / h
            dist.append(((nums[0] - cx) ** 2 + (nums[1] - cy) ** 2) ** 0.5)
            digits.update(str(int(v))[-1] for v in nums[:2])
        hits += hit
        per_group[it["group"]].append(hit)
    dist.sort()
    return {"acc": hits / len(samples), "median_dist": dist[len(dist) // 2] if dist else None,
            "by_group": {g: sum(v) / len(v) for g, v in sorted(per_group.items())},
            "last_digits": "".join(f"{d}:{digits.get(d, 0)} " for d in "0123456789").strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bonsai")
    ap.add_argument("parent")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--max-side", type=int, default=1280)
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--out", default=f"{ROOT}/eval/swap_eval.jsonl")
    args = ap.parse_args()

    samples = load_samples(args.n, args.max_side)
    processor = AutoProcessor.from_pretrained(args.bonsai)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(args.bonsai, dtype=torch.bfloat16, device_map="cuda").eval()
    params = dict(model.named_parameters())
    bonsai, parent = Tensors(args.bonsai), Tensors(args.parent)
    print(f"{len(samples)} samples, max side {args.max_side}; {len(params)} tensors", flush=True)

    for name in args.configs.split(","):
        keys = [k for k in params if CONFIGS[name](k) and k in parent.map]
        for k in keys:
            params[k].data.copy_(parent.get(k).to(params[k].device, params[k].dtype))
        started = time.time()
        r = score(model, processor, samples)
        for k in keys:
            params[k].data.copy_(bonsai.get(k).to(params[k].device, params[k].dtype))
        n_swapped = sum(params[k].numel() for k in keys)
        r.update(config=name, tensors=len(keys), weights_swapped=n_swapped, seconds=round(time.time() - started))
        with open(args.out, "a") as f:
            f.write(json.dumps(r) + "\n")
        print(f"{name:16s} acc {100 * r['acc']:5.1f}%  median dist {r['median_dist'] or 0:6.1f}  "
              f"swapped {len(keys):4d} tensors ({n_swapped / 1e9:5.2f}B weights)  "
              f"{' '.join(f'{g} {100 * a:.0f}%' for g, a in r['by_group'].items())}  "
              f"digits {r['last_digits']}  [{r['seconds']}s]", flush=True)


main()
