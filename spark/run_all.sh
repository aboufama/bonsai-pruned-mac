#!/bin/bash
# Speed-test all four Bonsai 2 models: single-stream llama-bench, then all four served at once.
# usage: ./run_all.sh [PTQ1_0|PQ2_0]      results: logs/run_<time>.log
cd ~/bonsai
PACK=${1:-PTQ1_0}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
BIN=./llama.cpp/build/bin
LOG=logs/run_$(date +%Y%m%d_%H%M%S).log
{
echo "pack $PACK, GPU utilisation from other jobs before start: $(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader)"
echo "== llama-bench, one model at a time (pp512 = prompt speed, tg128 = generation speed)"
for s in 2B 4B 9B 27B; do
  $BIN/llama-bench -m models/Ternary-Bonsai-2-$s-$PACK.gguf -ngl 99 -fa 1 -p 512 -n 128 -r 3 2>&1 | grep -E "^\| qwen" | awk -F"|" "{printf \"%-4s %s %s\n\", \"$s\", \$8, \$9}"
done
echo "== all four served at once (ports 8101-8104), then loaded with 1, 8 and 32 simultaneous requests each in turn"
port=8101; pids=""
for s in 2B 4B 9B 27B; do
  $BIN/llama-server -m models/Ternary-Bonsai-2-$s-$PACK.gguf --host 127.0.0.1 --port $port -ngl 99 -fa on -c 32768 -np 32 >logs/server_$s.log 2>&1 &
  pids="$pids $!"; port=$((port+1))
done
for p in 8101 8102 8103 8104; do for i in $(seq 1 120); do curl -sf http://127.0.0.1:$p/health >/dev/null && break; sleep 1; done; done
port=8101
for s in 2B 4B 9B 27B; do python3 serve_bench.py $s $port 1 8 32; port=$((port+1)); done
kill $pids 2>/dev/null
} 2>&1 | tee $LOG
