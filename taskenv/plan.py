"""Queue lines for taskenv/queue.sh (printed to stdout): which runs, in which order.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    python taskenv/plan.py 9101 first | ssh <pod> 'cat >> /root/te-runs/queue.txt'

A line is "<peak GB> <arguments of taskenv.run>". Zero-shot models get the "rules" prompt in
agent mode; action-trained patches get the prompt they were trained with ("plain").
"""
import sys

P = "export/patches/"
MODELS = {  # name: (bench key, patch, peak GB)
    "4b-v2-mixed": ("bonsai4b-new", P + "bonsai2-4b-point-v2-mixed.patch.safetensors", 20),
    "4b-v1": ("bonsai4b-new", P + "bonsai2-4b-point-v1.patch.safetensors", 20),
    "4b-tools": ("bonsai4b-new", P + "bonsai2-4b-point-tools-v1.patch.safetensors", 20),
    "4b-actions-u500": ("bonsai4b-new", P + "bonsai2-4b-actions-v1-u500.patch.safetensors", 20),
    "4b-actions-u1000": ("bonsai4b-new", P + "bonsai2-4b-actions-v1-u1000.patch.safetensors", 20),
    "4b-orig": ("bonsai4b-orig", None, 20),
    "9b-v3-gentle": ("bonsai9b-new", P + "bonsai2-9b-point-v3-gentle.patch.safetensors", 42),
    "9b-v2": ("bonsai9b-new", P + "bonsai2-9b-point-v2.patch.safetensors", 42),
    "9b-v3-tools": ("bonsai9b-new", P + "bonsai2-9b-point-v3-tools.patch.safetensors", 42),
    "9b-actions-u500": ("bonsai9b-new", P + "bonsai2-9b-actions-v1-u500.patch.safetensors", 42),
    "9b-orig": ("bonsai9b-orig", None, 42),
    "qwen35-9b": ("qwen35-9b", None, 21),
    "venus2-9b": ("venus2-9b", None, 21),
}
SETS = {
    "first": [("guided", "4b-v2-mixed", "s1280"), ("agent", "4b-actions-u500", "s1280"), ("agent", "qwen35-9b", "s1280"), ("guided", "qwen35-9b", "s1280"),
              ("guided", "9b-v3-gentle", "s1280"), ("guided", "venus2-9b", "s1280"), ("agent", "9b-actions-u500", "s1280"), ("guided", "4b-v2-mixed", "s896")],
    "second": [("guided", "9b-v2", "s1280"), ("guided", "9b-orig", "s1280"), ("agent", "4b-tools", "s1280"), ("guided", "4b-v1", "s1280"),
               ("agent", "9b-v3-tools", "s1280"), ("agent", "9b-orig", "s1280"), ("guided", "9b-v3-gentle", "s896"), ("agent", "venus2-9b", "s1280"),
               ("guided", "4b-orig", "s1280"), ("agent", "4b-actions-u500", "s896")],
    "third": [("guided", "9b-v2", "s896"), ("guided", "9b-v3-tools", "s1280"), ("guided", "9b-v3-tools", "s1280", "tool"), ("agent", "9b-v3-gentle", "s1280"),
              ("guided", "4b-v1", "s896"), ("agent", "9b-actions-u500", "s896"), ("agent", "qwen35-9b", "s896")],
}


def line(mode, name, size, ask="point", seeds="9101", prompt=None):
    key, patch, peak = MODELS[name]
    prompt = prompt or ("plain" if "actions" in name else "rules")
    out = f"{'g' if mode == 'guided' else 'a'}-{name}{'-tool' if ask == 'tool' else ''}-{size}"
    a = [f"--agent {mode}", f"--model {key}"] + ([f"--patch {patch}"] if patch else []) + ([f"--tag {name}"] if patch else []) + [f"--input {size}"]
    a += [f"--ask {ask}"] if mode == "guided" else [f"--prompt {prompt}"]
    a += [f"--seeds {seeds}", "--needed-from runs/oracle-test/episodes.jsonl", f"--out runs/{out}"]
    return f"{peak} " + " ".join(a)


if __name__ == "__main__":
    seeds, which = sys.argv[1], sys.argv[2:]
    for w in which:
        for item in SETS[w] if w in SETS else [tuple(w.split(":"))]:
            print(line(*item, seeds=seeds))
