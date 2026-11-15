#!/bin/bash
# Restart a pod's lab session and queue one job:  restart_lane.sh <experiments/lanes/job.py> [9B|4B]
# Kills by recorded pid, never by pattern (a pattern can match the calling shell).
cd /workspace/bonsai || exit 1
export BONSAI_SIZE=${2:-9B}
for f in logs/filler.pid lab/kernel.pid; do [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null; done
sleep 3
for p in $(pgrep -f "weightlab/client.py"); do kill "$p" 2>/dev/null; done
rm -f lab/kernel.sock
nohup python3 -m weightlab.kernel > lab/kernel.log 2>&1 &
for i in $(seq 1 30); do [ -S lab/kernel.sock ] && break; sleep 1; done
echo "$1" > queue/backlog.txt
nohup bash tools/filler.sh /workspace/bonsai > logs/filler.log 2>&1 &
sleep 1
echo "session up: $(tail -n 1 lab/kernel.log | cut -c1-20) | size $BONSAI_SIZE | queued $1 | fix lines $(grep -c _fast_patch_embed weightlab/core.py)"
