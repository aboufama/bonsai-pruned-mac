"""Scoring of tool calls against the expected behaviour stored in a case.

Rules
  * The function name must match exactly.
  * Arguments arrive as a JSON string and are parsed; nothing is string-matched.
  * Values are compared after type-aware normalisation driven by the tool's
    JSON schema: integers and numbers may arrive as numeric strings, booleans
    as "true"/"false", enum values in any letter case, strings with stray
    whitespace. Everything else must be equal.
  * `arg_match[tool][param]` can relax or annotate a parameter:
      {"mode": "contains"}  free text: the expected words must appear, in order,
                            in the actual value (case and punctuation ignored)
      {"mode": "any"}       any non-empty value of the right type
      {"unordered": true}   array compared as a multiset
      {"optional": true, "default": X}  optional parameter; leaving it out is
                            the same as passing X
  * An optional parameter the user did not mention must be absent, null, empty
    or equal to its declared default. Unknown parameters fail.
  * Independent calls of one turn may come in any order; an extra or a missing
    call fails. For "no call" cases any tool call fails.
  * Multi-step cases: the stored tool results are played back and every step
    must be called correctly; a call after the last step fails.
"""
import copy
import itertools
import json
import re

MISSING = object()


class Mismatch(Exception):
    pass


def parse_arguments(raw):
    """Return the arguments as a dict, or None if they are not a JSON object."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except ValueError:
            return None
        return value if isinstance(value, dict) else None
    return None


def _ws(s):
    return " ".join(s.split())


def _number(value):
    if isinstance(value, bool):
        raise Mismatch("boolean where a number is expected")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            pass
    raise Mismatch(f"not a number: {value!r}")


def canon(value, schema):
    """Canonical form of `value` under a JSON-schema fragment. Raises Mismatch."""
    t = schema.get("type")
    if t == "integer":
        f = _number(value)
        if not f.is_integer():
            raise Mismatch(f"not an integer: {value!r}")
        return int(f)
    if t == "number":
        return round(_number(value), 6)
    if t == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in ("true", "false"):
            return value.strip().lower() == "true"
        raise Mismatch(f"not a boolean: {value!r}")
    if t == "string":
        if isinstance(value, bool):
            raise Mismatch("boolean where a string is expected")
        if isinstance(value, int):
            value = str(value)
        elif isinstance(value, float):
            value = str(int(value)) if value.is_integer() else repr(value)
        if not isinstance(value, str):
            raise Mismatch(f"not a string: {value!r}")
        s = _ws(value)
        if "enum" in schema:
            for e in schema["enum"]:
                if e.casefold() == s.casefold():
                    return e
            raise Mismatch(f"{value!r} is not one of the allowed values")
        return s
    if t == "array":
        if not isinstance(value, list):
            raise Mismatch(f"not an array: {value!r}")
        return [canon(x, schema.get("items", {})) for x in value]
    if t == "object":
        if not isinstance(value, dict):
            raise Mismatch(f"not an object: {value!r}")
        props = schema.get("properties", {})
        out = {}
        for k, v in value.items():
            if k not in props:
                raise Mismatch(f"unknown field {k!r}")
            out[k] = canon(v, props[k])
        return out
    return value


def _tokens(s):
    return re.findall(r"[a-z0-9]+", s.casefold())


def _contains(expected, actual):
    e, a = _tokens(expected), _tokens(actual)
    if not e:
        return True
    return any(a[i:i + len(e)] == e for i in range(len(a) - len(e) + 1))


def values_match(expected, actual, schema, rule):
    """True if `actual` is an acceptable rendering of `expected`."""
    mode = rule.get("mode", "exact")
    try:
        ca = canon(actual, schema)
    except Mismatch:
        return False
    if mode == "any":
        if isinstance(ca, str):
            return bool(ca)
        if isinstance(ca, (int, float)) and not isinstance(ca, bool):
            return ca > 0
        return ca is not None
    if mode == "contains":
        return isinstance(ca, str) and _contains(str(expected), ca)
    try:
        ce = canon(expected, schema)
    except Mismatch:
        return False
    if schema.get("type") == "array" and rule.get("unordered", True):
        key = lambda x: json.dumps(x, sort_keys=True)
        return sorted(map(key, ce)) == sorted(map(key, ca))
    return ce == ca


def _empty(v):
    return v is None or (isinstance(v, (str, list, dict)) and len(v) == 0)


def check_call(expected, name, args, tool, rules):
    """Compare one actual call with one expected call. Returns (ok, reason)."""
    if name != expected["name"]:
        return False, f"wrong tool: got {name!r}, expected {expected['name']!r}"
    if args is None:
        return False, "arguments are not a JSON object"
    params = tool["function"]["parameters"]
    props = params.get("properties", {})
    exp_args = expected["arguments"]
    for k in args:
        if k not in props:
            return False, f"unknown argument {k!r}"
    for pname, schema in props.items():
        rule = rules.get(pname, {})
        a = args.get(pname, MISSING)
        if a is None:
            a = MISSING
        if pname not in exp_args:
            if a is MISSING or _empty(a):
                continue
            if "default" in rule and values_match(rule["default"], a, schema, {}):
                continue
            return False, f"argument {pname!r} was not requested by the user, got {a!r}"
        e = exp_args[pname]
        if a is MISSING:
            if rule.get("optional") and "default" in rule and values_match(rule["default"], e, schema, {}):
                continue
            return False, f"missing argument {pname!r} (expected {e!r})"
        if not values_match(e, a, schema, rule):
            return False, f"argument {pname!r}: expected {e!r}, got {a!r}"
    return True, ""


def match_calls(actual, expected, tools, arg_match, subset=False):
    """Assign actual calls to expected calls (order-free).

    actual: list of (name, args_dict_or_None); expected: list of expected calls.
    With subset=False every expected call must be matched by exactly one actual
    call. With subset=True the actual calls must map to distinct expected calls
    but need not cover all of them. Returns (ok, reason, assignment) where
    assignment[i] is the index of the expected call matched by actual call i.
    """
    if not subset and len(actual) != len(expected):
        kind = "extra" if len(actual) > len(expected) else "missing"
        return False, f"{kind} call: expected {len(expected)} call(s), got {len(actual)}", None
    if len(actual) > len(expected):
        return False, f"extra call: at most {len(expected)} call(s) expected here, got {len(actual)}", None
    ok_table, why = {}, {}
    for i, (name, args) in enumerate(actual):
        for j, exp in enumerate(expected):
            tool = tools.get(exp["name"])
            ok, reason = check_call(exp, name, args, tool, arg_match.get(exp["name"], {}))
            ok_table[i, j] = ok
            why[i, j] = reason
    for perm in itertools.permutations(range(len(expected)), len(actual)):
        if all(ok_table[i, j] for i, j in enumerate(perm)):
            return True, "", list(perm)
    # explain the first actual call that fits nothing
    for i in range(len(actual)):
        if not any(ok_table[i, j] for j in range(len(expected))):
            same = [j for j in range(len(expected)) if expected[j]["name"] == actual[i][0]]
            j = same[0] if same else 0
            return False, why[i, j], None
    return False, "calls cannot be assigned one-to-one to the expected calls", None


def extract_calls(message):
    """[(name, parsed_args_or_None, raw_arguments, id)] from an assistant message."""
    out = []
    for n, tc in enumerate(message.get("tool_calls") or []):
        fn = tc.get("function") or {}
        raw = fn.get("arguments")
        out.append((fn.get("name"), parse_arguments(raw), raw, tc.get("id") or f"call_{n}"))
    return out


def _fail_kind(reason):
    for key in ("wrong tool", "extra call", "missing call", "missing argument", "unknown argument",
                "was not requested", "not a JSON object"):
        if key in reason:
            return key.replace(" ", "_")
    return "wrong_value" if reason.startswith("argument") else "other"


def run_case(case, chat):
    """Run one case against `chat(messages, tools) -> assistant message` and score it.

    Returns {"id", "category", "pass", "kind", "reason", "turns"}.
    """
    tools = {t["function"]["name"]: t for t in case["tools"]}
    arg_match = case.get("arg_match", {})
    messages = copy.deepcopy(case["messages"])
    expected = case["expected"]
    turns = []

    def ask():
        msg = chat(messages, case["tools"]) or {}
        calls = extract_calls(msg)
        turns.append({"content": msg.get("content"),
                      "tool_calls": [{"name": n, "arguments": raw} for n, _, raw, _ in calls]})
        return msg, calls

    def result(ok, kind="", reason=""):
        return {"id": case["id"], "category": case["category"], "pass": bool(ok),
                "kind": kind, "reason": reason, "turns": turns}

    if expected.get("no_call"):
        _, calls = ask()
        if calls:
            return result(False, "called_when_no_call_expected",
                          f"expected no tool call, got {[c[0] for c in calls]}")
        return result(True)

    if "calls" in expected:
        _, calls = ask()
        if not calls:
            return result(False, "no_call", "no tool call was made")
        ok, reason, _ = match_calls([(n, a) for n, a, _, _ in calls], expected["calls"], tools, arg_match)
        return result(ok, "" if ok else _fail_kind(reason), reason)

    steps = expected["steps"]
    for si, step in enumerate(steps):
        pending = list(range(len(step["calls"])))
        while pending:
            msg, calls = ask()
            where = f"step {si + 1} of {len(steps)}"
            if not calls:
                return result(False, "stopped_early", f"no tool call at {where}")
            ok, reason, assign = match_calls([(n, a) for n, a, _, _ in calls],
                                             [step["calls"][j] for j in pending], tools, arg_match, subset=True)
            if not ok:
                return result(False, _fail_kind(reason), f"{where}: {reason}")
            messages.append({"role": "assistant", "content": msg.get("content") or "",
                             "tool_calls": [{"id": cid, "type": "function",
                                             "function": {"name": n, "arguments": raw if isinstance(raw, str)
                                                          else json.dumps(raw)}}
                                            for n, _, raw, cid in calls]})
            done = []
            for (n, _, _, cid), k in zip(calls, assign):
                j = pending[k]
                done.append(j)
                messages.append({"role": "tool", "tool_call_id": cid,
                                 "content": json.dumps(step["tool_results"][j], sort_keys=True)})
            pending = [j for j in pending if j not in done]
    _, calls = ask()
    if calls:
        return result(False, "extra_call", f"extra call after the last step: {[c[0] for c in calls]}")
    return result(True)


# --------------------------------------------------------------------------
# Structural validation of a case (used by selftest)
# --------------------------------------------------------------------------

def validate_case(case):
    """Check that a case is internally consistent. Raises AssertionError."""
    for key in ("id", "category", "split", "tools", "messages", "expected", "arg_match", "meta"):
        assert key in case, f"{case.get('id')}: missing field {key}"
    names = [t["function"]["name"] for t in case["tools"]]
    assert len(names) == len(set(names)), f"{case['id']}: duplicate tool names"
    tools = {t["function"]["name"]: t for t in case["tools"]}
    exp = case["expected"]
    if exp.get("no_call"):
        calls = []
    elif "calls" in exp:
        calls = exp["calls"]
        assert calls, case["id"]
    else:
        calls = [c for st in exp["steps"] for c in st["calls"]]
        assert 2 <= len(exp["steps"]) <= 4, case["id"]
        for st in exp["steps"]:
            assert len(st["calls"]) == len(st["tool_results"]), case["id"]
        # every later step must use a value that an earlier tool result returned
        for prev, st in zip(exp["steps"], exp["steps"][1:]):
            returned = set(_leaves(prev["tool_results"]))
            for c in st["calls"]:
                assert returned & set(_leaves(c["arguments"])), f"{case['id']}: step does not use a returned value"
    for c in calls:
        assert c["name"] in tools, f"{case['id']}: expected tool {c['name']} is not offered"
        params = tools[c["name"]]["function"]["parameters"]
        props = params["properties"]
        for req in params.get("required", []):
            assert req in c["arguments"], f"{case['id']}: required {req} missing from expected call"
        for k, v in c["arguments"].items():
            assert k in props, f"{case['id']}: expected argument {k} not in schema"
            _conforms(v, props[k], f"{case['id']}:{c['name']}.{k}")
        # an expected call must satisfy itself
        ok, reason = check_call(c, c["name"], c["arguments"], tools[c["name"]],
                                case["arg_match"].get(c["name"], {}))
        assert ok, f"{case['id']}: expected call does not satisfy itself: {reason}"


def _leaves(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _leaves(v)
    elif isinstance(x, list):
        for v in x:
            yield from _leaves(v)
    elif isinstance(x, str):
        yield x


def _conforms(v, schema, where):
    t = schema["type"]
    if t == "integer":
        assert isinstance(v, int) and not isinstance(v, bool), where
    elif t == "number":
        assert isinstance(v, (int, float)) and not isinstance(v, bool), where
    elif t == "boolean":
        assert isinstance(v, bool), where
    elif t == "string":
        assert isinstance(v, str), where
        if "enum" in schema:
            assert v in schema["enum"], where
    elif t == "array":
        assert isinstance(v, list), where
        for x in v:
            _conforms(x, schema["items"], where)
    elif t == "object":
        assert isinstance(v, dict) and set(v) == set(schema["properties"]), where
        for k, x in v.items():
            _conforms(x, schema["properties"][k], where)
