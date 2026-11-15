"""Category (h): computer-control actions as tools.

A screen is described as a numbered list of elements (role, label, state).
The five tools are fixed by the benchmark definition and therefore shared by
all splits; the applications, their labels and the task wordings are split
specific. Every scenario is built so that exactly one next action is right.
"""
import datetime as dt

from pools import part

KEYS = ["Enter", "Escape", "Tab", "Backspace", "Delete", "Space",
        "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "PageUp", "PageDown"]


def _fn(name, desc, props, required):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": required}}}


COMPUTER_TOOLS = [
    _fn("click", "Click the element with the given id.",
        {"element_id": {"type": "integer", "description": "Id of the element, as shown in brackets on the screen list."}},
        ["element_id"]),
    _fn("type_text", "Type text into the element with the given id. The element is focused automatically and "
                     "any text already in it is replaced. This does not press Enter.",
        {"element_id": {"type": "integer", "description": "Id of the text field, as shown in brackets on the screen list."},
         "text": {"type": "string", "description": "The exact text to type."}},
        ["element_id", "text"]),
    _fn("press_key", "Press a single key on the keyboard.",
        {"key": {"type": "string", "enum": KEYS, "description": "Name of the key."}},
        ["key"]),
    _fn("scroll", "Scroll the page to reveal elements that are not on the visible list.",
        {"direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "Scroll direction."},
         "amount": {"type": "integer", "description": "How far to scroll, in screen heights (1 = one screen)."}},
        ["direction", "amount"]),
    _fn("done", "Report that the task is already complete on the current screen.",
        {"summary": {"type": "string", "description": "One sentence saying what was achieved."}},
        ["summary"]),
]

SYSTEM_H = [
    "You operate a computer for the user through the provided tools. Each message contains a task and the "
    "current screen as a numbered list of elements: [id] role \"label\" (state). Reply with exactly one tool "
    "call, the single next action that makes progress on the task. Text fields can be filled directly with "
    "type_text; there is no need to click them first. A search box has no button of its own: once the query "
    "is in it, the search is started with the Enter key. A form is submitted with its own button, never with "
    "Enter. Elements that are not on the list are not visible; scroll to reach them. If the screen shows that "
    "the task is already complete, call done.",

    "You control a desktop application with tools. The user gives a task and a snapshot of the screen, listed "
    "as [id] role \"label\" (state). Answer with one tool call only: the next step toward the task, nothing "
    "more. You can type into a text field without clicking it first. Search boxes come without a button, so "
    "a query that is already typed is run by pressing Enter. Forms are different: they are sent with their "
    "button, not with Enter. Only listed elements are visible; scroll when the one you need is missing. When "
    "the task has already been achieved on this screen, call done.",

    "Computer-use mode. Input: a task plus the visible screen as lines of the form [id] role \"label\" "
    "(state). Output: exactly one tool call that performs the next action for the task. Use type_text "
    "directly on text fields (no click needed beforehand). To run a search whose query is already in the "
    "search box, press the Enter key; search boxes have no button. To submit a form, click its button; Enter "
    "does not submit forms. If the needed element is not listed, it is off-screen: scroll. If nothing remains "
    "to be done because the screen already shows the finished state, call done.",

    "Act as the user's hands on a computer. You receive the task and a list of on-screen elements in the "
    "format [id] role \"label\" (state). Choose the one next action and issue it as a single tool call. "
    "Typing does not require clicking the field first. A typed search query is started with the Enter key, "
    "because search boxes have no button; forms, in contrast, are only submitted through their button. "
    "Anything not in the list is outside the visible area and must be scrolled into view. Call done as soon "
    "as the screen shows that the task is complete.",
]

TASKS = {
    "form": [
        'fill in the "{form}" form in {app} with {pairs} and submit it',
        'complete the "{form}" form in {app} using {pairs}, then submit it',
        'use the "{form}" form in {app} to enter {pairs} and send it off',
        'submit the "{form}" form in {app} with these details: {pairs}',
    ],
    "toggle": [
        'turn {onoff} "{label}" under the "{tab}" tab in the {app} settings',
        'go to the "{tab}" tab of the {app} settings and switch "{label}" {onoff}',
        'make sure "{label}" on the "{tab}" tab of the {app} settings is {onoff}',
        'set the "{label}" option, found on the "{tab}" tab of the {app} settings, to {onoff}',
    ],
    "nav": [
        'open the "{link}" section of {app}',
        'go to the "{link}" page in {app}',
        'navigate to "{link}" in {app}',
        'bring up the "{link}" area of {app}',
    ],
    "search": [
        'search {app} for "{q}"',
        'look up "{q}" using the search in {app}',
        'run a search for "{q}" in {app}',
        'use the {app} search to find "{q}"',
    ],
    "select": [
        'set "{label}" to "{option}" in {app}',
        'change the "{label}" setting in {app} to "{option}"',
        'pick "{option}" for "{label}" in {app}',
        'choose "{option}" as the "{label}" in {app}',
    ],
    "dialog": [
        '{delete} the {noun} "{item}" in {app}',
        '{delete} the {noun} called "{item}" in {app}',
        'take the {noun} "{item}" out of {app}: {delete} it',
        'go into {app} and {delete} the {noun} named "{item}"',
    ],
    "check": [
        'select the {noun}s {items} in {app}',
        'tick the checkboxes for the {noun}s {items} in {app}',
        'mark these {noun}s as selected in {app}: {items}',
        'make sure the {noun}s {items} are selected in {app}',
    ],
    "escape": [
        'close the {overlay} in {app}',
        'dismiss the {overlay} that is open in {app}',
        'get the {overlay} in {app} out of the way',
        'close the {overlay} that is showing in {app}',
    ],
}

SCREEN_INTRO = [
    "Current screen:",
    "Screen right now:",
    "This is what the screen shows:",
    "Visible elements:",
]


LIST_PAGE = {"Ledgerly": "Invoices", "Quillmail": "Drafts", "Homely": "Scenes", "Shelfwise": "Products", "Tunedeck": "Playlists", "Brightdesk": "Queue", "Farely": "Trips", "Pantrio": "Lists", "Notewell": "All notes", "Clinica": "Patients", "Fleetwise": "Vehicles", "Classmate": "Courses", "Parcelino": "Shipments", "Bookmarkd": "Collections", "Staffly": "People", "Grovia": "Zones", "Eventory": "Events", "Codeharbor": "Repositories"}


class App:
    def __init__(self, name, nav, form, tabs, selects, items, delete, search, overlay, done):
        self.name = name
        self.nav = nav.split("|")
        title, fields, submit, others = form
        self.form_title, self.fields, self.submit, self.others = title, fields, submit, others.split("|")
        self.tabs = {k: v.split("|") for k, v in tabs.items()}
        self.selects = [(label, opts.split("|")) for label, opts in selects]
        self.item_noun, self.item_pool = items
        self.delete, self.search, self.overlay, self.done = delete, search, overlay, done
        self.list_page = LIST_PAGE[name]   # the page that lists this app's items
        assert self.list_page in self.nav, name


APPS = {
    "dev": [
        App("Ledgerly", "Dashboard|Clients|Invoices|Reports|Settings",
            ("New invoice", [("Client name", "company"), ("Contact email", "email"), ("Amount", "amount"),
                             ("Reference", "ref")], "Create invoice", "Cancel|Save as draft|Preview"),
            {"General": "Dark mode|Compact tables|Show tooltips",
             "Notifications": "Email me on payment|Weekly summary|Overdue reminders",
             "Privacy": "Share usage data|Remember this device|Show my name on invoices"},
            [("Currency", "USD|EUR|GBP|CHF"), ("Date format", "DD/MM/YYYY|MM/DD/YYYY|YYYY-MM-DD")],
            ("invoice", "ref"), "Delete", "Search invoices", "invoice preview", "Invoice created"),
        App("Quillmail", "Inbox|Sent|Drafts|Contacts|Settings",
            ("New message", [("To", "email"), ("Subject", "text:subject"), ("Message", "text:message")],
             "Send", "Discard|Save draft|Attach file"),
            {"Reading": "Show previews|Mark as read on open|Conversation view",
             "Sending": "Confirm before sending|Always add signature|Request read receipts",
             "Alerts": "Desktop notifications|Sound on new mail|Badge on icon"},
            [("Default font", "Serif|Sans|Mono"), ("Reply behaviour", "Reply|Reply all")],
            ("draft", "text:subject"), "Discard", "Search mail", "attachment preview", "Message sent"),
        App("Homely", "Rooms|Scenes|Devices|Energy|Settings",
            ("Add device", [("Device name", "text:place"), ("Room", "text:room"), ("Serial number", "ref")],
             "Add device", "Cancel|Scan QR code|Help"),
            {"Automation": "Away mode|Sunset lights|Morning routine",
             "Safety": "Smoke alerts|Leak alerts|Door chime",
             "Display": "Show energy tips|Use large tiles|24-hour clock"},
            [("Temperature unit", "Celsius|Fahrenheit"), ("Home screen", "Rooms|Scenes|Devices")],
            ("scene", "text:playlist"), "Remove", "Search devices", "camera view", "Device added"),
        App("Shelfwise", "Overview|Products|Suppliers|Orders|Settings",
            ("New product", [("Product name", "text:product"), ("Supplier", "company"), ("Unit price", "amount"),
                             ("SKU", "ref")], "Save product", "Cancel|Duplicate|Import CSV"),
            {"Stock": "Low stock warnings|Auto reorder|Count in cases",
             "Labels": "Print barcodes|Show prices on labels|Include logo",
             "Access": "Require approval|Allow guest view|Two-step sign-in"},
            [("Warehouse", "North|South|Harbour"), ("Rows per page", "25|50|100")],
            ("product", "text:product"), "Delete", "Search products", "label preview", "Product saved"),
        App("Tunedeck", "Home|Library|Playlists|Radio|Settings",
            ("New playlist", [("Playlist name", "text:playlist"), ("Description", "text:memo")],
             "Create playlist", "Cancel|Import|Choose cover"),
            {"Playback": "Crossfade|Gapless playback|Normalise volume",
             "Downloads": "Download on Wi-Fi only|Auto-download favourites|Keep screen awake",
             "Social": "Show what I play|Private session|Share listening history"},
            [("Audio quality", "Low|Normal|High|Lossless"), ("Start page", "Home|Library|Radio")],
            ("playlist", "text:playlist"), "Delete", "Search music", "lyrics view", "Playlist created"),
    ],
    "test": [
        App("Brightdesk", "Queue|Customers|Knowledge base|Reports|Admin",
            ("New ticket", [("Requester email", "email"), ("Subject", "text:issue"), ("Assigned agent", "person")],
             "Create ticket", "Cancel|Save as macro|Add attachment"),
            {"Workflow": "Auto-assign tickets|Close stale tickets|Round-robin routing",
             "Email": "Send satisfaction survey|Include ticket history|Notify on reply",
             "Agents": "Show agent status|Allow self-assign|Hide closed tickets"},
            [("Default priority", "Low|Normal|High|Urgent"), ("Time zone", "UTC|CET|EST|PST")],
            ("ticket", "text:issue"), "Delete", "Search tickets", "customer profile card", "Ticket created"),
        App("Farely", "Trips|Flights|Hotels|Rail|Account",
            ("Passenger details", [("Full name", "person"), ("Email", "email"), ("Phone", "phone"),
                                   ("Frequent flyer number", "ref")], "Continue to payment",
             "Back|Save for later|Clear form"),
            {"Preferences": "Aisle seat by default|Vegetarian meal|Extra legroom alerts",
             "Notifications": "Price drop alerts|Gate change alerts|Check-in reminders",
             "Privacy": "Personalised offers|Share trips with contacts|Remember payment method"},
            [("Cabin", "Economy|Premium|Business|First"), ("Currency", "USD|EUR|GBP|JPY")],
            ("trip", "city"), "Remove", "Search trips", "fare rules panel", "Passenger details saved"),
        App("Pantrio", "Shop|Offers|Lists|Orders|Account",
            ("Delivery address", [("Recipient", "person"), ("Street", "text:street"), ("City", "city"),
                                  ("Postal code", "text:zip")], "Save address", "Cancel|Use current location|Help"),
            {"Delivery": "Leave at door|Ring the bell|Text me on arrival",
             "Substitutions": "Allow substitutions|Prefer organic|Ask before replacing",
             "Receipts": "Email receipts|Itemised totals|Show savings"},
            [("Delivery slot", "Morning|Afternoon|Evening"), ("Bag type", "Paper|Reusable|None")],
            ("list", "text:notetitle"), "Delete", "Search groceries", "product photo", "Address saved"),
        App("Notewell", "All notes|Notebooks|Tags|Shared|Settings",
            ("New notebook", [("Notebook name", "text:notetitle"), ("Owner", "person")],
             "Create notebook", "Cancel|Choose cover|Import"),
            {"Editor": "Spell check|Smart quotes|Show word count",
             "Sync": "Sync on mobile data|Offline mode|Back up daily",
             "Sharing": "Allow comments|Link sharing|Show collaborators"},
            [("Theme", "Light|Dark|Sepia"), ("Font size", "Small|Medium|Large")],
            ("note", "text:notetitle"), "Delete", "Search notes", "version history panel", "Notebook created"),
        App("Clinica", "Today|Calendar|Patients|Billing|Setup",
            ("New appointment", [("Patient name", "person"), ("Clinician", "person"), ("Date", "date"),
                                 ("Contact phone", "phone")], "Book appointment",
             "Cancel|Check availability|Print"),
            {"Reminders": "Text reminders|Email reminders|Second reminder",
             "Booking": "Allow online booking|Require deposit|Waitlist enabled",
             "Records": "Lock signed notes|Show allergies banner|Audit trail"},
            [("Appointment length", "15 min|30 min|45 min|60 min"), ("Week starts on", "Monday|Sunday")],
            ("patient record", "person"), "Remove", "Search patients", "patient summary", "Appointment booked"),
    ],
    "train": [
        App("Fleetwise", "Vehicles|Drivers|Routes|Fuel|Preferences",
            ("Add vehicle", [("Plate", "text:plate"), ("Driver", "person"), ("Depot city", "city")],
             "Add vehicle", "Cancel|Import list|Help"),
            {"Tracking": "Live location|Speed alerts|Idle alerts",
             "Maintenance": "Service reminders|Tyre checks|Mileage logging",
             "Reports": "Weekly fuel report|Driver scorecards|Email PDF copies"},
            [("Distance unit", "Kilometres|Miles"), ("Map style", "Road|Satellite|Terrain")],
            ("vehicle", "text:plate"), "Remove", "Search vehicles", "route map", "Vehicle added"),
        App("Classmate", "Courses|Assignments|Grades|People|Options",
            ("New course", [("Course title", "text:course"), ("Instructor", "person"), ("Start date", "date")],
             "Create course", "Cancel|Copy from existing|Help"),
            {"Grading": "Show class average|Drop lowest score|Round final grades",
             "Access": "Allow late submissions|Require enrolment key|Guest access",
             "Messages": "Email on new post|Daily digest|Mute discussions"},
            [("Grading scale", "Letters|Percent|Pass/Fail"), ("Term", "Spring|Summer|Autumn")],
            ("course", "text:course"), "Delete", "Search courses", "syllabus preview", "Course created"),
        App("Parcelino", "Shipments|Addresses|Rates|Pickups|Account",
            ("New shipment", [("Recipient", "person"), ("Street", "text:street"), ("City", "city"),
                              ("Postal code", "text:zip")], "Create label", "Cancel|Save template|Weigh parcel"),
            {"Labels": "Print return label|Show sender logo|Thermal printer format",
             "Tracking": "Email tracking link|Text on delivery|Photo proof",
             "Billing": "Monthly invoice|Auto top-up|Show prices with tax"},
            [("Service", "Economy|Standard|Priority"), ("Label size", "A6|A5|4x6 inch")],
            ("shipment", "ref"), "Delete", "Search shipments", "label preview", "Label created"),
        App("Bookmarkd", "Reading list|Collections|Highlights|Archive|Options",
            ("New collection", [("Collection name", "text:folder"), ("Curator", "person")],
             "Create collection", "Cancel|Import bookmarks|Help"),
            {"Reader": "Serif font|Justify text|Night mode",
             "Saving": "Save images offline|Auto-tag articles|Remove duplicates",
             "Sharing": "Public profile|Weekly email of saves|Show reading stats"},
            [("Text size", "Small|Medium|Large"), ("Open links in", "Reader|Browser")],
            ("collection", "text:folder"), "Delete", "Search saved items", "highlight panel", "Collection created"),
        App("Staffly", "People|Time off|Payroll|Reviews|Admin",
            ("Add employee", [("Full name", "person"), ("Work email", "email"), ("Office", "city"),
                              ("Employee number", "ref")], "Add employee", "Cancel|Upload CSV|Help"),
            {"Leave": "Require manager approval|Carry over unused days|Show team calendar",
             "Payroll": "Email payslips|Split payments|Show year-to-date",
             "Security": "Single sign-on|Session timeout|Login alerts"},
            [("Pay period", "Weekly|Fortnightly|Monthly"), ("Language", "English|Deutsch|Svenska")],
            ("employee", "person"), "Remove", "Search people", "org chart", "Employee added"),
        App("Grovia", "Zones|Schedules|Sensors|History|Options",
            ("New zone", [("Zone name", "text:plant"), ("Valve number", "ref")],
             "Save zone", "Cancel|Test valve|Help"),
            {"Watering": "Skip when raining|Seasonal adjust|Cycle and soak",
             "Alerts": "Low moisture alerts|Leak detection|Frost warnings",
             "Device": "Status light|Child lock|Automatic updates"},
            [("Units", "Litres|Gallons"), ("Soil type", "Clay|Loam|Sand")],
            ("zone", "text:plant"), "Delete", "Search zones", "moisture chart", "Zone saved"),
        App("Eventory", "Events|Venues|Guests|Tickets|Options",
            ("New event", [("Event name", "text:meeting"), ("Host", "person"), ("City", "city"), ("Date", "date")],
             "Publish event", "Cancel|Save draft|Preview page"),
            {"Registration": "Require approval|Allow plus-ones|Close when full",
             "Emails": "Send confirmations|Reminder the day before|Thank-you note",
             "Page": "Show guest list|Show map|Allow comments"},
            [("Ticket type", "Free|Paid|Donation"), ("Time zone", "UTC|CET|EET")],
            ("event", "text:meeting"), "Delete", "Search events", "seating plan", "Event published"),
        App("Codeharbor", "Repositories|Pull requests|Issues|Pipelines|Preferences",
            ("New repository", [("Repository name", "text:repo"), ("Owner", "text:username"),
                                ("Description", "text:issue")], "Create repository", "Cancel|Import code|Help"),
            {"Merging": "Require reviews|Squash by default|Delete merged branches",
             "Pipelines": "Run on every push|Cancel superseded runs|Nightly builds",
             "Notices": "Email on failure|Mention digests|Security advisories"},
            [("Default branch", "main|trunk|develop"), ("Visibility", "Private|Internal|Public")],
            ("repository", "text:repo"), "Delete", "Search repositories", "diff viewer", "Repository created"),
    ],
}

KINDS = ["form_fill", "form_submit", "form_done", "toggle_change", "toggle_done", "tab_switch", "nav",
         "search_type", "search_enter", "scroll", "select_open", "select_pick", "dialog_confirm",
         "check_last", "escape"]


def pools_for(split):
    return {"apps": APPS[split], "system": part(SYSTEM_H, split), "intro": part(SCREEN_INTRO, split),
            "tasks": {k: part(v, split) for k, v in TASKS.items()}}


def _value(ctx, kind):
    rng, P = ctx.rng, ctx.P
    if kind == "person":
        return P.mk_person(rng)
    if kind == "company":
        return P.mk_company(rng)
    if kind == "email":
        return P.mk_email(rng)
    if kind == "city":
        return P.mk_city(rng)
    if kind == "amount":
        return f"{rng.randint(12, 980)}.{rng.choice(['00', '50', '25', '75', '90'])}"
    if kind == "ref":
        return f"{rng.choice('ABCDEFGHKLMNPRSTVWXZ')}{rng.choice('ABCDEFGHKLMNPRSTVWXZ')}-{rng.randint(1000, 9999)}"
    if kind == "phone":
        return P.t_phone(rng)
    if kind == "date":
        return (ctx.today + dt.timedelta(days=rng.randint(2, 60))).isoformat()
    assert kind.startswith("text:"), kind
    return P.text(kind[5:], rng)


def _distinct(ctx, kind, n):
    out = []
    for _ in range(200):
        v = _value(ctx, kind)
        if v not in out:
            out.append(v)
        if len(out) == n:
            return out
    raise RuntimeError("pool too small for " + kind)


class Screen:
    def __init__(self, app, page):
        self.app, self.page, self.els, self.top_note, self.bottom_note = app, page, [], None, None

    def add(self, role, label, state=None):
        self.els.append((role, label, state))
        return len(self.els)  # 1-based id

    def nav(self, current=None):
        ids = {}
        for link in self.app.nav:
            ids[link] = self.add("link", link, "current page" if link == current else None)
        return ids

    def render(self, intro):
        lines = [intro, f"Window: {self.app.name} - {self.page}"]
        if self.top_note:
            lines.append(self.top_note)
        for i, (role, label, state) in enumerate(self.els, 1):
            lines.append(f'[{i}] {role} "{label}"' + (f" ({state})" if state else ""))
        if self.bottom_note:
            lines.append(self.bottom_note)
        return "\n".join(lines)


def _call(name, **args):
    return {"name": name, "arguments": args}


def _quoted_list(items):
    q = [f'"{x}"' for x in items]
    return q[0] if len(q) == 1 else ", ".join(q[:-1]) + " and " + q[-1]


def build(ctx, hp):
    """Return dict(task, screen, expected_call, arg_match, scenario, app)."""
    rng = ctx.rng
    app = rng.choice(hp["apps"])
    kind = rng.choice(KINDS)
    amatch = {}
    T = lambda key: rng.choice(hp["tasks"][key])

    if kind in ("form_fill", "form_submit", "form_done") or (kind == "scroll" and rng.random() < 0.34):
        variant = "scroll_form" if kind == "scroll" else kind
        vals, seen = [], set()
        for label, k in app.fields:
            for _ in range(50):
                v = _value(ctx, k)
                if v not in seen:
                    break
            seen.add(v)
            vals.append((label, v))
        pairs = [f'{label} "{v}"' for label, v in vals]
        pairs_txt = pairs[0] if len(pairs) == 1 else ", ".join(pairs[:-1]) + " and " + pairs[-1]
        task = T("form").format(form=app.form_title, app=app.name, pairs=pairs_txt)
        if variant == "form_done":
            sc = Screen(app, app.done)
            sc.nav()
            sc.add("heading", app.done)
            sc.add("text", f"{vals[0][0]}: {vals[0][1]}")
            sc.add("button", "Add another")
            sc.add("link", f"Back to {app.nav[0].lower()}")
            exp = _call("done", summary=f"{app.done}.")
            amatch = {"done": {"summary": {"mode": "any"}}}
        else:
            sc = Screen(app, app.form_title)
            sc.nav()
            sc.add("searchbox", app.search, "empty")
            sc.add("heading", app.form_title)
            empty = rng.randrange(len(vals)) if variant == "form_fill" else None
            field_ids = []
            for i, (label, v) in enumerate(vals):
                field_ids.append(sc.add("textbox", label, "empty" if i == empty else f'value: "{v}"'))
            if variant == "scroll_form":
                sc.bottom_note = "(The page continues below the last listed element.)"
                exp = _call("scroll", direction="down", amount=1)
                amatch = {"scroll": {"amount": {"mode": "any"}}}
            else:
                buttons = [app.submit] + app.others
                rng.shuffle(buttons)
                bid = {b: sc.add("button", b) for b in buttons}
                if variant == "form_fill":
                    exp = _call("type_text", element_id=field_ids[empty], text=vals[empty][1])
                else:
                    exp = _call("click", element_id=bid[app.submit])
        return _pack(ctx, hp, app, variant, task, sc, exp, amatch)

    if kind in ("toggle_change", "toggle_done", "tab_switch") or kind == "scroll":
        variant = "scroll_toggle" if kind == "scroll" else kind
        if kind == "scroll" and rng.random() < 0.5:
            variant = "scroll_up_nav"
        tabs = list(app.tabs)
        tab = rng.choice(tabs)
        if variant == "scroll_up_nav":
            link = rng.choice([l for l in app.nav if l != app.nav[-1]])
            task = T("nav").format(link=link, app=app.name)
            sc = Screen(app, app.nav[-1])
            sc.top_note = "(The page is scrolled down; earlier elements are above the visible area.)"
            for t in tabs:
                sc.add("tab", t, "selected" if t == tab else None)
            for lab in app.tabs[tab]:
                sc.add("switch", lab, rng.choice(["on", "off"]))
            sc.add("button", "Restore defaults")
            exp = _call("scroll", direction="up", amount=1)
            amatch = {"scroll": {"amount": {"mode": "any"}}}
            return _pack(ctx, hp, app, variant, task, sc, exp, amatch)
        label = rng.choice(app.tabs[tab])
        want = rng.choice(["on", "off"])
        task = T("toggle").format(onoff=want, label=label, tab=tab, app=app.name)
        shown = tab if variant != "tab_switch" else rng.choice([t for t in tabs if t != tab])
        sc = Screen(app, "Settings")
        sc.nav()
        sc.add("heading", "Settings")
        tab_ids = {t: sc.add("tab", t, "selected" if t == shown else None) for t in tabs}
        labels = list(app.tabs[shown])
        if variant == "scroll_toggle":
            # the wanted switch is the last one on its tab and lies below the fold
            labels = [l for l in labels if l != label][:2]
            sc.bottom_note = "(The page continues below the last listed element.)"
        ids = {}
        for lab in labels:
            if lab == label:
                state = want if variant == "toggle_done" else ("off" if want == "on" else "on")
            else:
                state = rng.choice(["on", "off"])
            ids[lab] = sc.add("switch", lab, state)
        if variant != "scroll_toggle":
            sc.add("button", "Restore defaults")
        if variant == "toggle_change":
            exp = _call("click", element_id=ids[label])
        elif variant == "toggle_done":
            exp = _call("done", summary=f'"{label}" is already {want}.')
            amatch = {"done": {"summary": {"mode": "any"}}}
        elif variant == "tab_switch":
            exp = _call("click", element_id=tab_ids[tab])
        else:
            exp = _call("scroll", direction="down", amount=1)
            amatch = {"scroll": {"amount": {"mode": "any"}}}
        return _pack(ctx, hp, app, variant, task, sc, exp, amatch)

    if kind == "nav":
        current, link = rng.sample(app.nav, 2)
        task = T("nav").format(link=link, app=app.name)
        sc = Screen(app, current)
        ids = sc.nav(current)
        sc.add("heading", current)
        sc.add("searchbox", app.search, "empty")
        sc.add("button", "Refresh")
        sc.add("button", "Help")
        return _pack(ctx, hp, app, kind, task, sc, _call("click", element_id=ids[link]), amatch)

    if kind in ("search_type", "search_enter"):
        q = _value(ctx, app.item_pool if app.item_pool != "ref" else "text:query")
        task = T("search").format(q=q, app=app.name)
        page = app.list_page
        sc = Screen(app, page)
        sc.nav(page)
        sc.add("heading", page)
        if kind == "search_type":
            sid = sc.add("searchbox", app.search, "empty")
            exp = _call("type_text", element_id=sid, text=q)
        else:
            sc.add("searchbox", app.search, f'value: "{q}", focused')
            exp = _call("press_key", key="Enter")
        sc.add("text", f"Showing all {app.item_noun}s (no search applied)")
        sc.add("button", "Filters")
        sc.add("button", f"New {app.item_noun}")
        return _pack(ctx, hp, app, kind, task, sc, exp, amatch)

    if kind in ("select_open", "select_pick"):
        label, opts = rng.choice(app.selects)
        current, option = rng.sample(opts, 2)
        task = T("select").format(label=label, option=option, app=app.name)
        sc = Screen(app, "Settings")
        sc.nav()
        sc.add("heading", "Settings")
        target = None
        for lab, o in app.selects:
            if lab == label:
                cid = sc.add("combobox", lab, f'value: "{current}", ' + ("collapsed" if kind == "select_open" else "expanded"))
                if kind == "select_pick":
                    for opt in o:
                        oid = sc.add("option", opt, "selected" if opt == current else None)
                        if opt == option:
                            target = oid
                else:
                    target = cid
            else:
                sc.add("combobox", lab, f'value: "{rng.choice(o)}", collapsed')
        sc.add("button", "Restore defaults")
        return _pack(ctx, hp, app, kind, task, sc, _call("click", element_id=target), amatch)

    if kind in ("dialog_confirm", "check_last"):
        items = _distinct(ctx, app.item_pool, 5)
        page = app.list_page
        sc = Screen(app, page)
        sc.nav(page)
        sc.add("heading", page)
        if kind == "dialog_confirm":
            item = rng.choice(items)
            task = T("dialog").format(delete=app.delete.lower(), noun=app.item_noun, item=item, app=app.name)
            for it in items:
                sc.add("listitem", it)
            sc.add("dialog", f"{app.delete} '{item}'?", "open, in front of the page")
            buttons = [app.delete, "Cancel"]
            rng.shuffle(buttons)
            bid = {b: sc.add("button", b) for b in buttons}
            exp = _call("click", element_id=bid[app.delete])
        else:
            chosen = rng.sample(items, rng.choice([2, 3]))
            last = rng.choice(chosen)
            task = T("check").format(noun=app.item_noun, items=_quoted_list(chosen), app=app.name)
            ids = {}
            for it in items:
                ids[it] = sc.add("checkbox", it, "checked" if it in chosen and it != last else "unchecked")
            sc.add("button", "Export selected")
            exp = _call("click", element_id=ids[last])
        return _pack(ctx, hp, app, kind, task, sc, exp, amatch)

    assert kind == "escape"
    task = T("escape").format(overlay=app.overlay, app=app.name)
    page = rng.choice(app.nav)
    sc = Screen(app, page)
    sc.add("dialog", app.overlay.capitalize(), "open, covers the whole window")
    sc.add("text", "This view has no close button. Press Escape to close it.")
    sc.add("button", "Zoom in")
    sc.add("button", "Zoom out")
    return _pack(ctx, hp, app, kind, task, sc, _call("press_key", key="Escape"), amatch)


def _pack(ctx, hp, app, scenario, task, sc, exp, amatch):
    return {"task": task, "screen": sc.render(ctx.rng.choice(hp["intro"])), "expected": exp,
            "arg_match": amatch, "scenario": scenario, "app": app.name}
