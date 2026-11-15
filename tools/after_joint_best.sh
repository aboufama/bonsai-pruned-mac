#!/bin/bash
# When a joint decoder run ends: export its best scored step (highest "head on REPORT on target" in its
# job log; the earliest of equals), check the pair on the report set and the neighbour slice, wait for
# an optional marker file, then start the next job in a fresh session.
#   after_joint_best.sh <run tag> <base patch file> <out name> <next wrapper> <9B|4B> [marker file]
# Writes export/patches/<out name>-trunk.patch.safetensors and export/heads/<out name>-dec2x768-L20.safetensors.
cd /workspace/bonsai || exit 1
tag=$1; base=$2; name=$3; next=$4; size=$5; marker=$6
sleep 20; until [ "$(cat logs/current_job)" = idle ]; do sleep 10; done
log=$(ls -t logs/job_* | head -n 1)
step=$(grep "head on REPORT on target" "$log" | awk '{gsub(":","",$2); print $8+0, -$2, $2}' | sort -k1,1nr -k2,2nr | head -n 1 | awk '{print $3}')
echo "best scored step of $tag: $step ($(grep "step *$step: head on REPORT" "$log" | head -n 1))"
kill $(cat logs/filler.pid) $(cat lab/kernel.pid) 2>/dev/null; sleep 5
E=export
BONSAI_SIZE=$size python3 tools/joint_export.py $E/patches/$base lab/ckpt/joint018_${tag}_s${step}.pt $E/patches/$name-trunk.patch.safetensors $E/heads/$name-dec2x768-L20.safetensors > logs/export_$name.log 2>&1
BONSAI_SIZE=$size SIDES=1280 python3 tools/pointer_split.py $E/patches/$name-trunk.patch.safetensors $E/heads/$name-dec2x768-L20.safetensors > logs/split_$name.log 2>&1
BONSAI_SIZE=$size SET=mac:neighbour_test:test N=600 SIDES=1280 python3 tools/pointer_split.py $E/patches/$name-trunk.patch.safetensors $E/heads/$name-dec2x768-L20.safetensors > logs/split_nb_$name.log 2>&1
[ -n "$marker" ] && until [ -f "$marker" ]; do sleep 5; done
bash tools/restart_lane.sh $next $size
