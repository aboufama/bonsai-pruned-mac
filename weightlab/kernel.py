"""A persistent Python session with the weight lab loaded, driven over a local socket.

Start once:   nohup ~/bonsai/venv/bin/python -m weightlab.kernel > ~/bonsai/lab/kernel.log 2>&1 &
Then send code with weightlab/client.py. The session keeps its variables between requests, so
models stay in GPU memory and each experiment costs seconds instead of a reload.

Every request is saved under ~/bonsai/lab/cells/ with its output, so the full history of what
was run against the weights can be replayed and audited.
"""
import io
import json
import os
import signal
import socket
import sys
import time
import traceback

ROOT = os.path.expanduser("~/bonsai")
LAB = f"{ROOT}/lab"
SOCK = f"{LAB}/kernel.sock"


class Stream(io.TextIOBase):
    """Writes go to the client as they happen and into the cell's saved output."""

    def __init__(self, conn, log):
        self.conn, self.log = conn, log

    def write(self, s):
        if s:
            self.log.write(s)
            try:
                self.conn.sendall((json.dumps({"out": s}) + "\n").encode())
            except OSError:
                pass
        return len(s)

    def flush(self):
        self.log.flush()


def send(conn, obj):
    """Reply to the client; a client that has gone away must never take the session down."""
    try:
        conn.sendall((json.dumps(obj) + "\n").encode())
    except OSError:
        pass


def main():
    os.makedirs(f"{LAB}/cells", exist_ok=True)
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    with open(f"{LAB}/kernel.pid", "w") as f:
        f.write(str(os.getpid()))

    import numpy as np
    import torch
    from weightlab.core import Lab
    namespace = {"lab": Lab(ROOT), "torch": torch, "np": np}

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCK)
    server.listen(4)
    print("kernel ready", flush=True)
    n = len(os.listdir(f"{LAB}/cells")) // 2
    while True:
        conn, _ = server.accept()
        try:
            request = json.loads(conn.makefile("r").readline())
        except Exception:
            conn.close()
            continue
        if request.get("cmd") == "stop":
            send(conn, {"done": True, "ok": True})
            conn.close()
            break
        if request.get("cmd") == "status":
            mem = torch.cuda.memory_allocated() / 1e9 if torch.cuda.is_available() else 0
            lab = namespace["lab"]
            send(conn, {"done": True, "ok": True, "models": sorted(lab.models), "gpu_gb": round(mem, 1),
                        "edits": lab.stack, "forward_passes": lab.forward_passes, "cells": n})
            conn.close()
            continue
        n += 1
        stamp = time.strftime("%Y%m%dT%H%M%S")
        code = request.get("code", "")
        with open(f"{LAB}/cells/{n:05d}_{stamp}.py", "w") as f:
            f.write(code)
        ok, started = True, time.time()
        with open(f"{LAB}/cells/{n:05d}_{stamp}.out", "w") as log:
            stream = Stream(conn, log)
            old = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = stream
            try:
                exec(compile(code, f"cell-{n}", "exec"), namespace)
            except KeyboardInterrupt:
                ok = False
                print("\n[interrupted]")
            except BaseException:
                ok = False
                traceback.print_exc()
            finally:
                sys.stdout, sys.stderr = old
        send(conn, {"done": True, "ok": ok, "seconds": round(time.time() - started, 1), "cell": n})
        conn.close()
    os.unlink(SOCK)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.default_int_handler)
    main()
