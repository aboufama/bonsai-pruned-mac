"""Building blocks of the tool-calling benchmark: value kinds, slots, intents, domains.

Everything here is pure data plus small deterministic helpers. No randomness
is used except through the `rng` carried by the per-case context object.
"""
import calendar
import datetime as dt

NODEF = object()  # "this optional parameter has no declared default"

ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def num_words(n):
    """Spell a non-negative integer below one million in English words."""
    if n < 20:
        return ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return TENS[t] + ("-" + ONES[o] if o else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return ONES[h] + " hundred" + (" " + num_words(r) if r else "")
    th, r = divmod(n, 1000)
    return num_words(th) + " thousand" + (" " + num_words(r) if r else "")


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def camel(s):
    parts = s.split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def ident(s):
    return s


def bar(s):
    """Split an 'a|b|c' string (or pass a list through)."""
    return [x.strip() for x in s.split("|")] if isinstance(s, str) else list(s)


def join_and(items):
    items = list(items)
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def fmt_num(v):
    """Human rendering of a number: 21 -> '21', 2.5 -> '2.5'."""
    if isinstance(v, int) or float(v).is_integer():
        return str(int(v))
    return repr(round(float(v), 2))


# --------------------------------------------------------------------------
# Value kinds
# --------------------------------------------------------------------------

class Kind:
    jtype = "string"
    hint = ""        # appended to the parameter description
    uniq = False     # values of this kind must not repeat inside one case
    trapname = None  # category (g) trap this kind can express
    correctable = False

    def schema(self, cs):
        return {"type": self.jtype}

    def gen(self, ctx, gt=None, ne=None):
        raise NotImplementedError

    def say(self, v, cs=ident):
        return str(v)

    def trap(self, ctx):
        """Return dict(value, say, clause=None, drop_on=False) or None."""
        return None

    def wrong(self, ctx, v):
        """A different plausible value, used by the 'correction' phrasing."""
        for _ in range(30):
            w = self.gen(ctx)
            if w != v and self.say(w, ctx.cs) not in ctx.used:
                return w
        return None

    def default(self, ctx):
        return NODEF


class Person(Kind):
    uniq = True
    correctable = True

    def gen(self, ctx, gt=None, ne=None):
        return ctx.P.mk_person(ctx.rng)


class First(Kind):
    uniq = True
    correctable = True

    def gen(self, ctx, gt=None, ne=None):
        return ctx.rng.choice(ctx.P.first)


class Last(Kind):
    uniq = True

    def gen(self, ctx, gt=None, ne=None):
        return ctx.rng.choice(ctx.P.last)


class Email(Kind):
    uniq = True
    correctable = True

    def gen(self, ctx, gt=None, ne=None):
        return ctx.P.mk_email(ctx.rng)


class Company(Kind):
    uniq = True
    correctable = True

    def gen(self, ctx, gt=None, ne=None):
        return ctx.P.mk_company(ctx.rng)


class City(Kind):
    uniq = True
    correctable = True

    def gen(self, ctx, gt=None, ne=None):
        return ctx.P.mk_city(ctx.rng)


class DateK(Kind):
    hint = "Format: YYYY-MM-DD."
    trapname = "relative_date"
    correctable = True
    uniq = True

    def __init__(self, past=False):
        self.past = past

    def gen(self, ctx, gt=None, ne=None):
        rng = ctx.rng
        if gt is not None:
            base = dt.date.fromisoformat(gt)
            return (base + dt.timedelta(days=rng.randint(1, 10))).isoformat()
        delta = rng.randint(2, 75)
        return (ctx.today + dt.timedelta(days=-delta if self.past else delta)).isoformat()

    def wrong(self, ctx, v):
        base = dt.date.fromisoformat(v)
        for _ in range(30):
            w = (base + dt.timedelta(days=ctx.rng.choice([-3, -2, -1, 1, 2, 3, 7]))).isoformat()
            if self.past and w >= ctx.today.isoformat():
                continue
            if not self.past and w <= ctx.today.isoformat():
                continue
            if w not in ctx.used:
                return w
        return None

    def trap(self, ctx):
        t, rng = ctx.today, ctx.rng
        dim = calendar.monthrange(t.year, t.month)[1]
        fams = []
        if not self.past:
            fams.append([(0, "today", True)])
            fams.append([(1, "tomorrow", True), (2, "the day after tomorrow", True)])
            fams.append([(n, f"{num_words(n)} days from today", True) for n in (3, 4, 5, 6, 10)]
                        + [(n, f"{n} days from now", True) for n in (3, 4, 5, 6, 9, 12)])
            fams.append([(7, "a week from today", True), (14, "two weeks from today", True),
                         (21, "three weeks from today", True)])
            fams.append([(n, "this coming " + WEEKDAYS[(t + dt.timedelta(days=n)).weekday()], True)
                         for n in range(2, 7)])
            later = [(d - t.day, f"the {ordinal(d)} of this month", False)
                     for d in range(t.day + 2, dim + 1)]
            if later:
                fams.append(later)
            if t.day < dim - 1:
                fams.append([(dim - t.day, "the last day of this month", False)])
            nm = [(dim - t.day + d, f"the {ordinal(d)} of next month", False) for d in (1, 5, 10, 15, 20, 25)]
            fams.append(nm)
        else:
            fams.append([(0, "today", True)])
            fams.append([(-1, "yesterday", True), (-2, "the day before yesterday", True)])
            fams.append([(-n, f"{num_words(n)} days ago", True) for n in (3, 4, 5, 6, 10)]
                        + [(-n, f"{n} days ago", True) for n in (3, 4, 5, 6, 9, 12)])
            fams.append([(-7, "a week ago", True), (-14, "two weeks ago", True),
                         (-21, "three weeks ago", True)])
            earlier = [(d - t.day, f"the {ordinal(d)} of this month", False)
                       for d in range(1, t.day - 1)]
            if earlier:
                fams.append(earlier)
            first_prev = t.replace(day=1) - dt.timedelta(days=1)
            fams.append([((first_prev.replace(day=d) - t).days, f"the {ordinal(d)} of last month", False)
                         for d in (1, 5, 10, 15, 20, 25)])
        for _ in range(30):
            delta, text, drop_on = rng.choice(rng.choice(fams))
            value = (t + dt.timedelta(days=delta)).isoformat()
            if value not in ctx.used:
                return {"value": value, "say": text, "drop_on": drop_on}
        return None


class TimeK(Kind):
    hint = "Format: 24-hour HH:MM, for example 09:05 or 17:30."
    trapname = "time_12h"
    correctable = True
    uniq = True

    def gen(self, ctx, gt=None, ne=None):
        rng = ctx.rng
        if gt is not None:
            h, m = int(gt[:2]), int(gt[3:])
            h2 = min(23, h + rng.randint(1, 3))
            if h2 == h:
                m = min(59, m + 10)
            return f"{h2:02d}:{m:02d}"
        return f"{rng.randint(6, 19):02d}:{rng.choice([0, 0, 15, 30, 30, 45]):02d}"

    def wrong(self, ctx, v):
        h, m = int(v[:2]), int(v[3:])
        for _ in range(30):
            w = f"{min(22, max(5, h + ctx.rng.choice([-2, -1, 1, 2]))):02d}:{m:02d}"
            if w != v and w not in ctx.used:
                return w
        return None

    def trap(self, ctx):
        rng = ctx.rng
        for _ in range(30):
            form = rng.choice(["ampm", "ampm", "ampm_round", "words", "words", "named"])
            if form == "named":
                value, text = rng.choice([("12:00", "noon"), ("00:00", "midnight"), ("12:00", "midday")])
            elif form == "ampm":
                h, m = rng.randint(1, 23), rng.choice([5, 10, 15, 20, 30, 40, 45, 50])
                value = f"{h:02d}:{m:02d}"
                text = f"{(h - 1) % 12 + 1}:{m:02d} {'am' if h < 12 else 'pm'}"
            elif form == "ampm_round":
                h = rng.randint(1, 23)
                if h == 12:
                    continue
                value = f"{h:02d}:00"
                text = f"{(h - 1) % 12 + 1} {'am' if h < 12 else 'pm'}"
            else:
                part, hours = rng.choice([("morning", (7, 10)), ("afternoon", (13, 16)), ("evening", (18, 21))])
                h = rng.randint(*hours)
                m = rng.choice([15, 30, 45])
                value = f"{h:02d}:{m:02d}"
                spoken = num_words((h - 1) % 12 + 1)
                nxt = num_words(h % 12 + 1)
                text = {15: f"quarter past {spoken}", 30: f"half past {spoken}",
                        45: f"quarter to {nxt}"}[m] + f" in the {part}"
            if value not in ctx.used:
                return {"value": value, "say": text}
        return None


class IntK(Kind):
    jtype = "integer"
    trapname = "number_words"
    correctable = True

    def __init__(self, choices):
        self.choices = sorted(set(choices))

    def gen(self, ctx, gt=None, ne=None):
        pool = self.choices
        if gt is not None:
            bigger = [c for c in pool if c > gt]
            pool = bigger or [gt + 1]
        return ctx.rng.choice(pool)

    def wrong(self, ctx, v):
        others = [c for c in self.choices if c != v]
        return ctx.rng.choice(others) if others else None

    def trap(self, ctx):
        v = self.gen(ctx)
        return {"value": v, "say": num_words(v)}

    def default(self, ctx):
        return ctx.rng.choice(self.choices)


class NumK(Kind):
    jtype = "number"
    correctable = True

    def __init__(self, lo, hi, step):
        n = int(round((hi - lo) / step))
        self.choices = []
        for i in range(n + 1):
            v = round(lo + i * step, 2)
            self.choices.append(int(v) if float(v).is_integer() else v)

    def gen(self, ctx, gt=None, ne=None):
        return ctx.rng.choice(self.choices)

    def say(self, v, cs=ident):
        return fmt_num(v)

    def wrong(self, ctx, v):
        others = [c for c in self.choices if c != v]
        return ctx.rng.choice(others) if others else None


class AmountK(Kind):
    jtype = "number"
    correctable = True
    uniq = True

    def gen(self, ctx, gt=None, ne=None):
        rng = ctx.rng
        whole = rng.choice([rng.randint(5, 95), rng.randint(100, 950), 5 * rng.randint(4, 120)])
        if rng.random() < 0.5:
            return whole
        return whole + rng.choice([0.5, 0.25, 0.75, 0.99, 0.49, 0.2, 0.95])

    def say(self, v, cs=ident):
        return str(v) if isinstance(v, int) else f"{v:.2f}"


class EnumK(Kind):
    trapname = "enum_map"
    correctable = True

    def __init__(self, spec):
        self.values, self.natural = [], {}
        for item in bar(spec):
            if "=" in item:
                val, nat = item.split("=", 1)
                self.values.append(val.strip())
                self.natural[val.strip()] = nat.strip()
            else:
                self.values.append(item)

    def schema(self, cs):
        return {"type": "string", "enum": list(self.values)}

    def gen(self, ctx, gt=None, ne=None):
        pool = [v for v in self.values if v != ne] if ne is not None else self.values
        return ctx.rng.choice(pool)

    def say(self, v, cs=ident):
        return v.replace("_", " ")

    def wrong(self, ctx, v):
        others = [c for c in self.values if c != v]
        return ctx.rng.choice(others) if others else None

    def trap(self, ctx):
        if not self.natural:
            return None
        v = ctx.rng.choice(sorted(self.natural))
        return {"value": v, "say": v, "clause": self.natural[v]}

    def default(self, ctx):
        return ctx.rng.choice(self.values)


class BoolK(Kind):
    jtype = "boolean"
    trapname = "boolean"

    def __init__(self, yes, no):
        self.yes, self.no = bar(yes), bar(no)

    def gen(self, ctx, gt=None, ne=None):
        return ctx.rng.random() < 0.5

    def wrong(self, ctx, v):
        return None

    def default(self, ctx):
        return ctx.rng.random() < 0.5


class IdK(Kind):
    uniq = True
    correctable = True

    def __init__(self, prefix):
        self.prefix = prefix

    def gen(self, ctx, gt=None, ne=None):
        return f"{self.prefix}-{ctx.rng.randint(1000, 99999)}"


class TextK(Kind):
    uniq = True

    def __init__(self, pool):
        self.pool = pool

    def gen(self, ctx, gt=None, ne=None):
        return ctx.P.text(self.pool, ctx.rng)

    def wrong(self, ctx, v):
        return None


class ListK(Kind):
    jtype = "array"
    trapname = "array"

    def __init__(self, kind, lo, hi, ordered=False, quote=False):
        self.kind, self.lo, self.hi, self.ordered, self.quote = kind, lo, hi, ordered, quote

    def schema(self, cs):
        return {"type": "array", "items": self.kind.schema(cs)}

    def gen(self, ctx, gt=None, ne=None):
        n = ctx.rng.randint(self.lo, self.hi)
        out, seen = [], set()
        for _ in range(200):
            v = ctx.draw(self.kind)
            key = self.kind.say(v, ctx.cs)
            if key in seen:
                continue
            seen.add(key)
            out.append(v)
            if len(out) == n:
                break
        return out

    def say(self, v, cs=ident):
        items = [self.kind.say(x, cs) for x in v]
        if self.quote:
            items = [f'"{x}"' for x in items]
        return join_and(items)

    def wrong(self, ctx, v):
        return None


class ObjK(Kind):
    jtype = "object"
    trapname = "nested_object"

    def __init__(self, fields, tpl):
        self.fields, self.tpl = fields, tpl  # fields: list of (name, kind)

    def schema(self, cs):
        props = {}
        for name, kind in self.fields:
            s = kind.schema(cs)
            s["description"] = describe(name, kind)
            props[cs(name)] = s
        return {"type": "object", "properties": props, "required": [cs(n) for n, _ in self.fields]}

    def gen(self, ctx, gt=None, ne=None):
        return {ctx.cs(name): ctx.draw(kind) for name, kind in self.fields}

    def say(self, v, cs=ident):
        out = self.tpl
        for name, kind in self.fields:
            out = out.replace("{" + name + "}", kind.say(v[cs(name)], cs))
        return out

    def wrong(self, ctx, v):
        return None


class OListK(ListK):
    """Array of small objects, e.g. order lines."""
    trapname = "nested_object"

    def __init__(self, fields, tpl, lo, hi):
        super().__init__(ObjK(fields, tpl), lo, hi)


# --------------------------------------------------------------------------
# Constructors used by the domain files
# --------------------------------------------------------------------------

PERSON, FIRST, LAST, EMAIL, COMPANY, CITY = Person(), First(), Last(), Email(), Company(), City()
DATE, PDATE, TIME, AMOUNT = DateK(False), DateK(True), TimeK(), AmountK()


def INT(*choices):
    return IntK(choices)


def RNG(lo, hi, step=1):
    return IntK(range(lo, hi + 1, step))


def NUM(lo, hi, step):
    return NumK(lo, hi, step)


def ENUM(spec):
    return EnumK(spec)


def BOOL(yes, no):
    return BoolK(yes, no)


def ID(prefix):
    return IdK(prefix)


def T(pool):
    return TextK(pool)


def LIST(kind, lo, hi, ordered=False, quote=False):
    return ListK(kind, lo, hi, ordered, quote)


def OBJ(fields, tpl):
    return ObjK(fields, tpl)


def OLIST(fields, tpl, lo, hi):
    return OListK(fields, tpl, lo, hi)


DAYS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"
CURRENCY = ("USD=in US dollars|EUR=in euros|GBP=in British pounds|"
            "JPY=in Japanese yen|CHF=in Swiss francs")
ADDRESS = OBJ([("street", T("street")), ("city", CITY), ("postal_code", T("zip"))],
              "{street}, {city}, postal code {postal_code}")


def describe(name, kind, extra=None):
    text = extra or (name.replace("_", " ").capitalize() + ".")
    if kind.hint:
        text += " " + kind.hint
    return text


class Slot:
    def __init__(self, names, kind, clauses="", opt=False, ask=False, d=None,
                 loose=False, gt=None, ne=None):
        self.names = bar(names)
        self.key = self.names[0]
        self.kind = kind
        self.clauses = bar(clauses) if clauses else []
        self.opt, self.ask, self.desc, self.loose = bool(opt), bool(ask), d, bool(loose)
        self.gt, self.ne = gt, ne
        if not isinstance(kind, BoolK):
            assert self.clauses and all("{v}" in c for c in self.clauses), names
        assert not (self.opt and self.ask), names


S = Slot


class Intent:
    def __init__(self, names, descs, acts, *slots):
        self.names, self.descs, self.acts = bar(names), bar(descs), bar(acts)
        self.slots = list(slots)
        self.key = self.names[0]
        self.domain = None
        keys = [s.key for s in self.slots]
        assert len(set(keys)) == len(keys), names
        # slots that take part in an ordering/inequality constraint
        self.linked = {s.key for s in self.slots if s.gt or s.ne} | \
                      {s.gt for s in self.slots if s.gt} | {s.ne for s in self.slots if s.ne}

    def slot(self, key):
        return next(s for s in self.slots if s.key == key)


I = Intent


class Domain:
    def __init__(self, name, tags, split, intents):
        self.name, self.tags, self.split, self.intents = name, set(tags.split()), split, list(intents)
        for it in self.intents:
            it.domain = self


REGISTRY = []

# "domain.intent" keys whose request could arguably be served by a sibling tool of the same domain when
# the right tool is missing. They are never used for the near-miss variant of category f.
NEAR_MISS_UNSAFE = set()


def D(name, tags, split, *intents):
    dom = Domain(name, tags, split, intents)
    REGISTRY.append(dom)
    return dom


# ---- multi-step chains (category d) ---------------------------------------

class Level:
    """One entity level of a chain: a tool that returns the entity's id."""

    def __init__(self, ent, names, descs, nouns, out, key=None, inp=None, verb=None, extras=(), pick=None):
        self.ent, self.names, self.descs, self.nouns = ent, bar(names), bar(descs), bar(nouns)
        # Optional "list" variant of a hop: instead of returning the wanted entity directly, the tool
        # returns several candidates and the request's wording says which one is meant.
        # pick = (names, descriptions, list_key, attribute_key, kind, rule) with rule one of
        # "max", "min" (over the attribute), "rank1" (attribute counts 1..n, pick 1),
        # "true" (boolean flag), "eq:<value>" (enum attribute equal to value).
        self.pick = None
        if pick:
            pn, pd, list_key, attr, kind, rule = pick
            self.pick = {"names": bar(pn), "descs": bar(pd), "list_key": list_key, "attr": attr,
                         "kind": kind, "rule": rule}
        self.out_key, self.out_kind = out
        self.key = key            # root only: Slot with the user-supplied lookup value
        self.inp = bar(inp) if inp else None   # hops: parameter names taking the previous id
        self.verb = bar(verb) if verb else ["find", "look up"]
        self.extras = list(extras)  # (key, kind) noise fields in the simulated result


def R(ent, names, descs, key, out, nouns, verb=None, extras=()):
    return Level(ent, names, descs, nouns, out, key=key, verb=verb, extras=extras)


def H(ent, names, descs, inp, out, nouns, extras=(), pick=None):
    return Level(ent, names, descs, nouns, out, inp=inp, extras=extras, pick=pick)


class Action:
    """Final tool of a chain; acts on the entity of `level` (0 = root)."""

    def __init__(self, level, names, descs, acts, id_names, *slots):
        self.level, self.names, self.descs, self.acts = level, bar(names), bar(descs), bar(acts)
        self.id_names, self.slots = bar(id_names), list(slots)
        assert all("{ent}" in a for a in self.acts), names


A = Action


class Chain:
    def __init__(self, name, domain, split, levels, actions):
        self.name, self.domain, self.split = name, domain, split
        self.levels, self.actions = list(levels), list(actions)


CHAINS = []


def CH(name, domain, split, levels, actions):
    c = Chain(name, domain, split, levels, actions)
    CHAINS.append(c)
    return c
