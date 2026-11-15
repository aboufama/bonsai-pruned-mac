#!/usr/bin/env python
"""Pointing playground: one screenshot, one instruction, up to three models, all on this Mac.

    ~/Bonsai-demo/.venv-vlm/bin/python playground/server.py        then open http://127.0.0.1:8791

Models (see MODELS below):
    new    Bonsai 2 9B with the repaired multipliers. It is the ORIGINAL pack plus a small patch
           file that replaces the multipliers of layers 4..31 and the output head in memory, so
           old and new share one 3.5 GB copy and switching between them takes a fraction of a second.
    old    Bonsai 2 9B exactly as PrismML ships it.
    other  a conventional model of about the same size on disk (Qwen3.5-4B at 4 bits), if it has
           been downloaded.

Nothing leaves the machine: the server listens on 127.0.0.1 only, and models run through mlx-vlm.
Models are loaded on first use and can be unloaded from the page.
"""
import base64
import gc
import io
import json
import os
import re
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from PIL import Image

HERE = Path(__file__).resolve().parent
HOME = Path(os.environ.get("BONSAI_HOME", Path.home() / "Bonsai-demo"))
PORT = int(os.environ.get("PORT") or os.environ.get("PLAYGROUND_PORT") or 8791)
IMAGE_TYPES = (".png", ".jpg", ".jpeg")


def sample_dir():
    """Where the example screenshots are: real Mac screenshots in ~/Bonsai-demo/samples when present
    (they come from public datasets, so they stay out of the repo), else the generated screens here."""
    for d in (HOME / "samples", HERE / "samples"):
        if d.is_dir() and any(p.suffix.lower() in IMAGE_TYPES for p in d.iterdir()):
            return d
    return HERE / "samples"
BASE_PACK = HOME / "models" / "Ternary-Bonsai-2-9B-mlx-2bit"
MODELS = {
    "new": {"label": "Bonsai 2 9B, repaired", "note": "ternary, 3.5 GB on disk; original weights plus retuned multipliers",
            "kind": "bonsai", "patch": HOME / "models" / "patches" / "bonsai2-9b-point-v1.patch.safetensors"},
    "old": {"label": "Bonsai 2 9B, original", "note": "ternary, 3.5 GB on disk; as PrismML ships it",
            "kind": "bonsai", "patch": None},
    "other": {"label": "Qwen3.5-4B, 4-bit", "note": "conventional 4-bit model, 3.1 GB on disk",
              "kind": "plain", "path": HOME / "models" / "Qwen3.5-4B-MLX-4bit",
              "get": "mlx-community/Qwen3.5-4B-MLX-4bit"},
}
# The grounding prompt of the Qwen3.5 family (the one UI-Venus's evaluator uses); answers are
# "[x, y]" on a 0-1000 scale over the image the model was shown.
PROMPT = (
    "Output the center point of the position corresponding to the following instruction: \n"
    "{instruction}. \n\n"
    "The output should just be the coordinates of a point, in the format [x,y]. "
    "Additionally, if the task is infeasible (e.g., the task is not related to the image), "
    "the output should be [-1,-1]."
)
FIRST_SIDE = 1280        # long side of the first look, the size a Clicky-style assistant sends
SECOND_SIDE = 1024       # long side the zoomed window is shown at
ZOOM = 3                 # the second look sees a window of 1/ZOOM of each side

lock = threading.Lock()              # one generation at a time
state = {"bonsai": None, "bonsai_set": "old", "orig": None, "patches": {}, "plain": {}, "images": {}}
tmp = Path(tempfile.mkdtemp(prefix="pointing-playground-"))


def available(key):
    m = MODELS[key]
    if m["kind"] == "bonsai":
        return BASE_PACK.is_dir() and (m["patch"] is None or m["patch"].is_file())
    return (m["path"] / "config.json").is_file()


def loaded(key):
    m = MODELS[key]
    return state["bonsai"] is not None if m["kind"] == "bonsai" else key in state["plain"]


def get_model(key):
    """Returns (model, processor), loading or re-patching as needed."""
    import mlx.core as mx
    from mlx.utils import tree_flatten
    from mlx_vlm import load
    m = MODELS[key]
    if m["kind"] == "plain":
        if key not in state["plain"]:
            state["plain"][key] = load(str(m["path"]))
        return state["plain"][key]
    if state["bonsai"] is None:
        state["bonsai"] = load(str(BASE_PACK))
        state["bonsai_set"], state["orig"] = "old", None
    model, processor = state["bonsai"]
    if state["bonsai_set"] != key:
        if key == "new":
            if "new" not in state["patches"]:
                state["patches"]["new"] = mx.load(str(m["patch"]))
            patch = state["patches"]["new"]
            if state["orig"] is None:                       # remember what the patch replaces
                flat = dict(tree_flatten(model.parameters()))
                missing = [n for n in patch if n not in flat]
                if missing:
                    raise RuntimeError(f"patch does not fit this pack: {missing[:3]}")
                state["orig"] = {n: flat[n] for n in patch}
            model.load_weights(list(patch.items()), strict=False)
        else:
            model.load_weights(list(state["orig"].items()), strict=False)
        mx.eval(model.parameters())
        state["bonsai_set"] = key
    return model, processor


def unload():
    import mlx.core as mx
    state.update(bonsai=None, bonsai_set="old", orig=None, patches={}, plain={})
    gc.collect()
    mx.clear_cache()


def ask(model, processor, image, instruction):
    """One look: returns ((x, y) on the 0-1000 scale of `image`, or None), raw text and timings."""
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template
    path = tmp / f"look-{threading.get_ident()}.png"
    image.save(path)
    prompt = apply_chat_template(processor, model.config, PROMPT.format(instruction=instruction.strip().rstrip(".")),
                                 num_images=1, enable_thinking=False)
    t = time.time()
    out = generate(model, processor, prompt, [str(path)], max_tokens=24, temperature=0.0, verbose=False)
    seconds = time.time() - t
    text = (out if isinstance(out, str) else getattr(out, "text", str(out))).strip()
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
    point = (nums[0], nums[1]) if len(nums) >= 2 and nums[0] >= 0 and nums[1] >= 0 else None
    info = {"seconds": round(seconds, 2), "text": text, "image": list(image.size)}
    for k in ("prompt_tokens", "prompt_tps", "generation_tokens", "generation_tps"):
        v = getattr(out, k, None)
        if v is not None:
            info[k] = round(float(v), 1)
    return point, info


def fit(image, side):
    s = side / max(image.size)
    return image if s >= 1 else image.resize((round(image.width * s), round(image.height * s)), Image.LANCZOS)


def point(key, image, instruction, second_look):
    """Run one model. All coordinates returned are fractions (0..1) of the full screenshot."""
    t0 = time.time()
    was_loaded = loaded(key)
    model, processor = get_model(key)
    result = {"model": key, "load_seconds": 0 if was_loaded else round(time.time() - t0, 1)}
    p1, first = ask(model, processor, fit(image, FIRST_SIDE), instruction)
    result["first"] = dict(first, point=None if p1 is None else [p1[0] / 1000, p1[1] / 1000])
    result["point"] = result["first"]["point"]
    if second_look and p1 is not None:
        W, H = image.size
        cw, ch = W / ZOOM, H / ZOOM
        cx = min(max(p1[0] / 1000 * W, cw / 2), W - cw / 2)
        cy = min(max(p1[1] / 1000 * H, ch / 2), H - ch / 2)
        x0, y0 = cx - cw / 2, cy - ch / 2
        crop = image.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch)))
        s = SECOND_SIDE / max(crop.size)
        crop = crop.resize((round(crop.width * s), round(crop.height * s)), Image.LANCZOS)
        p2, second = ask(model, processor, crop, instruction)
        result["second"] = dict(second, window=[x0 / W, y0 / H, cw / W, ch / H],
                                point=None if p2 is None else [(x0 + p2[0] / 1000 * cw) / W, (y0 + p2[1] / 1000 * ch) / H])
        if p2 is not None:
            result["point"] = result["second"]["point"]
    result["seconds"] = round(sum(r["seconds"] for r in (result["first"], result.get("second")) if r), 2)
    return result


def status():
    import mlx.core as mx
    return {"models": [{"id": k, "label": m["label"], "note": m["note"], "available": available(k), "loaded": loaded(k),
                        "get": m.get("get"), "path": str(m.get("path", ""))} for k, m in MODELS.items()],
            "memory_gb": round(mx.get_active_memory() / 1e9, 2), "first_side": FIRST_SIDE, "zoom": ZOOM}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, code, body, kind="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self.send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/status":
            return self.send(200, status())
        if path.startswith("/samples/"):
            f = (sample_dir() / Path(path).name)
            if f.is_file() and f.suffix.lower() in IMAGE_TYPES:
                return self.send(200, f.read_bytes(), "image/png" if f.suffix.lower() == ".png" else "image/jpeg")
        if path == "/api/samples":
            d = sample_dir()
            names = sorted(p.name for p in d.iterdir() if p.suffix.lower() in IMAGE_TYPES) if d.is_dir() else []
            hints = json.loads((d / "hints.json").read_text()) if (d / "hints.json").is_file() else {}
            out = []
            for n in names:
                # hints.json: a plain request per file, or {"hints": [{"q": request, "box": [x0, y0, x1, y1]}], "note": ...}
                # with the box in fractions of the screenshot, so the page can say hit or miss by itself
                h = hints.get(n, "")
                h = {"hints": [{"q": h}] if h else []} if isinstance(h, str) else h
                out.append({"name": n, "url": f"/samples/{n}", "hints": h.get("hints", []), "note": h.get("note", "")})
            return self.send(200, out)
        self.send(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
            if self.path == "/api/image":            # the page uploads a screenshot once, then refers to it by id
                raw = base64.b64decode(body["data"].split(",", 1)[-1])
                image = Image.open(io.BytesIO(raw)).convert("RGB")
                key = f"img{int(time.time() * 1000)}"
                state["images"][key] = image
                for old in list(state["images"])[:-4]:
                    del state["images"][old]
                return self.send(200, {"id": key, "width": image.width, "height": image.height})
            if self.path == "/api/point":
                key, image = body["model"], state["images"].get(body.get("image"))
                if key not in MODELS or not available(key):
                    return self.send(400, {"error": "that model is not on this Mac"})
                if image is None:
                    return self.send(400, {"error": "upload the screenshot again"})
                if not str(body.get("instruction", "")).strip():
                    return self.send(400, {"error": "say what to point at"})
                with lock:
                    return self.send(200, point(key, image, body["instruction"], bool(body.get("second_look"))))
            if self.path == "/api/unload":
                with lock:
                    unload()
                return self.send(200, status())
            self.send(404, {"error": "not found"})
        except Exception as e:                       # shown on the page next to the model
            self.send(500, {"error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    if not BASE_PACK.is_dir():
        sys.exit(f"Bonsai pack not found at {BASE_PACK}")
    import mlx.core as mx
    mx.set_default_device(mx.gpu)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Pointing playground at http://127.0.0.1:{PORT}   (Ctrl-C to stop; models load on first use)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
