# The assistant on real macOS apps

Written 2026-11-15. The simulator of [TASKENV.md](TASKENV.md) measures the model. This bench measures the
whole assistant (`assistant/`) on Apple's own apps: Finder, Notes, Reminders, Calendar, Contacts, TextEdit,
Safari, Calculator, Terminal, System Settings and the Dock.

## Method

- **Where it runs.** The packaged app (`assistant/package.sh`, [the package's README](../assistant/package/README.md))
  runs inside a macOS 26 virtual machine (macOS 26.6.2, 4 CPUs, 6 GB, a 1280 x 800 screen; Tart with a public
  macOS base image) on a Mac mini. The model is not in the virtual machine: the host serves it to the app
  through an OpenAI-compatible server (llama.cpp's `llama-server`, the 9B as a Q2_0 GGUF with its vision file),
  and the app is started in its batch mode with `--plain-server`.
- **One run.** The Mac is reset: open menus and sheets dismissed, every app quit, the test files removed, light
  mode, the Dock's settings put back, and the notes, reminders, events and contacts of earlier runs deleted.
  Then the task's own setup is made (a file to rename, a reminder to complete). The request is given to the
  app as one typed line. When the app says it is finished, or the time limit is reached, a checker written
  for that task reads the Mac's state: files, `defaults`, and AppleScript queries of the apps. No screenshot
  and no model take part in the verdict. A run passes when the checker finds the task done after the run and
  did not find it done before.
- **Tasks.** 50 task templates, each with several wordings and parameters (762 instances in all). A round is
  one instance of each template, and every round below used the same 50 instances. The task definitions and
  checkers are in [`realmac/tasks.py`](../realmac/tasks.py). That file is for reading: it calls a small helper
  (`vm`) that runs commands, AppleScript and key presses in the virtual machine, and the helper and the
  runner are not in this repository.
- **Checking the checkers.** After a reset none of the 50 templates was already satisfied. 18 templates have
  a script that does the task directly; after that script, all 18 checkers passed.
- **How a request is handled** is recorded for every run:
  - *built-in tools*: the app carried the request out itself, with no model call;
  - *the model plans*: the model chose every step, one `next_step` call per step. Seven templates can be
    finished in one such step (open an app, open a site, a web search, a settings pane, a folder, a new Finder
    window, a screenshot); the others need several;
  - *spelled out*: the request named its own clicks or typing, and the model only pointed.

## Results

One run per task in each round. The rounds differ in the app build and in the planner model.

| Round | App | Planner model | Passed | Built-in tools | Model plans one step | Model plans several steps | Spelled out |
|---|---|---|---|---|---|---|---|
| 1 | first package | 9B before planner training (`orch-v1-u3000`) | **9 of 50** | 4 of 6 | 1 of 2 | 3 of 29 | 1 of 13 |
| 2 | after the first fixes | the same | **24 of 50** | 12 of 12 | 2 of 2 | 9 of 33 | 1 of 3 |
| 3 | the same build | planner after 500 updates (`planpoint-v1-u500`) | **26 of 50** | 12 of 12 | 2 of 2 | 11 of 33 | 1 of 3 |
| 4 | the same build | final planner, 1,500 updates (`planpoint-v1-u1500`) | **23 of 50** | 12 of 12 | 2 of 2 | 9 of 33 | 0 of 3 |
| 5 | requests done in parts; typing and Return fixes | final planner | **38 of 50** | 17 of 18 | 2 of 2 | 19 of 29 | 0 of 1 |
| 6 | a later build | final planner | **38 of 50** | 18 of 18 | 2 of 2 | 17 of 29 | 1 of 1 |

Round 4 was first logged as 23 of 49: the virtual machine had to be restarted with one run missing, and that
run failed when it was made. The denominators of the columns change between rounds because the app changed
which requests it handles itself.

How the failed runs ended:

| Round | Failed | Never said `done` (repeats a step with no effect) | `done` too early | Wrong control | Wrong tool | Other |
|---|---|---|---|---|---|---|
| 1 | 41 | 15 | 3 | 4 | 12 | 4 unusable answers, 2 built-in routes that reported success without the effect, 1 fault of the test bench |
| 2 | 26 | 18 | 5 | 1 | 2 | |
| 3 | 24 | 8 | 11 | 3 | 2 | |
| 4 | 27 | 2 | 14 | 8 | 3 | |
| 5 | 12 | 1 | 6 | 3 | 1 | 1 built-in route that reported success without the effect |
| 6 | 12 | 2 | 8 | 2 | 0 | |

What this says:

- **Most of the gain came from the app, not from the model.** From round 1 to round 2 the same model went from
  9 to 24 because requests to open something were no longer taken as a click, opened apps were brought to the
  front, and the built-in tools checked their own effect. From round 4 to round 5 the same planner went from 23
  to 38 because a request with "then" was carried out in parts, typing into one-line fields and Return were
  handled by the app, and more everyday requests got a built-in tool (12 to 18 of the 50).
- **On one build, planner training did not show up in the total.** 24, 26 and 23 of 50 for the planner before
  training, after 500 and after 1,500 updates. With one run per task a difference of two or three tasks is
  within the noise. What changed is how runs fail: the untrained planner mostly repeats a step that has no
  effect (18 of 26 failures), the trained ones mostly say `done` too early (11 of 24, 14 of 27). The simulator
  shows the same shift ([TASKENV.md](TASKENV.md), "Planner mode").
- **Where the model plans several steps** it finishes 19 and 17 of 29 tasks on the last two builds, against
  3 of 29 with the first package.
- A longer system text for the planner did not help: on the build of rounds 2 to 4, with the 500-update
  planner, 24 of 50 with the candidate text against 26 of 50 with the built-in one.
- Separately, 38 panes of System Settings were asked for by name through the built-in route: 31 were reached.
  Not reached: Bluetooth, Sharing, Siri and Time Machine (an app of a similar name was opened instead), VPN,
  Screen Saver and Trackpad.
- Speed on rounds 2 and 3: about 1.6 s for one planning answer, about 3 s for a step with its action, and
  15 to 18 s for a request.

## Limits

- **One run per task and round**, 50 tasks. No intervals are given; treat differences of a few tasks as noise.
- **The fixes were written from these tasks.** Between rounds the app was changed after reading the failures
  of these same 50 instances, so rounds 5 and 6 show how far the fixes went on this set, not what to expect on
  requests nobody has looked at. The other 712 instances were not run (a pass over them was stopped after 5
  runs, 1 passed, on the build of rounds 2 to 4).
- **A virtual machine**: a fresh account with almost no data, a small screen, 6 GB of memory. The model runs
  on the host, so nothing here says how the app and the model share one 16 GB Mac.
- **Typed requests only.** Speech to text is not part of these runs.
- **Email drafting cannot be tested there.** Mail in the virtual machine has no account, and a draft link
  opens its "add account" sheet instead of a compose window.
- **The newest app source in this repository has no completed round.** Round 6 is the last build with a
  full round.
- The checkers read state, so a task done in an unexpected way still passes, and a run that did the right
  thing in the wrong place fails.
