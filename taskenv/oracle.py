"""Solution steps of a task, written against the page itself.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

A task lists the steps that solve it. Each step finds its element in the live page (a Playwright
selector) when its turn comes, so the same list works for every seed and window position. The
steps serve three purposes:
  - the scripted oracle executes them and must pass every task (this proves tasks and checkers);
  - their count is the number of steps the task needs;
  - guided mode reads each step's `say` to the model, which only has to point.

    Click(sel, say)                 left click; count=2 double click; button="right"
    Drag(src, dst, say, say_to)     press on src, move, release on dst (at = fraction inside the box)
    Type(text)   Key("cmd+n")       keyboard; nothing to point at
    Reveal(sel)                     wheel the scrolling box around `sel` until it is in view
"""


class Step:
    pointing = False
    say = None

    def actions(self, env):
        """Yield the actions of this step one at a time; the caller executes each before asking
        for the next (a Reveal looks at the page again after every wheel move)."""
        raise NotImplementedError


def _point(env, sel, at=(0.5, 0.5)):
    b = env.box(sel)
    if b is None:
        raise LookupError(f"no element for {sel!r}")
    return b[0] + (b[2] - b[0]) * at[0], b[1] + (b[3] - b[1]) * at[1]


class Click(Step):
    pointing = True

    def __init__(self, sel, say, button="left", count=1, at=(0.5, 0.5), mods=None):
        self.sel, self.say, self.button, self.count, self.at, self.mods = sel, say, button, count, at, mods

    def targets(self, env):
        return [env.box(self.sel)]

    def build(self, points):
        (x, y), = points
        a = {"type": "click", "x": round(x, 1), "y": round(y, 1), "button": self.button, "count": self.count}
        if self.mods:
            a["mods"] = self.mods
        return a

    def actions(self, env):
        yield self.build([_point(env, self.sel, self.at)])


class Drag(Step):
    pointing = True

    def __init__(self, src, dst, say, say_to, src_at=(0.5, 0.5), dst_at=(0.5, 0.5)):
        self.src, self.dst, self.say, self.say_to, self.src_at, self.dst_at = src, dst, say, say_to, src_at, dst_at

    def targets(self, env):
        return [env.box(self.src), env.box(self.dst)]

    def build(self, points):
        (x1, y1), (x2, y2) = points
        return {"type": "drag", "x1": round(x1, 1), "y1": round(y1, 1), "x2": round(x2, 1), "y2": round(y2, 1)}

    def actions(self, env):
        yield self.build([_point(env, self.src, self.src_at), _point(env, self.dst, self.dst_at)])


class Type(Step):
    def __init__(self, text):
        self.text = text

    def actions(self, env):
        yield {"type": "type", "text": self.text}


class Key(Step):
    def __init__(self, keys):
        self.keys = keys

    def actions(self, env):
        yield {"type": "key", "keys": self.keys}


REVEAL_JS = """el => {
  let p = el.parentElement;
  while (p && !(p.scrollHeight > p.clientHeight + 1 && /(auto|scroll)/.test(getComputedStyle(p).overflowY))) p = p.parentElement;
  if (!p) return null;
  const r = el.getBoundingClientRect(), c = p.getBoundingClientRect();
  let dy = 0;
  if (r.bottom > c.bottom - 8) dy = r.bottom - c.bottom + Math.min(60, c.height / 4);
  else if (r.top < c.top + 8) dy = r.top - c.top - Math.min(60, c.height / 4);
  // at the end of the scroll range an element that is fully inside is as revealed as it gets
  if (dy > 0 && p.scrollTop + p.clientHeight >= p.scrollHeight - 1 && r.bottom <= c.bottom) dy = 0;
  if (dy < 0 && p.scrollTop <= 0 && r.top >= c.top) dy = 0;
  return {dy, x: c.left + c.width / 2, y: c.top + c.height / 2};
}"""


class Reveal(Step):
    """Scroll until the element is inside its scrolling box. At most `chunk` points per action, as
    a person turning a wheel would; an element already in view costs no action."""

    def __init__(self, sel, chunk=320):
        self.sel, self.chunk = sel, chunk

    def actions(self, env):
        for _ in range(40):
            r = env.page.locator(self.sel).first.evaluate(REVEAL_JS)
            if not r or abs(r["dy"]) < 1:
                return
            dy = max(-self.chunk, min(self.chunk, r["dy"]))
            yield {"type": "scroll", "x": round(r["x"], 1), "y": round(r["y"], 1), "dx": 0, "dy": round(dy)}
        raise RuntimeError(f"could not reveal {self.sel!r}")
