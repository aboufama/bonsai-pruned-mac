# Fifteen tasks in real macOS apps (prepared, not run)

**TEST ONLY. Nothing here may ever enter a training mix.** This list is for a later run on
a real Mac with a person watching. Nothing in it has been executed. The web replicas in `taskenv/web` are stand-ins; this is the check that the
numbers from them carry over to the real thing.

## How the run would work

- Same loop as `taskenv/run.py`: screenshot (the real screen), one
  `computer_use` action (docs/ACTION_FORMAT.md), executed by a small driver (CGEvent or
  `cliclick`), repeat. The driver needs Screen Recording and Accessibility permission for the
  one process that runs it. Step limit: twice the steps listed plus four.
- Everything happens in throwaway places: the folder `~/taskenv-scratch` (in the home folder,
  not under Documents, so no cloud sync sees it), a Notes folder called `taskenv scratch`, and
  untitled TextEdit documents. The setup command of each task creates what it needs; the reset
  command removes it. Appearance settings are read before the run and put back after it.
- The check of every task is a shell command or an AppleScript one-liner run after the model
  stops; it reads the result from the app or the disk, never from coordinates. Where macOS has
  no way to read the state (Calculator's display), the task ends by copying the result, and the
  check reads the clipboard.
- One-time preparation: `mkdir -p ~/taskenv-scratch`; in Notes, create the folder
  `taskenv scratch`; note the current appearance with
  `defaults read -g AppleInterfaceStyle 2>/dev/null || echo Light` and the accent colour with
  `defaults read -g AppleAccentColor 2>/dev/null || echo default`.
- Safety: the model is started only on these tasks, each with its app already frontmost; the
  person watching can stop the driver with a key at any time; no task touches Mail, Messages,
  a browser, the real Documents folder or any account.

## TextEdit

| # | Setup | Request | Steps | Check | Reset |
|---|---|---|---|---|---|
| 1 | `open -a TextEdit`, then File > New (an empty untitled document in front) | "Type: The quick brown fox, and nothing else." | 1 | `osascript -e 'tell application "TextEdit" to get text of front document'` prints exactly `The quick brown fox` | Close without saving |
| 2 | `printf 'Milk\nEggs\nBread\n' > ~/taskenv-scratch/shopping.txt; open -a TextEdit ~/taskenv-scratch/shopping.txt` | "Add Butter as a new last line and save the file." | 3 (click after the last line, type, Cmd+S) | `tail -n 1 ~/taskenv-scratch/shopping.txt` is `Butter`, and the first three lines are unchanged (`head -n 3` compared with the setup) | `rm ~/taskenv-scratch/shopping.txt` |
| 3 | `printf 'Dear Sam,\nsee you on Tuesday.\n' > ~/taskenv-scratch/letter.txt; open -a TextEdit ~/taskenv-scratch/letter.txt` | "Change Tuesday to Friday and save." | 3 (double-click the word, type, Cmd+S) | `grep -c Friday ~/taskenv-scratch/letter.txt` is 1 and `grep -c Tuesday` is 0 | `rm ~/taskenv-scratch/letter.txt` |
| 4 | An untitled document containing the line `Agenda` (typed by the setup script through `osascript -e 'tell application "TextEdit" to set text of front document to "Agenda"'`) | "Save this document as agenda in the taskenv-scratch folder." | 4 to 6 (Cmd+S, type the name, choose the folder with Cmd+Shift+G or the pop-up, Save) | `ls ~/taskenv-scratch/agenda.*` shows one file, and `textutil -convert txt -stdout` of it prints `Agenda` | `rm ~/taskenv-scratch/agenda.*` |

## Calculator

| # | Setup | Request | Steps | Check | Reset |
|---|---|---|---|---|---|
| 5 | `open -a Calculator`, press Escape twice (display 0); `pbcopy < /dev/null` | "Work out 48 times 12 and copy the result." | 6 to 7 (keys or clicks, then Cmd+C) | `pbpaste` prints `576` | Escape |
| 6 | As task 5 | "What is 15% of 240? Copy the answer." | 6 to 8 | `pbpaste` prints `36` | Escape |
| 7 | Calculator in Basic mode (`defaults read com.apple.calculator ViewDefaultsKey` is `Basic`) | "Switch the calculator to Scientific mode." | 2 (View menu, Scientific) or 1 (Cmd+2) | `defaults read com.apple.calculator ViewDefaultsKey` is `Scientific` after quitting the app; while it runs: `osascript -e 'tell application "System Events" to tell process "Calculator" to get value of attribute "AXMenuItemMarkChar" of menu item "Scientific" of menu "View" of menu bar 1'` returns a check mark | View > Basic |

## Finder, in `~/taskenv-scratch`

Setup for all four: `cd ~/taskenv-scratch && rm -rf * && mkdir Archive Photos && touch report.pdf notes.txt budget.xlsx old-draft.docx && open ~/taskenv-scratch` (one Finder window showing the folder, icon view).

| # | Request | Steps | Check | Reset |
|---|---|---|---|---|
| 8 | "Move budget.xlsx into the Archive folder." | 1 (drag) | `ls ~/taskenv-scratch/Archive` prints `budget.xlsx`; `ls ~/taskenv-scratch` no longer lists it; the other three files are where they were | The setup command |
| 9 | "Rename notes.txt to meeting-notes.txt." | 3 to 4 (select, Return, type, Return) | `ls ~/taskenv-scratch` lists `meeting-notes.txt` and not `notes.txt`; file count unchanged | The setup command |
| 10 | "Make a new folder called Invoices here." | 3 (Cmd+Shift+N, type, Return) | `test -d ~/taskenv-scratch/Invoices` and nothing else was added (`ls | wc -l` is 7) | The setup command |
| 11 | "Put old-draft.docx in the Trash." | 2 (select, Cmd+Delete) | `test ! -e ~/taskenv-scratch/old-draft.docx` and `ls ~/.Trash | grep -c old-draft.docx` is 1 | `mv ~/.Trash/old-draft.docx ~/taskenv-scratch/` then the setup command |

## System Settings, Appearance

| # | Setup | Request | Steps | Check | Reset |
|---|---|---|---|---|---|
| 12 | Appearance set to Light; `open "x-apple.systempreferences:com.apple.Appearance-Settings.extension"` (the Appearance pane in front) | "Switch this Mac to Dark mode." | 1 | `defaults read -g AppleInterfaceStyle` prints `Dark` | Put back the appearance noted before the run (`osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to false'`) |
| 13 | System Settings open on another pane (General); accent colour not green | "Change the accent colour to green." | 2 (Appearance in the sidebar, the green dot) | `defaults read -g AppleAccentColor` prints `3` | Put back the accent colour noted before the run (click it again; `defaults write` alone does not repaint running apps) |

## Notes, in the folder `taskenv scratch`

| # | Setup | Request | Steps | Check | Reset |
|---|---|---|---|---|---|
| 14 | Notes open with the folder `taskenv scratch` selected and empty | "Make a new note that says: Call the plumber on Monday." | 2 (Cmd+N or the compose button, type) | `osascript -e 'tell application "Notes" to get plaintext of every note of folder "taskenv scratch"'` returns one note whose text is that sentence | `osascript -e 'tell application "Notes" to delete every note of folder "taskenv scratch"'` |
| 15 | Two notes in the folder, created by `osascript -e 'tell application "Notes" to make new note at folder "taskenv scratch" with properties {body:"Groceries"}'` and the same with `"Packing list"` | "Delete the note called Groceries." | 2 (select it, Delete) or 2 (right-click, Delete) | `osascript -e 'tell application "Notes" to get name of every note of folder "taskenv scratch"'` returns only `Packing list` | As task 14 |

## Tasks with nothing to do, to add once the fifteen run

The web set has two kinds that matter for an assistant and cost nothing to copy here: asked for
Dark mode when the Mac is already dark (right answer: stop, change nothing; check: the value is
still `Dark` and no click landed on the appearance thumbnails, which the driver's log shows),
and asked to move a file that is not in the folder (right answer: `terminate` with status
`failure`; check: `ls -la` of the folder is byte-identical to before).

## What this run would and would not show

- It would show whether pointing at real macOS controls (smaller targets, translucency, real
  fonts, real menus) is as good as on the replicas, and whether the action schema drives a real
  desktop (drag in Finder, Cmd+S, typing into a save sheet).
- Fifteen tasks give an interval of roughly plus or minus 25 points around a rate near 50%, so
  it is a sanity check on the web numbers, not a second benchmark.
- Checks marked with `defaults read` see the stored setting; the on-screen state is the
  watcher's to confirm.
