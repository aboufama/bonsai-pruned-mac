#!/bin/sh
# Carries out a file of requests with nobody at the keyboard, against a plain OpenAI-compatible
# server (llama.cpp's llama-server on the VM host by default).
#   run-batch.sh REQUESTS.txt [STEPS.json]
# The log is written beside the steps file. Exit codes: see README.md.
here=$(cd "$(dirname "$0")" && pwd)
[ -n "$1" ] || { echo "usage: run-batch.sh REQUESTS.txt [STEPS.json]" >&2; exit 2; }
: "${BONSAI_SERVER:=http://192.168.64.1:1234}"
: "${BONSAI_PLAIN_SERVER:=1}"
export BONSAI_SERVER BONSAI_PLAIN_SERVER
out=${2:-$PWD/steps.json}
exec "$here/bonsai-assistant" --batch "$1" --out "$out" --log "${out%.json}.log"
