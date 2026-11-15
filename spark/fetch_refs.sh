#!/bin/bash
cd ~/bonsai/refs
get() { curl -sL --fail -C - -o "$2" "https://huggingface.co/$1/resolve/main/$3" && echo "OK $2 $(du -h "$2" | cut -f1)" || echo "FAILED $2"; }
get unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-mmproj-BF16.gguf mmproj-BF16.gguf
get bartowski/UI-Venus-2-9B-GGUF UI-Venus-2-9B-mmproj-BF16.gguf mmproj-UI-Venus-2-9B-bf16.gguf
get unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-Q8_0.gguf Qwen3.5-9B-Q8_0.gguf
get bartowski/UI-Venus-2-9B-GGUF UI-Venus-2-9B-Q8_0.gguf UI-Venus-2-9B-Q8_0.gguf
echo REFS_DONE
