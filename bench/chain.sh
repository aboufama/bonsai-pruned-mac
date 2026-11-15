#!/bin/bash
# Run benchmark jobs one after another on a machine:  bench/chain.sh <name>
# Reads <root>/benchruns/queue/<name>.txt; each line holds the arguments of one bench/run.py call
# and is removed when it starts. A line may begin with need=<GB>: the job then waits until the
# GPU has that much memory free (several chains share one GPU; a Bonsai model needs about 42 GB
# while it folds its ternary layers, a 9B reference about 24). Lines can be appended while it
# runs. An empty queue waits; `touch <root>/benchruns/queue/STOP` ends every chain after its
# current job.
root=${BONSAI_ROOT:-/workspace/bonsai}
q=$root/benchruns/queue/$1.txt
mkdir -p "$(dirname "$q")" "$root/logs/bench"; touch "$q"
cd "$root" || exit 1
echo $$ > "$root/benchruns/queue/$1.pid"
exec 9> "$root/benchruns/queue/.lock"
while [ ! -f "$root/benchruns/queue/STOP" ]; do
  line=$(head -n 1 "$q")
  if [ -z "$line" ]; then sleep 15; continue; fi
  need=0
  case "$line" in need=*) need=${line%% *}; need=${need#need=}; args=${line#* } ;; *) args=$line ;; esac
  flock 9
  free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n 1)
  if [ "$free" -lt $((need * 1024)) ]; then flock -u 9; sleep 20; continue; fi
  sed -i 1d "$q"
  echo "$(date +%H:%M:%S) START $args" >> "logs/bench/chain_$1.log"
  PYTORCH_ALLOC_CONF=expandable_segments:True python3 bench/run.py $args >> "logs/bench/chain_$1.out" 2>&1 &
  pid=$!
  echo $pid > "$root/benchruns/queue/$1.job.pid"
  sleep 90                       # let the model load before another chain measures free memory
  flock -u 9
  wait $pid; rc=$?
  echo "$(date +%H:%M:%S) END rc=$rc $args" >> "logs/bench/chain_$1.log"
done
