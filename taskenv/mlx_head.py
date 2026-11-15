"""The small pointing decoder (weightlab/head.py, DecoderHead) in MLX, with an early exit.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

The decoder reads the model's states after layer 20 (the request tokens and the image tokens)
and returns a point without generating any token, so layers 21 to 31 never run: this class
loads the pack and the patch, keeps the first 20 layers of the language model, and applies the
decoder to their output. Interface of bench/models.py (`point`), so it can be the pointer of
guided mode:

    --model mlx-4b-head --patch bonsai2-4b-point-v2-mixed.patch.safetensors --head <decoder file>

`split_timing` measures the two halves separately: reading the image through layer 20 (which
can be done ahead of the request and cached) and answering one request on a read image.
"""
import math
import os
import tempfile
import time

from .mlx_model import PROMPT

LAYER, MAX_REQUEST = 20, 96


class Decoder:
    """DecoderHead.forward for one request, in MLX. `P` is the head's tensors by their PyTorch names."""

    def __init__(self, P):
        import mlx.core as mx
        self.mx, self.P = mx, {k: v.astype(mx.float32) for k, v in P.items()}
        self.layers = 1 + max(int(k.split(".")[1]) for k in P if k.startswith("blocks."))
        self.r = P["qp.weight"].shape[0]

    def lin(self, x, name):
        return x @ self.P[name + ".weight"].T + self.P[name + ".bias"]

    def norm(self, x, name, eps=1e-5):
        mx = self.mx
        m = x.mean(-1, keepdims=True)
        v = ((x - m) ** 2).mean(-1, keepdims=True)
        return (x - m) / mx.sqrt(v + eps) * self.P[name + ".weight"] + self.P[name + ".bias"]

    def gelu(self, x):
        return 0.5 * x * (1 + self.mx.erf(x / math.sqrt(2)))

    def attend(self, q, kv, name, heads=8):
        mx, r = self.mx, self.r
        W, b = self.P[name + ".in_proj_weight"], self.P[name + ".in_proj_bias"]
        split = lambda x, i: (x @ W[i * r:(i + 1) * r].T + b[i * r:(i + 1) * r]).reshape(x.shape[0], heads, r // heads).transpose(1, 0, 2)
        Q, K, V = split(q, 0), split(kv, 1), split(kv, 2)                         # (heads, T, r / heads)
        a = mx.softmax(Q @ K.transpose(0, 2, 1) / math.sqrt(r // heads), axis=-1)
        out = (a @ V).transpose(1, 0, 2).reshape(q.shape[0], r)
        return out @ self.P[name + ".out_proj.weight"].T + self.P[name + ".out_proj.bias"]

    def __call__(self, qtok, keys, rows, cols):
        """qtok (T, d): states of the request tokens; keys (N, d): states of the image tokens, row by row.
        Returns (x, y) on the 0-1000 scale and the click logit."""
        mx = self.mx
        ys, xs = mx.arange(rows * cols) // cols, mx.arange(rows * cols) % cols
        centres = mx.stack([(xs + 0.5) / cols * 1000, (ys + 0.5) / rows * 1000], axis=-1).astype(mx.float32)
        cell = mx.array([1000 / cols, 1000 / rows], dtype=mx.float32)
        c = centres / 1000
        k = self.lin(self.norm(keys, "kn.0"), "kp")
        k = k + self.lin(self.gelu(self.lin(mx.concatenate([c, mx.sin(6.2832 * c)], axis=-1), "pos.0")), "pos.2")
        x = self.lin(self.norm(qtok, "qn"), "qp")
        for i in range(self.layers):
            b = f"blocks.{i}"
            h = self.norm(x, b + ".norm1")
            x = x + self.attend(h, h, b + ".self_attn")
            x = x + self.attend(self.norm(x, b + ".norm2"), k, b + ".multihead_attn")
            x = x + self.lin(mx.maximum(self.lin(self.norm(x, b + ".norm3"), b + ".linear1"), 0), b + ".linear2")
        q = self.norm(x[-1], "out")
        s = (self.lin(k, "kk") @ self.lin(q, "qk")) / math.sqrt(self.r)                      # (N,)
        est = centres + mx.tanh(self.lin(self.gelu(self.lin(k + q, "offset.0")), "offset.2")) * cell * 2.0
        best = int(mx.argmax(s).item())
        near = (mx.abs(ys - best // cols) <= 1) & (mx.abs(xs - best % cols) <= 1)
        w = mx.softmax(mx.where(near, s, -1e9), axis=-1)
        pt = (w[:, None] * est).sum(0)
        click = self.lin(self.gelu(self.lin(q, "click.0")), "click.2")
        mx.eval(pt, click)
        return float(pt[0].item()), float(pt[1].item()), float(click[0].item())


class HeadModel:
    def __init__(self, key, root, patch=None, head=None):
        import mlx.core as mx
        from mlx.utils import tree_flatten
        from mlx_vlm import load
        self.mx, self.key, self.root = mx, key, os.path.expanduser(root)
        size = key.split("-")[1].upper()
        self.pack = os.path.join(self.root, "models", f"Ternary-Bonsai-2-{size}-mlx-2bit")
        t = time.time()
        self.model, self.processor = load(self.pack)
        self.patch = None
        if patch:
            self.patch = patch if os.path.isabs(patch) else os.path.join(self.root, "patches", os.path.basename(patch))
            p = mx.load(self.patch)
            flat = dict(tree_flatten(self.model.parameters()))
            missing = [n for n in p if n not in flat]
            if missing:
                raise RuntimeError(f"patch does not fit this pack: {missing[:3]}")
            self.model.load_weights(list(p.items()), strict=False)
        self.lm = self.model.language_model
        self.lm.model.layers = self.lm.model.layers[:LAYER]                     # early exit: the decoder reads layer 20
        mx.eval(self.model.parameters())
        self.head_file = head if os.path.isabs(head) else os.path.join(self.root, "patches", os.path.basename(head))
        self.decoder = Decoder(mx.load(self.head_file))
        self.image_token = self.model.config.image_token_index
        self.load_seconds = time.time() - t
        self.tmp = os.path.join(tempfile.mkdtemp(prefix="taskenv-"), "look.png")

    def describe(self):
        return {"kind": "mlx-head", "pack": self.pack, "patch": self.patch, "head": self.head_file, "layers_run": LAYER, "load_seconds": round(self.load_seconds, 1)}

    def _inputs(self, image, instruction):
        from mlx_vlm.utils import prepare_inputs
        inst = instruction[:-1] if instruction.endswith(".") else instruction
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PROMPT.format(instruction=inst)}]}]
        prompt = self.processor.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, enable_thinking=False)
        image.save(self.tmp)
        return prepare_inputs(self.processor, images=[self.tmp], prompts=prompt, image_token_index=self.image_token, add_special_tokens=False)

    def _states(self, inputs, cache=None, ids=None, embeds=None, positions=None):
        """States after layer 20 for a token sequence (the whole prompt unless ids / embeds are given)."""
        mx = self.mx
        if ids is None:
            ids = inputs["input_ids"]
            e = self.model.get_input_embeddings(ids, inputs["pixel_values"], image_grid_thw=inputs.get("image_grid_thw"), mask=inputs.get("attention_mask"))
            embeds, positions = e.inputs_embeds, e.position_ids
        out = self.lm(ids, inputs_embeds=embeds, cache=cache, position_ids=positions, capture_layer_ids=[LAYER - 1], skip_logits=True)
        h = out.hidden_states[0][0].astype(mx.float32)
        mx.eval(h)
        return h

    def _grid(self, inputs):
        _, gh, gw = [int(v) for v in inputs["image_grid_thw"].tolist()[0]]
        return gh // 2, gw // 2

    def point(self, image, instruction, max_new_tokens=0):
        import numpy as np
        t = time.perf_counter()
        inputs = self._inputs(image, instruction)
        h = self._states(inputs)
        t1 = time.perf_counter()
        ids = np.array(inputs["input_ids"].tolist()[0])
        img = np.nonzero(ids == self.image_token)[0]
        rows, cols = self._grid(inputs)
        assert rows * cols == len(img), (rows, cols, len(img))
        a = max(int(img[-1]) + 1, len(ids) - MAX_REQUEST)
        x, y, click = self.decoder(h[a:], h[self.mx.array(img)], rows, cols)
        t2 = time.perf_counter()
        return {"raw": f"[{round(x)}, {round(y)}]", "click_logit": round(click, 2), "seconds": round(t2 - t, 3), "read_seconds": round(t1 - t, 3),
                "head_ms": round((t2 - t1) * 1000, 1), "prompt_tokens": len(ids), "new_tokens": 0,
                "peak_memory_gb": round(self.mx.get_peak_memory() / 1e9, 2)}

    def split_timing(self, image, instruction, repeats=5):
        """Best-of-`repeats` milliseconds for: the vision tower, the image part of the prompt through
        layer 20 (with a cache, as it would be read ahead of the request), and one request on that
        cache including the decoder. Also checks that the split gives the same point as one pass."""
        import numpy as np
        mx = self.mx
        whole = self.point(image, instruction)
        inputs = self._inputs(image, instruction)
        ids = inputs["input_ids"]
        flat = np.array(ids.tolist()[0])
        img = np.nonzero(flat == self.image_token)[0]
        n, (rows, cols) = int(img[-1]) + 1, self._grid(inputs)
        best = {}
        for _ in range(repeats):
            t0 = time.perf_counter()
            e = self.model.get_input_embeddings(ids, inputs["pixel_values"], image_grid_thw=inputs.get("image_grid_thw"), mask=inputs.get("attention_mask"))
            mx.eval(e.inputs_embeds)
            t1 = time.perf_counter()
            cache = self.lm.make_cache()
            pos = e.position_ids
            head = self._states(inputs, cache=cache, ids=ids[:, :n], embeds=e.inputs_embeds[:, :n], positions=None if pos is None else pos[..., :n])
            keys = head[mx.array(img)]
            mx.eval(keys)
            t2 = time.perf_counter()
            tail = self._states(inputs, cache=cache, ids=ids[:, n:], embeds=e.inputs_embeds[:, n:], positions=None if pos is None else pos[..., n:])
            x, y, click = self.decoder(tail[-MAX_REQUEST:], keys, rows, cols)
            t3 = time.perf_counter()
            for k, v in (("vision_ms", t1 - t0), ("image_through_layer_20_ms", t2 - t1), ("request_and_decoder_ms", t3 - t2)):
                best[k] = round(min(best.get(k, 1e9), v * 1000), 1)
        return dict(best, image_tokens=len(img), request_tokens=len(flat) - n, one_pass=whole["raw"], split=f"[{round(x)}, {round(y)}]",
                    one_pass_seconds=whole["seconds"])

    def chat(self, messages, tools=None, max_new_tokens=0, image=None):
        raise NotImplementedError("the decoder only points")

    def close(self):
        pass
