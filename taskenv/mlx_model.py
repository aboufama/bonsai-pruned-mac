"""Bonsai 2 in MLX on a Mac, with the interface of bench/models.py (point, chat), so that the
same loop runs on the target hardware.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    key    "mlx-4b" or "mlx-9b": the pack <root>/models/Ternary-Bonsai-2-<size>-mlx-2bit
    patch  a file in <root>/patches (or a path); applied as playground/server.py does
Every answer carries its timing as mlx-vlm reports it: prompt tokens (text and image) and the
speed they were read at, generated tokens and their speed, peak memory.
"""
import os
import tempfile
import time

PROMPT = ("Output the center point of the position corresponding to the following instruction: \n{instruction}. \n\n"
          "The output should just be the coordinates of a point, in the format [x,y]. Additionally, if the task is infeasible "
          "(e.g., the task is not related to the image), the output should be [-1,-1].")          # bench.models.PROMPTS["qwen35_point_v1"]


class MLXModel:
    def __init__(self, key, root, patch=None):
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
            mx.eval(self.model.parameters())
        self.load_seconds = time.time() - t
        self.tmp = os.path.join(tempfile.mkdtemp(prefix="taskenv-"), "look.png")

    def describe(self):
        import mlx_vlm
        return {"kind": "mlx", "pack": self.pack, "patch": self.patch, "mlx_vlm": mlx_vlm.__version__, "load_seconds": round(self.load_seconds, 1)}

    def _generate(self, prompt, image, max_tokens):
        from mlx_vlm import generate
        t = time.perf_counter()
        image.save(self.tmp)
        out = generate(self.model, self.processor, prompt, [self.tmp], max_tokens=max_tokens, temperature=0.0, verbose=False)
        r = {"raw": out if isinstance(out, str) else getattr(out, "text", str(out)), "seconds": round(time.perf_counter() - t, 3)}
        for src, dst in (("prompt_tokens", "prompt_tokens"), ("generation_tokens", "new_tokens"), ("prompt_tps", "read_tps"),
                         ("generation_tps", "write_tps"), ("peak_memory", "peak_memory_gb")):
            v = getattr(out, src, None)
            if v is not None:
                r[dst] = round(float(v), 2)
        return r

    def _prompt(self, messages, tools=None, thinking=False):
        """Chat messages (the first user message gets the image in front) as the model's prompt text."""
        msgs, seen = [], False
        for m in messages:
            content = [{"type": "text", "text": m["content"]}] if isinstance(m["content"], str) else list(m["content"])
            if m["role"] == "user" and not seen:
                content, seen = [{"type": "image"}] + content, True
            msgs.append({"role": m["role"], "content": content})
        kw = {"tools": tools} if tools else {}
        return self.processor.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, enable_thinking=bool(thinking), **kw)

    def point(self, image, instruction, max_new_tokens=24):
        inst = instruction[:-1] if instruction.endswith(".") else instruction
        r = self._generate(self._prompt([{"role": "user", "content": PROMPT.format(instruction=inst)}]), image, max_new_tokens)
        r["raw"] = r["raw"].strip()
        return r

    def chat(self, messages, tools=None, max_new_tokens=192, image=None, thinking=False):
        """With thinking=True the model reasons first (the template opens a <think> block); the
        reasoning is returned as "thinking" with its token count and removed from "raw"."""
        from bench import models
        r = self._generate(self._prompt(messages, tools, thinking), image, max_new_tokens + (1024 if thinking else 0))
        for stop in ("<|im_end|>", "<|endoftext|>"):
            r["raw"] = r["raw"].split(stop)[0]
        if thinking:
            think, sep, answer = r["raw"].partition("</think>")
            if not sep and "<tool_call>" in think:                       # it did not think at all
                think, answer = "", r["raw"]
            think = think.replace("<think>", "").strip()
            r.update(raw=answer.strip() if (sep or not think) else "", thinking=think[:600],
                     think_tokens=len(self.processor.tokenizer.encode(think)) if think else 0)
        content, calls = models.parse_tool_calls(r["raw"], tools)
        return dict(r, role="assistant", content=content, tool_calls=calls)

    def close(self):
        pass
