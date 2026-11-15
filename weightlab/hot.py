"""Pick up edited lab code in the running session without reloading the models.

    ./venv/bin/python weightlab/client.py exec "import weightlab.hot as h, importlib; importlib.reload(h); h.reload(globals())"

Re-imports the lab's modules and points the existing objects (the lab, every ternary layer) at
the new classes. State that lives in the objects (weights, caches, notes) is untouched.
"""
import importlib


def reload(namespace):
    import weightlab.ternary as ternary
    import weightlab.core as core
    import weightlab.fast as fast
    import weightlab.distill as distill
    import weightlab.tune as tune
    import weightlab.e2e as e2e
    import weightlab.chat as chat
    import weightlab.head as head
    for mod in (ternary, core, fast, distill, chat, tune, e2e, head):
        importlib.reload(mod)
    lab = namespace["lab"]
    lab.__class__ = core.Lab
    lab._images = {}
    n = 0
    for model in lab.models.values():
        if hasattr(model, "modules"):
            for m in model.modules():
                if type(m).__name__ == "TernaryLinear":
                    m.__class__ = ternary.TernaryLinear
                    for name, default in (("keep_hard", False), ("_hard", None), ("compute_dtype", None),
                                          ("lean", None), ("_m", None), ("_v", None)):
                        if name not in m.__dict__:
                            setattr(m, name, default)
                    n += 1
    for value in namespace.values():
        if type(value).__name__ == "FastEval":
            value.__class__ = fast.FastEval
    print(f"reloaded; {n} ternary layers re-pointed")
