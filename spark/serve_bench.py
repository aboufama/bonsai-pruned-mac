"""Throughput of an already-running llama-server.

usage: serve_bench.py <label> <port> <concurrency> [<concurrency> ...]
Greedy decoding, thinking off, 256 new tokens per request.
"""
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TOPICS = [
    "how a six-legged robot keeps its balance while walking",
    "how to write a debounce function in JavaScript",
    "three ways to reduce latency in a web app",
    "the difference between a mutex and a semaphore",
    "how public-key encryption works",
    "how to merge overlapping intervals in Python",
    "what a Kalman filter does",
    "the history of the transistor",
]


def ask(port, i, n=256):
    body = {"max_tokens": n, "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": f"Request {i}: explain {TOPICS[i % len(TOPICS)]} in detail."}]}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)["timings"]


label, port = sys.argv[1], int(sys.argv[2])
ask(port, 0, 8)  # warm-up
for c in map(int, sys.argv[3:]):
    started = time.time()
    with ThreadPoolExecutor(c) as pool:
        timings = list(pool.map(lambda i: ask(port, i), range(c)))
    wall = time.time() - started
    tokens = sum(t["predicted_n"] for t in timings)
    per = sum(t["predicted_per_second"] for t in timings) / c
    print(f"{label:4s} x{c:<3d} {tokens:5d} tokens in {wall:6.1f}s = {tokens / wall:7.1f} tok/s total, "
          f"{per:6.1f} tok/s per stream", flush=True)
