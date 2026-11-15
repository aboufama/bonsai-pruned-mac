# taskenv: a task-completion test for screen assistants

**TEST ENVIRONMENT ONLY. Nothing in this folder (apps, tasks, seeds, screenshots, runs) may ever
enter a training mix.** Every app and task here was written for the test; none of it shares
templates, icons or word pools with `bench/pointing/pointgen`, whose screens were trained on.

A model sees a screenshot of a Mac-style desktop, emits one action, the environment executes it
with real pointer and keyboard events, and this repeats until the model says it is done or runs
out of steps. Success is decided by the state of the app at the end, never by coordinates.

    taskenv/
      env.py        the desktop in headless Chromium: reset, screenshot, step (click, drag, type, key, scroll)
      web/          the desktop shell (menu bar, Dock, windows, menus) and the ten apps, as web pages
      tasks/        97 tasks: start states built from a seed, requests, solution steps and checkers
      oracle.py     the solution steps (also what guided mode reads to the model)
      actions.py    the computer_use call of docs/ACTION_FORMAT.md -> an action the environment executes
      agents.py     oracle, do-nothing, random clicker, guided mode
      policy.py     the models (through bench/models.py): pointing for guided mode, the agent loop
      run.py        runs an agent through the tasks and saves every step
      report.py     tables with intervals; update_doc.py puts them into docs/TASKENV.md
      viewer.py     one static replay page per run
      selftest.py   checks of the environment itself (oracle 100%, do-nothing agent, reproducibility, action forms)
      queue.sh, plan.py   a run queue for a GPU machine that also trains, and the list of reported runs
      APPS.md       how to add an app and its tasks
      real_mac_tasks.md   fifteen tasks in real macOS apps, prepared for a supervised run, not run

    python -m taskenv.selftest                                       # must say OK
    python -m taskenv.run --agent oracle --seeds dev --out <dir>     # must be 100%

Seeds 1 to 5 are for development. Seeds 9101, 9102 and 9103 are reserved for reported runs.

Results and limits: `docs/TASKENV.md`.
