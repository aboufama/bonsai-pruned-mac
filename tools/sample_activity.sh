#!/bin/bash
# Appends one line every 30 s: unix time, GPU utilisation %, GPU memory used by all processes (MiB),
# memory available on the machine (GB), and the name of the newest lab cell (what is running).
# Deterministic and tiny. Stop with: kill $(cat ~/bonsai/logs/activity.pid)
out=${1:-$HOME/bonsai/logs/activity_spark.csv}
echo $$ > "$(dirname "$out")/activity.pid"
while true; do
  util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -d " ")
  mem=$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits 2>/dev/null | awk "{s+=\$1} END {print s+0}")
  avail=$(awk "/MemAvailable/ {printf \"%d\", \$2/1048576}" /proc/meminfo)
  cell=$(ls -t $HOME/bonsai/lab/cells/*.py 2>/dev/null | head -n 1 | xargs -r basename)
  echo "$(date +%s),${util:-0},${mem:-0},${avail},${cell}" >> "$out"
  sleep 30
done
