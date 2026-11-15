# macsim: a training simulator of a Mac with verifiable rewards

`macsim/` makes training data: whole Mac desktops with nine apps, every element labelled, pointing
challenges, short multi-step tasks, and a scorer that says per answer whether it hit and, if not,
what it hit instead. It exists because on a real Mac the tuned 9B clicked the arrow beside
Calendar's "Today" button when asked for the button: the model needs many screens where the right
answer is decided by a name, a function, a neighbour, a state or a window.

It is the task environment's training twin, and it is kept apart from it. **Nothing from
`taskenv/` (the held-out test) is used here**: no app, layout, content, name pool, theme, seed or
task text. `python -m macsim.check_heldout` compares every content string of macsim with every
string of the test apps and tasks and fails when one is shared (0 shared at the time of writing;
59 were found and replaced before the first screen was made). Only the engine is common:
`macsim/web/shell.js` is derived from the test shell (windows, menus, drag, keys).

## How it differs from the test environment

| | test (`taskenv/`) | training (`macsim/`) |
|---|---|---|
| screen | 1440 x 900 points | 1470 x 956, 1440 x 900, 1512 x 982, 1728 x 1117, 1280 x 800 points, menu bar 24, 33 or 37 points high |
| saved picture | 2880 x 1800 | the whole screen at 1280 px on the long side, as the assistant sees it |
| font | Inter (bundled) | the macOS system font, rendered on a Mac |
| icons | drawn for the project | Apple's own symbol renders (775) and app icons (69), read from a folder outside git |
| appearance | light | light and dark, eight accent colours, six wallpapers |
| windows | one task app, others from the Dock | one to three overlapping windows, one of them in front |
| on top | menus | pull-down menus with submenus, context menus, pop-up menus, alert sheets, the event popover, Spotlight |
| labels | none (the checker reads the state) | every element: role, name, function, state, box, visible share, neighbours |
| names and texts | its own pools | its own pools, checked to share nothing with the test |
| seeds | 1 to 5 and 9101 to 9103 | `macsim/<split>/<seed>`, a different random stream for each split |

Apps of the same kind exist on both sides; the code, layout and content of each macsim app were
written for this folder (`macsim/web/apps.js`, `apps.css`, `macsim/world.py`).

| macsim app | test app of the same kind | what is different in macsim |
|---|---|---|
| Calendar | calendar | Day, Week, Month and Year views; a calendar list with coloured checkboxes; the Previous / Today / Next group above the grid; an event popover with Delete Event; no typed event entry |
| Finder | files | sidebar with Favourites, iCloud, Locations and Tags; four view buttons, Group, Share and Action; a path bar and a status bar; a context menu; no preview pane and no sorting |
| Mail | mail | three groups of mailboxes; a toolbar of eleven icon buttons that have only accessibility names; a reading pane; a new-message panel |
| Notes | notes | folders and tags in the sidebar; list and gallery; checklists inside notes; notes are read, not edited |
| Reminders | reminders | five smart tiles above the lists; round checkboxes; no typed entry |
| Safari | browser | eight invented sites in four page kinds (article, shop, results, form); tabs with close buttons; a favourites bar; a bookmarks sidebar |
| System Settings | settings | nineteen panes; rows with switches, pop-up buttons, steppers, sliders, checkboxes and buttons |
| Music | music | Home, New, Radio, Library and Playlists in the sidebar; transport buttons, a now-playing display and a volume slider in the toolbar; a song table or an album grid |
| Messages | none | conversation list, message bubbles, a text field |

The test's calculator and sheet apps have no twin here.

## Screens

`world.build(seed, split)` draws the screen size, appearance, accent, wallpaper, the Dock (Finder,
six to twelve other apps, the Bin), the menu-bar extras, one to three apps with their contents, and
what is on top: an alert sheet (16% of screens), a pull-down menu (16%, sometimes with a submenu),
a context menu, Spotlight with a query and results, or a pop-up menu. Calendar is on about half of
the screens. Train and steps place windows towards different corners; dev uses a cascade, three
other accent colours and two other wallpapers, so dev screens are new layouts as well as new seeds.

## Elements and challenges

Every element that can be asked for carries `data-role` and `data-name` (the visible title, or the
accessibility description of an icon: the two arrows beside Today are "Previous" and "Next"),
often `data-fn` (what it does, one or more wordings) and `data-state` (checked, on, selected,
unread, completed, playing). The collector (`sim.COLLECT_JS`) probes each element on a 7 x 7 grid
with `elementFromPoint`, so the box of a partly hidden element is the part that can be seen and
clicked, and an element that cannot be clicked is never a target. Child controls inside an element
(a tab's close button, an event in a day cell) are holes: the target box is the free part.

`cases.make` writes up to about thirteen cases per screen, each target once:

| kind | the instruction picks the target by | example |
|---|---|---|
| name | visible title or accessibility description | "Click the Next button", "the Reply All button in the Mail window" |
| function | what it does | "Go back one month", "I want to archive the selected message" |
| position | a neighbour, or its place in a row or column | "the arrow to the right of the Today button", "the second tab in Safari" |
| state | its state among like elements | "the unchecked calendar checkbox in Calendar", "the selected mailbox" |
| same_name | the window or surface, when the name is on screen twice | "the search field in the Finder window", "Music in the Dock" |
| tiny | (target at most 14 px on its short side) | stepper arrows, traffic lights, tab close buttons, checkboxes |
| partial | (less than three quarters visible) | a row cut by the window edge, a button half under another window |

Tiny and partial targets are phrased in one of the first five ways (`meta.phrase`); `meta.tiny`
and `meta.partial` mark every such target whatever its kind. On every Calendar screen one of
Previous, Today, Next is asked for (`meta.must = "calendar_nav"`); what is open on top (menu,
alert, popover, Spotlight) is asked for too. At most one traffic light, two menu-bar and one or two
Dock targets per screen, so the cases stay with the windows.

## Step tasks

`steps.py` has 35 task templates over the nine apps, the Dock and Spotlight (two to five steps:
clicks, double clicks, right clicks, typed text, Return). The oracle finds each target by role,
name, place and function on the live screen, the screenshot before each step is saved, and the
state checker decides at the end; only tasks the checker accepts are kept (238 of 240 in the first
test; the two others had their target outside the window).

Examples: "Show March 2027 in Calendar" (Next, three times), "Delete the event …" (event, Delete
Event), "Move … to the Bin" (right click, Move to Bin; or select, File, Move to Bin), "Write an
email to … with the subject … and send it", "In Sound settings, set Alert sound to Breeze" (pane,
pop-up, item), "Bring Mail to the front and open the Drafts mailbox" (Dock, mailbox), "Use
Spotlight to open Notes" (menu-bar icon, type, Return).

## The reward

`macsim/score.py` is plain Python with no dependencies, for the Spark and the pods.

    python macsim/score.py --data ~/bonsai/benchdata/pointing/macsim_dev_s1 --answers answers.jsonl --out scored.jsonl

`answers.jsonl`: `{"id", "point": [x, y]}` in pixels of the image, or `{"id", "grid": [x, y]}` on
the 1000 grid, or `{"id", "raw": "<model text>"}`. Per case it returns `hit` and a class:

| class | meaning |
|---|---|
| hit | inside the target and not on a child control |
| child_element | on a control inside the target |
| same_name | on another element with the same name |
| left_neighbour, right_neighbour, up_neighbour, down_neighbour | on the element next to the target on that side |
| wrong_window | on another window or surface (a menu, the Dock, a window in front) |
| near, far | on nothing else; within 12 px, or further (`distance` in px, `distance_points` in screen points) |
| no_answer | no point, or [-1, -1] |

The summary gives the hit rate overall, by kind, by phrase, for tiny and partly hidden targets, by
app, and the count of each class. For a step set it adds the task verdict: a task is done when
every pointing step of it is a hit. That is the checker's verdict, because the oracle's path was
accepted by the checker when the data was made and a click inside the target does what the
oracle's click did. In code: `from macsim.score import classify, reward`; `reward(case, x, y)` is 1
or 0, and with `shaped=True` a miss that lands on nothing earns up to 0.5 by closeness while a miss
on a neighbour, a same-name element or another window earns 0.

`python -m macsim.gen self --data <folder>` checks the scorer against known answers: the oracle's
point must be a hit, a point on each neighbour and on each same-name element must be a miss of the
right class.

## Output format

The loader's format (`gen:` in `weightlab/core.py`, like `icons_train_s1`):

- `cases.jsonl`: `id`, `image`, `width`, `height`, `bbox` [x1, y1, x2, y2] in image pixels,
  `instruction`, `element` {`label`, `label_visible`, `region`, `role`, `ui_type`}, `tags`, and
  `meta`: `archetype` ("macsim_<kind>"), `kind`, `phrase`, `app`, `where`, `surface`, `role`,
  `name`, `function`, `state`, `visible`, `full_box`, `holes`, `tiny`, `partial`, `neighbours`
  {side: name, role, box, gap}, `same_name` [name, role, box, surface], `surfaces` back to front.
- `screens.jsonl`: one line per picture with its apps, what is on top, the surfaces and every
  element (role, label, function, state, box, visible share, neighbours).
- `images/`: PNG, 1280 px on the long side.
- `summary.json`: the counts.
- step sets also have `actions.jsonl` (every step as one `computer_use` action in the case format
  of `weightlab/actions.py`: `goal`, `history`, `action` with pixel coordinates, plus `step` in
  the orchestrator's words; typing, keys and the final `terminate` included) and `tasks.jsonl`.
  In `cases.jsonl` of a step set each pointing step is a case whose `meta.task` holds the request,
  the step number and the history.

## Making the data

On the Mac mini (system font and Apple's renders; `~/bonsai/venv` has Playwright):

    cd ~/bonsai/repo
    ~/bonsai/venv/bin/python -m macsim.gen make --out ~/bonsai/macsim/macsim_train_s1 --split train --start 0 --n 3000 --workers 8
    ~/bonsai/venv/bin/python -m macsim.gen make --out ~/bonsai/macsim/macsim_dev_s1   --split dev   --start 0 --n 400  --workers 8
    ~/bonsai/venv/bin/python -m macsim.gen make --out ~/bonsai/macsim/macsim_steps_s1 --split steps --start 0 --n 1200 --workers 8
    ~/bonsai/venv/bin/python -m macsim.gen sheet --data ~/bonsai/macsim/macsim_train_s1 --out sheet.png --tiles
    ~/bonsai/venv/bin/python -m macsim.gen self  --data ~/bonsai/macsim/macsim_train_s1

`make` with a later `--start` adds to a folder and rebuilds `cases.jsonl` and the summary. The
contact sheet draws the boxes for looking only; no picture in a set has anything drawn on it.

## Sets made

<!-- DELIVERED:BEGIN -->
On the Spark, 15 Nov 2026 (rendered on the Mac mini, 8 workers: about 12 screens a second on a free machine,
3 to 7 while it was shared):

| set | where | screens | cases |
|---|---|---|---|
| `macsim_train_s1` | `~/bonsai/benchdata/pointing/macsim_train_s1` (`gen:benchdata/pointing/macsim_train_s1`) | 3,000 | 36,484 |
| `macsim_dev_s1` | `~/bonsai/benchdata/pointing/macsim_dev_s1` (new layouts and seeds, never train on it) | 300 | 3,677 |

Train cases by kind: name 11,102, function 6,337, same name 6,171, position 5,980, state 2,631, tiny 2,369,
partly hidden 1,894. Over all kinds 4,349 targets are tiny and 2,680 partly hidden; 1,157 cases are Calendar's
Previous / Today / Next. By place: windows 24,828, menu bar 5,210, Dock 3,621, open menus 1,306, alerts 707,
Spotlight 484, popovers 328. Light 22,181, dark 14,303.

The scorer is at `~/bonsai/macsim/score.py` on the Spark. Its self-test on the train set: the oracle's point is a
hit on all 36,484 cases; of 96,594 points placed on neighbours and same-name elements, 4 were classed wrongly
(elements that overlap the target).

Not made: the step set (`macsim_steps_s1`) and more screens. The plan changed on 15 Nov: planner training data comes
from the task environment's training apps (`docs/TASKENV.md`, "Planner mode"), and the Mac mini was given to other
work. `python -m macsim.gen make --split steps` and `--start 3000` make them when a Mac is free.
<!-- DELIVERED:END -->

## Limits

- Pointing and short tasks only: no dragging, no scrolling, no text editing beyond typed fields.
- Each app has one window; "the same name in two windows" comes from different apps that share a
  name (Search, Share, Back, Delete, Previous, Next, Sidebar, List view) and from names shared by
  a window, the Dock and the menu bar.
- Finder shows files as symbols, not thumbnails; web pages are four invented layouts.
- The task verdict of the scorer follows the oracle's path; a model that reaches the goal another
  way is not credited. A live replay through the simulator is not written yet.
