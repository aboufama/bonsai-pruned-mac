#!/bin/bash
set -e
cd ~/bonsai
[ -d llama.cpp ] || git clone -q --depth 1 -b prism https://github.com/PrismML-Eng/llama.cpp.git
cd llama.cpp
export PATH=/usr/local/cuda/bin:$PATH LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH CUDACXX=/usr/local/cuda/bin/nvcc
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
nice -n 5 cmake --build build -j 12 --target llama-bench llama-server llama-cli
echo BUILD_DONE
