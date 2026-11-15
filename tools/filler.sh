#!/bin/bash
# Keeps a machine busy: whenever the lab session is idle, start the next line of the backlog.
#   usage: filler.sh [bonsai root]          (default ~/bonsai)
# Backlog: <root>/queue/backlog.txt, one experiment script per line (path relative to the root).
# A line is removed when it starts; its output goes to <root>/logs/job_<time>_<name>.log and its
# name to <root>/logs/current_job. Deterministic: no model decides anything here.
root=${1:-$HOME/bonsai}
cd "$root" || exit 1
mkdir -p logs queue; touch queue/backlog.txt
echo $$ > logs/filler.pid
while true; do
  if ! pgrep -f "[w]eightlab/client.py (run|exec)" > /dev/null && [ -S lab/kernel.sock ] && [ -s queue/backlog.txt ]; then
    job=$(head -n 1 queue/backlog.txt); sed -i 1d queue/backlog.txt
    if [ -n "$job" ] && [ -f "$job" ]; then
      name=$(basename "$job" .py); echo "$name" > logs/current_job
      ./venv/bin/python weightlab/client.py run "$job" > "logs/job_$(date +%H%M%S)_${name}.log" 2>&1
      echo "idle" > logs/current_job
    fi
  fi
  sleep 15
done
