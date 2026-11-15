"""Reminders (smart lists, the user's lists, reminders that are ticked off): start state and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
"""
import datetime

from ..oracle import Click, Drag, Key, Reveal, Type
from .base import Spec, by_id, cond, norm, only, say, task, unchanged, verdict

SIZE = (900, 640)
WIN = '.win[data-app="reminders"] '
FIRST_DUE = datetime.date(2026, 10, 29)      # the menu bar clock is between 2 and 12 Nov 2026

# One pool of titles per list. Titles are distinct across all pools and none contains another.
BIG = {
    "Home": ["Call the plumber", "Descale the kettle", "Change the smoke alarm battery", "Hoover under the sofa", "Defrost the freezer",
             "Clean the oven", "Water the house plants", "Take out the recycling", "Fix the squeaky door", "Replace the hallway bulb",
             "Wash the bedding", "Bleed the radiators", "Clear the gutters", "Sort the sock drawer", "Wipe the skirting boards",
             "Order new vacuum bags", "Hang the mirror", "Oil the garden gate", "Empty the dishwasher filter", "Dust the bookshelves",
             "Mop the kitchen floor", "Tighten the loose shelf", "Clean the windows", "Book the chimney sweep", "Read the gas meter",
             "Put up the coat hooks", "Re-grout the shower", "Sharpen the kitchen knives", "Wash the curtains", "Tidy the hallway cupboard",
             "Label the fuse box", "Check the boiler pressure", "Unblock the bathroom sink", "Rotate the mattress", "Clean the fridge shelves",
             "Sweep the balcony", "Test the carbon monoxide alarm", "Polish the dining table"],
    "Groceries": ["Oat milk", "Free-range eggs", "Sourdough loaf", "Cherry tomatoes", "Unsalted butter", "Basmati rice", "Red lentils",
                  "Olive oil", "Greek yoghurt", "Bananas", "Baby spinach", "Cheddar", "Coffee beans", "Garlic", "Lemons", "Tinned chickpeas",
                  "Wholemeal pasta", "Peanut butter", "Dishwasher tablets", "Kitchen roll", "Spring onions", "Fresh ginger", "Soy sauce",
                  "Frozen peas", "Porridge oats", "Honey", "Sweet potatoes", "Mushrooms", "Blueberries", "Chicken thighs", "Smoked paprika",
                  "Plain flour", "Dark chocolate", "Orange juice", "Green tea", "Tortilla wraps", "Feta", "Washing-up liquid"],
    "Work": ["Send the Q3 report", "Reply to Dana about the contract", "Book a room for the workshop", "Review Tobias's pull request",
             "Update the project timeline", "Prepare slides for Monday", "Submit the expense report", "Call the supplier back",
             "Renew the software licence", "Write up the meeting notes", "Order new business cards", "Schedule the performance reviews",
             "Fix the broken link on the pricing page", "Draft the newsletter", "Back up the shared drive", "Approve Priya's holiday request",
             "Chase invoice 4471", "Test the new login flow", "Proofread the press release", "Set up the new starter's laptop",
             "Archive last year's projects", "Plan the team offsite", "Send the agenda for Thursday", "Update my out-of-office message",
             "Check the analytics dashboard", "Confirm the catering order", "Share the design files with Marcus", "Read the security guidelines",
             "Register for the conference", "Clear the support inbox", "Rewrite the onboarding email", "Print the handouts",
             "Collect feedback on the demo", "File the signed contract", "Record the product walkthrough", "Tidy up the ticket backlog",
             "Email the minutes to Elena", "Renew the domain name"],
}
SMALL = {
    "Errands": ["Pick up the dry cleaning", "Post the parcel to Ingrid", "Return the library books", "Collect the prescription", "Get keys cut",
                "Drop off the charity bags", "Buy stamps", "Take the bike for a service", "Renew the parking permit", "Pick up the birthday cake",
                "Return the drill to Bruno", "Get passport photos taken", "Top up the travel card", "Collect the framed print"],
    "Family": ["Call Grandma on Sunday", "Sign the school trip form", "Book the swimming lessons", "Buy a present for Oskar",
               "Plan Mum's birthday dinner", "Send photos to Aunt Leila", "Order the school uniform", "Arrange a babysitter for Friday",
               "Renew the family railcard", "Book the dentist for the kids", "Print the holiday photos", "Help Yusuf with his project",
               "Fill in the nursery forms", "Write to Uncle Viktor"],
    "Travel": ["Renew my passport", "Book the airport transfer", "Check in online", "Buy travel insurance", "Print the boarding passes",
               "Exchange some currency", "Reserve seats on the train", "Download offline maps", "Pack the adapters", "Confirm the hotel booking",
               "Arrange cat sitting", "Hold the post", "Buy sun cream", "Charge the camera batteries"],
    "Garden": ["Mow the lawn", "Prune the roses", "Plant the tulip bulbs", "Turn the compost", "Repair the fence panel", "Feed the tomatoes",
               "Rake up the leaves", "Clean the greenhouse glass", "Order seeds for spring", "Net the strawberries", "Empty the water butt",
               "Sharpen the secateurs", "Cut back the lavender", "Weed the vegetable bed"],
}
POOLS = {**BIG, **SMALL}
COLORS = ["#ff3b30", "#ff9500", "#28b24b", "#0a7aff", "#5856d6", "#af52de", "#a2845e", "#20a5ba"]
NOTES = ["Before the weekend", "Not urgent", "Ask Mei first", "Check the price first", "On the way home", "Second time of asking",
         "Only if there is time", "Do not forget this time", "Morning is best", "Halima can help"]
SHOPPING_NOTES = ["Two packs", "The big one", "From the market if possible", "Whatever is on offer", "For Saturday's dinner",
                  "Check the date on it", "Organic if they have it", "We are nearly out"]


def default(rng):
    long_name = rng.choice(sorted(BIG))
    others = rng.sample([n for n in sorted(POOLS) if n != long_name], rng.choice([3, 3, 4]))
    names = [long_name] + others
    rng.shuffle(names)
    colors = rng.sample(COLORS, len(names))
    lists = [{"id": f"l{i + 1}", "name": n, "color": c} for i, (n, c) in enumerate(zip(names, colors))]
    items = []
    for l in lists:
        is_long = l["name"] == long_name
        n_open = rng.randint(29, 32) if is_long else rng.randint(5, 8)
        n_done = rng.randint(3, 4) if is_long else rng.randint(1, 3)
        titles = rng.sample(POOLS[l["name"]], n_open + n_done)
        done = set(rng.sample(titles, n_done))
        for t in titles:
            due = (FIRST_DUE + datetime.timedelta(days=rng.randint(0, 28))).isoformat() if rng.random() < 0.3 else ""
            items.append({"id": f"r{len(items) + 1}", "list": l["id"], "title": t, "done": t in done, "flagged": rng.random() < 0.12,
                          "due": due, "note": rng.choice(SHOPPING_NOTES if l["name"] == "Groceries" else NOTES) if rng.random() < 0.2 else ""})
    return {"lists": lists, "items": items, "next": len(items) + 1,
            "ui": {"list": rng.choice(lists)["id"], "sel": None, "showCompleted": False, "adding": False, "draft": ""}}


# ------------------------------------------------------------------ helpers
def in_list(s, lid, done=False):
    """The reminders of a list in display order: the open ones, or the completed ones."""
    return [i for i in s["items"] if i["list"] == lid and i["done"] == done]


def long_list(s):
    return max(s["lists"], key=lambda l: len(in_list(s, l["id"])))


def short_lists(s):
    return [l for l in s["lists"] if l["id"] != long_list(s)["id"]]


def item(st, i):
    return by_id(st["apps"]["reminders"]["items"], i)


def order(st, lid):
    return [i["id"] for i in st["apps"]["reminders"]["items"] if i["list"] == lid]


def row(i):
    return WIN + f'.r-row[data-arg="{i["id"]}"]'


def circle(i):
    return row(i) + " .r-circle"


def side(l):
    return WIN + f'.r-list[data-arg="{l["id"]}"]'


def tick(i):
    return Click(circle(i), f"Click the round checkbox to the left of “{i['title']}”")


def open_list(l):
    return Click(side(l), f"Click the list “{l['name']}” in the sidebar of Reminders")


def unused_titles(s, name=None):
    taken = {norm(i["title"]) for i in s["items"]}
    pool = POOLS[name] if name else [t for p in POOLS.values() for t in p]
    return [t for t in pool if norm(t) not in taken]


def start(s, l, show_completed=False):
    s["ui"].update(list=l["id"], sel=None, showCompleted=show_completed, adding=False, draft="")


TOP = 7          # this many rows are in view at the top of a list whatever their height


def vary(S, tid):
    """The tasks of one seed would otherwise all make the same picks (same folder, same row, same
    window position), because each starts from the same random state."""
    S.rng.seed(f"{S.seed}/{tid}")


# ------------------------------------------------------------------ tasks
@task("reminders.check_off", "single")
def check_off(S):
    vary(S, "reminders.check_off")
    s = S.apps["reminders"]
    l = S.rng.choice(s["lists"])
    start(s, l)
    it = S.rng.choice(in_list(s, l["id"])[:TOP])
    S.open("reminders")
    return Spec(request=say(S.rng, f"Tick off “{it['title']}” in my {l['name']} list.", f"I've done “{it['title']}”. Mark that reminder as completed."),
                steps=[tick(it)],
                check=lambda st, init: verdict(cond(item(st, it["id"]) and item(st, it["id"])["done"] is True, "the reminder is not completed"),
                                               only(st, init, f"reminders.items.{it['id']}.done")))


@task("reminders.add", "typing")
def add(S):
    vary(S, "reminders.add")
    s = S.apps["reminders"]
    l = S.rng.choice(s["lists"])
    first = l if S.rng.random() < 0.5 else S.rng.choice([x for x in s["lists"] if x["id"] != l["id"]])
    start(s, first)
    title = S.rng.choice(unused_titles(s, l["name"]))
    S.open("reminders")

    def check(st, init):
        old = {i["id"] for i in init["apps"]["reminders"]["items"]}
        new = [i for i in st["apps"]["reminders"]["items"] if i["id"] not in old]
        return verdict(cond(len(new) == 1, f"{len(new)} reminders were added, not one"),
                       cond(new and norm(new[0]["title"]) == norm(title), f"the new reminder is called “{new[0]['title'] if new else ''}”"),
                       cond(new and new[0]["list"] == l["id"], f"the new reminder is not in {l['name']}"),
                       cond(new and not new[0]["done"] and not new[0]["flagged"], "the new reminder is completed or flagged"),
                       only(st, init, "reminders.items.+*", "reminders.next"))
    steps = [] if first["id"] == l["id"] else [open_list(l)]
    steps += [Click(WIN + '.tb-btn[data-act="add"]', "Click the + button at the top right of the Reminders window"), Type(title), Key("enter")]
    return Spec(request=say(S.rng, f"Add “{title}” to my {l['name']} list.", f"Put a new reminder on the {l['name']} list: {title}"),
                steps=steps, check=check)


@task("reminders.reorder", "drag")
def reorder(S):
    vary(S, "reminders.reorder")
    s = S.apps["reminders"]
    l = S.rng.choice(short_lists(s))
    start(s, l)
    rows = in_list(s, l["id"])[:TOP]
    to_top = S.rng.random() < 0.5
    j = 0 if to_top else S.rng.randrange(1, len(rows) - 1)           # the reminder it goes above
    it = S.rng.choice(rows[j + 1:])
    above = rows[j]
    want = [r["id"] for r in in_list(s, l["id"]) if r is not it]
    want.insert(j, it["id"])
    S.open("reminders")

    def check(st, init):
        s1, s0 = st["apps"]["reminders"], init["apps"]["reminders"]
        return verdict(cond([i["id"] for i in in_list(s1, l["id"])] == want, "the reminders of the list are not in the order asked for"),
                       cond([i for i in order(st, l["id"]) if i != it["id"]] == [i for i in order(init, l["id"]) if i != it["id"]], "other reminders of the list moved"),
                       cond(all(order(st, x["id"]) == order(init, x["id"]) for x in s0["lists"] if x["id"] != l["id"]), "the order of another list changed"),
                       only(st, init, "reminders.items.<order>"))
    request = (say(S.rng, f"Move “{it['title']}” to the top of my {l['name']} list.", f"In my {l['name']} list, put “{it['title']}” first.") if to_top else
               say(S.rng, f"In my {l['name']} list, move “{it['title']}” so that it sits directly above “{above['title']}”.",
                   f"Reorder my {l['name']} reminders: “{it['title']}” should come right before “{above['title']}”."))
    return Spec(request=request,
                steps=[Drag(row(it), row(above), f"the reminder “{it['title']}”", f"the reminder “{above['title']}”", dst_at=(0.4, 0.3))],
                check=check)


@task("reminders.delete", "menu")
def delete(S):
    vary(S, "reminders.delete")
    s = S.apps["reminders"]
    l = S.rng.choice(s["lists"])
    start(s, l)
    it = S.rng.choice(in_list(s, l["id"])[:TOP])
    S.open("reminders")
    return Spec(request=say(S.rng, f"Delete the reminder “{it['title']}”.", f"Remove “{it['title']}” from my {l['name']} list. I don't need it any more."),
                steps=[Click(row(it), f"Right-click the reminder “{it['title']}”", button="right"),
                       Click('.menu-item:has(.mi-label:text-is("Delete"))', "Click “Delete” in the menu")],
                check=lambda st, init: verdict(cond(item(st, it["id"]) is None, "the reminder is still there"),
                                               only(st, init, f"reminders.items.-{it['id']}")))


@task("reminders.show_completed", "menu")
def show_completed(S):
    vary(S, "reminders.show_completed")
    s = S.apps["reminders"]
    start(s, S.rng.choice(s["lists"]))
    S.open("reminders")
    return Spec(request=say(S.rng, "Turn on Show Completed in Reminders.", "Stop hiding the reminders I've ticked off: completed ones should stay visible in my lists."),
                steps=[Click('.mb-item:text-is("View")', "Click “View” in the menu bar"),
                       Click('.menu-item:has(.mi-label:text-is("Show Completed"))', "Click “Show Completed” in the menu")],
                check=lambda st, init: verdict(cond(st["apps"]["reminders"]["ui"]["showCompleted"] is True, "completed reminders are still hidden"),
                                               unchanged(st, init)))


@task("reminders.check_two", "chain")
def check_two(S):
    vary(S, "reminders.check_two")
    s = S.apps["reminders"]
    l = S.rng.choice(s["lists"])
    start(s, S.rng.choice([x for x in s["lists"] if x["id"] != l["id"]]))
    a, b = S.rng.sample(in_list(s, l["id"])[:TOP], 2)
    S.open("reminders")
    return Spec(request=say(S.rng, f"In my {l['name']} list, tick off “{a['title']}” and “{b['title']}”.",
                            f"Mark two reminders on the {l['name']} list as done: “{a['title']}” and “{b['title']}”."),
                steps=[open_list(l), tick(a), tick(b)],
                check=lambda st, init: verdict(cond(item(st, a["id"]) and item(st, a["id"])["done"] is True, f"“{a['title']}” is not completed"),
                                               cond(item(st, b["id"]) and item(st, b["id"])["done"] is True, f"“{b['title']}” is not completed"),
                                               only(st, init, f"reminders.items.{a['id']}.done", f"reminders.items.{b['id']}.done")))


@task("reminders.check_far", "scroll")
def check_far(S):
    vary(S, "reminders.check_far")
    s = S.apps["reminders"]
    l = long_list(s)
    start(s, l)
    it = S.rng.choice(in_list(s, l["id"])[-8:])
    S.open("reminders")
    return Spec(request=say(S.rng, f"Tick off “{it['title']}” in my {l['name']} list.", f"“{it['title']}” on my {l['name']} list is done. Mark it as completed."),
                steps=[Reveal(row(it)), tick(it)],
                check=lambda st, init: verdict(cond(item(st, it["id"]) and item(st, it["id"])["done"] is True, "the reminder is not completed"),
                                               only(st, init, f"reminders.items.{it['id']}.done")))


@task("reminders.already_completed", "already_done")
def already_completed(S):
    vary(S, "reminders.already_completed")
    s = S.apps["reminders"]
    l = S.rng.choice(short_lists(s))
    start(s, l, show_completed=True)
    rows = [i for i in s["items"] if i["list"] == l["id"]]
    it = S.rng.choice([i for i in rows[:TOP] if i["done"]] or [i for i in rows if i["done"]])
    S.open("reminders")
    return Spec(request=say(S.rng, f"Tick off “{it['title']}” in my {l['name']} list.", f"Make sure “{it['title']}” on my {l['name']} list is marked as completed."),
                steps=[], kind="already_done", check=unchanged)


@task("reminders.missing_reminder", "infeasible")
def missing_reminder(S):
    vary(S, "reminders.missing_reminder")
    s = S.apps["reminders"]
    l = S.rng.choice(s["lists"])
    start(s, S.rng.choice(s["lists"]))
    ghost = S.rng.choice(unused_titles(s, l["name"]))
    S.open("reminders")
    return Spec(request=say(S.rng, f"Tick off “{ghost}” in my {l['name']} list.", f"I've done “{ghost}”. Mark that reminder as completed."),
                steps=[], kind="infeasible", check=unchanged)
