#!/usr/bin/env python
"""A small local helper that only points: Bonsai-Pruned 4B (PrismML's Ternary Bonsai 2 4B in MLX
with a trunk patch, cut after layer 20, and the 25 M-parameter pointing decoder on that layer).
The menu-bar assistant asks it "where is X on this screenshot" instead of its language model.

    ~/Bonsai-demo/.venv-vlm/bin/python assistant/tools/pointer_server.py --port 1235 [--pack DIR] [--patch FILE] [--head FILE] [--side 1280]

    GET  /health -> {"ok": true, "ready": true, "model": "bonsai-pruned-4b", "side": 1280}
    POST /point  {"image_b64": "<PNG or JPEG bytes, base64>", "request": "<what to find>", "looks": 1}
              -> {"x": 0..1, "y": 0..1, "seconds": 0.3, "read_seconds": 0, "cached": true}
    POST /read   {"image_b64": "..."}  -> {"read_seconds": 0.9, "cached": false}

x and y are fractions of the picture's width and height. "request" is the target in words
("the 5 key", "Add a new event"); it is put in the pointing prompt the decoder was trained
with. The picture is shrunk so that its long side is at most --side before the model sees it,
and never enlarged. The read of the most recent picture is kept (by a hash of its bytes), so a
further request about the same screenshot skips the read: only the request's few tokens and
the decoder run. /read does that read ahead of any request (when the screenshot is taken).
"looks": 2 takes a second look: a square of half the picture's long side around the first
answer, read at 1280 px, asked again, mapped back.
Errors are HTTP 400 / 500 / 503 (still loading) with {"error": "..."}.

Uses the loader of the task benchmark as it is (taskenv/mlx_head.py). Listens on 127.0.0.1
only, one request at a time, no network use; it prints one line when ready and one per request.
The loader keeps one temporary picture file, removed when the helper stops.
"""
import argparse
import base64
import binascii
import copy
import hashlib
import io
import json
import queue
import shutil
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
ROOT = Path.home() / "Bonsai-demo"
NAME = "bonsai-pruned-4b"
SECOND_SIDE = 1280                       # the second look reads its crop at this size
MAX_BODY = 64 * 1024 * 1024              # bytes of one request
WAIT = 120                               # seconds a request waits for its answer
AHEAD = "the Close button"               # stands for the request when a picture is read ahead of one


class Bad(Exception):
    """A request that cannot be answered as it was sent (HTTP 400)."""


def fit(image, side):
    from PIL import Image
    s = side / max(image.size)
    return image if s >= 1 else image.resize((round(image.width * s), round(image.height * s)), Image.LANCZOS)


def picture(data):
    from PIL import Image
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as err:
        raise Bad(f"image_b64 is not a picture that can be read ({type(err).__name__})")
    if image.format not in ("PNG", "JPEG"):
        raise Bad(f"image_b64 is a {image.format} picture; PNG or JPEG only")
    if min(image.size) < 32:
        raise Bad(f"the picture is too small: {image.width} x {image.height}")
    return image.convert("RGB")


def arrays(mx, tree):
    if isinstance(tree, mx.array):
        yield tree
    elif isinstance(tree, (list, tuple)):
        for t in tree:
            yield from arrays(mx, t)


class Pointer:
    """The loaded model and the read of the most recent picture. Used from one thread only."""

    def __init__(self, pack, patch, head, side):
        import mlx.core as mx
        import mlx_vlm
        import numpy as np
        from taskenv import mlx_head
        self.mx, self.np, self.side = mx, np, side
        self.prompt, self.max_request = mlx_head.PROMPT, mlx_head.MAX_REQUEST
        load = mlx_vlm.load
        mlx_vlm.load = lambda _, *a, **k: load(str(pack), *a, **k)       # the loader builds its pack's path from a root folder; --pack names the folder itself
        try:
            self.m = mlx_head.HeadModel("mlx-4b-head", str(pack.parent.parent), patch=str(patch), head=str(head))
        finally:
            mlx_vlm.load = load
        self.m.pack = str(pack)
        self.last = None                 # (hash of the bytes, the read, the picture as it was sent)
        self.note = None                 # why a read could not be kept, if that ever happened

    def read(self, image, request, keep=True):
        """Reads a picture: the image part of the prompt through layer 20 into a cache, as
        HeadModel.split_timing does. Returns the read (what any request on this picture needs)
        and this request's own tokens, embeddings and positions."""
        m, mx, np = self.m, self.mx, self.np
        inputs = m._inputs(image, request)
        ids = inputs["input_ids"]
        flat = np.array(ids.tolist()[0])
        img = np.nonzero(flat == m.image_token)[0]
        rows, cols = m._grid(inputs)
        if not len(img) or rows * cols != len(img):
            raise RuntimeError(f"the image tokens do not match their grid: {len(img)} against {rows} x {cols}")
        n = int(img[-1]) + 1
        grid, mask = inputs.get("image_grid_thw"), inputs.get("attention_mask")
        e = m.model.get_input_embeddings(ids, inputs["pixel_values"], image_grid_thw=grid, mask=mask)
        pos = e.position_ids
        cache = m.lm.make_cache()
        head = m._states(inputs, cache=cache, ids=ids[:, :n], embeds=e.inputs_embeds[:, :n], positions=None if pos is None else pos[..., :n])
        keys = head[mx.array(img)]
        mx.eval(keys, *arrays(mx, [getattr(c, "state", None) for c in cache]))
        tail = (ids[:, n:], e.inputs_embeds[:, n:], None if pos is None else pos[..., n:])
        r = {"cache": cache, "keys": keys, "rows": rows, "cols": cols, "n": n, "grid": grid, "before": flat[:int(img[0])].tolist(),
             "prefix": flat[:n].tolist(), "ids_dtype": ids.dtype, "embed_dtype": e.inputs_embeds.dtype,
             "mask_dtype": None if mask is None else mask.dtype, "reusable": False}
        if keep:
            # a further request is prepared without the image; that way is only used if, for this
            # request, it gives exactly what the full way gave
            try:
                a, b, c = self.tail(r, request)
                same = (pos is not None and a.shape == tail[0].shape and bool(mx.array_equal(a, tail[0]).item())
                        and bool(mx.array_equal(c, tail[2]).item()) and bool(mx.allclose(b, tail[1]).item()))
                why = None if same else "a request prepared without the image differs from the same request prepared with it"
            except Exception as err:
                same, why = False, f"{type(err).__name__}: {err}"
            r["reusable"] = same
            if why and why != self.note:
                self.note = why
                print(f"the read of a picture is not kept: {why}", flush=True)
        return r, tail

    def tail(self, r, request):
        """A request's tokens after the image, their embeddings and positions, without touching
        the image: the prompt is tokenised as text, where one token stands for the image."""
        m, mx = self.m, self.mx
        inst = request[:-1] if request.endswith(".") else request
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": self.prompt.format(instruction=inst)}]}]
        prompt = m.processor.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, enable_thinking=False)
        ids = [int(i) for i in m.processor.tokenizer(prompt, add_special_tokens=False)["input_ids"]]
        if ids.count(m.image_token) != 1:
            raise RuntimeError("the prompt as text does not hold exactly one image token")
        i = ids.index(m.image_token)
        if ids[:i] != r["before"]:
            raise RuntimeError("the prompt as text starts differently")
        whole = mx.array([r["prefix"] + ids[i + 1:]], dtype=r["ids_dtype"])
        mask = None if r["mask_dtype"] is None else mx.ones(whole.shape, dtype=r["mask_dtype"])
        pos, _ = m.lm.get_rope_index(whole, r["grid"], None, mask)
        after = whole[:, r["n"]:]
        return after, m.lm.model.embed_tokens(after).astype(r["embed_dtype"]), pos[..., r["n"]:]

    def answer(self, r, tail):
        """One request on a read picture: a copy of the picture's cache takes the request's
        tokens (layers that carry a running state cannot be wound back), then the decoder."""
        ids, embeds, pos = tail
        states = self.m._states(None, cache=copy.deepcopy(r["cache"]), ids=ids, embeds=embeds, positions=pos)
        x, y, _ = self.m.decoder(states[-self.max_request:], r["keys"], r["rows"], r["cols"])
        return min(max(x / 1000, 0.0), 1.0), min(max(y / 1000, 0.0), 1.0)

    def see(self, data, request=None):
        """The read of these bytes: the kept one when they are the most recent picture's (then
        no tokens of a request come with it), a new one otherwise. Also the picture as sent
        and the seconds the read took."""
        t = time.perf_counter()
        key = hashlib.sha256(data).hexdigest()
        if self.last is not None and self.last[0] == key:
            return self.last[1], self.last[2], None, 0.0
        whole = picture(data)
        self.last = None
        self.mx.clear_cache()                                            # the previous picture's read goes before the new one is made
        r, tail = self.read(fit(whole, self.side), request or AHEAD)
        if r["reusable"]:
            self.last = (key, r, whole)
        return r, whole, tail, time.perf_counter() - t

    def ahead(self, data):
        r, _, tail, seconds = self.see(data)
        return {"read_seconds": round(seconds, 3), "cached": tail is None, "kept": r["reusable"]}

    def point(self, data, request, looks=1):
        from PIL import Image
        t = time.perf_counter()
        r, whole, tail, read_seconds = self.see(data, request)
        cached = tail is None
        x, y = self.answer(r, tail or self.tail(r, request))
        out = {"cached": cached, "read_seconds": round(read_seconds, 3), "looks": 1}
        if looks == 2:
            t2 = time.perf_counter()
            W, H = whole.size
            w, h = min(max(W, H) / 2, W), min(max(W, H) / 2, H)
            left, top = min(max(x * W - w / 2, 0), W - w), min(max(y * H - h / 2, 0), H - h)
            box = (round(left), round(top), round(left + w), round(top + h))
            crop = whole.crop(box)
            s = SECOND_SIDE / max(crop.size)
            crop = crop.resize((max(32, round(crop.width * s)), max(32, round(crop.height * s))), Image.LANCZOS)
            r2, tail2 = self.read(crop, request, keep=False)
            cx, cy = self.answer(r2, tail2)
            out.update(looks=2, first={"x": round(x, 5), "y": round(y, 5)}, second_seconds=round(time.perf_counter() - t2, 3))
            x, y = (box[0] + cx * (box[2] - box[0])) / W, (box[1] + cy * (box[3] - box[1])) / H
        return dict({"x": round(min(max(x, 0.0), 1.0), 5), "y": round(min(max(y, 0.0), 1.0), 5), "seconds": round(time.perf_counter() - t, 3)}, **out)


class Server(HTTPServer):
    allow_reuse_address = True
    allow_reuse_port = False


class Handler(BaseHTTPRequestHandler):
    server_version = "pointer"
    timeout = 30                         # a caller that stops sending does not hold the helper

    def log_message(self, *args):
        pass

    def reply(self, status, body):
        data = json.dumps(body).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            pass                         # the caller went away

    def do_GET(self):
        if self.path.split("?")[0] == "/health":
            self.reply(200, dict(self.server.state))
        else:
            self.reply(404, {"error": f"no such path: {self.path[:80]}"})

    def do_POST(self):
        try:
            status, body = self.post()
        except Bad as err:
            status, body = 400, {"error": str(err)}
        except Exception as err:
            status, body = 500, {"error": f"{type(err).__name__}: {err}"}
        self.reply(status, body)

    def post(self):
        path = self.path.split("?")[0]
        if path not in ("/point", "/read"):
            return 404, {"error": f"no such path: {self.path[:80]}"}
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise Bad("no Content-Length")
        if not 0 < length <= MAX_BODY:
            raise Bad(f"the body must be 1 to {MAX_BODY} bytes, not {length}")
        raw = self.rfile.read(length)
        if len(raw) < length:
            raise Bad("the body is shorter than its Content-Length")
        try:
            body = json.loads(raw)
        except ValueError:
            raise Bad("the body is not JSON")
        if not isinstance(body, dict):
            raise Bad("the body is not a JSON object")
        image, request, looks = body.get("image_b64"), body.get("request"), body.get("looks", 1)
        if not isinstance(image, str) or not image:
            raise Bad("image_b64 is missing")
        if path == "/read":
            request, looks = None, 1
        else:
            request = request.strip().rstrip(".") if isinstance(request, str) else ""      # the app's pointing prompt drops the final full stops too
            if not request:
                raise Bad("request is missing")
            if isinstance(looks, bool) or looks not in (1, 2):
                raise Bad("looks is 1 or 2")
        if image.startswith("data:") and "base64," in image[:64]:
            image = image.split("base64,", 1)[1]
        try:
            data = base64.b64decode("".join(image.split()), validate=True)
        except (binascii.Error, ValueError):
            raise Bad("image_b64 is not base64")
        if not self.server.state["ready"]:
            return 503, {"error": "the model is still loading"}
        job = {"data": data, "request": request, "looks": int(looks), "done": threading.Event()}
        self.server.jobs.put(job)
        if not job["done"].wait(WAIT):
            return 500, {"error": f"no answer within {WAIT} s"}
        if "error" in job:
            return job["status"], {"error": job["error"]}
        return 200, job["result"]


def main():
    ap = argparse.ArgumentParser(description="Local pointing helper (Bonsai-Pruned 4B) on 127.0.0.1.")
    ap.add_argument("--port", type=int, default=1235)
    ap.add_argument("--host", default="127.0.0.1", help="address to listen on; leave it at 127.0.0.1 unless a test machine must reach the helper from a virtual machine")
    ap.add_argument("--pack", default=str(ROOT / "models/Ternary-Bonsai-2-4B-mlx-2bit"))
    ap.add_argument("--patch", default=str(ROOT / "models/patches/bonsai2-4b-joint-h1-trunk-s12500.patch.safetensors"))
    ap.add_argument("--head", default=str(ROOT / "models/heads/bonsai2-4b-joint-h1-dec2x768-L20-s12500.safetensors"))
    ap.add_argument("--side", type=int, default=1280, help="the picture's long side as the model sees it, at most (the app sends 1280 px)")
    args = ap.parse_args()
    pack, patch, head = (Path(p).expanduser().resolve() for p in (args.pack, args.patch, args.head))
    for f in (pack / "config.json", patch, head):
        if not f.is_file():
            sys.exit(f"missing: {f}")
    if not 256 <= args.side <= 4096:
        sys.exit("--side is between 256 and 4096")

    def stop(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)

    try:
        server = Server((args.host, args.port), Handler)
    except OSError as err:
        sys.exit(f"port {args.port} cannot be used: {err}")
    server.state = {"ok": True, "ready": False, "model": NAME, "side": args.side}
    server.jobs = queue.Queue()
    threading.Thread(target=server.serve_forever, daemon=True).start()   # answers /health while the model loads

    pointer = None
    try:
        import mlx.core as mx
        from PIL import Image
        t = time.time()
        pointer = Pointer(pack, patch, head, args.side)
        loaded = time.time() - t
        try:                                                             # one read of a blank screen, so that the first real question is not the slow one
            blank = Image.new("RGB", (args.side, round(args.side * 0.625)), (236, 236, 236))
            pointer.answer(*pointer.read(blank, "Point at the Close button", keep=False))
        except Exception as err:
            print(f"the first read failed ({type(err).__name__}: {err}); carrying on", flush=True)
        peak = lambda: round(mx.get_peak_memory() / 1e9, 2)
        server.state.update(ready=True, load_seconds=round(time.time() - t, 1), peak_memory_gb=peak())
        print(f"ready: {NAME} on http://{args.host}:{args.port}, loaded in {time.time() - t:.1f} s (model {loaded:.1f} s, then one blank read), "
              f"peak memory {peak()} GB, pictures read at {args.side} px", flush=True)
        while True:
            job = server.jobs.get()
            what = "read ahead" if job["request"] is None else f"point \"{job['request'][:60]}\""
            try:
                if job["request"] is None:
                    r = job["result"] = pointer.ahead(job["data"])
                    line = "read before" if r["cached"] else f"read in {r['read_seconds']} s"
                else:
                    r = job["result"] = pointer.point(job["data"], job["request"], job["looks"])
                    line = (f"{r['seconds']} s ({'read before' if r['cached'] else 'read in ' + str(r['read_seconds']) + ' s'}"
                            f"{', 2 looks' if r['looks'] == 2 else ''}) -> {r['x']}, {r['y']}")
            except Bad as err:
                job["status"], job["error"] = 400, str(err)
                line = f"refused: {err}"
            except Exception as err:
                job["status"], job["error"] = 500, f"{type(err).__name__}: {err}"
                pointer.last = None
                line = f"failed: {job['error']}"
            job["done"].set()
            server.state["peak_memory_gb"] = peak()
            print(f"{what}: {line}", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        if pointer is not None:
            shutil.rmtree(Path(pointer.m.tmp).parent, ignore_errors=True)


if __name__ == "__main__":
    main()
