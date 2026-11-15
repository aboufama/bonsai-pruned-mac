"""Headless Chromium rendering. One Renderer per process; pages are served from memory through a
request route, so nothing touches the network and nothing is written besides the screenshot."""
import os

from .css import BASE_CSS

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ORIGIN = "http://pointgen.local"

# Runs in the page: places overlays next to their anchors, then reports every target's box,
# whether it is fully visible and on top, and all visible text and icon glyphs.
COLLECT_JS = r"""
async (ovs) => {
  // Load every weight of the page's two font families up front, then wait until no font is
  // pending. Overlays added below can ask for a weight the page has not used yet; measuring
  // before that font arrives would report boxes for the fallback font.
  const root = getComputedStyle(document.documentElement);
  const fams = [root.getPropertyValue('--font'), root.getPropertyValue('--mono')].map(s => s.trim()).filter(Boolean);
  await Promise.all(fams.flatMap(f => [400, 500, 600, 700].map(w => document.fonts.load(w + ' 13px ' + f).catch(() => null))));
  const settle = async () => {
    for (let i = 0; i < 40; i++) {
      await document.fonts.ready;
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      if (document.fonts.status === 'loaded') return;
    }
  };
  await settle();
  const W = innerWidth, H = innerHeight, failed = [];
  const hit = (el, x, y) => {
    if (x < 0 || y < 0 || x >= W || y >= H) return false;
    const e = document.elementFromPoint(x, y);
    return !!e && (e === el || el.contains(e));
  };
  for (const ov of ovs) {
    const host = document.createElement('div');
    host.innerHTML = ov.html;
    if (ov.place === 'modal') { document.getElementById('win').appendChild(host.firstElementChild); continue; }
    const a = document.querySelector('[data-t="' + ov.anchor + '"]');
    if (!a) { failed.push(ov.id); continue; }
    const ar = a.getBoundingClientRect();
    if (!(ar.width > 0 && hit(a, ar.left + ar.width / 2, ar.top + ar.height / 2))) { failed.push(ov.id); continue; }
    host.className = 'ovl';
    document.body.appendChild(host);
    const r = host.getBoundingClientRect();
    let x = ar.left, y = ar.bottom + 2;
    if (ov.place === 'below-end') x = ar.right - r.width;
    else if (ov.place === 'below-center') { x = ar.left + ar.width / 2 - r.width / 2; y = ar.bottom + 6; }
    else if (ov.place === 'above-center') { x = ar.left + ar.width / 2 - r.width / 2; y = ar.top - r.height - 6; }
    else if (ov.place === 'right-start') { x = ar.right + 2; y = ar.top - 4; }
    else if (ov.place === 'point') { x = ar.left + ar.width * ov.fx; y = ar.top + ar.height * ov.fy; }
    if (y + r.height > H - 4) y = ov.place.startsWith('below') ? ar.top - r.height - 2 : H - r.height - 4;
    if (ov.place === 'above-center' && y < 4) y = ar.bottom + 6;
    x = Math.round(Math.min(Math.max(4, x), W - r.width - 4));
    y = Math.round(Math.max(4, y));
    host.style.left = x + 'px';
    host.style.top = y + 'px';
    if (ov.mark) a.classList.add(ov.mark);
  }
  document.body.getBoundingClientRect();
  await settle();
  const styles = new Map();
  const cs = (el) => { let c = styles.get(el); if (!c) { c = getComputedStyle(el); styles.set(el, c); } return c; };
  const clip = (el) => {
    let x1 = 0, y1 = 0, x2 = W, y2 = H;
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const c = cs(p);
      if (c.overflowX !== 'visible' || c.overflowY !== 'visible') {
        const r = p.getBoundingClientRect();
        x1 = Math.max(x1, r.left); y1 = Math.max(y1, r.top); x2 = Math.min(x2, r.right); y2 = Math.min(y2, r.bottom);
      }
    }
    return [x1, y1, x2, y2];
  };
  const px = [.5, .2, .8, .2, .8], py = [.5, .25, .25, .75, .75];
  const targets = [...document.querySelectorAll('[data-t]')].map(el => {
    const r = el.getBoundingClientRect(), [x1, y1, x2, y2] = clip(el);
    const full = r.left >= x1 - .5 && r.top >= y1 - .5 && r.right <= x2 + .5 && r.bottom <= y2 + .5;
    const some = Math.min(r.right, x2) - Math.max(r.left, x1) > 2 && Math.min(r.bottom, y2) - Math.max(r.top, y1) > 2;
    let top = some, any = false;
    if (some) for (let k = 0; k < 5; k++) {
      const ok = hit(el, r.left + r.width * px[k], r.top + r.height * py[k]);
      top = top && ok; any = any || ok;
    }
    let trunc = false;
    const chk = (e) => { if (e.scrollWidth > e.clientWidth + 1) trunc = true; };
    if (el.classList.contains('el')) chk(el);
    el.querySelectorAll('.el').forEach(chk);
    return {t: +el.dataset.t, x: r.left, y: r.top, w: r.width, h: r.height, full, top, part: some && any, trunc};
  });
  const owner = (el) => { const o = el.closest('[data-t],[data-o]'); return o ? +(o.dataset.t || o.dataset.o) : 0; };
  const texts = [], range = document.createRange();
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    const s = n.nodeValue.trim();
    const p = n.parentElement;
    if (!s || !p || p.closest('svg,style,script')) continue;
    range.selectNodeContents(n);
    const r = range.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    if (!hit(p, r.left + r.width / 2, r.top + r.height / 2) && !hit(p, r.left + Math.min(6, r.width / 2), r.top + r.height / 2)) continue;
    texts.push([s, owner(p)]);
  }
  const glyphs = [];
  for (const s of document.querySelectorAll('svg[data-i]')) {
    const r = s.getBoundingClientRect();
    const x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (r.width < 1 || x < 0 || y < 0 || x >= W || y >= H) continue;
    const e = document.elementFromPoint(x, y);
    if (!e || !(e === s || s.contains(e) || e === s.parentElement)) continue;
    glyphs.push([s.dataset.i, owner(s)]);
  }
  return {W, H, targets, texts, glyphs, failed};
}
"""


class Renderer:
    def __init__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(args=[
            "--font-render-hinting=none", "--disable-lcd-text", "--hide-scrollbars",
            "--force-color-profile=srgb", "--disable-gpu",
            # one full raster of the final frame: without these, tiles repainted in part (after a font
            # arrives or an overlay is added) can differ by a grey level along the repainted edge
            "--disable-partial-raster", "--run-all-compositor-stages-before-draw", "--disable-threaded-animation",
            "--disable-threaded-scrolling", "--disable-checker-imaging", "--disable-new-content-rendering-timeout",
            "--disable-image-animation-resync",
        ])
        self._html = ""
        self._fonts = {}

    def _route(self, route):
        path = route.request.url[len(ORIGIN):].split("?")[0]
        if path == "/s.html":
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=self._html)
        elif path == "/base.css":
            route.fulfill(status=200, content_type="text/css; charset=utf-8", body=BASE_CSS,
                          headers={"Cache-Control": "max-age=31536000"})
        elif path.startswith("/fonts/"):
            name = os.path.basename(path)
            if name not in self._fonts:
                with open(os.path.join(ASSETS, "fonts", name), "rb") as f:
                    self._fonts[name] = f.read()
            route.fulfill(status=200, content_type="font/woff2", body=self._fonts[name],
                          headers={"Cache-Control": "max-age=31536000"})
        else:
            route.fulfill(status=404, body="")

    def render(self, html, width, height, dpr, overlays, png_path, check_boxes=False):
        """Render, collect measurements, save the screenshot. Returns the page report.

        Every screen gets a fresh browser context at its own viewport size. Reusing one page and
        resizing it made a few anti-aliased corner pixels depend on what had been drawn before,
        so the same seed could give PNGs that differed by one grey level in a handful of pixels.
        """
        context = self.browser.new_context(device_scale_factor=dpr, viewport={"width": width, "height": height},
                                           reduced_motion="reduce", color_scheme="light")
        try:
            context.route("**/*", self._route)
            page = context.new_page()
            self._html = html
            page.goto(ORIGIN + "/s.html", wait_until="load")
            report = page.evaluate(COLLECT_JS, overlays)
            report["dpr"] = dpr
            self._finish(page, report, png_path, check_boxes)
        finally:
            context.close()
        return report

    def _finish(self, page, report, png_path, check_boxes):
        if check_boxes:
            worst = 0.0
            for m in report["targets"][:: max(1, len(report["targets"]) // 25)]:
                bb = page.locator(f'[data-t="{m["t"]}"]').bounding_box()
                if bb:
                    worst = max(worst, abs(bb["x"] - m["x"]), abs(bb["y"] - m["y"]),
                                abs(bb["width"] - m["w"]), abs(bb["height"] - m["h"]))
            report["box_check_max_diff"] = worst
        page.screenshot(path=png_path, type="png", animations="disabled", caret="hide")

    def close(self):
        try:
            self.browser.close()
            self._pw.stop()
        except Exception:
            pass
