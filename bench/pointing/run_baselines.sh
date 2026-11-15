#!/bin/bash
# Run on the Spark. Baselines on one data directory: Qwen3.5-9B (Q8), then Ternary Bonsai 2 9B.
# One model server at a time on port 8122 with -np 4, each started only if the memory check ($MEM_OK <GB>,
# skipped when that script does not exist) allows it (the Spark's memory is one pool for CPU and GPU)
# and stopped as soon as its run finishes. Results resume: cases already answered are skipped.
#   run_baselines.sh [DATA_DIR]      logs go to ~/bonsai/benchdata/pointing/logs/
D=$HOME/bonsai/benchdata/pointing
MEM_OK=${MEM_OK:-$HOME/bonsai/queue/mem_ok.sh}
DATA=${1:-$D/dev_20261114}
PY=$HOME/bonsai/venv/bin/python
mkdir -p $D/logs
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

serve_and_eval() {   # label, GB needed, model, mmproj, log name
  local label=$1 need=$2 model=$3 mmproj=$4 log=$5 tries=0
  until [ ! -x "$MEM_OK" ] || "$MEM_OK" "$need" >> $D/logs/run_all.out 2>&1; do
    tries=$((tries + 1)); [ $tries -gt 90 ] && { echo "MEM_NO $label" >> $D/logs/$log; return 1; }
    sleep 60
  done
  cd $HOME/bonsai
  setsid nohup ./llama.cpp/build/bin/llama-server -m "$model" --mmproj "$mmproj" --image-max-tokens 16384 \
    --host 127.0.0.1 --port 8122 -ngl 99 -fa on -c 65536 -np 4 > $D/logs/server_$label.log 2>&1 &
  local pid=$!
  echo $pid > $D/logs/server.pid
  until [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8122/health)" = 200 ]; do
    ps -p $pid > /dev/null || { echo "SERVER_DIED $label" >> $D/logs/$log; return 1; }
    sleep 2
  done
  cd $HOME/bonsai/bench/pointing
  $PY evaluate.py --data "$DATA" --base-url http://127.0.0.1:8122/v1 --label "$label" --max-side 1280 --concurrency 4 > $D/logs/$log 2>&1
  if ps -p $pid -o cmd= | grep -q "port 8122"; then kill $pid; while ps -p $pid > /dev/null 2>&1; do sleep 1; done; fi
}

serve_and_eval qwen35_9b 12 refs/Qwen3.5-9B-Q8_0.gguf refs/Qwen3.5-9B-mmproj-BF16.gguf eval_qwen35_9b.log
serve_and_eval bonsai2_9b_ternary 5 models/Ternary-Bonsai-2-9B-PTQ1_0.gguf models/Ternary-Bonsai-2-9B-mmproj-BF16.gguf eval_bonsai2_9b.log
echo ALL_DONE >> $D/logs/eval_bonsai2_9b.log
