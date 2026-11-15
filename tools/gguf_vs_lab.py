#!/usr/bin/env python3
"""Compare a GGUF served by llama.cpp with the lab's written answers (tools/lab_answers.py).

  python3 tools/gguf_vs_lab.py <llama-server> <model.gguf> <mmproj.gguf> <answers dir> [port=8391] [ngl=0]

Starts the server (CPU by default, 8 threads), asks each case of <answers dir>/answers.jsonl with the
shrunk PNG the lab used and the lab's grounding prompt (image first, temperature 0, thinking off), and
prints both answers side by side with their distance on the 0-1000 scale, then the totals. Stops the
server it started, by pid. Standard library only.
"""
import base64
import json
import math
import re
import subprocess
import sys
import time
import urllib.request

server, model, mmproj, adir = sys.argv[1:5]
port = int(sys.argv[5]) if len(sys.argv) > 5 else 8391
ngl = sys.argv[6] if len(sys.argv) > 6 else "0"
PROMPT = ("Output the center point of the position corresponding to the following instruction: \n{instruction}. \n\n"
          "The output should just be the coordinates of a point, in the format [x,y]. "
          "Additionally, if the task is infeasible (e.g., the task is not related to the image), the output should be [-1,-1].")
proc = subprocess.Popen([server, "--model", model, "--mmproj", mmproj, "--host", "127.0.0.1", "--port", str(port), "-ngl", ngl, "-t", "8",
                         "-fa", "on", "-c", "8192", "-np", "1", "--jinja", "--image-max-tokens", "4096", "--temp", "0"],
                        stdout=open(f"{adir}/llama_server.log", "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(240):
        try:
            if urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2).status == 200:
                break
        except Exception:
            if proc.poll() is not None:
                raise SystemExit("llama-server exited; see llama_server.log")
            time.sleep(1)
    nums = lambda t: [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", t)][:2]
    same = near = hit_l = hit_g = n = 0
    for line in open(f"{adir}/answers.jsonl"):
        c = json.loads(line)
        img = base64.b64encode(open(f"{adir}/images/{c['image']}", "rb").read()).decode()
        body = {"messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + img}},
                    {"type": "text", "text": PROMPT.format(instruction=c["instruction"].rstrip("."))}]}],
                "temperature": 0, "max_tokens": 24, "chat_template_kwargs": {"enable_thinking": False}}
        t = time.time()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
        text = json.load(urllib.request.urlopen(req, timeout=900))["choices"][0]["message"]["content"].strip()
        a, g, b = nums(c["answer"]), nums(text), c["box1000"]
        d = math.hypot(a[0] - g[0], a[1] - g[1]) if len(a) == 2 and len(g) == 2 else None
        inbox = lambda p: len(p) == 2 and b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]
        n += 1; same += d == 0; near += d is not None and d <= 10; hit_l += inbox(a); hit_g += inbox(g)
        print("%-14s lab %-12s gguf %-12s distance %s   [%.0f s]" % (c["id"], c["answer"].strip(), text, "n/a" if d is None else "%.0f" % d, time.time() - t), flush=True)
    print("GGUF VS LAB: %d cases; identical answers %d; within 10 units %d; on target: lab %d, gguf %d" % (n, same, near, hit_l, hit_g), flush=True)
finally:
    proc.terminate()
