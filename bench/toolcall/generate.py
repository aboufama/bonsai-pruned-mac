#!/usr/bin/env python3
"""Procedural generator of tool-calling benchmark cases.

    python3 generate.py --seed 20261114 --n 400 --split dev --out runs/dev_20261114

Writes DIR/cases.jsonl. The same seed and arguments always give byte-identical
output: every case draws from its own random.Random seeded by
sha256(seed, split, index); no global random state, no clock, sorted keys.

Ground truth is fixed first (which tool, which argument values) and the user
request is then written from templates that state every needed value, so the
expected calls are exact by construction. No language model is involved.
"""
import argparse
import copy
import datetime as dt
import hashlib
import itertools
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import phrasing  # noqa: E402
import screens  # noqa: E402
import spec  # noqa: E402
from pools import BASE, SPLITS, Pools, part  # noqa: E402
from spec import NODEF, BoolK, EnumK, IntK, ListK, ObjK, OListK, camel, ident  # noqa: E402

import domains_dev  # noqa: E402,F401  (fills spec.REGISTRY / spec.CHAINS)
import domains_test  # noqa: E402,F401
import domains_train  # noqa: E402,F401

CATEGORIES = ["a_single", "b_selection", "c_parallel", "d_multistep",
              "e_missing", "f_irrelevant", "g_typing", "h_computer"]
PLAIN_STYLES = ("terse", "polite", "indirect", "chatter")
VALUE_TRAPS = ("relative_date", "time_12h", "number_words", "enum_map")


# --------------------------------------------------------------------------
# Per-split vocabulary
# --------------------------------------------------------------------------

class Vocab:
    def __init__(self, split):
        self.split = split
        self.P = Pools(split)
        self.domains = [d for d in spec.REGISTRY if d.split == split]
        self.by_name = {d.name: d for d in self.domains}
        self.intents = [it for d in self.domains for it in d.intents]
        self.chains = [c for c in spec.CHAINS if c.split == split]
        self.ph = phrasing.pools_for(split)
        self.hp = screens.pools_for(split)
        self.askable = [it for it in self.intents if any(s.ask for s in it.slots)]
        self.near_miss = [it for it in self.intents
                          if f"{it.domain.name}.{it.key}" not in spec.NEAR_MISS_UNSAFE and len(it.domain.intents) >= 3]
        self.traps = {}
        for it in self.intents:
            for s in it.slots:
                name = trap_of(it, s)
                if name:
                    self.traps.setdefault(name, []).append((it, s))
        self.trap_names = sorted(self.traps)


def trap_of(intent, slot):
    """Name of the category-g trap this slot can express, or None."""
    k = slot.kind
    if isinstance(k, (OListK, ObjK)):
        return "nested_object"
    if isinstance(k, ListK):
        return "array"
    if isinstance(k, BoolK):
        return "boolean"
    if isinstance(k, EnumK):
        return "enum_map" if k.natural else None
    if slot.key in intent.linked:
        return None
    if isinstance(k, IntK):
        return "number_words" if any(wordable(c) for c in k.choices) else None
    return k.trapname


def wordable(n):
    """Integers that read naturally when spelled out."""
    return 0 < n < 1000 or (n % 500 == 0 and n <= 20000)


_VOCABS = {}


def vocab(split):
    if split not in _VOCABS:
        _VOCABS[split] = Vocab(split)
    return _VOCABS[split]


class Ctx:
    def __init__(self, rng, V, today, cs, aux=None):
        self.rng, self.V, self.P, self.today, self.cs = rng, V, V.P, today, cs
        self.aux = aux or random.Random(0)   # second stream for choices added after the main one was fixed
        self.used = set()

    def draw(self, kind, gt=None, ne=None):
        v = None
        for _ in range(60):
            v = kind.gen(self, gt=gt, ne=ne)
            if not kind.uniq:
                return v
            key = kind.say(v, self.cs)
            if key not in self.used:
                self.used.add(key)
                return v
        return v


# --------------------------------------------------------------------------
# Tool instances
# --------------------------------------------------------------------------

class Param:
    def __init__(self, name, kind, desc, required=True, default=NODEF, slot=None, loose=False):
        self.name, self.kind, self.desc, self.required = name, kind, desc, required
        self.default, self.slot, self.loose = default, slot, loose


class Tool:
    def __init__(self, name, desc, params, intent=None):
        self.name, self.desc, self.params, self.intent = name, desc, params, intent

    def schema(self, cs):
        props = {}
        for p in self.params:
            s = p.kind.schema(cs)
            desc = p.desc
            if not p.required:
                desc += " Optional."
                if p.default is not NODEF:
                    s["default"] = p.default
                    desc += f" Default: {json.dumps(p.default)}."
            s["description"] = desc
            props[p.name] = s
        return {"type": "function", "function": {
            "name": self.name, "description": self.desc,
            "parameters": {"type": "object", "properties": props,
                           "required": [p.name for p in self.params if p.required]}}}

    def rules(self):
        out = {}
        for p in self.params:
            r = {}
            if p.loose:
                r["mode"] = "contains"
            if isinstance(p.kind, ListK):
                r["unordered"] = not p.kind.ordered
            if not p.required:
                r["optional"] = True
                if p.default is not NODEF:
                    r["default"] = p.default
            if r:
                out[p.name] = r
        return out


def pick_name(ctx, names, taken):
    cands = [ctx.cs(n) for n in names]
    ctx.rng.shuffle(cands)
    for n in cands:
        if n not in taken:
            taken.add(n)
            return n
    return None


def make_tool(ctx, intent, taken, force=()):
    """Instantiate one concrete tool schema from an intent."""
    rng = ctx.rng
    name = pick_name(ctx, intent.names, taken)
    if name is None:
        return None
    params, used = [], set()
    for slot in intent.slots:
        required = True
        if slot.opt:
            r = rng.random()
            if slot.key in force:
                required = r >= 0.75
            elif r < 0.25:
                continue            # this variant of the tool does not have the parameter
            else:
                required = r >= 0.8  # sometimes promoted to required
        free = [n for n in rng.sample(slot.names, len(slot.names)) if ctx.cs(n) not in used]
        if not free:
            raise RuntimeError(f"no free parameter name for {intent.key}/{slot.key}")
        base = free[0]
        used.add(ctx.cs(base))
        default = NODEF
        if not required:
            if rng.random() < 0.6:
                default = slot.kind.default(ctx)
            elif isinstance(slot.kind, BoolK):
                # An optional boolean always declares its default. Otherwise "whether or not they are
                # open" (false) and leaving the argument out would both be defensible answers.
                default = ctx.aux.random() < 0.5
        params.append(Param(ctx.cs(base), slot.kind, spec.describe(base, slot.kind, slot.desc),
                            required, default, slot, slot.loose))
    return Tool(name, rng.choice(intent.descs), params, intent)


def pick_others(ctx, exclude_tags, k, taken):
    """Up to k tools from domains that share no tag with `exclude_tags`."""
    rng = ctx.rng
    doms = [d for d in ctx.V.domains if not (d.tags & exclude_tags)]
    rng.shuffle(doms)
    out = []
    for d in doms:
        if len(out) >= k:
            break
        take = min(len(d.intents), rng.randint(1, 3), k - len(out))
        for it in rng.sample(d.intents, take):
            t = make_tool(ctx, it, taken)
            if t:
                out.append(t)
    return out


# --------------------------------------------------------------------------
# From a tool to an expected call plus the clauses that state its values
# --------------------------------------------------------------------------

SINGULAR = {"days": "day", "minutes": "minute", "hours": "hour", "weeks": "week", "seconds": "second",
            "people": "person", "bags": "bag", "rows": "row", "columns": "column", "stars": "star",
            "shares": "share", "zones": "zone", "parcels": "parcel", "servings": "serving", "units": "unit",
            "passengers": "passenger", "travellers": "traveller", "guests": "guest", "entries": "entry",
            "results": "result", "departures": "departure", "items": "item", "notes": "note", "cards": "card",
            "points": "point", "calories": "calorie", "story points": "story point"}
_ONE = re.compile(r"\b(1|one) (" + "|".join(sorted(SINGULAR, key=len, reverse=True)) + r")\b")


def singular(text):
    """'by 1 days' -> 'by 1 day'."""
    return _ONE.sub(lambda m: f"{m.group(1)} {SINGULAR[m.group(2)]}", text)


_A_AN = re.compile(r"\b([Aa]) (?=(?:[aeiouAEIOU]|8\d*\b|11\b|18\b))(?!(?:one|once|uni|use|usu|eu|ub)[a-z]*)")


def articles(text):
    """'a aisle seat' -> 'an aisle seat', 'a 8 km radius' -> 'an 8 km radius'."""
    return _A_AN.sub(lambda m: m.group(1) + "n ", text)


def render_clause(ctx, slot, value, trap=None):
    return singular(_render_clause(ctx, slot, value, trap))


def _render_clause(ctx, slot, value, trap=None):
    kind, rng = slot.kind, ctx.rng
    if isinstance(kind, BoolK):
        return rng.choice(kind.yes if value else kind.no)
    if trap and trap.get("clause"):
        return trap["clause"]
    tpl = rng.choice(slot.clauses)
    if trap:
        said = trap["say"]
        if trap.get("drop_on"):
            tpl = tpl.replace("on {v}", "{v}")
    else:
        said = kind.say(value, ctx.cs)
    return tpl.replace("{v}", said)


def is_tail(param, text, trap):
    return (isinstance(param.slot.kind, BoolK) or bool(trap and trap.get("clause"))
            or text.startswith(("and ", "but ", "then ", "so that ", "so ")))


def reorder(rng, items):
    """Order of clauses that differs from the schema order (alphabetical by
    parameter name, because cases are serialised with sorted keys)."""
    n = len(items)
    nat = list(range(n))
    schema = sorted(nat, key=lambda i: items[i][0].name)
    if n <= 5:
        perms = [list(p) for p in itertools.permutations(nat)]
    else:
        perms = [rng.sample(nat, n) for _ in range(40)]
    cands = [p for p in perms if p != schema and p != nat] or [p for p in perms if p != schema]
    return rng.choice(cands) if cands else nat


def plan_call(ctx, tool, style="terse", omit=None, trap_key=None):
    """Choose argument values for one call and write the clauses that state them.

    Returns dict(args, core, style, trap, corrected). `style` may be downgraded
    to a plain one when 'reordered' or 'correction' is not applicable.
    """
    rng, it = ctx.rng, tool.intent
    mentioned = [p for p in tool.params if p is not omit and
                 (p.required or p.slot.key == trap_key or rng.random() < 0.5)]
    mentioned.sort(key=lambda p: it.slots.index(p.slot))  # natural (hand-written) order
    values, trap = {}, None
    for p in mentioned:
        slot, kind = p.slot, p.slot.kind
        if slot.key == trap_key and trap_of(it, slot) in VALUE_TRAPS:
            trap = trap_value(ctx, kind)
            v = trap["value"]
            if kind.uniq:
                ctx.used.add(kind.say(v, ctx.cs))
        else:
            v = ctx.draw(kind, gt=values.get(slot.gt), ne=values.get(slot.ne))
        values[slot.key] = v
    items = [[p, render_clause(ctx, p.slot, values[p.slot.key], trap if p.slot.key == trap_key else None)]
             for p in mentioned]
    # Subordinate clauses (booleans, natural-language enum clauses, "and ...") are kept at the end of the
    # request in every style, so that they can never attach to the wrong noun after reordering.
    tails = [x for x in items if is_tail(x[0], x[1], trap if x[0].slot.key == trap_key else None)]
    items = [x for x in items if x not in tails]

    corrected = None
    if style == "correction":
        cands = [i for i, (p, _) in enumerate(items)
                 if p.slot.kind.correctable and p.slot.key not in it.linked and p.slot.key != trap_key]
        rng.shuffle(cands)
        for i in cands:
            p = items[i][0]
            kind = p.slot.kind
            wrong = kind.wrong(ctx, values[p.slot.key])
            if wrong is None:
                continue
            tpl = rng.choice(p.slot.clauses)
            items[i][1] = (singular(tpl.replace("{v}", kind.say(wrong, ctx.cs))) + rng.choice(ctx.V.ph["corrections"])
                           + " " + kind.say(values[p.slot.key], ctx.cs))
            items.append(items.pop(i))  # the corrected clause goes last
            corrected = p.name
            break
        if corrected is None:
            style = rng.choice(PLAIN_STYLES)
    elif style == "reordered":
        if len(items) >= 2:
            items = [items[i] for i in reorder(rng, items)]
        else:
            style = rng.choice(PLAIN_STYLES)

    core = " ".join([rng.choice(it.acts)] + [text for _, text in items + tails])
    args = {p.name: values[p.slot.key] for p in mentioned}
    return {"args": args, "core": core, "style": style, "corrected": corrected,
            "trap": bool(trap)}


def trap_value(ctx, kind):
    if isinstance(kind, IntK):
        v = ctx.rng.choice([c for c in kind.choices if wordable(c)])
        return {"value": v, "say": spec.num_words(v)}
    t = kind.trap(ctx)
    assert t is not None
    return t


def stylize(ctx, core, style):
    ph, rng = ctx.V.ph, ctx.rng
    out = rng.choice(ph["wrappers"][style])
    core = articles(core)
    out = out.replace("{Req}", core[:1].upper() + core[1:]).replace("{req}", core)
    if "{c1}" in out or "{c2}" in out:
        c1, c2 = rng.sample(ph["chatter"], 2)
        out = out.replace("{c1}", c1).replace("{c2}", c2)
    return out


def system_prompt(ctx):
    t = ctx.today
    today = ctx.rng.choice(ctx.V.ph["today"]).format(
        wd=spec.WEEKDAYS[t.weekday()], d=t.day, month=spec.MONTHS[t.month - 1], y=t.year, iso=t.isoformat())
    return ctx.rng.choice(ctx.V.ph["system"]).replace("{today}", today)


def call(tool, args):
    return {"name": tool.name, "arguments": args}


def finish(ctx, tools, user, expected, used_tools, meta, system=None):
    ctx.rng.shuffle(tools)
    return {
        "tools": [t.schema(ctx.cs) for t in tools],
        "messages": [{"role": "system", "content": system or system_prompt(ctx)},
                     {"role": "user", "content": user}],
        "expected": expected,
        "arg_match": {t.name: t.rules() for t in used_tools if t.rules()},
        "meta": meta,
    }


# --------------------------------------------------------------------------
# Category builders
# --------------------------------------------------------------------------

def build_single(ctx):
    rng = ctx.rng
    it = rng.choice(ctx.V.intents)
    taken = set()
    tool = make_tool(ctx, it, taken)
    plan = plan_call(ctx, tool, rng.choice(phrasing.STYLES))
    tools = [tool] + pick_others(ctx, it.domain.tags, rng.randint(0, 2), taken)
    return finish(ctx, tools, stylize(ctx, plan["core"], plan["style"]),
                  {"calls": [call(tool, plan["args"])]}, [tool],
                  {"domain": it.domain.name, "style": plan["style"], "intent": it.key})


def build_selection(ctx):
    rng = ctx.rng
    it = rng.choice(ctx.V.intents)
    taken = set()
    tool = make_tool(ctx, it, taken)
    plan = plan_call(ctx, tool, rng.choice(phrasing.STYLES))
    n = rng.randint(6, 12)
    distractors, twin = [], None
    if rng.random() < 0.6:
        twin = rng.choice(["deprecated", "dryrun"])
        t = make_twin(ctx, tool, twin, taken)
        if t:
            distractors.append(t)
        else:
            twin = None
    siblings = [s for s in it.domain.intents if s is not it]
    rng.shuffle(siblings)
    distractors += [t for t in (make_tool(ctx, s, taken) for s in siblings[:n - len(distractors)]) if t]
    distractors += pick_others(ctx, it.domain.tags, n - len(distractors), taken)
    return finish(ctx, [tool] + distractors, stylize(ctx, plan["core"], plan["style"]),
                  {"calls": [call(tool, plan["args"])]}, [tool],
                  {"domain": it.domain.name, "style": plan["style"], "intent": it.key,
                   "n_distractors": len(distractors), "twin": twin or "none"})


def make_twin(ctx, tool, kind, taken):
    """A near-duplicate of `tool` with the same parameters whose description rules it out."""
    rng, ph = ctx.rng, ctx.V.ph
    suffix = rng.choice(ph[f"twin_{kind}_suffix"])
    desc = rng.choice(ph[f"twin_{kind}_desc"]).replace("{name}", tool.name)
    for base in rng.sample(tool.intent.names, len(tool.intent.names)):
        name = ctx.cs(f"{base}_{suffix}")
        if name not in taken:
            taken.add(name)
            return Tool(name, desc, list(tool.params), tool.intent)
    return None


def build_parallel(ctx):
    rng, V = ctx.rng, ctx.V
    k = rng.choice([2, 2, 2, 2, 2, 2, 3, 3, 3, 4])
    style = rng.choice(phrasing.STYLES)
    taken = set()
    if rng.random() < 0.4:
        it = rng.choice(V.intents)
        tool = make_tool(ctx, it, taken)
        tools = [tool] * k
    else:
        tools = []
        for it in rng.sample(V.intents, len(V.intents)):
            t = make_tool(ctx, it, taken)
            if t:
                tools.append(t)
            if len(tools) == k:
                break
    plans = []
    for i in range(k):
        for attempt in range(60):
            if attempt == 50:
                # the tool has too few distinct argument combinations: use another tool for this call
                others = [it for it in V.intents if all(it is not t.intent for t in tools)]
                tools[i] = next(t for t in (make_tool(ctx, it, taken) for it in rng.sample(others, len(others))) if t)
            plan = plan_call(ctx, tools[i], style if i == 0 else "terse")
            if all(not (tools[j] is tools[i] and plans[j]["args"] == plan["args"]) for j in range(i)):
                break
        else:
            raise RuntimeError("could not make distinct parallel calls")
        plans.append(plan)
    style = plans[0]["style"]
    core = plans[0]["core"]
    for plan in plans[1:]:
        core += rng.choice(V.ph["joiners"]) + plan["core"]
    tags = set().union(*(t.intent.domain.tags for t in tools))
    uniq = list(dict.fromkeys(tools))
    all_tools = uniq + pick_others(ctx, tags, rng.randint(2, 5), taken)
    return finish(ctx, all_tools, stylize(ctx, core, style),
                  {"calls": [call(t, p["args"]) for t, p in zip(tools, plans)]}, uniq,
                  {"domain": "+".join(dict.fromkeys(t.intent.domain.name for t in tools)), "style": style,
                   "intent": "+".join(t.intent.key for t in tools), "n_calls": k})


def build_multistep(ctx):
    rng, V, cs = ctx.rng, ctx.V, ctx.cs
    ch = rng.choice(V.chains)
    depth = rng.choice([0, 1, 1, 2, 2])
    act = rng.choice([a for a in ch.actions if a.level == depth])
    taken = set()
    keys = [lv.out_key for lv in ch.levels]

    def fix(desc):  # keep result-key names in descriptions consistent with the naming style
        for key in keys:
            desc = desc.replace(key, cs(key))
        return desc

    # hops that return a list of candidates instead of the wanted entity itself
    listed = {i for i in range(1, len(ch.levels)) if ch.levels[i].pick and rng.random() < 0.5}

    def level_tool(i):
        lv = ch.levels[i]
        src = lv.pick if i in listed else {"names": lv.names, "descs": lv.descs}
        name = pick_name(ctx, src["names"], taken)
        if i == 0:
            base = rng.choice(lv.key.names)
            p = Param(cs(base), lv.key.kind, spec.describe(base, lv.key.kind))
        else:
            base = rng.choice(lv.inp)
            prev = ch.levels[i - 1]
            p = Param(cs(base), prev.out_kind, f"The {cs(prev.out_key)} of the {prev.ent}.")
        desc = rng.choice(src["descs"])
        if i in listed:  # the attribute name follows the case's naming style too
            desc = desc.replace(lv.pick["attr"], cs(lv.pick["attr"]))
        return Tool(name, fix(desc), [p])

    def action_tool(a):
        lv = ch.levels[a.level]
        params = [Param(cs(rng.choice(a.id_names)), lv.out_kind, f"The {cs(lv.out_key)} of the {lv.ent}.")]
        for s in a.slots:
            base = rng.choice(s.names)
            params.append(Param(cs(base), s.kind, spec.describe(base, s.kind, s.desc), slot=s, loose=s.loose))
        return Tool(pick_name(ctx, a.names, taken), fix(rng.choice(a.descs)), params)

    level_tools = [level_tool(i) for i in range(depth + 1)]
    final = action_tool(act)

    key_val = ctx.draw(ch.levels[0].key.kind)
    ids = [ctx.draw(ch.levels[i].out_kind) for i in range(depth + 1)]
    args = {final.params[0].name: ids[depth]}
    clauses = []
    for p in final.params[1:]:
        v = ctx.draw(p.kind)
        args[p.name] = v
        clauses.append(render_clause(ctx, p.slot, v))

    def result(i):
        lv = ch.levels[i]
        if i not in listed:
            out = {cs(lv.out_key): ids[i]}
            for k, kind in lv.extras:
                out[cs(k)] = ctx.draw(kind)
            return out
        # list variant: 3 or 4 candidates, exactly one of which fits the wording of the request
        pk, n = lv.pick, rng.randint(3, 4)
        rule, kind = pk["rule"], pk["kind"]
        if rule in ("max", "min"):
            vals = rng.sample(kind.choices, n) if isinstance(kind, IntK) else [ctx.draw(kind) for _ in range(n)]
            assert len(set(vals)) == n
            best = max(vals) if rule == "max" else min(vals)
            vals.remove(best)
            vals = [best] + vals
        elif rule == "rank1":
            vals = list(range(1, n + 1))
        elif rule == "true":
            vals = [True] + [False] * (n - 1)
        else:
            want = rule.split(":", 1)[1]
            vals = [want] + [rng.choice([v for v in kind.values if v != want]) for _ in range(n - 1)]
        entries = [{cs(lv.out_key): ids[i] if j == 0 else ctx.draw(lv.out_kind), cs(pk["attr"]): v}
                   for j, v in enumerate(vals)]   # entry 0 is the wanted one
        extra = next(((k, kd) for k, kd in lv.extras if k != pk["attr"]), None)
        if extra:   # one neutral descriptive field per entry
            for e in entries:
                e[cs(extra[0])] = ctx.draw(extra[1])
        rng.shuffle(entries)
        return {cs(pk["list_key"]): entries}

    steps = []
    for i in range(depth + 1):
        arg = key_val if i == 0 else ids[i - 1]
        steps.append({"calls": [call(level_tools[i], {level_tools[i].params[0].name: arg})],
                      "tool_results": [result(i)]})
    steps.append({"calls": [call(final, args)], "tool_results": [{"status": "success"}]})

    root = ch.levels[0]
    root_np = rng.choice(root.nouns).replace("{v}", root.key.kind.say(key_val, cs))
    narrated = depth >= 1 and rng.random() < 0.4
    if narrated:
        parts = [f"{rng.choice(root.verb)} {root_np}"]
        for i in range(1, depth + 1):
            noun = rng.choice(ch.levels[i].nouns).replace("{prev}", "that " + ch.levels[i - 1].ent)
            parts.append(f"{rng.choice(['find', 'get', 'look up'])} {noun}")
        parts.append(" ".join([rng.choice(act.acts).replace("{ent}", "that " + ch.levels[depth].ent)] + clauses))
        core = parts[0]
        for part_ in parts[1:]:
            core += rng.choice(V.ph["thens"]) + part_
    else:
        np_ = root_np
        for i in range(1, depth + 1):
            np_ = rng.choice(ch.levels[i].nouns).replace("{prev}", np_)
        core = " ".join([rng.choice(act.acts).replace("{ent}", np_)] + clauses)

    # distractors: sibling actions, deeper lookups of the same chain, unrelated tools
    extra = []
    for a in rng.sample([a for a in ch.actions if a is not act], rng.randint(1, 3)):
        extra.append(action_tool(a))
    for i in range(depth + 1, len(ch.levels)):
        if rng.random() < 0.5:
            extra.append(level_tool(i))
    extra = [t for t in extra if t.name]
    extra += pick_others(ctx, V.by_name[ch.domain].tags, rng.randint(0, 3), taken)
    style = rng.choice(PLAIN_STYLES)
    return finish(ctx, level_tools + [final] + extra, stylize(ctx, core, style), {"steps": steps},
                  level_tools + [final],
                  {"domain": ch.domain, "style": style, "intent": f"{ch.name}/{act.names[0]}",
                   "n_steps": depth + 2, "narrated": narrated,
                   "list_results": len([i for i in listed if i <= depth])})


def build_missing(ctx):
    rng = ctx.rng
    it = rng.choice(ctx.V.askable)
    slot = rng.choice([s for s in it.slots if s.ask])
    taken = set()
    tool = make_tool(ctx, it, taken)
    omit = next(p for p in tool.params if p.slot is slot)
    plan = plan_call(ctx, tool, rng.choice(phrasing.STYLES), omit=omit)
    tools = [tool] + pick_others(ctx, it.domain.tags, rng.randint(0, 3), taken)
    return finish(ctx, tools, stylize(ctx, plan["core"], plan["style"]), {"no_call": True}, [],
                  {"domain": it.domain.name, "style": plan["style"], "intent": it.key,
                   "missing": omit.name, "target_tool": tool.name})


def build_irrelevant(ctx):
    rng, V = ctx.rng, ctx.V
    taken = set()
    r = rng.random()
    if r < 0.70:
        # The request needs a tool that is not offered. Either only unrelated tools are offered, or
        # ("near miss") sibling tools of the same domain are offered but the one that fits is missing.
        near = r >= 0.35
        pool = V.near_miss if near else V.intents
        it = rng.choice(pool)
        tool = make_tool(ctx, it, taken)          # only used to word the request; not offered
        plan = plan_call(ctx, tool, rng.choice(phrasing.STYLES))
        tools = []
        if near:
            siblings = [s for s in it.domain.intents if s is not it]
            for s in rng.sample(siblings, min(len(siblings), rng.randint(2, 4))):
                t = make_tool(ctx, s, taken)
                if t:
                    tools.append(t)
        tools += pick_others(ctx, it.domain.tags, rng.randint(1, 4) if near else rng.randint(3, 8), taken)
        user = stylize(ctx, plan["core"], plan["style"])
        meta = {"domain": it.domain.name, "style": plan["style"], "intent": it.key,
                "variant": "near_miss" if near else "other_domain"}
    else:
        tools = pick_others(ctx, set(), rng.randint(3, 8), taken)
        if rng.random() < 0.5:
            user = rng.choice(V.ph["smalltalk"])
        else:
            user = rng.choice(V.ph["smalltalk_t"]).replace("{x}", rng.choice(V.ph["smalltalk_topics"]))
        meta = {"domain": "none", "style": "smalltalk", "intent": "none", "variant": "smalltalk"}
    return finish(ctx, tools, user, {"no_call": True}, [], meta)


def build_typing(ctx):
    rng, V = ctx.rng, ctx.V
    trap = rng.choice(V.trap_names)
    it, slot = rng.choice(V.traps[trap])
    taken = set()
    tool = make_tool(ctx, it, taken, force={slot.key})
    plan = plan_call(ctx, tool, rng.choice([s for s in phrasing.STYLES if s != "correction"]),
                     trap_key=slot.key)
    tools = [tool] + pick_others(ctx, it.domain.tags, rng.randint(0, 3), taken)
    pname = next(p.name for p in tool.params if p.slot is slot)
    return finish(ctx, tools, stylize(ctx, plan["core"], plan["style"]),
                  {"calls": [call(tool, plan["args"])]}, [tool],
                  {"domain": it.domain.name, "style": plan["style"], "intent": it.key,
                   "trap": trap, "trap_param": pname})


def build_computer(ctx):
    rng, V = ctx.rng, ctx.V
    b = screens.build(ctx, V.hp)
    style = rng.choice(PLAIN_STYLES)
    user = stylize(ctx, b["task"], style) + "\n\n" + b["screen"]
    return {
        "tools": copy.deepcopy(screens.COMPUTER_TOOLS),
        "messages": [{"role": "system", "content": rng.choice(V.hp["system"])},
                     {"role": "user", "content": user}],
        "expected": {"calls": [b["expected"]]},
        "arg_match": b["arg_match"],
        "meta": {"domain": "computer:" + b["app"], "style": style, "intent": b["scenario"]},
    }


BUILDERS = {
    "a_single": build_single, "b_selection": build_selection, "c_parallel": build_parallel,
    "d_multistep": build_multistep, "e_missing": build_missing, "f_irrelevant": build_irrelevant,
    "g_typing": build_typing, "h_computer": build_computer,
}


def make_case(seed, split, i):
    V = vocab(split)
    digest = hashlib.sha256(f"toolcall-bench/{seed}/{split}/{i}".encode()).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    cat = CATEGORIES[i % len(CATEGORIES)]
    today = dt.date(2026, 1, 1) + dt.timedelta(days=rng.randrange(730))
    ctx = Ctx(rng, V, today, rng.choice([ident, camel]), random.Random(int.from_bytes(digest[8:16], "big")))
    body = BUILDERS[cat](ctx)
    body["meta"].update({"seed": seed, "index": i, "today": today.isoformat(),
                         "naming": "camelCase" if ctx.cs is camel else "snake_case"})
    case = {"id": f"{split}-{seed}-{i:06d}", "category": cat, "split": split}
    case.update(body)
    return case


def dumps(case):
    return json.dumps(case, sort_keys=True, ensure_ascii=False)


# --------------------------------------------------------------------------
# Split disjointness (asserted on every run)
# --------------------------------------------------------------------------

def split_inventory(split):
    """Everything split-specific that a case of this split can be built from."""
    V = vocab(split)
    names, acts = set(), set()
    for it in V.intents:
        for n in it.names:
            names |= {n, camel(n)}
        acts |= set(it.acts)
    for ch in V.chains:
        for lv in ch.levels:
            for n in lv.names + (lv.pick["names"] if lv.pick else []):
                names |= {n, camel(n)}
            acts |= set(lv.nouns)
        for a in ch.actions:
            for n in a.names:
                names |= {n, camel(n)}
            acts |= set(a.acts)
    templates = set(phrasing.all_templates(split))
    hp = V.hp
    templates |= set(hp["system"]) | set(hp["intro"])
    for lst in hp["tasks"].values():
        templates |= set(lst)
    values = set()
    for key, lst in BASE.items():
        values |= {(key, x) for x in part(lst, split)}
    return {
        "domains": {d.name for d in V.domains} | {a.name for a in hp["apps"]},
        "intents": {(it.domain.name, it.key) for it in V.intents} | {c.name for c in V.chains},
        "tool_names": names,
        "request_phrases": acts,
        "templates": templates,
        "pool_values": values,
    }


def assert_disjoint():
    inv = {s: split_inventory(s) for s in SPLITS}
    for a, b in itertools.combinations(SPLITS, 2):
        for key in inv[a]:
            common = inv[a][key] & inv[b][key]
            assert not common, f"{key} shared by {a} and {b}: {sorted(map(str, common))[:8]}"
    return inv


def stats():
    out = {}
    for s in SPLITS:
        V = vocab(s)
        chain_tools = sum(len(c.levels) + len(c.actions) + sum(1 for lv in c.levels if lv.pick)
                          for c in V.chains)
        out[s] = {"domains": len(V.domains), "intents": len(V.intents), "chain_tools": chain_tools,
                  "base_tool_schemas": len(V.intents) + chain_tools,
                  "computer_apps": len(V.hp["apps"])}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--split", choices=SPLITS, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    assert_disjoint()
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "cases.jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for i in range(args.n):
            f.write(dumps(make_case(args.seed, args.split, i)) + "\n")
    print(f"wrote {args.n} cases to {path}")


if __name__ == "__main__":
    main()
