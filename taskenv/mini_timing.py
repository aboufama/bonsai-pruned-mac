"""Speed of Bonsai 2 against ordinary 4-bit and 8-bit MLX builds of the same designs, on a Mac.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    ~/bonsai/venv/bin/python taskenv/mini_timing.py        # on the Mac mini, with nothing else running

Timed exactly as ~/bonsai/time_mini.py times Bonsai: the same screenshot (~/bonsai/sample.jpg),
the pointing prompt, 24 new tokens at most, at 1280 and 896 px, best of three. Reports seconds
per answer, tokens read and written per second, peak memory and size on disk, as JSON lines
and as ~/bonsai/time_refs.json.
"""
import gc
import json
import os
import time
from pathlib import Path

import mlx.core as mx
from mlx_vlm import generate, load
from mlx_vlm.prompt_utils import apply_chat_template
from PIL import Image

HOME = Path.home() / "bonsai"
PROMPT = ("Output the center point of the position corresponding to the following instruction: \n{instruction}. \n\n"
          "The output should just be the coordinates of a point, in the format [x,y]. Additionally, if the task is infeasible "
          "(e.g., the task is not related to the image), the output should be [-1,-1].")
MODELS = [("Bonsai 2 9B (ternary)", "models/Ternary-Bonsai-2-9B-mlx-2bit"), ("Qwen3.5-9B, 4-bit", "models/refs/Qwen3.5-9B-MLX-4bit"),
          ("Qwen3.5-9B, 8-bit", "models/refs/Qwen3.5-9B-8bit"), ("Bonsai 2 4B (ternary)", "models/Ternary-Bonsai-2-4B-mlx-2bit"),
          ("Qwen3.5-4B, 4-bit", "models/refs/Qwen3.5-4B-MLX-4bit")]


def disk_gb(path):
    return round(sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file() and ".cache" not in f.parts) / 1e9, 2)


def main():
    shot = Image.open(HOME / "sample.jpg").convert("RGB")
    rows = []
    for name, rel in MODELS:
        path = HOME / rel
        if not (path / "config.json").exists():
            print(json.dumps({"model": name, "missing": str(path)}), flush=True)
            continue
        mx.reset_peak_memory()
        t = time.time()
        model, processor = load(str(path))
        load_s = time.time() - t
        prompt = apply_chat_template(processor, model.config, PROMPT.format(instruction="Point at the Automate button"), num_images=1, enable_thinking=False)
        for side in (1280, 896):
            s = side / max(shot.size)
            file = HOME / f"t_{side}.png"
            shot.resize((round(shot.width * s), round(shot.height * s)), Image.LANCZOS).save(file)
            best = None
            for _ in range(3):
                t = time.time()
                out = generate(model, processor, prompt, [str(file)], max_tokens=24, temperature=0.0, verbose=False)
                r = {"model": name, "side": side, "seconds": round(time.time() - t, 2), "text": getattr(out, "text", str(out)).strip()[:30]}
                for k in ("prompt_tokens", "prompt_tps", "generation_tokens", "generation_tps"):
                    if getattr(out, k, None) is not None:
                        r[k] = round(float(getattr(out, k)), 1)
                if best is None or r["seconds"] < best["seconds"]:
                    best = r
            best.update(load_s=round(load_s, 1), peak_memory_gb=round(mx.get_peak_memory() / 1e9, 2), disk_gb=disk_gb(path))
            rows.append(best)
            print(json.dumps(best), flush=True)
        del model, processor
        gc.collect()
        mx.clear_cache()
    json.dump(rows, open(HOME / "time_refs.json", "w"), indent=1)
    head_file = HOME / "patches" / "bonsai2-4b-h1-dec2x768-L20-s6000.safetensors"
    if head_file.exists():                               # the pointing decoder on the first 20 layers of the 4B
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from taskenv.mlx_head import HeadModel
        m = HeadModel("mlx-4b-head", str(HOME), patch="bonsai2-4b-point-v2-mixed.patch.safetensors", head=str(head_file))
        for side in (1280, 896):
            s = side / max(shot.size)
            r = m.split_timing(shot.resize((round(shot.width * s), round(shot.height * s)), Image.LANCZOS), "Point at the Automate button")
            r.update(model="Bonsai 2 4B, pointing decoder on 20 layers", side=side, peak_memory_gb=round(mx.get_peak_memory() / 1e9, 2))
            rows.append(r)
            print(json.dumps(r), flush=True)
        json.dump(rows, open(HOME / "time_refs.json", "w"), indent=1)


if __name__ == "__main__":
    main()
