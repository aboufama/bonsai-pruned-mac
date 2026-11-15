#!/bin/bash
# Grounding benchmark for one or more models served by llama-server.
# usage: ./run_ground.sh "<names>" [eval_ground.py args]
#   names: 2B 4B 9B 27B (Bonsai 2, PTQ1_0), qwen9b (Qwen3.5-9B Q8_0), venus9b (UI-Venus-2-9B Q8_0)
#   e.g.   ./run_ground.sh "9B qwen9b" --dataset ssv2 --limit 150
#          ./run_ground.sh "9B" --dataset sspro --max-side 1280 --limit 40
cd ~/bonsai
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
NAMES=$1; shift
PORT=8112
for s in $NAMES; do
  case $s in
    qwen9b)  M=refs/Qwen3.5-9B-Q8_0.gguf;     P=refs/Qwen3.5-9B-mmproj-BF16.gguf ;;
    venus9b) M=refs/UI-Venus-2-9B-Q8_0.gguf;  P=refs/UI-Venus-2-9B-mmproj-BF16.gguf ;;
    *)       M=models/Ternary-Bonsai-2-$s-PTQ1_0.gguf; P=models/Ternary-Bonsai-2-$s-mmproj-BF16.gguf ;;
  esac
  ./llama.cpp/build/bin/llama-server -m $M --mmproj $P --image-max-tokens 16384 \
    --host 127.0.0.1 --port $PORT -ngl 99 -fa on -c 131072 -np 8 >logs/ground_server_$s.log 2>&1 &
  pid=$!
  for i in $(seq 1 240); do curl -sf http://127.0.0.1:$PORT/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
  if ! curl -sf http://127.0.0.1:$PORT/health >/dev/null; then echo "$s: server failed to start"; tail -5 logs/ground_server_$s.log; kill $pid 2>/dev/null; continue; fi
  python3 eval_ground.py $s $PORT "$@"
  kill $pid; wait $pid 2>/dev/null
done
