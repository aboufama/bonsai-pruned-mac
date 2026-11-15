"""The models of the benchmark and how each one is asked.

Three kinds:
  bonsai   PrismML's MLX pack read by the weight lab (ternary codes x multipliers, folded to
           bfloat16), optionally with a patch applied in memory: the shipped artifact
  hf       a full-precision checkpoint loaded with transformers in bfloat16
  gguf     a GGUF file served by llama-server (PrismML's llama.cpp fork), one slot, one request
           at a time

Every model of the Qwen3.5 family is asked with the family's documented grounding prompt, the one
UI-Venus-2's reference evaluator sends (models/grounding/ui_venus2_gd.py in
github.com/inclusionAI/UI-Venus, branch UI-Venus-2): a single user message, image first, thinking
off, answer "[x,y]" in coordinates normalised to 0-1000. Decoding is greedy everywhere.
"""
import ast
import base64
import io
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROMPTS = {
    # verbatim from ui_venus2_gd.py (DEFAULT_USER_PROMPT); one trailing full stop of the
    # instruction is removed first, as that file does
    "qwen35_point_v1": (
        "Output the center point of the position corresponding to the following instruction: \n"
        "{instruction}. \n\n"
        "The output should just be the coordinates of a point, in the format [x,y]. "
        "Additionally, if the task is infeasible (e.g., the task is not related to the image), "
        "the output should be [-1,-1]."
    ),
}
MAX_PIXELS = 12845056          # the reference evaluator's max_pixels (16384 * 28 * 28)
FACTOR = 32                    # Qwen3.5: 16 px patches merged 2 x 2

MODELS = {
    "bonsai9b-new": {"title": "Bonsai 2 9B, repaired", "kind": "bonsai", "size": "9B",
                     "patch": "export/patches/bonsai2-9b-point-v2.patch.safetensors"},
    "bonsai9b-orig": {"title": "Ternary Bonsai 2 9B, original", "kind": "bonsai", "size": "9B", "patch": None},
    "qwen35-9b": {"title": "Qwen3.5-9B (parent)", "kind": "hf", "path": "hf/Qwen3.5-9B"},
    "venus2-9b": {"title": "UI-Venus-2-9B", "kind": "hf", "path": "hf/UI-Venus-2-9B"},
    "bonsai4b-orig": {"title": "Ternary Bonsai 2 4B, original", "kind": "bonsai", "size": "4B", "patch": None},
    "bonsai4b-new": {"title": "Bonsai 2 4B, repaired", "kind": "bonsai", "size": "4B", "patch": None},
    "qwen35-4b-q4": {"title": "Qwen3.5-4B, 4-bit (Q4_K_M GGUF)", "kind": "gguf",
                     "gguf": "refs/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf", "mmproj": "refs/Qwen3.5-4B-GGUF/mmproj-BF16.gguf"},
    "bonsai9b-orig-gguf": {"title": "Ternary Bonsai 2 9B, original (PTQ1_0 GGUF, llama.cpp)", "kind": "gguf",
                           "gguf": "models/Ternary-Bonsai-2-9B-PTQ1_0.gguf", "mmproj": "models/Ternary-Bonsai-2-9B-mmproj-BF16.gguf"},
    "bonsai9b-new-gguf": {"title": "Bonsai 2 9B, repaired (PTQ1_0 GGUF, llama.cpp)", "kind": "gguf",
                          "gguf": "export/bonsai2-9b-point.gguf", "mmproj": "models/Ternary-Bonsai-2-9B-mmproj-BF16.gguf"},
}


# ------------------------------------------------------------------ answers
def parse_point(text):
    """(point, kind) from a model's answer. `point` is (x, y) on the 0-1000 scale or None.

    kind: "point"        "[x, y]"
          "box_center"   four numbers, read as a box and reduced to its centre
          "refusal"      "[-1,-1]": the model says there is nothing to point at
          "unparseable"  no coordinates found
    The order of the rules is that of `extract_coordinates_qwen35` in UI-Venus-2's evaluator.
    """
    t = text.strip()
    m = re.search(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]", t)
    if not m:
        m = re.search(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]\s*,\s*\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]", t)
    if m:
        v = [float(g) for g in m.groups()]
        if v[0] == -1 and v[1] == -1:
            return None, "refusal"
        return ((v[0] + v[2]) / 2, (v[1] + v[3]) / 2), "box_center"
    m = re.search(r"\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]", t)
    if m:
        x, y = float(m.group(1)), float(m.group(2))
        return (None, "refusal") if (x == -1 and y == -1) else ((x, y), "point")
    nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", t)]
    if len(nums) == 2 or len(nums) == 3:
        return (None, "refusal") if (nums[0] == -1 and nums[1] == -1) else ((nums[0], nums[1]), "point")
    if len(nums) >= 4:
        if nums[0] == -1 and nums[1] == -1:
            return None, "refusal"
        return ((nums[0] + nums[2]) / 2, (nums[1] + nums[3]) / 2), "box_center"
    return None, "unparseable"


def point_text(prompt_id, instruction):
    inst = instruction[:-1] if instruction.endswith(".") else instruction
    return PROMPTS[prompt_id].format(instruction=inst)


# ------------------------------------------------------------------ images
def smart_resize(height, width, factor=FACTOR, min_pixels=3136, max_pixels=MAX_PIXELS):
    """The Qwen-VL resizing rule (as vendored in ui_venus2_gd.py): both sides multiples of
    `factor`, area within [min_pixels, max_pixels], aspect ratio kept as closely as possible."""
    h_bar, w_bar = round(height / factor) * factor, round(width / factor) * factor
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar, w_bar = math.floor(height / beta / factor) * factor, math.floor(width / beta / factor) * factor
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar, w_bar = math.ceil(height * beta / factor) * factor, math.ceil(width * beta / factor) * factor
    return h_bar, w_bar


def prepare(image, policy):
    """The image handed to the model's own processor.

    "native"   the screenshot as it is, shrunk only if it has more than MAX_PIXELS pixels (the
               reference evaluator's setting)
    "sNNNN"    shrunk (Lanczos) so that its longer side is at most NNNN px, never enlarged: what
               an assistant that captures the screen at that size sends. The repaired Bonsai was
               trained and selected at s1280.
    """
    from PIL import Image
    if policy == "native":
        if image.width * image.height > MAX_PIXELS:
            h, w = smart_resize(image.height, image.width)
            image = image.resize((w, h), Image.BICUBIC)
        return image
    side = int(policy[1:])
    scale = side / max(image.size)
    if scale < 1:
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    return image


# ------------------------------------------------------------------ tool calls in text
def parse_tool_calls(text, tools=None):
    """Tool calls a Qwen3.5-family model wrote, as OpenAI-style tool_calls.

    The family's chat template writes a call as
        <tool_call>\\n<function=NAME>\\n<parameter=KEY>\\nVALUE\\n</parameter>\\n...</function>\\n</tool_call>
    with strings raw and every other value as JSON. A value is read back as JSON unless the
    tool's schema says the parameter is a string (the same rule llama.cpp's parser applies).
    Returns (content without the calls, [tool_call, ...]).
    """
    schemas = {t["function"]["name"]: (t["function"].get("parameters") or {}).get("properties") or {} for t in tools or []}
    calls = []
    for n, block in enumerate(re.findall(r"<tool_call>(.*?)(?:</tool_call>|$)", text, flags=re.S)):
        m = re.search(r"<function=([^>\n]+)>", block)
        if not m:
            try:                                           # the older JSON form {"name": ..., "arguments": {...}}
                obj = json.loads(block.strip())
                calls.append({"id": f"call_{n}", "type": "function",
                              "function": {"name": obj.get("name"), "arguments": json.dumps(obj.get("arguments") or {})}})
            except (ValueError, AttributeError):
                calls.append({"id": f"call_{n}", "type": "function", "function": {"name": None, "arguments": block.strip()}})
            continue
        name = m.group(1).strip()
        args = {}
        for key, value in re.findall(r"<parameter=([^>\n]+)>\n?(.*?)\n?</parameter>", block, flags=re.S):
            key = key.strip()
            kind = (schemas.get(name, {}).get(key) or {}).get("type")
            if kind == "string":
                args[key] = value
            else:
                try:
                    args[key] = json.loads(value)
                except ValueError:
                    try:                                   # the models also write Python literals: True, False, None, 'text'
                        got = ast.literal_eval(value.strip())
                        args[key] = list(got) if isinstance(got, tuple) else got
                    except (ValueError, SyntaxError):
                        args[key] = value
        calls.append({"id": f"call_{n}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}})
    content = re.sub(r"<tool_call>.*?(?:</tool_call>|$)", "", text, flags=re.S).strip()
    return content, calls


def _template_messages(messages):
    """OpenAI-style messages -> what the family's chat template expects: content as a list of
    parts, tool-call arguments as objects."""
    out = []
    for m in messages:
        m = dict(m)
        if isinstance(m.get("content"), str):
            m["content"] = [{"type": "text", "text": m["content"]}]
        elif m.get("content") is None:
            m["content"] = []
        if m.get("tool_calls"):
            calls = []
            for tc in m["tool_calls"]:
                fn = dict(tc["function"])
                if isinstance(fn.get("arguments"), str):
                    try:
                        fn["arguments"] = json.loads(fn["arguments"])
                    except ValueError:
                        fn["arguments"] = {}
                calls.append({"id": tc.get("id"), "type": "function", "function": fn})
            m["tool_calls"] = calls
        out.append(m)
    return out


# ------------------------------------------------------------------ transformers models
class TorchModel:
    """A model held in this process (kinds "bonsai" and "hf")."""

    def __init__(self, key, root, patch=None, head=None):
        import torch
        from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration
        from weightlab import core
        self.torch, self.key, self.spec, self.root = torch, key, dict(MODELS[key]), root
        self.prompt_id = "qwen35_point_v1"
        t = time.time()
        if self.spec["kind"] == "bonsai":
            os.environ["BONSAI_SIZE"] = self.spec["size"]
            from weightlab import state
            self.lab = core.Lab(root)
            self.lab._journal = lambda *a, **k: None          # the benchmark keeps its own records
            self.model = self.lab.B
            self.processor = self.lab.processor
            patch = patch or self.spec.get("patch")
            self.patch = os.path.join(root, patch) if patch and not os.path.isabs(patch) else patch
            self.patch_counts = state.apply_patch(self.lab, self.patch) if self.patch else None
            self.source = self.lab.paths["pack"]
        else:
            self.lab, self.patch, self.patch_counts = None, None, None
            self.source = os.path.join(root, self.spec["path"])
            self.processor = AutoProcessor.from_pretrained(self.source)
            self.model = Qwen3_5ForConditionalGeneration.from_pretrained(self.source, dtype=torch.bfloat16, device_map="cuda").eval()
            for p in self.model.parameters():
                p.requires_grad_(False)
            getattr(core, "_fast_patch_embed", lambda m: None)(self.model)      # absent in older copies of the lab (the Spark)
        tok = self.processor.tokenizer
        ids = {tok.eos_token_id, tok.convert_tokens_to_ids("<|im_end|>"), tok.convert_tokens_to_ids("<|endoftext|>")}
        self.stop_ids = [i for i in ids if isinstance(i, int) and i >= 0]
        # one short forward pass: a patched Bonsai folds its changed ternary layers on first use,
        # which needs about 12 GB of scratch memory; do it now and hand the scratch back
        with torch.inference_mode():
            self.model(input_ids=torch.tensor([[self.stop_ids[0]] * 4], device=self.model.device))
        torch.cuda.empty_cache()
        # a pointing decoder (weightlab/head.py, DecoderHead "cross_dec:768:2" reading layer 20): when given,
        # point() returns its answer instead of the written one
        self.head_file, self.bench = None, None
        if head:
            from safetensors.torch import load_file
            from weightlab import head as headmod
            self.head_file = os.path.join(root, head) if not os.path.isabs(head) else head
            self.head_spec = ("H1 dec2x768 k20", "cross_dec:768:2", 20, (20,))
            self.bench = headmod.HeadBench(self.lab, [self.head_spec])
            self.bench.heads[self.head_spec[0]].load_state_dict(load_file(self.head_file))
            self.bench.heads[self.head_spec[0]].eval()
        self.load_seconds = time.time() - t

    def describe(self):
        torch = self.torch
        return {"kind": self.spec["kind"], "source": self.source, "patch": self.patch, "patch_counts": self.patch_counts, "head": self.head_file,
                "dtype": "bfloat16", "parameters": sum(p.numel() for p in self.model.parameters()),
                "gpu_memory_after_load_gb": round(torch.cuda.memory_allocated() / 1e9, 2),
                "generation_config": self.model.generation_config.to_dict(), "load_seconds": round(self.load_seconds, 1)}

    def _generate(self, inputs, max_new_tokens):
        torch = self.torch
        n = inputs["input_ids"].shape[1]
        with torch.inference_mode():
            out = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, use_cache=True,
                                      eos_token_id=self.stop_ids)
        torch.cuda.synchronize()
        return out[0, n:], n

    def point(self, image, instruction, max_new_tokens=32):
        """Ask where `instruction` is on `image` (a PIL image, already prepared). Returns a dict
        with the raw answer, token counts and seconds (preprocessing, prompt and generation)."""
        t = time.perf_counter()
        messages = [{"role": "user", "content": [{"type": "image", "image": image},
                                                 {"type": "text", "text": point_text(self.prompt_id, instruction)}]}]
        inputs = self.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True,
                                                    return_tensors="pt", enable_thinking=False).to(self.model.device)
        if self.bench is not None:
            n = inputs["input_ids"].shape[1]
            with self.torch.no_grad():
                states, img, centres, cell, grid = self.bench.forward(inputs)
                out = self.bench.heads[self.head_spec[0]](*self.bench.features(self.bench.specs[0], states, img, centres, cell, grid,
                                                                                [(int(img[-1]) + 1, n)]))
            x, y = out[1][0].tolist()
            self.torch.cuda.synchronize()
            return {"raw": f"[{x:.1f}, {y:.1f}]", "prompt_tokens": n, "new_tokens": 0, "click_logit": round(out[2].item(), 3),
                    "seconds": round(time.perf_counter() - t, 3)}
        new, n = self._generate(inputs, max_new_tokens)
        raw = self.processor.decode(new, skip_special_tokens=True)
        return {"raw": raw, "prompt_tokens": n, "new_tokens": int(new.shape[0]), "seconds": round(time.perf_counter() - t, 3)}

    def chat(self, messages, tools=None, max_new_tokens=512, image=None):
        """OpenAI-style chat: returns an assistant message {"content", "tool_calls", "raw", ...}.
        `image` (PIL) is put in front of the first user message's text."""
        t = time.perf_counter()
        msgs = _template_messages(messages)
        if image is not None:
            first = next(m for m in msgs if m["role"] == "user")
            first["content"] = [{"type": "image", "image": image}] + first["content"]
        kw = {"tools": tools} if tools else {}
        inputs = self.processor.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                                    return_tensors="pt", enable_thinking=False, **kw).to(self.model.device)
        new, n = self._generate(inputs, max_new_tokens)
        raw = self.processor.decode(new, skip_special_tokens=False)
        for stop in ("<|im_end|>", "<|endoftext|>"):
            raw = raw.split(stop)[0]
        content, calls = parse_tool_calls(raw, tools)
        return {"role": "assistant", "content": content, "tool_calls": calls, "raw": raw, "prompt_tokens": n,
                "new_tokens": int(new.shape[0]), "seconds": round(time.perf_counter() - t, 3)}

    def close(self):
        pass


# ------------------------------------------------------------------ llama-server models
class ServerModel:
    """A GGUF served by llama-server: one slot, requests one at a time (the only setting in which
    its answers repeat exactly, see FINDINGS.md section 6, "Measurement noise")."""

    def __init__(self, key, root, port=8131, binary=None, gguf=None):
        self.key, self.spec, self.root, self.port = key, dict(MODELS[key]), root, port
        self.prompt_id = "qwen35_point_v1"
        self.gguf = gguf or os.path.join(root, self.spec["gguf"])
        self.mmproj = os.path.join(root, self.spec["mmproj"])
        binary = binary or os.environ.get("LLAMA_SERVER") or "/root/llama-build/bin/llama-server"
        self.cmd = [binary, "-m", self.gguf, "--mmproj", self.mmproj, "--image-max-tokens", "16384", "--host", "127.0.0.1",
                    "--port", str(port), "-ngl", "99", "-fa", "on", "-c", "32768", "-np", "1", "--jinja"]
        self.log = open(f"/tmp/llama_server_{key}_{port}.log", "w")
        t = time.time()
        self.proc = subprocess.Popen(self.cmd, stdout=self.log, stderr=subprocess.STDOUT)
        while True:
            if self.proc.poll() is not None:
                raise RuntimeError(f"llama-server exited, see {self.log.name}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                    if r.status == 200:
                        break
            except Exception:
                pass
            if time.time() - t > 600:
                self.close()
                raise RuntimeError("llama-server did not become healthy in 600 s")
            time.sleep(1)
        self.load_seconds = time.time() - t

    def describe(self):
        return {"kind": "gguf", "source": self.gguf, "mmproj": self.mmproj, "command": self.cmd,
                "file_bytes": os.path.getsize(self.gguf), "mmproj_bytes": os.path.getsize(self.mmproj),
                "load_seconds": round(self.load_seconds, 1)}

    def _post(self, body):
        body = dict(body, temperature=0, top_k=1, seed=0, chat_template_kwargs={"enable_thinking": False})
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.load(r)

    @staticmethod
    def _image_part(image):
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}}

    def point(self, image, instruction, max_new_tokens=32):
        t = time.perf_counter()
        d = self._post({"max_tokens": max_new_tokens, "messages": [{"role": "user", "content": [
            self._image_part(image), {"type": "text", "text": point_text(self.prompt_id, instruction)}]}]})
        usage, tim = d.get("usage", {}), d.get("timings", {})
        return {"raw": d["choices"][0]["message"].get("content") or "", "prompt_tokens": usage.get("prompt_tokens"),
                "new_tokens": usage.get("completion_tokens"), "seconds": round(time.perf_counter() - t, 3),
                "server_prompt_ms": tim.get("prompt_ms"), "server_predicted_ms": tim.get("predicted_ms")}

    def chat(self, messages, tools=None, max_new_tokens=512, image=None):
        t = time.perf_counter()
        msgs = [dict(m) for m in messages]
        if image is not None:
            first = next(m for m in msgs if m["role"] == "user")
            text = first["content"] if isinstance(first["content"], str) else ""
            first["content"] = [self._image_part(image), {"type": "text", "text": text}]
        body = {"max_tokens": max_new_tokens, "messages": msgs}
        if tools:
            body.update(tools=tools, parallel_tool_calls=True)
        d = self._post(body)
        msg, usage, tim = d["choices"][0]["message"], d.get("usage", {}), d.get("timings", {})
        if not msg.get("tool_calls") and "<tool_call>" in (msg.get("content") or ""):
            # the server did not recognise the calls; read them with the rule used for the other models
            msg["content"], msg["tool_calls"] = parse_tool_calls(msg["content"], tools)
        return {"role": "assistant", "content": msg.get("content") or "", "tool_calls": msg.get("tool_calls") or [],
                "raw": json.dumps(msg, ensure_ascii=False), "prompt_tokens": usage.get("prompt_tokens"),
                "new_tokens": usage.get("completion_tokens"), "seconds": round(time.perf_counter() - t, 3),
                "server_prompt_per_second": tim.get("prompt_per_second"), "server_predicted_per_second": tim.get("predicted_per_second")}

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def load(key, root, patch=None, port=8131, gguf=None, head=None):
    if MODELS[key]["kind"] == "gguf":
        return ServerModel(key, root, port=port, gguf=gguf)
    return TorchModel(key, root, patch=patch, head=head)
