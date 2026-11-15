"""Hand-written phrasing templates. Each list is partitioned between the splits
with `pools.part` (index % 4: 0 -> dev, 1 -> test, 2/3 -> train), so a
template used for `test` never appears in `dev` or `train`.

`{req}` is the request as a lower-case imperative verb phrase ("schedule a
meeting called ..."), `{Req}` the same with a capital first letter. Every
template keeps the assistant as the one who acts, so any imperative fits.
"""
from pools import part

STYLES = ("terse", "polite", "indirect", "chatter", "reordered", "correction")

WRAPPERS = {
    "terse": [
        "{Req}.",
        "{Req}",
        "{Req}, thanks.",
        "Quick one: {req}.",
        "Task for you: {req}.",
        "{Req}. That's all.",
        "Need this done: {req}.",
        "{Req} asap.",
        "To do: {req}.",
        "Next up: {req}.",
        "{Req}. Nothing else.",
        "Right, {req}.",
    ],
    "polite": [
        "Could you please {req}? Thank you!",
        "Would you mind helping me out here? Please {req}.",
        "Hi! When you get a chance, please {req}. Thanks a lot.",
        "Hello, I'd be grateful if you could {req}.",
        "Please {req}. Much appreciated!",
        "Good morning! Could I ask you to {req}? Thanks in advance.",
        "If it's not too much trouble, please {req}.",
        "Hey there, would you be so kind as to {req}?",
        "Kindly {req}. Thank you very much.",
        "May I ask you to {req}? Cheers.",
        "Hi, hope you're well. Can you {req} for me, please?",
        "Thanks for your help so far. Could you now {req}?",
    ],
    "indirect": [
        "I need you to {req}.",
        "It would be great if you could {req}.",
        "I was hoping you could {req}.",
        "I'd like you to {req}.",
        "I was wondering whether you could {req}.",
        "It'd really help me if you would {req}.",
        "I don't suppose you could {req}?",
        "What I'm after is for you to {req}.",
        "I think the next thing is for you to {req}.",
        "Is there any chance you could {req}?",
        "My plan is to have you {req}.",
        "I've been meaning to ask you to {req}.",
    ],
    "chatter": [
        "{c1} Anyway, {req}.",
        "{c1} Oh, and before I forget: {req}. {c2}",
        "{Req}. {c1}",
        "{c1} {c2} Right, back to business: {req}.",
        "So, {req}. {c1} {c2}",
        "{c1} Where was I... ah yes, please {req}.",
        "{c1} Not that it matters. Can you {req}? {c2}",
        "Long day. {c1} Could you {req}? {c2}",
        "{c1} By the way, I need you to {req}.",
        "{c1} Enough about that. {Req}.",
        "Funny story: {c1} Anyway, on to the real thing: {req}. {c2}",
        "{c1} {Req}. {c2}",
    ],
    "reordered": [
        "{Req}, please.",
        "Here's what I need: {req}.",
        "Okay, so {req}.",
        "Please {req}, okay?",
        "One request: {req}.",
        "Go ahead and {req}.",
        "Can you {req}?",
        "I want you to {req}.",
    ],
    "correction": [
        "Please {req}.",
        "Can you {req}? Thanks.",
        "{Req}, if you would.",
        "Do me a favour and {req}.",
        "Would you {req}?",
        "I'd like to ask you to {req}.",
        "Please go ahead: {req}.",
        "Help me out and {req}.",
    ],
}

# irrelevant small talk; deliberately free of dates, times, names and numbers
CHATTER = [
    "My neighbour's dog has been barking all day.",
    "I spilled tea all over my sleeve earlier.",
    "The lift in my building is out of order again.",
    "I think I left my umbrella on the bus.",
    "My shoelace snapped on the way in.",
    "Someone parked a bright orange van outside my window.",
    "I still can't find my other glove.",
    "The vending machine ate my coins again.",
    "My cousin just adopted a very grumpy parrot.",
    "I had the strangest dream about a giant pineapple.",
    "The office plant is somehow still alive.",
    "I finally fixed the squeaky door at home.",
    "There was a pigeon inside the supermarket.",
    "My sandwich fell apart before I could eat it.",
    "I've been yawning non-stop.",
    "The corridor smells of fresh paint.",
    "My pen ran out of ink halfway through a sentence.",
    "A squirrel stole a biscuit right off my plate.",
    "I walked into a glass door, very gracefully.",
    "My socks don't match and nobody has noticed.",
    "The kettle in the break room whistles like a ghost.",
    "I think my chair is slowly sinking.",
    "The window cleaner waved at me and I panicked.",
    "My aunt knitted me a jumper with three sleeves.",
    "I stepped in a puddle and my shoe is still wet.",
    "The stapler on my desk has gone missing again.",
    "I sneezed so loudly that the cat left the room.",
    "My left sock has a hole in it.",
    "The ceiling fan is making a funny clicking noise.",
    "I waved back at someone who wasn't waving at me.",
    "There's a moth living in my coat pocket.",
    "My thermos leaked into my bag.",
]

# "<clause with the wrong value><connector> <right value>"
CORRECTIONS = [
    ", actually make it",
    " - no wait,",
    ", sorry, I meant",
    "... scratch that,",
    ", let me correct that:",   # not ", or rather": inside a question that reads like a choice of two
    ", hmm, change that to",
    " - correction:",
    ", no, make that",
    ", wait, I mean",
    ", my mistake, it should be",
    " - sorry, not that,",
    ", on second thought",
]

# glue between independent requests in one turn (category c)
JOINERS = [
    ", and also ",
    "; separately, ",
    ", and in addition ",
    ", and on top of that ",
    ", plus ",
    "; and then also ",
    ", and as a second thing ",
    ", and while you're at it ",
    "; besides that, ",
    ", and another thing: ",
    "; I also need you to ",
    ", and furthermore ",
]

# glue between the steps of a narrated multi-step request (category d)
THENS = [
    ", then ",
    ", and then ",
    "; after that, ",
    ", next ",
    "; once you have it, ",
    ", and once that's done ",
    ", and with that ",
    "; when that comes back, ",
]

SYSTEM = [
    "You are an assistant that can use tools. {today} Call a tool whenever the user's request can be carried "
    "out with one of the available tools. If the request contains several independent actions, call a tool for "
    "each of them in the same turn. If an action needs information that another tool returns, call that tool "
    "first and wait for its result. If the user did not give a value for a required argument, do not guess: ask "
    "for it and call nothing. Pass optional arguments only when the user specified them. If none of the "
    "available tools fits the request, do not call a tool; answer in plain text.",

    "{today} You have access to a set of tools. Use them to do what the user asks. Several independent actions "
    "in one request mean several tool calls in one turn. When one call depends on the output of another, make "
    "the first call, wait for the result, then continue. Never invent a required value the user left out; ask "
    "the user instead and make no tool call. Leave out optional arguments the user did not mention. When no "
    "tool matches what the user wants, reply normally without calling anything.",

    "You help the user by calling tools. {today} Rules: (1) if a tool can do what is asked, call it with "
    "exactly the values the user gave; (2) independent actions in one message are issued together as separate "
    "calls; (3) if a call needs data from an earlier call, wait for that result before making it; (4) if a "
    "required value is missing, ask for it and do not call any tool; (5) do not fill in optional arguments the "
    "user did not state; (6) if no tool is relevant, respond in plain text only.",

    "Tool-using assistant. {today} Act on the user's request with the tools provided. Make one call per "
    "independent action, all in the same turn. For actions that rely on a previous tool result, proceed step "
    "by step and wait for each result. Ask a question, and call no tool, when a required argument has not been "
    "provided. Do not supply optional arguments unless the user gave them. If the request is outside what the "
    "tools can do, just reply in text.",

    "{today} You are connected to several tools. Whenever the user's message asks for something a tool can do, "
    "call that tool. Requests with more than one independent action need one call for each, issued together. "
    "Dependent actions are done in sequence: call, wait for the result, then call again. A required argument "
    "the user has not given must be asked for, with no tool call in that turn. Optional arguments are only "
    "passed if the user stated them. Requests that no tool covers get a plain-text reply and no tool call.",

    "You are a careful assistant with tools. {today} Choose the tool that matches the request and fill its "
    "arguments from the user's words. Issue all independent actions of a request in one turn. If you need the "
    "result of one tool to call another, wait for it. If something required is missing from the request, ask "
    "the user and do not call a tool yet. Skip optional arguments that were not mentioned. If nothing fits, "
    "do not call any tool and answer directly.",

    "{today} Your job is to turn user requests into tool calls. Call every tool the request needs; "
    "independent actions go out together in one turn, while an action that depends on a tool result waits for "
    "that result. Do not make up required values: when one is missing, ask and call nothing. Only include "
    "optional arguments the user specified. When the available tools cannot do what is asked, reply with text "
    "and no tool call.",

    "Assistant with function calling. {today} Follow these points. Use a function when the request matches "
    "it. Use several functions at once for several independent actions. Chain functions one step at a time "
    "when later arguments come from earlier results. Ask the user, without calling a function, if a required "
    "argument is not in the request. Omit optional arguments the user did not give. Call no function when "
    "none applies, and reply in plain text.",
]

TODAY = [
    "Today is {wd}, {d} {month} {y}.",
    "Current date: {iso} ({wd}).",
    "The date today is {wd}, {month} {d}, {y}.",
    "Today's date is {iso}, a {wd}.",
    "It is {wd} {iso} today.",
    "Date: {wd}, {d} {month} {y}.",
    "Today: {iso} ({wd}).",
    "The current date is {month} {d}, {y}, which is a {wd}.",
]

# Requests that need no tool at all (category f, small-talk variant)
SMALLTALK = [
    "What's a good name for a goldfish?",
    "Tell me a short joke about penguins.",
    "Why do cats purr?",
    "Give me a fun fact about octopuses.",
    "Write a two-line poem about autumn leaves.",
    "How many legs does a spider have?",
    "Can you say something encouraging? I've had a rough day.",
    "Which is heavier, a kilogram of feathers or a kilogram of bricks?",
    "Suggest a name for a pirate ship.",
    "What colour do you get when you mix blue and yellow?",
    "Do you think robots dream?",
    "Give me a tongue twister.",
    "Count from one to five for me.",
    "Is a tomato a fruit or a vegetable?",
    "Describe the taste of a lemon in three words.",
    "Thanks, that's all for now!",
    "Good morning! How are you doing?",
    "What's your favourite shape, and why?",
    "Finish this sentence: the early bird...",
    "Never mind, I sorted it out myself.",
    "Tell me something interesting about the moon.",
    "Invent a silly word and tell me what it means.",
    "What sound does a duck make?",
    "Which came first, the chicken or the egg?",
    "Can you wish me luck for my exam?",
    "How do you spell 'rhythm'?",
    "What is two plus two?",
    "Tell me a riddle about a river.",
    "Is it better to be an early bird or a night owl?",
    "Name three things that are yellow.",
    "Pretend you're a pirate and say hello.",
    "Why is the letter Q almost always followed by U?",
]


# small-talk templates; {x} is filled from SMALLTALK_TOPICS
SMALLTALK_T = [
    "Tell me a short joke about {x}.",
    "Give me a fun fact about {x}.",
    "Write a two-line poem about {x}.",
    "Make up a limerick about {x}.",
    "What would be a good name for a band made up of {x}?",
    "Describe {x} in exactly five words.",
    "Invent a superhero whose powers come from {x}.",
    "Why do people find {x} funny?",
    "Write a haiku about {x}.",
    "Pretend you are a world expert on {x} and introduce yourself.",
    "If {x} could talk, what would they complain about?",
    "Give me three adjectives that describe {x}.",
]

SMALLTALK_TOPICS = [
    "penguins", "octopuses", "hedgehogs", "giraffes", "owls", "snails", "kangaroos", "llamas", "beavers",
    "flamingos", "walruses", "armadillos", "teapots", "umbrellas", "staplers", "socks", "cactuses",
    "balloons", "pillows", "mittens", "marbles", "buttons", "spoons", "ladders", "pebbles", "candles",
    "pencils", "wheelbarrows", "doorknobs", "buckets", "sponges", "zebras", "moles", "crabs", "pelicans",
    "geckos", "wombats", "badgers", "lobsters", "shoelaces",
]


# Near-duplicate "twin" tools for category b: same parameters as the right tool, but the description
# says the twin must not be used for a real request. {name} is the right tool's name.
TWIN_DEPRECATED_SUFFIX = ["legacy", "v1", "old", "deprecated", "classic", "obsolete", "retired", "previous"]
TWIN_DEPRECATED_DESC = [
    "Deprecated, do not call. Replaced by {name}.",
    "Old version kept for compatibility only; it is switched off and always fails. Use {name} instead.",
    "DEPRECATED: this function no longer works. Call {name}.",
    "Superseded by {name} and scheduled for removal. Do not use.",
]
TWIN_DRYRUN_SUFFIX = ["dry_run", "preview", "simulate", "test_only", "validate_only", "sandbox", "rehearsal",
                      "mock"]
TWIN_DRYRUN_DESC = [
    "Dry run of {name}: checks the arguments and reports what would happen, without doing anything.",
    "Simulation only. Validates the arguments like {name} but performs no action and changes nothing.",
    "Test stub for {name}. Nothing is carried out; it only returns whether the arguments are valid.",
    "Preview mode of {name}: returns a description of the effect, but the action itself is not performed.",
]


def pools_for(split):
    return {
        "wrappers": {style: part(lst, split) for style, lst in WRAPPERS.items()},
        "chatter": part(CHATTER, split),
        "corrections": part(CORRECTIONS, split),
        "joiners": part(JOINERS, split),
        "thens": part(THENS, split),
        "system": part(SYSTEM, split),
        "today": part(TODAY, split),
        "smalltalk": part(SMALLTALK, split),
        "twin_deprecated_suffix": part(TWIN_DEPRECATED_SUFFIX, split),
        "twin_deprecated_desc": part(TWIN_DEPRECATED_DESC, split),
        "twin_dryrun_suffix": part(TWIN_DRYRUN_SUFFIX, split),
        "twin_dryrun_desc": part(TWIN_DRYRUN_DESC, split),
        "smalltalk_t": part(SMALLTALK_T, split),
        "smalltalk_topics": part(SMALLTALK_TOPICS, split),
    }


def all_templates(split):
    """Flat list of every hand-written phrasing template available to a split."""
    p = pools_for(split)
    out = []
    for lst in p["wrappers"].values():
        out += lst
    for key in ("chatter", "corrections", "joiners", "thens", "system", "today", "smalltalk",
                "smalltalk_t", "smalltalk_topics", "twin_deprecated_suffix", "twin_deprecated_desc",
                "twin_dryrun_suffix", "twin_dryrun_desc"):
        out += p[key]
    return out
