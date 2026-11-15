"""Send code to the weight-lab session.

  client.py exec "print(lab.score(lab.B, lab.data(n=20))['acc'])"
  client.py run experiment.py
  client.py -                 (read code from stdin)
  client.py status | interrupt | stop

From another machine:  ssh <user>@<host> '~/bonsai/venv/bin/python ~/bonsai/weightlab/client.py -' < experiment.py
"""
import json
import os
import signal
import socket
import sys

LAB = os.path.expanduser("~/bonsai/lab")


def request(payload):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(f"{LAB}/kernel.sock")
    s.sendall((json.dumps(payload) + "\n").encode())
    ok = True
    for line in s.makefile("r"):
        msg = json.loads(line)
        if "out" in msg:
            sys.stdout.write(msg["out"])
            sys.stdout.flush()
        if msg.get("done"):
            ok = msg.get("ok", True)
            rest = {k: v for k, v in msg.items() if k not in ("done", "ok")}
            if rest:
                print(f"\n[{'ok' if ok else 'FAILED'}] {json.dumps(rest)}")
            break
    return ok


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "interrupt":
        os.kill(int(open(f"{LAB}/kernel.pid").read()), signal.SIGINT)
        return
    if cmd in ("status", "stop"):
        sys.exit(0 if request({"cmd": cmd}) else 1)
    if cmd == "exec":
        code = sys.argv[2]
    elif cmd == "run":
        code = open(sys.argv[2]).read()
    elif cmd == "-":
        code = sys.stdin.read()
    else:
        sys.exit(__doc__)
    sys.exit(0 if request({"code": code}) else 1)


main()
