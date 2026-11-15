#!/bin/bash
# TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
# Runs on a pod: a worker that takes run lines from /root/te-runs/queue.txt one at a time.
#   nohup bash taskenv/queue.sh A > /root/te-runs/logs/worker_A.log 2>&1 &
# A queue line is   <peak GB> <arguments of python -m taskenv.run>   e.g.
#   42 --agent guided --model bonsai9b-new --patch export/patches/x.safetensors --tag v3-gentle --seeds 9101 --out runs/guided-v3-gentle-s1280
# The worker starts a line only when the GPU has the line's peak memory free plus RESERVE GB (the pod's
# training job must never be pushed out of memory), and holds a lock while a model loads so that two
# workers never measure free memory at the same moment. `touch /root/te-runs/STOP` ends the workers
# after their current run; a run resumes from its episodes.jsonl when its line is queued again.
R=/root/te-runs; Q=$R/queue.txt; L=$R/logs; RESERVE=${RESERVE:-10}; W=${1:-A}
mkdir -p "$L"; touch "$Q"; cd /workspace/te || exit 1
free_gb() { nvidia-smi --query-gpu=memory.total,memory.used --format=csv,noheader,nounits | awk -F', ' '{print int(($1-$2)/1024)}'; }
# GPU memory held by this queue's own runs. The training job may be between two cells when a worker looks,
# so free memory alone is not enough: the queue also never holds more than CAP GB itself.
mine_gb() {
  nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | while IFS=', ' read -r pid mb; do
    grep -qa "taskenv.run" /proc/$pid/cmdline 2>/dev/null && echo "$mb"; done | awk '{s+=$1} END {print int(s/1024)}'
}
CAP=${CAP:-46}
while [ ! -e $R/STOP ]; do
  line=$(flock $R/queue.lock bash -c 'head -n 1 "$0"; sed -i 1d "$0"' "$Q")
  if [ -z "$line" ]; then sleep 15; continue; fi
  peak=${line%% *}; args=${line#* }
  name=$(echo "$args" | sed -n 's/.*--out runs\/\([^ ]*\).*/\1/p')
  (
    flock 9
    until { [ "$(free_gb)" -ge $((peak + RESERVE)) ] && [ $(( $(mine_gb) + peak )) -le "$CAP" ]; } || [ -e $R/STOP ]; do sleep 10; done
    [ -e $R/STOP ] && { echo "$line" >> "$Q"; exit 0; }
    echo "$(date -u +%H:%M:%S) $W start $name (free $(free_gb) GB)" >> $L/queue.log
    TASKENV_STRICT=1 nohup ./venv/bin/python -m taskenv.run --root /root/te-root $args > "$L/$name.log" 2>&1 &
    echo $! > $R/worker_$W.pid
    sleep 100                                   # the model is loaded (and a Bonsai folded) before anyone measures again
  ) 9> $R/load.lock
  [ -e $R/STOP ] && break
  pid=$(cat $R/worker_$W.pid)
  while kill -0 "$pid" 2>/dev/null; do sleep 5; done
  echo "$(date -u +%H:%M:%S) $W end $name: $(tail -n 1 "$L/$name.log" | cut -c1-120)" >> $L/queue.log
done
