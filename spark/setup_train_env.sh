#!/bin/bash
# User-space Python environment for training (no sudo needed).
cd ~/bonsai
python3 -m venv venv || exit 1
./venv/bin/pip -q install --upgrade pip
./venv/bin/pip -q install torch torchvision --index-url https://download.pytorch.org/whl/cu130 || ./venv/bin/pip -q install torch torchvision
./venv/bin/pip -q install transformers safetensors accelerate pillow numpy huggingface_hub
./venv/bin/python -c "import torch; print(\"torch\", torch.__version__, \"cuda\", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"\")"
echo ENV_DONE
