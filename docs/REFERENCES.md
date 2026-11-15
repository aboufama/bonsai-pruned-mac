# References

The articles and sources behind this project, each with a link and notes in our own words. The articles themselves are not copied here; follow the links for the originals.

## Articles that shaped the approach

### Weight-Space Programming (Rikiya Takehi and co-authors, MIT CSAIL)

https://rikiyat.github.io/blog/weight-space-programming/ · logs: https://github.com/RikiyaT/lm_understand-logs · edited model: https://huggingface.co/RikiyaT/Qwen3.5-0.8B-weight-space-programming

- A frontier model (GPT-6 Astra) was given a Python session with a small model's weights loaded and a budget of forward passes, and asked to improve the model by editing weights directly, with no gradients or training.
- On Qwen3.5-0.8B with thinking on, it found that the model's reasoning loops traced to one direction written by the MLPs in layers 15 and 19, and subtracted that direction from 64 output columns in each: 131,072 weights, 0.016% of the model.
- With a budget of 50 forward passes, MATH-500 went from 7.9% to 48.1%, GSM8K from 13.8% to 67.1%, IFEval from 21.0% to 62.3%, and the share of answers hitting the token limit from 93% to 33%. At 10 and 25 passes the loops barely went away.
- Limits the authors state: the edit removed an obstacle and did not add an ability. On Gemma 3 270M, which rarely loops, no improvement was found. A reader note on the announcement makes the same point: the gain is mostly fixing a known looping fault.
- **Why it matters here:** Bonsai's pointing failure is also a narrow fault in a model that otherwise works, and we have something the authors did not: a full-precision twin with the same architecture to compare against, layer by layer.

### Deletion Tuning (Jack Lu, Zhibo Yang and co-authors, NYU; NeurIPS 2026)

https://agenticlearning.ai/deleting-weights/ · paper: https://arxiv.org/abs/2611.10866 · code: https://github.com/agentic-learning-ai-lab/deleting-weights · masks: https://huggingface.co/Jacklu0831/deletion-tuning-masks

- Post-training by deletion alone: pretrained weights stay frozen, and each weight in every block's gate projection gets one trainable logit. Training multiplies the weight by a sigmoid of that logit, sharpened over training until it becomes a hard keep-or-delete decision. The result is one bit per weight.
- Logits start from Wanda pruning scores; no sparsity target is set. Under 0.05% of weights end up deleted.
- It matched full fine-tuning at 7B and above under reinforcement learning (for example Qwen 7B 52.3 vs 51.9, Qwen3-30B-A3B 58.5 vs 58.4), and also under supervised fine-tuning and self-distillation on tool use. At 0.5B to 3B it trailed by 1 to 6 points.
- It forgets far less: within a point of the base model on six prior tasks, where full fine-tuning lost 1.3 to 3.1 points and LoRA up to 5.4.
- **Why it matters here:** Bonsai's weights are -1, 0 or +1, so deleting a weight sets it to a value the format already allows. A deletion mask keeps the model ternary and the file unchanged in size. That fit is our inference; the paper does not test quantised models. About a third of Bonsai's weights are already zero.

### How to be more ambitious: a tutorial for humans with models (Felix Rieseberg)

https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/

- Four kinds of ambition when working with models: speed, altitude (ask for the outcome, not the task), depth (work the way a field-leading expert would) and range (bring in more fields than was economical before).
- Depth techniques we use: the best practitioners' instruments, goals that sound unreasonable, challenging what we think we know, and an outside judge so the model never grades itself.
- **How it is applied here:** the target is "beat the full-precision fine-tune", not "make it work"; every claim is checked by a benchmark tool or a second runtime; reference models with published scores validate the harness before any Bonsai number is trusted.

### Redesigning source control (Anthropic)

https://www.anthropic.com/research/redesigning-source-control

- Introduces "superfans": Claude instances each tasked with being obsessively focused on the health of one component, with access to telemetry and logs, behaving like an experienced engineer with nothing better to do than refresh charts and look for anything strange. The post says they catch subtle and novel issues that conventional alerts miss. It gives no prompts, cadence or guardrails.
- **How it is applied here:** a few single-metric watcher agents (GPU idle time, evaluation speed, downloads) ran during the project. Their notes are not part of this repository.

## Models

- Bonsai 2 family announcement: https://prismml.com/news/bonsai-2-family
- Bonsai 2 small-model whitepaper: https://github.com/PrismML-Eng/Bonsai-demo/blob/main/bonsai-2-small-whitepaper.pdf
- Bonsai 2 27B whitepaper: https://github.com/PrismML-Eng/Bonsai-demo/blob/main/bonsai-2-27b-whitepaper.pdf
- PrismML demo repo and llama.cpp fork: https://github.com/PrismML-Eng/Bonsai-demo · https://github.com/PrismML-Eng/llama.cpp
- Bonsai 2 9B weights: https://huggingface.co/prism-ml/Ternary-Bonsai-2-9B-gguf · https://huggingface.co/prism-ml/Ternary-Bonsai-2-9B-mlx-2bit
- Qwen3.5-9B (the parent): https://huggingface.co/Qwen/Qwen3.5-9B
- UI-Venus-2-9B (computer-use fine-tune of the parent; ScreenSpot-Pro 73.0): https://huggingface.co/inclusionAI/UI-Venus-2-9B · code: https://github.com/inclusionAI/UI-Venus
- Community ONNX conversion documenting the ternary format: https://huggingface.co/Mike0021/Ternary-Bonsai-2-9B-text-ONNX

## Benchmarks

- ScreenSpot-Pro: https://huggingface.co/datasets/likaixin/ScreenSpot-Pro
- ScreenSpot-v2: https://huggingface.co/datasets/OS-Copilot/ScreenSpot-v2
- OSWorld and OSWorld-G: https://os-world.github.io · https://osworld-grounding.github.io
- Collected grounding benchmarks: https://huggingface.co/datasets/yyyang/UI-Grounding-Benchmarks

## The reference application

- Clicky (open source, MIT): https://github.com/farzaa/clicky · product: https://www.heyclicky.com
- In the open-source version, Claude Sonnet reads a screenshot of each display shrunk to 1280 px on its long side and ends its spoken reply with `[POINT:x,y:label]`; a transparent overlay animates a cursor to that point. Speech-to-text is AssemblyAI and text-to-speech is ElevenLabs. A second path uses the dedicated computer-use tool at 1280x800 for more precise locating.
- Write-up of the interface: https://isaac-flath.kit.com/posts/point-and-talk-how-clicky-s-ai-interface-works
