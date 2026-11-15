# Action format for the computer-use loop

Written 2026-11-15. The loop we want: the model reads a screenshot, emits ONE action as a tool call,
the harness executes it, repeat. This page records how existing harnesses define their actions, what the
Qwen family (the parent of Bonsai 2) uses, and the schema this project adopts. Code:
`weightlab/actions.py`.

Every claim below is marked **verified** (read in the named file or page on 2026-11-14/15) or
**inferred**. Nothing about Qwen3.5 is stated from memory.

## Short version

- **Qwen3.5 ships no computer-use tool.** Its files hold a generic tool-calling chat template and
  nothing else about actions (verified). Its model card reports computer-use scores (OSWorld-Verified
  41.8 for the 9B) without naming the harness (verified).
- **The Qwen family does have one schema, used unchanged since Qwen2.5-VL: a function called
  `computer_use`** with an `action` argument (`left_click`, `left_click_drag`, `type`, `key`, `scroll`,
  `wait`, `terminate`, ...) and the arguments `coordinate`, `keys`, `text`, `pixels`, `time`, `status`
  (verified in four Qwen sources). The Qwen team's 2026 agent writes these calls in exactly the
  `<function=...><parameter=...>` syntax of the Qwen3.5 chat template (verified).
- **That Qwen3.5-9B was trained on this schema is an inference**, not a published fact. It rests on:
  same team, same tool in every family release before and after, the card's OSWorld score, and the
  matching call syntax.
- **We adopt `computer_use`** with the family's action names, argument names and coordinate grid, and
  **one addition**: `left_click_drag` may carry `start_coordinate`, so a drag is one call with both ends.
  In the family schema a drag is two steps (`mouse_move` to the start, then `left_click_drag` to the
  end). A call without `start_coordinate` keeps the family meaning, so the family form stays valid.
- Coordinates are integers on the family's 1000 x 1000 screen: `round(1000 * x / width)`, kept to
  0-999. This is the number the lab already writes for pointing.

## What the parent family uses

### Shipped with Qwen3.5 (verified)

| Fact | Source |
|---|---|
| The model folder holds `chat_template.jinja`, configs, tokenizer and weights. No tool definitions, no cookbook, no mention of `computer_use` in any text file | Spark: `~/bonsai/hf/Qwen3.5-9B/` (listing and `grep`); same file list at https://huggingface.co/Qwen/Qwen3.5-9B/tree/main |
| The chat template lists tools as JSON lines inside `<tools>` and asks for calls as `<tool_call>` / `<function=name>` / `<parameter=key>` value `</parameter>` / `</function>` / `</tool_call>`. List and object arguments are written as JSON, other values as plain text | Spark: `~/bonsai/hf/Qwen3.5-9B/chat_template.jinja` (7,756 bytes, same size as the Hugging Face file) |
| Bonsai 2 uses the identical template | Spark: `cmp` of the template in `Qwen3.5-9B/` and `Bonsai-2-9B-dense/` |
| The model card has no computer-use section. "Agentic Usage" shows Qwen-Agent with an MCP file server only | https://huggingface.co/Qwen/Qwen3.5-9B (README.md) |
| The card reports, under "Visual Agent": ScreenSpot Pro 65.2, OSWorld-Verified 41.8, AndroidWorld 57.8 for Qwen3.5-9B (60.3, 35.6, 58.6 for the 4B). The harness is not described | same README |
| There is no Qwen3.5 repository or cookbook under github.com/QwenLM (repositories listed 2026-11-14). The newest Qwen cookbook with computer use is the Qwen3-VL one | https://github.com/QwenLM |

### The family's `computer_use` tool (verified)

Four sources from the Qwen team define the same function. Action names and argument names are identical
in all four; they differ in call syntax and in small additions.

| Source | Date | Call syntax | Coordinates | Notes |
|---|---|---|---|---|
| Qwen2.5-VL cookbook, [`cookbooks/computer_use.ipynb`](https://github.com/QwenLM/Qwen3-VL/blob/d08310cb51/cookbooks/computer_use.ipynb) and [`utils/agent_function_call.py`](https://github.com/QwenLM/Qwen3-VL/blob/d08310cb51/cookbooks/utils/agent_function_call.py) | 2025-01-27 | JSON inside `<tool_call>`: `{"name": "computer_use", "arguments": {...}}` | Pixels of the resized image the model saw (`display_width_px` = resized width) | 11 actions |
| Qwen3-VL cookbook, [same files on `main`](https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/utils/agent_function_call.py) | 2025-09-23 | Same JSON form | 1000 x 1000 grid ("The screen's resolution is 1000x1000"; the notebook divides by 1000) | Adds `triple_click`, `hscroll`, `answer`: 14 actions |
| Alibaba Model Studio, [GUI-Plus](https://help.aliyun.com/en/model-studio/gui-automation), system prompt for `gui-plus-2026-02-26` | page read 2026-11-14 | Same JSON form, preceded by a line `Action: ...` | 1000 x 1000 grid, "normalized coordinate system" | Adds `interact` |
| OSWorld, [`mm_agents/qwen/`](https://github.com/xlang-ai/OSWorld/tree/main/mm_agents/qwen) (`prompts.py`, `actions.py`, `parser.py`, `images.py`), added by a Qwen author, cites the Qwen-CUA paper ([arXiv 2608.02352](https://arxiv.org/abs/2608.02352)) | 2026-06-10 | **The Qwen3.5 template syntax**: `<tool_call><function=computer_use><parameter=action>...`. Its system prompt repeats the template's tool section word for word. Preceded by a line `Action: ...` | Default "relative": 1000 x 1000 in the prompt, harness multiplies by `width / 999` | Internal variant adds `key_down`, `key_up`, `left_mouse_down`, `left_mouse_up`, `screenshot`, `call_user` |

The Qwen3-VL definition, which the others repeat:

| Action | Arguments | Meaning |
|---|---|---|
| `left_click`, `right_click`, `middle_click`, `double_click`, `triple_click` | `coordinate: [x, y]` | Click at the point |
| `mouse_move` | `coordinate` | Move the pointer |
| `left_click_drag` | `coordinate` | "Click and drag the cursor to a specified (x, y)": from the current pointer position to this point |
| `type` | `text` | Type the text. The OSWorld harness presses Enter for every newline in it |
| `key` | `keys: [..]` | Press the keys in order, release in reverse order (a shortcut) |
| `scroll`, `hscroll` | `pixels` | Scroll; positive is up. The harnesses pass the number straight to `pyautogui.scroll` |
| `wait` | `time` | Wait that many seconds |
| `terminate` | `status`: `success` or `failure` | End the task |
| `answer` | `text` | Answer a question |

The names and the description text come from Anthropic's first computer-use demo (October 2024), in
which `left_click_drag` also took one point and dragged from the current position
([`computer.py` at the first commit](https://github.com/anthropics/claude-quickstarts/blob/2539a189d52d19f681f86eb4f168dabebb9829d9/computer-use-demo/computer_use_demo/tools/computer.py), verified).

### What is inferred, and how to settle it

- **Inferred: Qwen3.5-9B knows `computer_use`.** No source says what Qwen3.5 was trained or evaluated
  with. Supporting facts, all verified above: every Qwen release with a published GUI recipe before it
  (Qwen2.5-VL, Qwen3-VL) and after it (the 2026 OSWorld agent) uses this function; the card reports an
  OSWorld-Verified score; the 2026 agent writes the calls in the Qwen3.5 template syntax.
- **Inferred: `gui-plus-2026-02-26` is of the Qwen3.5 generation.** It is dated one day before the
  Qwen3.5-9B repository was created (2026-02-27, Hugging Face API), has the same 262,144-token context
  and the same thinking / non-thinking switch. Its page does not name its base model.
- **Check that settles it (not run):** give the parent
  (`bench/models.py`, key `qwen35-9b`) the tool definition below plus a screenshot and an instruction,
  20 cases. If it answers with well-formed `left_click` calls whose points land in the box when read on
  the 1000 grid, the schema is known to the parent. The same run on Bonsai shows what the ternary
  conversion kept.

### UI-Venus-2, our teacher (verified)

UI-Venus-2-9B is a Qwen3.5-9B fine-tune and does **not** use `computer_use`. Its reference prompt
([`models/computer/computer_example.py`](https://github.com/inclusionAI/UI-Venus/blob/UI-Venus-2/models/computer/computer_example.py))
asks for `<think>...</think><action>...</action>` with Python-style calls: `Click(box=(x, y))`,
`DoubleClick`, `TripleClick`, `RightClick`, `MiddleClick`, `Hover`, `Drag(end=(x2, y2), start=(x1, y1))`
(start optional), `Swipe(amount, axis)`, `Type(content)`, `Hotkey(keys, repeat)`, `KeyDown`, `KeyUp`,
`MouseDown`, `MouseUp`, `Sequence`, `Wait()`, `CallUser`, `Finished`. Coordinates 0-999. If its
trajectories are ever used as labels they need a converter to our schema; the mapping is one to one for
every action we use, including drag.

## Other harnesses

| Harness | Tool and call form | Actions | Arguments | Coordinates | Source (verified) |
|---|---|---|---|---|---|
| **Anthropic**, current | Toolset `computer_toolset_20260801`; each action is its own tool. Earlier versions (`computer_20251124`, `computer_20250124`): one tool `computer` with an `action` field, same names | `screenshot`, `zoom`, `left_click`, `right_click`, `middle_click`, `double_click`, `triple_click`, `left_click_drag`, `mouse_move`, `left_mouse_down`, `left_mouse_up`, `cursor_position`, `scroll`, `type`, `key`, `hold_key`, `wait` | `coordinate: [x, y]`; `start_coordinate`; `text` (typed string, key combination such as `ctrl+s`, or modifiers held during a click); `scroll_direction`, `scroll_amount`; `repeat`; `duration`; `region` | Pixels of the screenshot the application returned | https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool |
| **OpenAI** | Tool `{"type": "computer"}`; the model returns a `computer_call` with an ordered `actions` array | `click`, `double_click`, `drag`, `move`, `scroll`, `keypress`, `type`, `wait`, `screenshot` | `x`, `y`; `button`; `path` (list of `{x, y}`); `keys` (list); `scroll_x`, `scroll_y`; `text` | Pixels of the screenshot ("if you downscale a screenshot, map the model's coordinates back") | https://developers.openai.com/api/docs/guides/tools-computer-use and [`response_computer_tool_call.py`](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/response_computer_tool_call.py) |
| **UI-TARS** 1.5 | Plain text `Thought: ...` / `Action: ...`, one Python-style call | `click`, `left_double`, `right_single`, `drag`, `hotkey`, `type`, `scroll`, `wait`, `finished` | `point='<point>x y</point>'`; `start_point`, `end_point`; `key='ctrl c'`; `content` (a trailing `\n` submits); `direction` | Pixels of the resized image for the Qwen2.5-VL-based models; the older Qwen2-VL-based ones used a 1000 grid | [`codes/ui_tars/prompt.py`](https://github.com/bytedance/UI-TARS/blob/main/codes/ui_tars/prompt.py), [`action_parser.py`](https://github.com/bytedance/UI-TARS/blob/main/codes/ui_tars/action_parser.py), README |
| **Qwen family** | Function `computer_use`, see above | 14, see above | `action`, `coordinate`, `keys`, `text`, `pixels`, `time`, `status` | 1000 x 1000 grid since Qwen3-VL | see above |
| **AgentNet / OpenCUA** | Python code, one or more lines per step | `pyautogui.click`, `doubleClick`, `rightClick`, `middleClick`, `moveTo`, `dragTo`, `scroll`, `hscroll`, `write`, `press`, `hotkey`; `computer.tripleClick`, `computer.terminate` (the OpenCUA prompt also lists `computer.wait`) | `x=`, `y=`; `button='left'`; a number of scroll clicks; `message=`; a key name and `presses=`; a list of keys; `status='success'` or `'fail'` | Dataset: normalised 0-1 (measured: all 84,576 coordinate calls of the macOS part). OpenCUA models answer in pixels of the resized image | [dataset card](https://huggingface.co/datasets/xlangai/AgentNet), [OpenCUA-7B card](https://huggingface.co/xlangai/OpenCUA-7B), [`mm_agents/opencua/prompts.py`](https://github.com/xlang-ai/OSWorld/blob/main/mm_agents/opencua/prompts.py); function names and arguments measured on the 97,435 macOS steps on the Spark |

## How each one expresses a drag

| Harness | Drag | Steps |
|---|---|---|
| Anthropic, current | `left_click_drag` with `start_coordinate` and `coordinate`: press at the start, drag, release. Separate `left_mouse_down` / `mouse_move` / `left_mouse_up` exist for drags this cannot express | One action, two points |
| Anthropic, October 2024 demo | `left_click_drag` with `coordinate` only, from the current pointer position | Two (move, then drag) |
| OpenAI | `drag` with `path`, a list of at least two points | One action, a path |
| UI-TARS | `drag(start_point, end_point)` | One action, two points |
| Qwen `computer_use` | `left_click_drag` with `coordinate` only, from the current pointer position. The 2026 internal variant also has `left_mouse_down` / `left_mouse_up` | Two (`mouse_move`, then `left_click_drag`) |
| UI-Venus-2 | `Drag(end, start)`, start optional; also `MouseDown` / `MouseUp` | One action, two points |
| AgentNet | `pyautogui.moveTo(x1, y1)` then `pyautogui.dragTo(x2, y2, button='left')` in one step (4,019 macOS steps, always the left button) | One step, two points |

## The schema for this project

Tool name `computer_use`, written with the Qwen3.5 chat template. The definition is
`weightlab/actions.py: COMPUTER_USE_TOOL`.

| Action | Arguments | The harness does |
|---|---|---|
| `left_click`, `double_click`, `right_click`, `triple_click`, `middle_click` | `coordinate: [x, y]` | Move there and click |
| `left_click_drag` | `start_coordinate: [x, y]` (ours, optional), `coordinate: [x, y]` | Move to the start, press, move to `coordinate`, release. Without `start_coordinate` it starts at the current pointer position |
| `mouse_move` | `coordinate` | Move the pointer |
| `type` | `text` | Type the text. A newline at the end means: then press Return |
| `key` | `keys: ["cmd", "s"]` | Press in order, release in reverse order |
| `scroll`, `hscroll` | `coordinate` (where), `pixels` (scroll-wheel clicks: positive up, negative down; for `hscroll` positive right) | Move there and scroll |
| `wait` | `time` (seconds) | Wait, then take the next screenshot |
| `terminate` | `status`: `success` or `failure` | Stop the loop. This is "done" |
| `answer` | `text` | Say the text to the user |

A click and a drag as the model writes them:

```
<tool_call>
<function=computer_use>
<parameter=action>
left_click
</parameter>
<parameter=coordinate>
[537, 336]
</parameter>
</function>
</tool_call>
```

```
<tool_call>
<function=computer_use>
<parameter=action>
left_click_drag
</parameter>
<parameter=start_coordinate>
[212, 340]
</parameter>
<parameter=coordinate>
[640, 340]
</parameter>
</function>
</tool_call>
```

**Coordinates.** Integers on the 1000 x 1000 screen of the family: `round(1000 * x / width)` and
`round(1000 * y / height)`, kept to 0-999, where width and height are those of the screenshot. The
harness turns them back with `x * width / 1000`. This is the same number `weightlab/chat.py` and
`core.py` already write for pointing (`box1000`, `target`); the lab writes it as a plain integer without
leading zeros, and so do we. Qwen's own harnesses disagree on the last step (the cookbook divides by
1000, the OSWorld agents by 999); the difference is at most 0.1 % of the screen, 1.3 px at 1,280.

**Drag: the one departure from the family.** The family schema does say something different from what
we wanted (one point, two steps), so by the rule "follow the family unless..." the two-step form was the
default candidate. We still chose one call with both ends, for these reasons:

1. It is an addition, not a change. Every family-style call means the same under our schema, and the
   harness handles both. `actions.family_drag(case)` splits a drag case into the family's two steps if we
   want to train that form instead.
2. The argument name and meaning (`start_coordinate` plus `coordinate` on `left_click_drag`) are those of
   the current Anthropic tool, from which the family copied its names, and UI-Venus-2 and UI-TARS also
   put both ends in one action.
3. AgentNet records a drag as one step with one screenshot. The family form needs a second screenshot
   with the pointer at the start, which the data does not have.
4. Each step costs a full screenshot on the device.
5. That the parent knows the family form is itself only inferred.

**The prompt.** System message: one of the lab's short lines (`chat.SYSTEMS`); the template adds the tool
list. User message: the screenshot, then the Qwen agents' wording:

```
Please generate the next move according to the UI screenshot, instruction and previous actions.

Instruction: <goal>

Previous actions:
Step 1: left_click [412, 388]
Step 2: type "quarterly report\n"
```

The history lines are produced from the executed calls by `actions.describe()`, which the harness must
also use, so training and use see the same text. The last eight steps are shown.

**Differences from the Qwen harnesses, all deliberate:**

- No `Action: ...` sentence before the call. The Qwen agents ask for one and reuse it as the history
  line. We emit the call only, as the lab does for `point`, which saves about 25 generated tokens a step.
  If multi-step behaviour turns out to need it, AgentNet has such a sentence for every step
  (`meta.sentence` in the cases).
- `type` with a final newline presses Return. The Qwen parser strips the value, so there it takes a
  second `key` step. Ours removes exactly the one newline the template adds
  (`actions.parse_answer`), which keeps "type and submit" one action, the way AgentNet records it
  (2,630 macOS steps).
- The tool description says "macOS desktop" where the family text says there is no applications menu and
  programs are started from desktop icons (true of their Linux test machines, not of a Mac). The
  other sentences are the family's.
- `scroll` takes `coordinate`. The family lists the argument without restricting it; its harnesses
  scroll at the current pointer position.
- The lines for `triple_click` and `hscroll` drop the family's remarks "simulated as double-click" and
  "mapped to regular scroll", which describe their test harness. Ours does the real thing.

**Cost in tokens** (measured with the Bonsai tokenizer on 122 cases). The tool list adds 965 tokens to
the prompt; `point` with three other tools adds 511. A whole prompt is about 2,100 tokens, half of it the
screenshot. The system part never changes, so a runtime can keep it cached between steps. An answer is 49
tokens for a click, 62 for a scroll, 70 for a drag, 38 to 47 for typing: the template's tags cost most of
it.

## Scoring

`actions.score_answer(case, text)`. AgentNet records where a person clicked, not the element's box, so a
point counts when it lies within 24 px of the recorded point, measured on the recorded screenshot.

| Action | Correct when |
|---|---|
| Clicks, `mouse_move` | Same action name, point within 24 px |
| `left_click_drag` | Same name, start within 24 px of the recorded start and end within 24 px of the recorded end |
| `type` | Same name, text identical (including a final newline) |
| `key` | Same name, same keys after normalising names (`command` = `cmd`, `return` = `enter`, ...); modifiers in any order |
| `scroll`, `hscroll` | Same name, same direction |
| `terminate` | Same name, same status |
| `wait`, `answer` | Same name |

## Cases from AgentNet

`weightlab/actions.py convert` turns AgentNet's macOS trajectories into cases; the set marks the platform
(`system` = `Darwin` in `meta_data_merged.jsonl`). Result on the Spark, 2026-11-15:
`~/bonsai/data/mac/agentnet/cases_actions.jsonl` and `stats_actions.json`.

- 5,168 trajectories, 97,435 steps, **79,173 cases**: 71,417 for training from 4,651 trajectories and
  7,756 reserved from 498.
- One case per step that is exactly one action. The goal is the trajectory's human-written
  `instruction` (median 36 words). The history is one line per earlier step, including steps that gave
  no case; the last 20 are stored, the last 8 shown.
- Steps without a case: 13,379 flagged incorrect and 2,256 flagged redundant by the dataset, 2,251 with
  more than one action (for example three presses of Backspace, or typing in two fields), 164 drags
  shorter than 24 px, 114 points on the screen edge, 49 in trajectories with no screenshot on disk, 49
  others.
- A trajectory is reserved when `sha1(task_id) % 10 == 0`. That is a fixed rule instead of a seed, chosen
  because it contains the 89 test sessions of the pointing set (`% 50 == 0`). 499 of 5,168 trajectories
  satisfy it (9.7 %).

| Action | Train | Reserved | Screenshot on the Spark |
|---|---|---|---|
| `left_click` | 52,324 | 5,738 | Yes |
| `double_click` | 1,728 | 189 | Yes |
| `right_click` | 834 | 87 | Yes |
| `triple_click` | 52 | 8 | Yes |
| `scroll` (4,072 down, 862 up) | 4,468 | 466 | Yes |
| `hscroll` | 20 | 1 | Yes |
| `middle_click`, `mouse_move` | 1 each | 0 | Yes |
| `left_click_drag` | 2,185 | 193 | Yes |
| `type` (1,999 end with Return) | 4,461 | 469 | Yes |
| `key` (67 different shortcuts; `cmd+v`, `cmd+c`, `enter` lead) | 2,092 | 245 | Yes |
| `terminate` (3,542 success, 69 failure) | 3,251 | 360 | Yes |
| `wait`, `answer` | 0 | 0 | AgentNet's macOS part has none |

**Screenshots.** The first download took only the screenshots of pointer steps
([MAC_DATA.md](MAC_DATA.md)). The 13,256 screenshots of the drag, type, key and terminate cases
(4.87 GB) were fetched afterwards from the list that `actions.py need` writes
(`~/bonsai/data/mac/raw/agentnet_actions_fetch/`). Checked 2026-11-15: all 79,173 cases have their
screenshot on the Spark. `actions.load_cases` skips a case whose screenshot is missing.

**The reserved part and pointing training.** 408 of the reserved trajectories are training sessions of
the pointing set, so their click screenshots are in the pool `mac:agentnet:train`. The current mix draws
1,500 of that pool's 60,082 cases; 129 of them come from reserved trajectories, and 119 reserved action
cases sit on exactly those screenshots. The 89 trajectories that are test sessions of both sets were
never in any training pool: 1,364 cases, `actions.load_cases(path, "reserved", never_trained=True)`.
Quote that part, or keep reserved trajectories out of future pointing mixes.

**Not checked.** No drag, type, key or terminate case has been looked at on its screenshot. The click cases carry the same points as the pointing set
(59,042 compared, none differ), which was checked by eye when it was made. No guard against
near-identical screenshots across the split was applied, as it was for the pointing set.

## Using the cases

```python
from weightlab import actions, chat, mixes
train = mixes.action_samples(lab)             # 3,000 chat samples, shares per action in actions.DEFAULT_SHARE
tuner.train(other_samples + train, ...)       # TaskTuner takes them next to point_call and tool_call samples
test = actions.samples(lab, "reserved", n=300, never_trained=True)
chat.score(lab, lab.B, test)                  # teacher-forced: tf_exact, nll_per_token
answers = [actions.generate(lab, lab.B, s)[0] for s in test]
actions.score_answers([s["case"] for s in test], answers)
```

A sample has `kind` `"action_call"` and carries its screenshot the way `point_call` samples do. The
tool-call branch of `chat.supervise` builds text-only messages, so `actions.py` has its own `supervise`
with the same return value, and `actions.install()` makes `chat.supervise` hand action samples to it in
the running process. `action_case()` calls `install()` itself. A script that reloads `chat` after
building its samples must call `actions.install()` again; if it does not, `chat.supervise` stops with
`KeyError: 'messages'` instead of training without the screenshot. Coordinate digits are trained like
pointing digits: every digit that keeps the point within 1.2 % of the image width of the recorded point
counts (four times that for where to scroll); every other token is exact.

Checked on the Spark's CPU with the real processor and no model: for 122 cases over all twelve action
types the appended answer decodes to the rendered call, every coordinate is tokenised digit by digit,
and the chat template renders the same call from structured arguments. `tests/test_actions.py` covers
rendering, parsing and scoring without a GPU.

## Orchestrator steps

For tasks of many steps ("check my email") the plan is two models: a 9B Bonsai that says in plain words
what to do next, and a separate pointer that finds the target. The orchestrator therefore answers with
ONE call of a second tool, `next_step`, which has no coordinates. Code: the last part of
`weightlab/actions.py`. Cases: `~/bonsai/data/mac/agentnet/cases_steps.jsonl` and `stats_steps.json`.

| Argument | For | Meaning |
|---|---|---|
| `action` | always | `click`, `double_click`, `right_click`, `drag`, `type`, `key`, `scroll`, `done` |
| `target` | clicks and `drag`; optional for `type` and `scroll` | The element to act on, in plain words. For `drag`, where it starts |
| `target_end` | `drag` | Where the drag ends |
| `text` | `type`, `done` | The text to type (a final newline presses Return); for `done`, one sentence for the user |
| `keys` | `key` | The keys to press together |
| `direction` | `scroll` | `up`, `down`, `left`, `right` |

The tool description tells the model to describe the target plainly enough that someone could point at
it, and not to give coordinates. Three answers as rendered from real cases:

```
<tool_call>
<function=next_step>
<parameter=action>
click
</parameter>
<parameter=target>
the "Done" button
</parameter>
</function>
</tool_call>
```

```
<tool_call>
<function=next_step>
<parameter=action>
drag
</parameter>
<parameter=target>
the quality slider
</parameter>
<parameter=target_end>
the "Best" position on the right side of the slider bar
</parameter>
</function>
</tool_call>
```

```
<tool_call>
<function=next_step>
<parameter=action>
done
</parameter>
<parameter=text>
All requirements have been completed.
</parameter>
</function>
</tool_call>
```

**Where the words come from.** AgentNet gives every step four texts written by a model from the
recording (measured on the macOS part; one step of 97,435 has none):

| Field | Holds | Median length |
|---|---|---|
| `observation` | What is on the screen | 170 words |
| `thought` | Reasoning about progress and the next move | 300 words |
| `action` | The step as one instruction: "Click the ... to ..." | 18 words |
| `reflection` | What the step did, judged from the next screenshot | 130 words |

Each trajectory has `instruction` (written by a person, 33 words), `natural_language_task` (44),
`actual_task` (64) and `reason` (a judge's summary, 93). The last step is always
`computer.terminate(status=...)`; there is no answer to the user anywhere in the data.

The target is the `action` sentence without its verb and without its purpose: "Click the globe icon next
to the first citation to access formatting options" gives `the globe icon next to the first citation`.
Text, keys and scroll direction come from the recording, not from the sentence. A `done` step takes its
sentence from the reason the description gives ("... as both histories have been deleted"), when it gives
one; that is a statement that the task is finished, not an answer to a question. The history is the last
four earlier steps in plain words, built by `actions.describe_step()` from each step itself, so the
harness can build the same lines from the orchestrator's own answers.

**A short thought, optional.** AgentNet's `thought` is long: a check of the last action, a list of
progress so far, then the reasoning. `actions.short_thought()` keeps one sentence of it, at most 25
words: the one that best says what on the screen matters and why the step follows, with its preamble
("I can see that", "I need to", "The next logical step would be to") cut. 70,508 of the 76,831 cases have
one (63,612 train, 6,896 reserved; median 17 words), stored as `thought`. `step_case(case, thought=True)`
switches thinking on in the prompt and writes the thought, the closing tag, then the call. The default
leaves the thought out and switches thinking off, as everywhere else in the lab. Three of them:

- `type`: The search field is currently empty and active, so typing "beethovan" is the natural progression.
- `type`: The title field is currently active and awaiting input, which is exactly what we need to proceed with our task.
- `done`: Each filter was applied correctly, and the result shows only the entries matching all three criteria.

The sentence is chosen by rules, not rewritten. Sentences about the last action, list items, coordinates,
addresses, links, long numbers, possessive names and capitalised names that the task's instruction does
not contain are not used; a name inside a quoted label can remain. Of 12 looked at under the final
rules, 8 said something about the screen or the reason; the others named the element without a verb or
repeated the step with its purpose. An answer with a thought is about 71 tokens instead of about 45.

**Cases** (same steps, filters and split as the action cases; all screenshots on the Spark):

| Action | Train | Reserved | Notes |
|---|---|---|---|
| `click` | 52,228 | 5,724 | |
| `double_click` | 1,727 | 189 | |
| `right_click` | 833 | 87 | |
| `drag` | 890 | 73 | Both ends described |
| `type` | 4,461 | 469 | 3,970 name the field |
| `key` | 2,092 | 245 | |
| `scroll` | 3,800 | 402 | 3,138 name the area |
| `done` | 3,251 | 360 | 3,208 with a sentence |
| **Total** | **69,282** | **7,549** | 76,831 cases; 1,325 reserved cases were never in pointing training |

Left out because of the description: 2,419 drags whose sentence does not name both ends as things
("drag the chart upward to reposition it"), 1,074 scrolls whose sentence gives another direction than the
recording, 175 sentences that start with another verb than the action, 60 that name no target, 107
triple clicks, middle clicks and pointer moves. On the scrolls: the page movement between the
screenshots before and after could be measured for 21 such steps, and all 21 agree with the recording,
so the recording is kept as the truth and those sentences are not used.

Each case keeps the recorded point as `point` (and `point_end` for a drag) in pixels of the screenshot.
`actions.step_points(case)` returns the pairs (description, point) a pointer has to find: 65,852 in all.

**Scoring** (`actions.score_step`). The action must be right; typed text and keys exact; scroll direction
right. The target is judged by the content words it shares with the dataset's description (F1 of the two
word sets, at least 0.5). This is rough: it knows no synonyms, so "the gear icon" and "the settings
button" share nothing, and it cannot tell whether a different but correct description would work. The
better test is to give the orchestrator's description to the pointer and score the point against
`step_points(case)`.

```python
train = mixes.step_samples(lab)               # 3,000 chat samples (kind "step_call"), off by default
train = mixes.step_samples(lab, thought=True) # the same with the short thought; only cases that have one
test = actions.step_samples(lab, "reserved", n=300, never_trained=True)
answers = [chat.generate(lab, lab.B, s, max_new_tokens=128)[0] for s in test]
actions.score_steps([s["case"] for s in test], answers)
```

Measured with the Bonsai tokenizer on 80 cases: the tool list adds 524 tokens, a prompt is about 1,600
tokens, an answer 40 to 60 tokens for a click and up to 89 for a drag. The descriptions were written by
a model, not by a person, and nobody here has compared them with their screenshots; the pointing set
made from the same sentences had 12 of 14 right when it was checked by eye.

## Sources read

Spark, read only: `~/bonsai/hf/Qwen3.5-9B/`, `~/bonsai/hf/Bonsai-2-9B-dense/`,
`~/bonsai/hf/UI-Venus-2-9B/`, `~/bonsai/hf/Ternary-Bonsai-2-9B-mlx-2bit/README.md`,
`~/bonsai/data/mac/raw/agentnet/`.

Web, fetched 2026-11-14 and 2026-11-15: the pages linked above; also
https://github.com/xlang-ai/OSWorld/blob/main/mm_agents/qwen3vl_agent.py (2025-09-15, JSON call form,
"relative: scale from 0..999 grid"), https://github.com/QwenLM/Qwen-Agent (no computer-use tool in the
package; `examples/assistant_qwen3.5.py` uses MCP), https://github.com/QwenLM/open-computer-use (an MCP
desktop driver for Qwen Code, not a model action schema), and
https://github.com/anthropics/claude-quickstarts/blob/main/computer-use-demo/computer_use_demo/tools/computer.py.
The Qwen3.5 blog page (https://qwen.ai/blog?id=qwen3.5) is rendered by script and could not be read.
