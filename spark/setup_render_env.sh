#!/bin/bash
# Headless browser for rendering fresh benchmark screens (user space, no sudo).
cd ~/bonsai
for i in $(seq 1 240); do grep -q ENV_DONE logs/setup_train_env.log && break; sleep 5; done
./venv/bin/pip -q install playwright
./venv/bin/playwright install chromium 2>&1 | tail -2
./venv/bin/python - <<"PY"
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 800})
    pg.set_content("<button id=a style=\"margin:40px\">Save changes</button>")
    print("box", pg.locator("#a").bounding_box())
    b.close()
print("RENDER_OK")
PY
echo RENDER_ENV_DONE
