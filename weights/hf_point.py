"""Run the grounding prompt through a transformers checkpoint and compare with stored answers.

usage: hf_point.py <checkpoint-dir> <reference.jsonl> [--n 12] [--dtype float32|bfloat16] [--max-pixels N]

<reference.jsonl> is a result file written by eval_ground.py / eval_sspro.py (ScreenSpot-Pro);
for each sample the script prints this checkpoint's answer next to the stored one and the target.
Used to prove that the dense conversion of Bonsai reproduces llama.cpp's Bonsai answers, and to
put Bonsai, Qwen3.5 and UI-Venus through one identical code path.
"""
import argparse
import glob
import json
import os
import re
import time

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

ROOT = os.path.expanduser("~/bonsai")
PROMPT = (
    "Output the center point of the position corresponding to the following instruction: \n"
    "{instruction}. \n\n"
    "The output should just be the coordinates of a point, in the format [x,y]. "
    "Additionally, if the task is infeasible (e.g., the task is not related to the image), "
    "the output should be [-1,-1]."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checkpoint")
    ap.add_argument("reference")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--dtype", default="float32")
    ap.add_argument("--max-pixels", type=int, default=2560 * 1600)
    args = ap.parse_args()

    items = {}
    for path in glob.glob(f"{ROOT}/sspro/annotations/*.json"):
        for it in json.load(open(path)):
            items[it["id"]] = it
    ref = [json.loads(line) for line in open(args.reference)]
    ref = [r for r in ref if items[r["id"]]["img_size"][0] * items[r["id"]]["img_size"][1] <= args.max_pixels][:args.n]

    processor = AutoProcessor.from_pretrained(args.checkpoint)
    started = time.time()
    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        args.checkpoint, dtype=getattr(torch, args.dtype), device_map="cuda")
    model.eval()
    print(f"loaded {args.checkpoint} as {args.dtype} in {time.time() - started:.0f}s", flush=True)

    same = hits = 0
    for r in ref:
        it = items[r["id"]]
        image = Image.open(f"{ROOT}/sspro/images/{it['img_filename']}").convert("RGB")
        messages = [{"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": PROMPT.format(instruction=it["instruction"].rstrip("."))}]}]
        inputs = processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True,
            return_tensors="pt", enable_thinking=False).to(model.device)
        started = time.time()
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=24, do_sample=False)
        text = processor.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", text)]
        point = nums[:2] if len(nums) >= 2 else None
        w, h = it["img_size"]
        b = it["bbox"]
        hit = bool(point) and b[0] <= point[0] * w / 1000 <= b[2] and b[1] <= point[1] * h / 1000 <= b[3]
        hits += hit
        same += point == r["point"]
        box = [round(1000 * b[0] / w), round(1000 * b[1] / h), round(1000 * b[2] / w), round(1000 * b[3] / h)]
        print(f"{r['id'][:26]:26s} here {point} | stored {r['point']} | target {box} | "
              f"{'HIT' if hit else 'miss'} | {inputs['input_ids'].shape[1]} tok {time.time() - started:.1f}s", flush=True)
    print(f"\nidentical to stored answers: {same}/{len(ref)}   hits here: {hits}/{len(ref)}   "
          f"stored hits: {sum(r['hit_norm'] for r in ref)}/{len(ref)}")


main()
