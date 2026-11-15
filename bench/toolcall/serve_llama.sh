#!/bin/bash
# Start llama-server for one model on port 8121 and wait until it is healthy.
#   ./serve_llama.sh ~/bonsai/models/Ternary-Bonsai-2-9B-PTQ1_0.gguf
# The PID is written to server.pid next to this script; stop the server with
#   kill "$(cat server.pid)"
# Rules on a machine whose memory is one pool for CPU and GPU (the DGX Spark): one server at a time,
# at most 4 slots, stop it as soon as the run is done, and never start one unless the memory check
# ($MEM_OK <GB>, a small script that says yes or NO; skipped when it does not exist) agrees.
# NEED_GB is the memory the model needs: about 5 for a Bonsai 9B, 12 for a 9B Q8 (default 12).
set -u
LLAMA=${LLAMA_SERVER:-$HOME/bonsai/llama.cpp/build/bin/llama-server}
PORT=${PORT:-8121}
MEM_OK=${MEM_OK:-$HOME/bonsai/queue/mem_ok.sh}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
cd "$(dirname "$0")"
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then echo "port $PORT is busy"; exit 1; fi
if [ -x "$MEM_OK" ] && ! "$MEM_OK" "${NEED_GB:-12}"; then echo "not starting: memory check failed"; exit 1; fi
nohup "$LLAMA" -m "$1" --host 127.0.0.1 --port "$PORT" -ngl 99 -fa on -c 32768 -np 4 --jinja > server.log 2>&1 &
echo $! > server.pid
for i in $(seq 1 300); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/health")" = "200" ]; then
    echo "ready: pid $(cat server.pid), ${i}s"; exit 0
  fi
  if ! kill -0 "$(cat server.pid)" 2>/dev/null; then echo "server exited:"; tail -20 server.log; exit 1; fi
  sleep 1
done
echo "timed out waiting for /health"; exit 1
