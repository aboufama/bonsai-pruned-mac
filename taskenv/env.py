"""The environment: a macOS-style desktop in headless Chromium, driven with real pointer and
keyboard events.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    env = Env()
    env.reset(state)            # state: the start state of an episode (taskenv.tasks.build)
    image = env.screenshot()    # PIL image, 2880 x 1800 (1440 x 900 points, device scale 2)
    env.step({"type": "click", "x": 412, "y": 300})
    env.state()                 # the apps' state, for the checker

Actions (coordinates in points, origin top left, x 0..1440, y 0..900):
    {"type": "click", "x", "y", "button": "left"|"right", "count": 1|2, "mods": ["cmd", ...]}
    {"type": "drag", "x1", "y1", "x2", "y2"}        press, several moves, release
    {"type": "type", "text"}                        "\n" presses Return
    {"type": "key", "keys": "cmd+shift+n"}
    {"type": "scroll", "x", "y", "dx", "dy"}        wheel at a point; dy > 0 scrolls down (points)
    {"type": "move", "x", "y"}                      move the pointer
    {"type": "wait"}
    {"type": "say", "text"}                         a message to the user; changes nothing
    {"type": "done", "status": "done"|"infeasible", "message": "..."}
Key names follow docs/ACTION_FORMAT.md: "backspace" is the Mac's delete key, "delete" is forward delete.

The page is served from memory (web/), no network is touched.
"""
import io
import mimetypes
import os
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
ORIGIN = "http://taskenv.local"
W, H, DPR = 1440, 900, 2

KEYS = {"cmd": "Meta", "command": "Meta", "meta": "Meta", "super": "Meta", "win": "Meta", "⌘": "Meta",
        "ctrl": "Control", "control": "Control", "⌃": "Control", "alt": "Alt", "option": "Alt", "opt": "Alt", "⌥": "Alt",
        "shift": "Shift", "⇧": "Shift", "enter": "Enter", "return": "Enter", "esc": "Escape", "escape": "Escape",
        "delete": "Delete", "backspace": "Backspace", "del": "Delete", "forwarddelete": "Delete", "space": "Space", "fn": None,
        "tab": "Tab", "up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight",
        "arrowup": "ArrowUp", "arrowdown": "ArrowDown", "arrowleft": "ArrowLeft", "arrowright": "ArrowRight",
        "home": "Home", "end": "End", "pageup": "PageUp", "pagedown": "PageDown", "plus": "+", "minus": "-",
        "equal": "=", "equals": "=", "comma": ",", "period": ".", "slash": "/"}
KEYS.update({f"f{i}": f"F{i}" for i in range(1, 13)})


def key_combo(keys):
    """'cmd+shift+n' (or a list of key names) -> 'Meta+Shift+n', Playwright's spelling.
    Raises ValueError on an unknown key or when there is not exactly one key besides modifiers."""
    if isinstance(keys, str):
        text = keys.strip()
        parts = [text] if len(text) <= 1 else [p for p in text.replace(" ", "+").split("+") if p] + (["+"] if text.endswith("++") or text == "+" else [])
    else:
        parts = [str(k) for k in keys]
    out = []
    for p in parts:
        if p.lower() in KEYS:
            k = KEYS[p.lower()]
            if k is None:
                continue                                  # fn: no such key here
        elif len(p) == 1:
            k = p.lower() if p.isalpha() else p
        else:
            raise ValueError(f"unknown key {p!r}")
        out.append(k)
    mods = list(dict.fromkeys(k for k in out if k in ("Meta", "Control", "Alt", "Shift")))
    rest = [k for k in out if k not in ("Meta", "Control", "Alt", "Shift")]
    if len(rest) != 1:
        raise ValueError(f"need exactly one key besides modifiers in {keys!r}")
    return "+".join(mods + rest)


ELEMENTS_JS = """() => {
  const out = [], sel = '[data-act],[data-dbl],[data-ctx],[data-drag],[data-drop],[data-slider],[data-select],[data-tl],input,textarea,.menu-item:not(.disabled),.mb-item,.dock-item';
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.right <= 0 || r.bottom <= 0 || r.left >= innerWidth || r.top >= innerHeight) continue;
    const cx = Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), cy = Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2));
    const top = document.elementFromPoint(cx, cy);
    if (!top || !(el === top || el.contains(top))) continue;
    out.push({box: [r.left, r.top, r.right, r.bottom], text: (el.innerText || el.value || el.placeholder || '').trim().slice(0, 60)});
  }
  return out;
}"""


# Is the point on something a person would call a thing (text or an icon), even if it is not a control?
UNDER_JS = """([x, y]) => { const e = document.elementFromPoint(x, y); if (!e) return false; if (e.closest('svg')) return true;
  for (const n of e.childNodes) if (n.nodeType === 3 && n.textContent.trim()) return true; return false; }"""


def index_html():
    apps = sorted(f[:-3] for f in os.listdir(os.path.join(WEB, "apps")) if f.endswith(".js"))
    css = "".join(f'<link rel="stylesheet" href="apps/{a}.css">' for a in apps if os.path.exists(os.path.join(WEB, "apps", a + ".css")))
    js = "".join(f'<script src="apps/{a}.js"></script>' for a in apps)
    return ('<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="shell.css">' + css +
            '</head><body><div id="desktop"><div id="menubar"></div><div id="windows"></div><div id="dock"></div>'
            '<div id="overlays"></div></div><script src="shell.js"></script>' + js + "</body></html>")


CAPTION_H = 64      # video mode: a caption bar below the desktop, outside what the model is shown
VIDEO_CSS = """html, body { height: %dpx !important; background: #101012; }
#desktop { bottom: auto !important; height: 900px !important; }
#te-cap { position: fixed; left: 0; top: 900px; width: 1440px; height: %dpx; background: #101012; color: #fff; font: 15px/1.3 Inter, sans-serif;
  display: flex; align-items: center; gap: 18px; padding: 0 20px; z-index: 99999; }
#te-cap b { flex: none; padding: 3px 10px; border-radius: 6px; background: #2c2c31; font-weight: 600; }
#te-cap span { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#te-cap i { flex: none; font-style: normal; font-variant-numeric: tabular-nums; color: #ffd166; font-weight: 600; }
#te-ring { position: fixed; left: -100px; top: -100px; width: 36px; height: 36px; margin: -18px 0 0 -18px; border-radius: 50%%; border: 3.5px solid #ff2d78;
  background: rgba(255, 45, 120, .2); box-shadow: 0 0 0 2.5px #fff; pointer-events: none; z-index: 99998; transition: left .35s ease, top .35s ease; }
#te-ring.pulse { animation: te-pulse .5s ease-out; }
@keyframes te-pulse { 0%% { transform: scale(1); } 40%% { transform: scale(.55); background: rgba(255, 45, 120, .75); } 100%% { transform: scale(1); } }
#te-line { position: fixed; left: 0; top: 0; width: 1440px; height: 900px; pointer-events: none; z-index: 99997; }""" % (H + CAPTION_H, CAPTION_H)
VIDEO_JS = """() => {
  const add = (tag, id, html) => { const e = document.createElementNS(tag === 'svg' ? 'http://www.w3.org/2000/svg' : 'http://www.w3.org/1999/xhtml', tag); e.id = id; e.innerHTML = html || ''; document.body.appendChild(e); return e; };
  add('div', 'te-cap', '<b></b><span></span><i></i>'); add('div', 'te-ring'); add('svg', 'te-line', '<line stroke="#ff2d78" stroke-width="4" stroke-linecap="round" stroke-dasharray="2 9"/>');
}"""
HIDE_IN_SHOT = "#te-ring, #te-line { visibility: hidden !important; }"


class Env:
    def __init__(self, headless=True, video_dir=None):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=headless, args=["--force-color-profile=srgb", "--font-render-hinting=none",
                                                                         "--disable-lcd-text"])
        self.video = bool(video_dir)                       # record the page; the model still sees only the 1440 x 900 desktop
        vh = H + CAPTION_H if self.video else H
        kw = {"record_video_dir": video_dir, "record_video_size": {"width": W, "height": vh}} if self.video else {}
        self.context = self.browser.new_context(viewport={"width": W, "height": vh}, device_scale_factor=DPR, **kw)
        self.context.route("**/*", self._serve)
        self.page = self.context.new_page()
        self.page.set_default_timeout(4000)
        self.page_errors = []
        self.page.on("pageerror", lambda e: self.page_errors.append(str(e)))
        self._index = index_html()

    def _serve(self, route):
        url = urlparse(route.request.url)
        if url.netloc != "taskenv.local":
            return route.abort()
        if url.path in ("", "/"):
            return route.fulfill(body=self._index, content_type="text/html; charset=utf-8")
        path = os.path.normpath(os.path.join(WEB, url.path.lstrip("/")))
        if not path.startswith(WEB) or not os.path.isfile(path):
            return route.fulfill(status=404, body="")
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        with open(path, "rb") as f:
            route.fulfill(body=f.read(), content_type=ctype)

    # ------------------------------------------------------------------ episode
    def reset(self, state):
        self.page_errors.clear()
        self.page.goto(ORIGIN + "/")
        self.page.evaluate("s => TE.boot(s)", state)
        self.pointer = (W - 6.0, H - 6.0)
        self.page.mouse.move(*self.pointer)
        if self.video:
            self.page.add_style_tag(content=VIDEO_CSS)
            self.page.evaluate(VIDEO_JS)
        self._settle()

    # ------------------------------------------------------------------ video mode: what a viewer sees, never the model
    def caption(self, who, text, right=""):
        self.page.evaluate("([a, b, c]) => { const e = document.getElementById('te-cap'); e.children[0].textContent = a; e.children[1].textContent = b; e.children[2].textContent = c; }", [who, text, right])

    def show_pointer(self, x, y, pulse=False):
        self.page.evaluate("([x, y, p]) => { const r = document.getElementById('te-ring'); r.style.left = x + 'px'; r.style.top = y + 'px'; r.classList.remove('pulse'); if (p) { void r.offsetWidth; r.classList.add('pulse'); } }", [x, y, pulse])

    def show_line(self, x1=0, y1=0, x2=0, y2=0):
        self.page.evaluate("(v) => { const l = document.querySelector('#te-line line'); ['x1', 'y1', 'x2', 'y2'].forEach((k, i) => l.setAttribute(k, v[i])); }", [x1, y1, x2, y2])

    def _settle(self, ms=40):
        self.page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
        if ms:
            self.page.wait_for_timeout(ms)

    def screenshot(self):
        from PIL import Image
        kw = {"clip": {"x": 0, "y": 0, "width": W, "height": H}, "style": HIDE_IN_SHOT} if self.video else {}
        return Image.open(io.BytesIO(self.page.screenshot(type="png", caret="initial", **kw))).convert("RGB")

    def state(self):
        return self.page.evaluate("() => TE.snapshot()")

    def errors(self):
        return self.page.evaluate("() => TE.errors") + self.page_errors

    def box(self, selector):
        """Bounding box (points) of the first element matching a Playwright selector, or None."""
        loc = self.page.locator(selector).first
        try:
            b = loc.bounding_box(timeout=800)
        except Exception:
            return None
        return b and (b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"])

    def elements(self):
        """What an accessibility query would return here: the boxes (points) of the controls that
        can be acted on and are in view and not covered, with a short text."""
        return self.page.evaluate(ELEMENTS_JS)

    def on_content(self, x, y):
        """True when the point is on text or an icon (so it is not in a gap between things)."""
        return bool(self.page.evaluate(UNDER_JS, [x, y]))

    # ------------------------------------------------------------------ actions
    def step(self, a):
        p, t = self.page, a["type"]
        cx = lambda v: float(min(max(v, 0), W - 1))
        cy = lambda v: float(min(max(v, 0), H - 1))
        if t == "click":
            mods = [KEYS[m.lower()] for m in a.get("mods") or []]
            for m in mods:
                p.keyboard.down(m)
            p.mouse.move(cx(a["x"]), cy(a["y"]))
            p.mouse.click(cx(a["x"]), cy(a["y"]), button=a.get("button", "left"), click_count=int(a.get("count", 1)))
            for m in reversed(mods):
                p.keyboard.up(m)
            self.pointer = (cx(a["x"]), cy(a["y"]))
        elif t == "move":
            p.mouse.move(cx(a["x"]), cy(a["y"]), steps=4)
            self.pointer = (cx(a["x"]), cy(a["y"]))
        elif t == "drag":
            p.mouse.move(cx(a["x1"]), cy(a["y1"]))
            p.mouse.down()
            p.mouse.move(cx(a["x2"]), cy(a["y2"]), steps=12)
            p.wait_for_timeout(30)
            p.mouse.move(cx(a["x2"]), cy(a["y2"]))
            p.mouse.up()
            self.pointer = (cx(a["x2"]), cy(a["y2"]))
        elif t == "type":
            for i, part in enumerate(str(a["text"]).replace("\r\n", "\n").split("\n")):
                if i:
                    p.keyboard.press("Enter")
                if part:
                    p.keyboard.type(part)
        elif t == "key":
            p.keyboard.press(key_combo(a["keys"]))
        elif t == "scroll":
            p.mouse.move(cx(a["x"]), cy(a["y"]))
            p.mouse.wheel(float(a.get("dx", 0)), float(a.get("dy", 0)))
            self.pointer = (cx(a["x"]), cy(a["y"]))
        elif t == "wait":
            p.wait_for_timeout(300)
        elif t in ("done", "say"):
            return
        else:
            raise ValueError(f"unknown action type {t!r}")
        self._settle()

    def close(self):
        try:
            self.context.close()                           # writes the video, if one is being recorded
            self.browser.close()
        finally:
            self._pw.stop()
