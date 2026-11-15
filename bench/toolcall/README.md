# Tool-calling benchmark (procedural, seeded)

Generates tool-calling test cases from a random seed and scores a model on them.
The expected answer of every case is known exactly, because the intended tool
call and its argument values are decided first and the user request is then
written from templates that state those values. No language model is used to
build cases. A new seed gives a new set of cases; the `dev`, `test` and `train`
splits draw from disjoint vocabularies, so training data made with this
generator can never contain a test tool or a test phrasing.

Python 3.9+ and the standard library only.

## Use

```bash
# 1. generate (same seed and arguments -> byte-identical file)
python3 generate.py --seed 20261114 --n 400 --split dev --out runs/dev_20261114

# 2. evaluate a model behind an OpenAI-compatible endpoint
python3 evaluate.py --cases runs/dev_20261114 --base-url http://127.0.0.1:8121/v1 --label bonsai2-9b

# 3. look at what went wrong
python3 failures.py --cases runs/dev_20261114 --label bonsai2-9b --category e_missing --limit 20

# 4. check the generator and the scorer (no model, about 3 s)
python3 selftest.py          # in-process checks
python3 selftest.py --http   # also sends the oracle through evaluate.py's HTTP client (localhost only)
```

`evaluate.py` writes `runs/.../results_<label>.jsonl` (one line per case, appended
as cases finish) and `summary_<label>.json`, and prints overall accuracy and
accuracy per category. Running the same command again resumes: finished cases
are skipped. Each result stores a fingerprint of its case, so if `cases.jsonl`
is regenerated after a generator change, only the cases that actually changed
are run again. Options: `--limit N`, `--concurrency 4`, `--max-tokens 512`,
`--detail` (accuracy per sub-type inside each category), `--retry-errors`,
`--extra-body '{"key": value}'`, `--model NAME`.

Each request sends `temperature: 0`, `max_tokens: 512`,
`parallel_tool_calls: true` and `chat_template_kwargs: {"enable_thinking": false}`.

Serving a model with llama.cpp (one server at a time, port 8121):

```bash
NEED_GB=5 ./serve_llama.sh ~/bonsai/models/Ternary-Bonsai-2-9B-PTQ1_0.gguf   # waits for /health, writes server.pid
kill "$(cat server.pid)"                                                     # stop it as soon as the run is done
```

On the Spark memory is one pool for CPU and GPU. `serve_llama.sh` refuses
to start when `~/bonsai/queue/mem_ok.sh <NEED_GB>` says no (about 5 GB for a
Bonsai 9B, 12 GB for a 9B Q8, the default). Run one server at a time.

which runs

```bash
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
llama-server -m MODEL.gguf --host 127.0.0.1 --port 8121 -ngl 99 -fa on -c 32768 -np 4 --jinja
```

## Categories

Cases cycle through the eight categories, so each has exactly n/8 cases.

| Tag | What is tested | Correct behaviour |
|---|---|---|
| `a_single` | one tool (plus 0 to 2 unrelated ones) | one call |
| `b_selection` | the right tool among 6 to 12 distractors: the sibling tools of the same domain (create / reschedule / cancel ...), unrelated tools, and in 60% of cases a "twin" with the same parameters whose description says it is deprecated or a dry run | one call to the real tool |
| `c_parallel` | 2 to 4 independent actions in one message (60% two, 30% three, 10% four), in 40% of cases the same tool several times | all calls in one turn, any order |
| `d_multistep` | 2 to 4 dependent steps; a later call needs an id returned by an earlier one. About half of the intermediate lookups return a list of 3 or 4 candidates, and the request says which one is meant ("the most recent order", "the primary supplier") | the evaluator plays the stored tool results back; every step must be right, and no call may follow the last step |
| `e_missing` | a required value that cannot be guessed is left out | ask, call nothing |
| `f_irrelevant` | no offered tool can do the request: only unrelated tools are offered (35%), or sibling tools of the right domain are offered but the one that fits is missing (35%), or the message is small talk (30%) | call nothing |
| `g_typing` | one argument needs conversion: words to enum value, number written in words, relative date (with "today is ..." in the system prompt), 12-hour time, boolean, array, nested object | one call |
| `h_computer` | the screen is a numbered list of elements; tools are `click`, `type_text`, `press_key`, `scroll`, `done` | the single next action |

Every request is wrapped in one of six phrasing styles: `terse`, `polite`,
`indirect`, `chatter` (irrelevant small talk around the request), `reordered`
(values in a different order than the schema) and `correction` ("at 15:30,
actually make it 16:30"). The style is recorded in `meta.style`.

The system prompt states the policy the cases are scored against: call tools
when one fits, make independent calls together, wait for results that later
calls need, ask instead of guessing a missing required value, do not fill
optional arguments the user did not mention, and call nothing when no tool fits.

## Case format (one JSON object per line of `cases.jsonl`)

| Field | Content |
|---|---|
| `id` | `<split>-<seed>-<index>` |
| `category`, `split` | as above |
| `tools` | OpenAI tool format |
| `messages` | system and user message |
| `expected` | `{"calls": [...]}` or `{"steps": [{"calls": [...], "tool_results": [...]}, ...]}` or `{"no_call": true}` |
| `arg_match` | per tool and parameter: `{"mode": "contains"}` (free text), `{"mode": "any"}`, `{"unordered": true}` (arrays), `{"optional": true, "default": X}` |
| `meta` | domain, intent, phrasing style, seed, index, the case's "today", naming style, and category-specific notes (trap type, missing parameter, number of steps) |

## Scoring

- The function name must match exactly.
- Arguments arrive as a JSON string and are parsed; nothing is string-matched.
- Values are compared after normalisation driven by the tool's JSON schema:
  integers and numbers may be numeric strings, booleans may be `"true"` /
  `"false"`, enum values may differ in letter case, strings may carry stray
  whitespace, digits-only strings may arrive as numbers. Everything else must be
  equal, including letter case of ordinary strings and the `HH:MM` /
  `YYYY-MM-DD` formats.
- Free-text arguments marked `contains` pass when the expected words appear in
  order in the actual value (case and punctuation ignored).
- Arrays are compared as multisets unless the case marks them ordered.
- An optional parameter the user did not mention must be absent, null, empty,
  or equal to the default declared in the schema. An optional parameter whose
  requested value equals the declared default may be left out. Unknown
  parameters fail.
- Independent calls may come in any order. An extra or a missing call fails.
  For "no call" cases any tool call fails.
- Multi-step: at each step the calls must match the stored step; a call after
  the last step fails.
- In `h_computer`, `scroll.amount` and `done.summary` accept any positive number
  / non-empty text, because the screen does not determine them.

## Rules that keep one answer correct

These are enforced by the generator or by how the domain files are written.

- Every value the expected call needs is stated in the request; values of one
  case never repeat (two people, two dates, two ids are always different).
- Within a domain no tool can serve a sibling tool's request. Unrelated
  distractors come only from domains that share no tag with the request's
  domain (tags group things like `time`, `money`, `comm`, `docs`).
- Clauses that could attach to the wrong noun when moved (booleans, "so that
  ...", natural-language enum clauses) always stay at the end, also in the
  `reordered` style. Id clauses name their entity ("with the event ID ...").
- An optional boolean always declares its default, so "whether or not they are
  open" and leaving the argument out cannot both be right unless the scorer
  accepts both (it does when the stated value equals the declared default).
- `e_missing` only leaves out values that cannot be filled in sensibly: no enum
  where calling the tool once per allowed value would answer the request
  ("check my leave balance"), no date where today is the natural reading
  ("show my calendar").
- `f_irrelevant` near-miss cases never use an intent listed in
  `NEAR_MISS_UNSAFE` (requests that a sibling tool could arguably approximate).
- List results in `d_multistep` have distinct values for the attribute the
  request selects on, and exactly one entry fits.
- `h_computer` screens are built so that one action is next: a form has exactly
  one empty field or none, a search box has no button (Enter submits it, as the
  system prompt says), forms are only submitted by their button, and a missing
  target is announced by a note that the page continues.

## How breadth is obtained

A domain is a list of hand-written *intents*. An intent lists alternative tool
names, descriptions and request verbs, and its *slots*; a slot lists
alternative parameter names, a value kind, clause templates, and whether it is
optional. For each case a concrete tool schema is drawn from that space: tool
name variant, snake_case or camelCase, description variant, parameter name
variants, which optional parameters exist, whether an optional parameter is
promoted to required, and which defaults are declared. Values come from seeded
generators (fictional people, companies, cities, addresses, dates, times,
amounts, ids, titles, file paths).

Current size (printed by `selftest.py`): 54 domains, 258 intents and 140
multi-step chain tools (398 hand-written base tool schemas), 18 screen
applications. 7,200 generated cases contained about 2,800 distinct tool names
and about 20,000 distinct tool schemas. 100,000 `train` cases take about 10
seconds to generate and about 310 MB on disk.

## Split partition (asserted in code on every run)

| What | Rule |
|---|---|
| Domains, intents, tool names, request verbs, multi-step chains | each domain file belongs to one split: `domains_dev.py` (12 domains), `domains_test.py` (12), `domains_train.py` (30) |
| Phrasing templates (style wrappers, small talk, correction connectors, joiners, system prompts, date lines, no-tool questions, screen task wordings) | position in the list modulo 4: 0 -> dev, 1 -> test, 2 and 3 -> train (`pools.part`) |
| Value pools (first names, surnames, company words, city names, title words, messages, ...) | same modulo-4 rule |
| Screen applications of `h_computer` | listed per split in `screens.py` |

`generate.assert_disjoint()` runs before any file is written and fails if two
splits share a domain, an intent, a tool name (in either naming style), a
request phrase, a phrasing template or a pool value.

Shared by design: the five `h_computer` tools (fixed by the task definition),
slot-level function words such as "on {date}" or "to {person}", enum values
(for example weekday names and currency codes), and the scenario types of
`h_computer`.

## Files

| File | Role |
|---|---|
| `generate.py` | case builders for the eight categories, CLI, disjointness assertion |
| `spec.py` | value kinds (date, time, enum, list, object, ...), slot / intent / domain / chain definitions |
| `domains_dev.py`, `domains_test.py`, `domains_train.py` | tool vocabularies and multi-step chains per split |
| `pools.py` | seeded value pools and the split partition rule |
| `phrasing.py` | style wrappers, small talk, system prompts |
| `screens.py` | screen applications and scenarios for `h_computer` |
| `scoring.py` | normalisation, call matching, multi-step playback, case validation |
| `evaluate.py` | runs a served model over a case file, resumable |
| `failures.py` | prints failed cases of a run next to what the model called |
| `serve_llama.sh` | starts llama-server for one GGUF file on port 8121 and waits until it is healthy |
| `selftest.py` | oracle = 100%, never-call baseline = share of no-call cases, 56k wrong answers all rejected |

## First results (2026-11-14)

`--split dev --seed 20261114 --n 400`, llama.cpp server, thinking off, temperature 0.
The evaluated cases and the per-case results are kept in `runs/dev_20261114/`.

| Category | Ternary Bonsai 2 9B (PTQ1_0) | Qwen3.5-9B (Q8_0) |
|---|---|---|
| `a_single` | 50/50 | 49/50 |
| `b_selection` | 50/50 | 48/50 |
| `c_parallel` | 45/50 | 50/50 |
| `d_multistep` | 43/50 | 47/50 |
| `e_missing` | 13/50 | 18/50 |
| `f_irrelevant` | 50/50 | 49/50 |
| `g_typing` | 45/50 | 49/50 |
| `h_computer` | 43/50 | 46/50 |
| **Overall** | **339/400 = 84.8%** | **356/400 = 89.0%** |

A model that never calls a tool scores 100/400 = 25.0%.

Twelve of these 400 cases used the correction connector ", or rather", which
has since been replaced by ", let me correct that:" in `phrasing.py` (inside a
question, "80 minutes, or rather 70?" can be read as a choice; Qwen failed 3 of
the 12 that way, Bonsai none). The table above is as run, with the old wording.
Without those 12 cases the scores are 328/388 = 84.5% and 347/388 = 89.4%.
Regenerating the set with the current code changes exactly these 12 cases, and
`evaluate.py` then re-runs only them.

## Known limits

- Requests are template text. They are grammatical and unambiguous but more
  regular than real user language.
- Tool results in `d_multistep` are small objects or lists of 3 or 4 entries
  and chains are linear; there are no error results or retries.
- `h_computer` uses a text list of elements, not screenshots, and asks for one
  action per case.
- Two tools that could both satisfy a request are never offered together, so
  the benchmark does not measure tie-breaking between equivalent tools. The
  rules behind this are hand-maintained: each domain is written so that no
  sibling tool can serve another sibling's request, unrelated distractors come
  only from domains that share no tag with the request's domain, and intents
  listed in `NEAR_MISS_UNSAFE` are never used for the "fitting tool is missing"
  variant of `f_irrelevant`.
- In `c_parallel` all independent calls must be made in the same turn, as the
  system prompt asks. A model that issues them one turn at a time fails.
- A model that asks a clarifying question where the case expects a call is
  scored as wrong, also when its question is reasonable.
