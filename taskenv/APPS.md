# Writing an app and its tasks

TEST ENVIRONMENT ONLY. Nothing in `taskenv/` may ever enter a training mix. Everything here is
written fresh for the test; do not read or reuse `bench/pointing/pointgen` (those screens were
trained on).

An app is three files. `files` is the reference implementation: read `web/apps/files.js`,
`web/apps/files.css` and `tasks/files.py` before writing a new one, and the header of
`web/shell.js` for the full list of hooks.

## `web/apps/<app>.js`

`TE.register('<app>', def)`. The app is a pure function from its state to HTML; the shell owns
every event listener and re-renders the window after each handler.

- `def.render(s)` returns the HTML of the window body from `s = TE.state.apps.<app>`.
- `def.on.<act>(s, arg, v, el)` changes `s`. Elements name their handler in markup:
  `data-act` (click), `data-dbl` (double click), `data-ctx` (right click, then `def.context(s, arg)`
  returns the menu), `data-input` (text field), `data-enter` / `data-esc` (Return / Escape in a
  text field), `data-drag` + `data-drop` (then `def.drop(s, dragArg, dropArg, info)`),
  `data-slider`, `data-select`. Use the widgets in `TE.w` (toggle, check, slider, select, seg,
  input, search) and `TE.icon(name, size)`; add icons with `TE.addIcons({name: 'svg path'})`.
- `def.menus(s)` gives the menu bar menus between the app menu and Window; `def.keys` maps
  shortcuts (`'Meta+n'`, `'Backspace'`, `'Meta+Shift+n'`) to handlers; `def.key(s, e)` receives
  other key presses outside text fields.
- `def.before(s, act)` runs before every handler (for example to commit an inline edit).
- Text fields: `data-focus="key"` keeps focus and caret across re-renders; `TE.focus(key, true)`
  inside a handler focuses a field after the re-render (and selects its text).
- Scrolling boxes: `class="scroll" data-scroll="unique-key"` keeps the scroll position.
- The window's top 52 px is the toolbar zone; the traffic lights sit at its left (20 px in, so
  leave about 80 px free there, or put a sidebar under them as Files does). Add `data-windrag`
  to the toolbar and sidebar so the window can be moved. `chrome: 'compact'` gives a small
  title-bar style window (traffic lights 9 px in).

Rules:

- State is plain JSON. Records in lists carry a unique `"id"`. Everything that is only about
  the view (selection, current folder, open panel, search text, scroll, an unsent draft) lives
  under `s.ui`; everything a task could be judged on that outlives the view lives outside it.
- Nothing random and no clocks in JS (`Math.random`, `Date.now`, timers, CSS transitions or
  animations are all forbidden): a screenshot must depend only on the state. "Today" and
  similar come from the state.
- No native `<select>`, date pickers, `title` tooltips, `alert`/`confirm`, emoji or web images:
  none of them renders the same way (or at all) in a headless screenshot. Icons are inline SVG.
- Act on `click`, never on `mousedown` (the shell re-renders on click; an element replaced on
  mousedown never receives its click).
- Make it look like the real macOS app: same layout, proportions and controls. Look at your
  screenshots (the runner saves them) and fix what looks off.

## `tasks/<app>.py`

- `SIZE = (w, h)`: window size in points. It must fit a 1440 x 900 desktop with a 28 px menu
  bar and an 80 px Dock: at most about 1100 x 700.
- `default(rng)`: the app's seeded start state (names, order, contents all vary with the seed).
  It is built for every episode of every app, because any app can be opened from the Dock.
- Tasks: `@task("<app>.<name>", "<category>")` on a function of the builder `S`. It may change
  `S.apps["<app>"]` to set the scene, calls `S.open("<app>")`, and returns a `Spec`:
  - `request`: what a person would say to an assistant. No UI instructions ("click the…"),
    no selectors; name things the way they appear on screen. Give two phrasings with `say()`.
  - `steps`: the solution, as `Click`, `Drag`, `Type`, `Key`, `Reveal` (see `oracle.py`). Each
    pointing step has `say`: one short imperative sentence naming the element as a person
    would ("Click the Archive button in the toolbar"). Guided mode reads these to a pointing
    model, so they must identify the element on the screenshot without ambiguity.
  - `check(st, init)`: decides success from the final state only. Use `verdict(cond(...),
    only(st, init, "<app>.path.that.may.change", ...))`: the positive condition plus "nothing
    else changed anywhere" (`unchanged(st, init)` when nothing may change). Paths are those of
    `base.diff`: `mail.messages.m3.box`, `files.items.+*` (a record was added), `notes.notes.-n2`
    (removed), `reminders.items.<order>`. Typed text is compared with `norm()`.
  - `kind="already_done"`: the request is already satisfied; the right behaviour is to stop
    without changing anything (`steps=[]`, `check=unchanged`). `kind="infeasible"`: it cannot
    be done (the thing asked for does not exist); the right behaviour is to say so.
- Categories: `single` (one click), `chain` (2 to 8 steps), `typing`, `drag`, `scroll` (the
  target is out of view at the start), `menu` (menu bar or right-click menu), `shortcut` (the
  solution uses a key combination), `already_done`, `infeasible`.
- Every task must vary with the seed (which item, which value, where the window is) and must
  be solved by the oracle on every seed.

## Test

    ~/Bonsai-demo/.venv-taskenv/bin/python -m taskenv.run --agent oracle --tasks '<app>.*' \
        --seeds 1 2 3 4 5 9101 9102 9103 --out ~/Bonsai-demo/taskenv-runs/dev-<app>

(from the repository root). Every line must say PASS and there must be no `ORACLE FAILED` line;
page errors (exceptions in a handler) also count as failures. Screenshots of every step are in
`<out>/shots/`. Also check by hand that a wrong action does NOT pass (a checker that always
says yes is worse than none).
