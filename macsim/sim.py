"""macsim.sim: the desktop in headless Chromium (Playwright), for TRAINING data.

Run it on a Mac: the page asks for the system font (-apple-system), and the symbols and app icons
are Apple's own renders, read from a folder outside the repository (--icons, on the Mac mini
~/bonsai/icon_render with symbols/ and apps/). Apple images never go into git.

    sim = Sim(icons)
    sim.boot(state)                 # macsim.world.build(seed, split)[0]
    image, scale = sim.shot()       # the whole screen as the assistant sees it: 1280 px on the long side
    els, surfaces = sim.elements()  # every element with role, name, function, state, box, visible share
    sim.click(x, y)                 # points of the screen, like the other actions
"""
import io
import math
import mimetypes
import os
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
ORIGIN = "http://macsim.local"
DPR = 2          # a Retina screen
LONG = 1280      # the assistant's screenshot: this many pixels on the long side
INDEX = ('<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="shell.css"><link rel="stylesheet" href="apps.css"></head>'
         '<body><div id="desktop"><div id="menubar"></div><div id="windows"></div><div id="dock"></div><div id="overlays"></div></div>'
         '<script src="shell.js"></script><script src="apps.js"></script></body></html>')
SUFFIX = ".regular.48.black.png"

# Every element with data-role: its box, how much of it can be seen and clicked (a 7 x 7 grid of probes), the part
# that can be seen, where it is (window of an app, alert, popover, menu, menu bar, Dock, Spotlight), its parent element.
COLLECT_JS = """() => {
  const all = [...document.querySelectorAll('[data-role]')], idx = new Map(all.map((e, i) => [e, i])), out = [], N = 7, W = innerWidth, H = innerHeight;
  const menus = [...document.querySelectorAll('.menu')];
  for (const el of all) {
    const r = el.getBoundingClientRect();
    if (r.width < 3 || r.height < 3 || r.right <= 1 || r.bottom <= 1 || r.left >= W - 1 || r.top >= H - 1) continue;
    let vis = 0, a0 = N, a1 = -1, b0 = N, b1 = -1;
    for (let a = 0; a < N; a++) for (let b = 0; b < N; b++) {
      const px = r.left + (a + .5) * r.width / N, py = r.top + (b + .5) * r.height / N;
      if (px < 0 || py < 0 || px >= W || py >= H) continue;
      const t = document.elementFromPoint(px, py);
      if (t && (t === el || el.contains(t))) { vis++; a0 = Math.min(a0, a); a1 = Math.max(a1, a); b0 = Math.min(b0, b); b1 = Math.max(b1, b); }
    }
    if (!vis) continue;
    const whole = vis === N * N, cw = r.width / N, ch = r.height / N;
    const box = whole ? [r.left, r.top, r.right, r.bottom] : [r.left + (a0 + .25) * cw, r.top + (b0 + .25) * ch, r.left + (a1 + .75) * cw, r.top + (b1 + .75) * ch];
    const mid = document.elementFromPoint((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), p = el.parentElement && el.parentElement.closest('[data-role]'), m = el.closest('.menu'), w = el.closest('.win'), d = el.dataset;
    const where = m ? 'menu' : el.closest('#spot') ? 'spotlight' : el.closest('#menubar') ? 'menubar' : el.closest('#dock') ? 'dock' : !w ? 'desktop' : el.closest('.alert') ? 'alert' : el.closest('.c-pop') ? 'popover' : 'window';
    out.push({i: idx.get(el), role: d.role, name: d.name, fn: d.fn || '', state: d.state || '', noun: d.noun || '', icon: !!d.icon, where, app: w ? w.dataset.app : null, menu: m ? menus.indexOf(m) : -1,
      box, full: [r.left, r.top, r.right, r.bottom], vis: vis / (N * N), mid: !!(mid && (mid === el || el.contains(mid))), parent: p ? idx.get(p) : null,
      text: (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 80), dim: el.classList.contains('dim') || el.classList.contains('disabled')});
  }
  const surf = [], S = (name, el, z) => { if (!el) return; const r = el.getBoundingClientRect(); if (r.width > 2) surf.push({name, box: [r.left, r.top, r.right, r.bottom], z}); };
  document.querySelectorAll('.win').forEach(w => { if (w.style.display !== 'none') S('window:' + w.dataset.app, w, +w.style.zIndex || 10); });
  S('dock', document.getElementById('dock'), 900); S('menubar', document.getElementById('menubar'), 1000); S('spotlight', document.getElementById('spot'), 1500);
  menus.forEach((m, k) => S('menu:' + k, m, 2000 + k));
  surf.sort((a, b) => a.z - b.z);
  return {els: out, surf, front: TE.front()};
}"""

# Wait until every symbol and icon on the page is decoded, so that no screenshot shows a hole.
READY_JS = """async () => {
  const seen = window._seen = window._seen || new Set(), jobs = [];
  document.querySelectorAll('i.sym').forEach(e => { const m = /url\\(([^)]+)\\)/.exec(e.getAttribute('style') || ''); if (!m) return; const u = m[1].replace(/["']/g, '');
    if (!seen.has(u)) { seen.add(u); const im = new Image(); im.src = u; jobs.push(im.decode().catch(() => {})); } });
  for (const i of document.images) if (!i.complete || !i.naturalWidth) jobs.push(i.decode().catch(() => {}));
  await Promise.all(jobs); await document.fonts.ready;
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  return jobs.length;
}"""

SPOTS_JS = """sel => [...document.querySelectorAll(sel)].map(e => { const r = e.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  if (r.width < 3 || x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) return null; const t = document.elementFromPoint(x, y); return t && (t === e || e.contains(t)) ? [x, y] : null; }).filter(Boolean)"""


class Sim:
    def __init__(self, icons, headless=True):
        from playwright.sync_api import sync_playwright
        self.icons = os.path.expanduser(icons)
        self.syms = sorted(f[:-len(SUFFIX)] for f in os.listdir(os.path.join(self.icons, "symbols")) if f.endswith(SUFFIX))
        if len(self.syms) < 300:
            raise RuntimeError(f"{self.icons}/symbols holds {len(self.syms)} symbols; this simulator draws with Apple's renders and needs them")
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=headless, args=["--force-color-profile=srgb"])
        self.size = (1470, 956)
        self.context = self.browser.new_context(viewport={"width": self.size[0], "height": self.size[1]}, device_scale_factor=DPR)
        self.context.route("**/*", self._serve)
        self._files = {}
        self.page = self.context.new_page()
        self.page.set_default_timeout(8000)
        self.page_errors = []
        self.page.on("pageerror", lambda e: self.page_errors.append(str(e)))
        self.page.goto(ORIGIN + "/")

    def _serve(self, route):
        url = urlparse(route.request.url)
        if url.netloc != "macsim.local":
            return route.abort()
        if url.path in ("", "/"):
            return route.fulfill(body=INDEX, content_type="text/html; charset=utf-8")
        if url.path not in self._files:
            if url.path.startswith("/sym/"):
                path, base = os.path.join(self.icons, "symbols", url.path[5:]), self.icons
            elif url.path.startswith("/app/"):
                path, base = os.path.join(self.icons, "apps", url.path[5:]), self.icons
            else:
                path, base = os.path.join(WEB, url.path.lstrip("/")), WEB
            path = os.path.normpath(path)
            self._files[url.path] = open(path, "rb").read() if path.startswith(base) and os.path.isfile(path) else None
        body = self._files[url.path]
        if body is None:
            return route.fulfill(status=404, body="")
        ctype = mimetypes.guess_type(url.path)[0] or "application/octet-stream"
        route.fulfill(body=body, content_type=ctype + ("; charset=utf-8" if ctype.startswith("text/") or ctype.endswith("javascript") else ""), headers={"Cache-Control": "max-age=86400"})

    # ------------------------------------------------------------------ a screen
    def boot(self, state):
        W, H = state["screen"]
        if (W, H) != self.size:
            self.page.set_viewport_size({"width": W, "height": H})
            self.size = (W, H)
        self.page_errors.clear()
        have = lambda d: isinstance(d, dict) and d.get("icon") and not os.path.isfile(os.path.join(self.icons, "apps", d["icon"]))
        dock = [dict(d, icon=None) if have(d) else d for d in state["dock"]]            # no render of this icon here: the drawn one
        self.page.evaluate("s => TE.boot(s)", dict(state, syms=self.syms, dock=dock))
        self.page.mouse.move(W - 2, H * 0.4)
        self.ready()

    def ready(self):
        if self.page.evaluate(READY_JS):
            self.page.wait_for_timeout(60)                 # new images: one more frame for the masks to paint

    def post(self, post, r):
        """Things done in the browser before the picture: open a menu (sometimes a submenu), a context menu, a pop-up."""
        p = self.page
        for kind, arg in post:
            if kind == "menu":
                spots = p.evaluate(SPOTS_JS, ".mb-item")
                if not spots:
                    continue
                x, y = spots[(arg + 1) % len(spots)]
                p.mouse.click(x, y)
                if r.random() < 0.4:
                    subs = p.evaluate(SPOTS_JS, ".menu .menu-item:not(.disabled):has(.mi-short svg)")
                    if subs:
                        p.mouse.move(*r.choice(subs))
            elif kind == "context":
                spots = p.evaluate(SPOTS_JS, f'.win[data-app="{arg}"] [data-ctx]')
                if spots:
                    x, y = r.choice(spots)
                    p.mouse.click(x + r.uniform(-20, 20), y, button="right")
            elif kind == "popup":
                spots = p.evaluate(SPOTS_JS, f'.win[data-app="{arg}"] .popup[data-act="pop"]')
                if spots:
                    p.mouse.click(*r.choice(spots))
        self.ready()

    def shot(self):
        from PIL import Image
        img = Image.open(io.BytesIO(self.page.screenshot(type="png", caret="initial"))).convert("RGB")
        W, H = self.size
        s = LONG / max(W, H)
        return img.resize((round(W * s), round(H * s)), Image.LANCZOS), s

    def elements(self):
        d = self.page.evaluate(COLLECT_JS)
        return d["els"], d["surf"], d["front"]

    def state(self):
        return self.page.evaluate("() => TE.snapshot()")

    def errors(self):
        return self.page.evaluate("() => TE.errors") + self.page_errors

    # ------------------------------------------------------------------ actions (points of the screen)
    def click(self, x, y, button="left", count=1):
        self.page.mouse.move(x, y)
        self.page.mouse.click(x, y, button=button, click_count=count)
        self.ready()

    def type(self, text):
        self.page.keyboard.type(text)
        self.ready()

    def key(self, combo):
        self.page.keyboard.press(combo)
        self.ready()

    def close(self):
        try:
            self.context.close()
            self.browser.close()
        finally:
            self._pw.stop()


def to_image(els, surf, s):
    """Boxes from screen points to pixels of the saved image (floor / ceil, so a box never loses its edge)."""
    q = lambda b: [int(math.floor(b[0] * s)), int(math.floor(b[1] * s)), int(math.ceil(b[2] * s)), int(math.ceil(b[3] * s))]
    for e in els:
        e["box"], e["full"] = q(e["box"]), q(e["full"])
        e["surface"] = {"window": f"window:{e['app']}", "alert": f"window:{e['app']}", "popover": f"window:{e['app']}", "menu": f"menu:{e['menu']}"}.get(e["where"], e["where"])
    for u in surf:
        u["box"] = q(u["box"])
    return els, surf
