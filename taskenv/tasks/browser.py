"""Browser (a web browser in the style of Safari, with a small invented web): start state and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
"""
import datetime
import re

from ..oracle import Click, Key, Reveal, Type
from . import pools
from .base import Spec, by_id, cond, norm, only, say, task, verdict

SIZE = (1080, 680)
WIN = '.win[data-app="browser"] '
START = "favorites://"

# What may differ when a page was visited on the way: where the tabs that were open are, and their history.
NAV = ("browser.tabs.*.url", "browser.tabs.*.back*", "browser.tabs.*.fwd*")
NEW_TAB = ("browser.tabs.+*", "browser.active", "browser.next")

# ------------------------------------------------------------------ word pools (invented for this test set: no real sites, brands or people)
TOWNS = ["Marlow Quay", "Northbank", "Aldermere", "Fernhollow", "Saltmarsh", "Kestrel Valley", "Harrowfield", "Thistledown", "Larkspur Bay", "Eastmoor"]
PLACES = ["Alder Row", "Brightwater", "Fennick Street", "Quayside", "Mulberry Lane", "Old Mill", "Larch Avenue", "Summerfield", "Bell Yard", "Tanner's Gate"]
STREETS = ["Quay Road", "Mill Lane", "Station Parade", "Chapel Street", "Orchard Rise", "Weaver's Walk", "Lower Green", "Foundry Row"]
CLINICS = {
    "dental": {"names": ["{} Dental Care", "{} Family Dentistry", "{} Dental Studio"], "title": "Dr ",
               "tagline": "Gentle, unhurried dental care for the whole family.",
               "services": ["Routine check-up", "Cleaning and polish", "Whitening consultation", "Filling", "Emergency visit",
                            "Children's appointment", "Orthodontic review", "Crown fitting"]},
    "physio": {"names": ["{} Physiotherapy", "{} Physio Clinic"], "title": "",
               "tagline": "Hands-on physiotherapy that gets you moving again.",
               "services": ["Initial assessment", "Sports massage", "Back and neck session", "Post-surgery rehab", "Running gait analysis",
                            "Follow-up session", "Shoulder clinic"]},
    "eye": {"names": ["{} Eye Clinic", "{} Opticians"], "title": "Dr ",
            "tagline": "Careful eye tests, and glasses that actually fit.",
            "services": ["Full eye test", "Contact lens fitting", "Children's vision check", "Glasses adjustment", "Dry eye consultation",
                         "Driving vision test", "Lens aftercare"]},
}
GRID = [f"{m // 60:02d}:{m % 60:02d}" for m in range(8 * 60 + 30, 17 * 60 + 1, 30)]        # 08:30 ... 17:00
EVENING = ["18:00", "18:30", "19:00", "19:30", "07:00", "07:30"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FULLDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
PAPERS = ["Courier", "Post", "Ledger", "Gazette", "Record", "Herald"]
BRIEFS = [
    ["Weather", "Fog is expected on the estuary road until mid-morning; drivers are asked to allow extra time."],
    ["Schools", "The primary school on Larch Avenue reopens on Monday after repairs to its heating."],
    ["Sport", "The under-16 rowing crew finished second at the regional regatta, their best result in nine years."],
    ["Council", "A public meeting on the new cycle lanes takes place at the town hall on Thursday at seven."],
    ["Markets", "The Saturday market moves to the quay for four weeks while the square is repaved."],
    ["Culture", "The film society opens its winter season with a programme of silent comedies and live piano."],
]
ARTICLES = [
    {"section": "Transport", "slug": "night-tram-returns", "role": "Transport correspondent",
     "title": "Night tram to return to {town} after two-year break",
     "stand": "The late service between the harbour and the hospital will run again from next month, with new low-floor carriages and a flat fare.",
     "caption": "The line passes the old quarter on its way to the harbour terminus. Illustration: {paper}",
     "quote": "“That is not a transport system, that is half of one.”",
     "paras": [
         "The night tram that once carried bar staff, nurses and the last stragglers of the evening across {town} will return next month, the transport authority confirmed on Tuesday. The service was suspended two years ago when the old depot on Quay Road was closed for repairs that took far longer than planned.",
         "From the first Friday of the month, trams will leave the harbour terminus every twenty minutes between midnight and five in the morning. The route follows the daytime line as far as the market, then turns north past the university to finish at the hospital gates.",
         "{p1}, who chairs the authority's operations board, said the decision followed a survey of more than four thousand residents. “People told us the same thing again and again,” {l1} said. “They can get into the centre in the evening, but they cannot get home. That is not a transport system, that is half of one.”",
         "The six carriages that will work the night timetable are new. They have low floors, wider doors and space for four bicycles, and they are noticeably quieter than the stock they replace, which matters on a line that passes within a few metres of bedroom windows.",
         "Fares will be simpler too. A single journey at night will cost the same flat price whatever the distance, and daytime season tickets will be valid without a supplement. Staff at the hospital, who lobbied hardest for the service, will travel free during a three-month trial.",
         "Not everyone is pleased. Residents of Alder Row, where the line runs down a narrow street, have asked for a lower speed limit after midnight. {p2}, who has lived there for thirty years, welcomes the trams but not the bell. “Ring it at noon if you must,” {l2} said. “Not at three in the morning.”",
         "The authority says drivers will be told to use the bell only in an emergency on that stretch, and that the new carriages brake more smoothly than the old ones. A noise survey will be carried out after the first eight weeks and the results published in full.",
         "Businesses near the harbour expect the change to be felt quickly. {p3}, who runs a late café beside the terminus, plans to stay open until two at weekends. “For two years my staff have been leaving early to catch the last bus,” {l3} said. “Now the customers can stay, and so can we.”",
         "The authority has set itself a modest target of nine hundred passengers a night by the spring. If the numbers hold, a second night route to the eastern suburbs will be considered next year. For now, the first tram leaves the harbour at three minutes past midnight.",
     ]},
    {"section": "Business", "slug": "bakers-buy-the-old-mill", "role": "Business reporter",
     "title": "Bakers' cooperative buys the old {town} mill",
     "stand": "A group of forty members has raised enough to keep the building standing, and plans to be selling bread from it by the summer.",
     "caption": "The mill has stood empty at the edge of the town for eleven years. Illustration: {paper}",
     "quote": "“It took us an embarrassingly long time to notice that we were somebody.”",
     "paras": [
         "The stone mill at the edge of {town}, empty for eleven years and twice scheduled for demolition, has been bought by a cooperative of local bakers. The sale was completed on Monday for a price that neither side would disclose, though both described it as fair.",
         "The cooperative, which has forty members and began in a rented kitchen behind the sports hall, intends to restore one of the two millstones and to open a bakery and a small shop on the ground floor. The upper floors will be let as workshops.",
         "{p1}, one of the founders, said the group had been looking for premises for three years. “We kept walking past the mill and saying somebody should do something,” {l1} said. “It took us an embarrassingly long time to notice that we were somebody.”",
         "The building needs a good deal of work. The roof is sound, but the water wheel has not turned since the channel was diverted, and the floor of the grain store has rotted through in two places. An engineer's report puts the cost of the first phase at a little under the sum the members have already raised.",
         "Most of that money came in small amounts. More than six hundred households bought a share, the cheapest of which cost about the price of ten loaves. Shareholders will receive no dividend, but they will have a vote at the annual meeting and a discount on bread.",
         "The council, which owned the site, had received a higher offer from a developer who wanted to build flats. {p2}, the councillor responsible for planning, said the decision was not difficult in the end. “Flats can go in many places,” {l2} said. “There is only one mill.”",
         "Local farmers are watching with interest. Two have already agreed to grow older varieties of wheat that suit stone milling, and a third is experimenting with rye. If the harvest is good, the first flour ground in the building for forty years could be on sale in the autumn.",
         "There are sceptics. {p3}, who ran the last commercial bakery in the town until it closed, wished the group well but warned that the hours are brutal and the margins thin. “Everybody loves the smell,” {l3} said. “Fewer people love the alarm clock at half past two.”",
         "The cooperative says it knows what it has taken on. Work on the grain store begins next week, volunteers are wanted for the weekend after, and the members hope to sell their first loaf from the mill door on midsummer morning.",
     ]},
    {"section": "Culture", "slug": "library-to-open-late", "role": "Culture reporter",
     "title": "{town} library to open late after record year",
     "stand": "Borrowing rose by a third in twelve months. From January the central branch will stay open until ten on weekdays.",
     "caption": "The central library, where every desk is taken by mid-afternoon. Illustration: {paper}",
     "quote": "“It is the cheapest warm, well-lit room we can offer, and it comes with books.”",
     "paras": [
         "The central library in {town} will stay open until ten o'clock on weekday evenings from January, after a year in which more books were borrowed than at any time since records began. The extended hours will be tried for six months and made permanent if they are used.",
         "Figures published this week show that loans rose by a third over the past twelve months. The increase was sharpest among readers under twenty-five, a group the library had all but given up on a decade ago, and among people borrowing cookery books, which staff put down to the price of eating out.",
         "{p1}, the head librarian, said the building had changed more than the readers had. “We took out the turnstiles, we let people bring coffee in and we stopped telling them to be quiet on the ground floor,” {l1} said. “It turns out that was most of what was wrong.”",
         "The upper reading room remains silent, and is busier than ever. On weekday afternoons every one of its hundred and twenty desks is taken by three o'clock, largely by students who say they cannot work at home. The late opening is meant chiefly for them.",
         "The change will cost the council the wages of four additional members of staff. {p2}, who holds the culture budget, said the sum was small beside what the town spends on almost anything else. “It is the cheapest warm, well-lit room we can offer,” {l2} said, “and it comes with books.”",
         "Some of the new readers have arrived by an unexpected route. The library began lending tools two years ago, starting with a single drill, and now keeps more than three hundred items, from sewing machines to a telescope. One borrower in five last year took home something that was not a book.",
         "The branch libraries will not share in the longer hours for now, a decision that has disappointed residents of the northern estates. {p3}, who runs a homework club at the smallest branch, said the children there are the ones who most need somewhere to go in the evening.",
         "The council has promised to look again in the summer. In the meantime a free evening bus will run from the northern estates to the central library on Tuesdays and Thursdays, leaving at half past six and returning when the building closes.",
         "The first late evening is the second Monday of January. The library will mark it with a reading in the main hall, and the café, which has also agreed to keep longer hours, will serve soup until the doors are locked.",
     ]},
]
COMPANIES = [
    ("Brindle and Oak", "Furniture built to be repaired, not replaced.", "We design and make tables, chairs and shelving in our own workshop, and we sell the spare parts for every piece we have ever made."),
    ("Quillfeather Software", "Scheduling tools for small clinics and surgeries.", "Four thousand practices use our calendar every day. We keep the product small, the support fast and the prices on the website."),
    ("Tamarind Logistics", "Same-day freight for the towns the motorways miss.", "Our vans and drivers connect two hundred small towns to the main depots, six days a week, with a tracking page that tells the truth."),
    ("Osprey Valley Rail", "Regional trains, run on time.", "We operate eleven stations and forty services a day on the valley line, and we publish our punctuality figures every morning."),
    ("Lanternworks", "Lighting design for theatres and public spaces.", "From village halls to the new concert house, we plan, build and install lighting that people notice only when it is missing."),
    ("Mossgiel Energy", "Community-owned wind and solar.", "Our members own nine turbines and three solar fields between them. The power is sold locally and the surplus pays for insulation."),
    ("Pebblebrook Foods", "Honest soups and stews from a kitchen in the valley.", "We cook in small batches with vegetables from farms we can cycle to, and deliver to shops and canteens across the region."),
    ("Hexley Robotics", "Small, patient robots for warehouses.", "Our machines carry shelves so that people do not have to. They are slow, quiet and very hard to knock over."),
]
JOBS = {
    "Data Analyst": ("Finance", ["Build the weekly sales and stock reports", "Keep the forecasting model up to date", "Answer questions from the regional teams with numbers they can trust"]),
    "Product Designer": ("Design", ["Sketch, prototype and test new features with customers", "Keep the design library tidy and documented", "Work with engineers from the first idea to the release"]),
    "Office Manager": ("Operations", ["Keep the office stocked, safe and pleasant to work in", "Welcome visitors and look after new starters on their first day", "Manage suppliers and the monthly facilities budget"]),
    "Support Engineer": ("Customer Support", ["Solve customer problems by email and phone", "Write up recurring issues for the product team", "Take part in the weekend rota one week in six"]),
    "Marketing Lead": ("Marketing", ["Plan the campaigns for the coming year", "Manage a team of three and two agencies", "Report every month on what worked and what did not"]),
    "Payroll Specialist": ("Finance", ["Run the monthly payroll for about two hundred people", "Answer colleagues' questions about pay and tax", "Keep records ready for the annual audit"]),
    "QA Tester": ("Engineering", ["Test each release before it reaches customers", "Write clear bug reports that are easy to reproduce", "Automate the checks that are run most often"]),
    "Warehouse Supervisor": ("Logistics", ["Lead a shift of twelve in the main warehouse", "Plan the loading schedule with the transport desk", "Keep the site safe and the stock count accurate"]),
    "Technical Writer": ("Product", ["Write and maintain the user guides", "Turn release notes into plain English", "Work with support to find the pages that confuse people"]),
    "Account Manager": ("Sales", ["Look after forty existing customers", "Visit the largest accounts twice a year", "Spot problems early and bring in the right colleagues"]),
    "Backend Developer": ("Engineering", ["Build and maintain the services behind the booking system", "Review colleagues' code and have yours reviewed", "Share the on-call duty with five other developers"]),
    "People Partner": ("People", ["Advise managers on hiring, pay and difficult conversations", "Run the twice-yearly review process", "Keep our policies short, fair and up to date"]),
    "Finance Controller": ("Finance", ["Prepare the monthly management accounts", "Model the cost of new projects before they start", "Explain the numbers to people who do not enjoy numbers"]),
    "Field Technician": ("Service", ["Install and service equipment at customer sites", "Keep the van stocked and the paperwork complete", "Train customers to use what you have installed"]),
    "Content Editor": ("Marketing", ["Edit everything we publish, from the website to the newsletter", "Commission freelance writers and photographers", "Keep the style guide alive"]),
    "Operations Coordinator": ("Operations", ["Schedule deliveries and keep customers informed", "Chase what is late and fix what went wrong", "Report the week's numbers every Friday"]),
}
WANTS = ["Two or more years in a similar role", "Clear, friendly written English", "Comfortable working in a small team", "Careful with details and deadlines",
         "Happy to be on site at least two days a week", "Willing to ask questions early", "A full driving licence", "Confident with spreadsheets"]
EXTRAS = [
    ("Pinewood Weather", "Bright spells today, with a light westerly wind", "A dry day for most of the valley. Cloud builds from the west after dark, with rain by Thursday morning.",
     [["Morning", "8°, mist clearing by ten"], ["Afternoon", "13°, sunny intervals"], ["Evening", "9°, dry with a light breeze"]]),
    ("Saffron Table", "Recipe of the week: roasted squash with brown butter and sage", "One tray, one pan and about an hour. It is better the next day, if any is left.",
     [["Prep", "20 minutes"], ["Cook", "45 minutes"], ["Serves", "Four, with leftovers"]]),
    ("Rook and Castle Chess Club", "Club night is Thursday: doors at seven, all levels welcome", "We meet upstairs at the old corn exchange. Boards and clocks are provided, and so is tea.",
     [["Beginners", "Coaching table from 19:00"], ["League", "Home match on the 19th"], ["Juniors", "Saturday mornings at ten"]]),
    ("Slowboat Travel", "Three slow routes for a long weekend", "No flights and no motorways: journeys where getting there is most of the point.",
     [["By rail", "The coast line, end to end"], ["By water", "Two days on the canal"], ["On foot", "The ridge path in four stages"]]),
    ("Tinker Street Cycles", "Winter service: book your bike in before the first frost", "A family workshop since 1988. We fix everything with two wheels, and a few things with three.",
     [["Basic", "Brakes, gears and a safety check"], ["Full", "Strip, clean and rebuild"], ["Wheels", "Truing and new spokes"]]),
    ("Wavelength Radio Guide", "Tonight at nine: a documentary on the last lighthouse keepers", "Listings for the week ahead, chosen by people who still listen to the radio.",
     [["19:00", "The Evening Record"], ["21:00", "Keepers of the Light"], ["22:30", "Late Jazz"]]),
    ("Hobbs Lane Allotments", "Plots are available from March. Join the waiting list now", "Forty-two plots, a shared shed and a tap that mostly works. New growers are very welcome.",
     [["Full plot", "250 square metres"], ["Half plot", "Ideal for beginners"], ["Raised beds", "For members who prefer not to dig"]]),
    ("Quire and Quill", "New in: notebooks with paper that loves fountain pens", "A small stationery shop with a workbench at the back. Everything is made to be refilled.",
     [["Notebooks", "Dotted, lined and plain"], ["Pens", "Refillable, from our own bench"], ["Ink", "Twelve colours, mixed in small batches"]]),
]


def slug(text, sep=""):
    return sep.join(re.findall(r"[a-z0-9]+", text.lower().replace("'", "")))


def site(rng):
    """The invented web of one episode: a clinic with a booking form, a local paper, a company with a careers page, a few small sites."""
    town = rng.choice(TOWNS)
    people = pools.people(rng, 8)
    kind = rng.choice(sorted(CLINICS))
    c = CLINICS[kind]
    name = rng.choice(c["names"]).format(rng.choice(PLACES))
    host = slug(name) + ".example"
    # the menu bar's "today" is between 2 and 20 November 2026: appointments are offered after it, the article is older
    day = datetime.date(2026, 11, 23) + datetime.timedelta(days=7 * rng.randint(0, 2) + rng.randint(0, 4))
    dates = []
    while len(dates) < 5:
        if day.weekday() < 5:
            dates.append(f"{WEEKDAYS[day.weekday()]} {day.day} {pools.MONTHS[day.month - 1]}")
        day += datetime.timedelta(days=1)
    times = sorted(rng.sample(GRID, 10))
    taken = set(rng.sample(times, 2))
    clinic = {"kind": kind, "name": name, "tagline": c["tagline"], "home": f"https://{host}", "book": f"https://{host}/book",
              "since": str(rng.randint(1978, 2014)), "street": f"{rng.randint(2, 88)} {rng.choice(STREETS)}", "hours": "Monday to Friday, 08:30 to 17:30",
              "team": [c["title"] + p for p in people[:3]], "services": rng.sample(c["services"], 5), "dates": dates,
              "slots": [{"t": t, "taken": t in taken} for t in times]}

    paper = f"The {town} {rng.choice(PAPERS)}"
    host = slug(paper[4:]) + ".example"
    art = rng.choice(ARTICLES)
    fill = {"town": town, "paper": paper}
    for i, p in enumerate(people[4:7], 1):
        fill[f"p{i}"], fill[f"l{i}"] = p, p.split()[-1]
    d = datetime.date(2026, 10, 19) + datetime.timedelta(days=rng.randint(0, 13))
    news = {"name": paper, "home": f"https://{host}", "date": f"{FULLDAYS[d.weekday()]} {d.day} {d.strftime('%B')} 2026", "briefs": rng.sample(BRIEFS, 4),
            "article": {"url": f"https://{host}/{slug(art['section'])}/{art['slug']}", "section": art["section"], "title": art["title"].format(**fill),
                        "stand": art["stand"], "author": people[3], "role": art["role"], "read": f"{rng.randint(5, 8)} min read",
                        "caption": art["caption"].format(**fill), "quote": art["quote"], "paras": [p.format(**fill) for p in art["paras"]]}}

    cname, tagline, about = rng.choice(COMPANIES)
    host = slug(cname) + ".example"
    jobs = []
    for i, title in enumerate(rng.sample(sorted(JOBS), 8), 1):
        team, duties = JOBS[title]
        place = rng.choice([town, town, "Remote", rng.choice([t for t in TOWNS if t != town])])
        low = rng.randrange(28, 52) * 1000
        jobs.append({"id": f"j{i}", "title": title, "team": team, "place": place, "type": rng.choice(["Full-time", "Full-time", "Part-time", "Contract"]),
                     "pay": f"£{low:,} to £{low + rng.choice([4, 5, 6, 8]) * 1000:,}", "url": f"https://{host}/careers/{slug(title, '-')}",
                     "about": f"{cname} is looking for {'an' if title[0] in 'AEIOU' else 'a'} {title} to join the {team} team"
                              f"{', working remotely' if place == 'Remote' else ' in ' + place}. You will report to {people[7]} and work alongside {rng.randint(3, 11)} colleagues.",
                     "duties": duties, "wants": rng.sample(WANTS, 3)})
    company = {"name": cname, "tagline": tagline, "about": about, "home": f"https://{host}", "careers": f"https://{host}/careers",
               "since": str(rng.randint(1994, 2019)), "people": rng.randint(40, 180), "jobs": jobs}
    extras = [{"name": n, "url": f"https://{slug(n)}.example", "heading": h, "blurb": b, "cards": cards} for n, h, b, cards in rng.sample(EXTRAS, 4)]
    return {"town": town, "clinic": clinic, "news": news, "company": company, "extras": extras}


def main_pages(st):
    """The pages a favourite may point to: (title in the favourites bar, address)."""
    return [(st["clinic"]["name"], st["clinic"]["home"]), ("Appointments", st["clinic"]["book"]), (st["news"]["name"], st["news"]["home"]),
            (st["company"]["name"], st["company"]["home"]), (st["company"]["name"].split()[0] + " Careers", st["company"]["careers"])]


def default(rng):
    st = site(rng)
    marks = rng.sample(main_pages(st), rng.randint(2, 3)) + [(x["name"], x["url"]) for x in rng.sample(st["extras"], 3)]
    rng.shuffle(marks)
    return {"tabs": [{"id": "t1", "url": START, "back": [], "fwd": []}], "active": "t1",
            "bookmarks": [{"id": f"b{i}", "title": title, "url": url} for i, (title, url) in enumerate(marks, 1)],
            "forms": {"booking": {"name": "", "email": "", "service": "", "date": st["clinic"]["dates"][rng.randrange(3)], "slot": None,
                                  "reminder": False, "submitted": False},
                      "newsletter": {"email": "", "subscribed": False}},
            "saved": [], "site": st, "next": 100, "ui": {"address": None, "err": None}}


# ------------------------------------------------------------------ helpers
def show(S, *urls, active=0, back=None):
    """Open these pages in tabs t1, t2, ...; the tab number `active` is in front."""
    s = S.apps["browser"]
    s["tabs"] = [{"id": f"t{i}", "url": u, "back": list(back if back is not None else ([START] if u != START else [])), "fwd": []} for i, u in enumerate(urls, 1)]
    s["active"] = f"t{active + 1}"
    S.open("browser")
    return s["tabs"][active]


def shown(url):
    return url.replace("https://", "")


def unmarked(s, urls):
    marked = {b["url"] for b in s["bookmarks"]}
    return [u for u in urls if u not in marked]


def simple_pages(s):
    return [u for _, u in main_pages(s["site"])] + [x["url"] for x in s["site"]["extras"]]


def front_tab(st):
    b = st["apps"]["browser"]
    return by_id(b["tabs"], b["active"]) or {}


def customer(rng):
    person = pools.person(rng)
    return person, pools.email_of(person, rng)


# ------------------------------------------------------------------ tasks
@task("browser.book_appointment", "typing")
def book_appointment(S):
    s = S.apps["browser"]
    c = s["site"]["clinic"]
    person, email = customer(S.rng)
    service = S.rng.choice(c["services"])
    slot = S.rng.choice([x["t"] for x in c["slots"] if not x["taken"]])
    show(S, c["book"], back=[START, c["home"]])

    def check(st, init):
        b, b0 = st["apps"]["browser"]["forms"]["booking"], init["apps"]["browser"]["forms"]["booking"]
        sent = b["submitted"] if isinstance(b["submitted"], dict) else {}
        return verdict(cond(sent, "the booking form was not sent"),
                       cond(norm(sent.get("name")) == norm(person), f"the name on the booking is “{sent.get('name')}”"),
                       cond(norm(sent.get("email")) == norm(email), f"the email on the booking is “{sent.get('email')}”"),
                       cond(sent.get("service") == service, f"the service on the booking is “{sent.get('service')}”"),
                       cond(sent.get("slot") == slot, f"the time on the booking is {sent.get('slot')}"),
                       cond(sent.get("date") == b0["date"], "the date of the booking was changed"),
                       cond(sent.get("reminder") == b0["reminder"], "the reminder box was changed"),
                       only(st, init, "browser.forms.booking.*", *NAV))
    return Spec(request=say(S.rng, f"Book “{service}” at {slot} on this form for {person}, email {email}, and send it.",
                            f"Please fill in this booking form for me ({person}, {email}): the service is “{service}” and the time is {slot}. Then book the appointment."),
                steps=[Click(WIN + '.field[data-arg="name"]', "Click the “Full name” field on the booking form"), Type(person),
                       Click(WIN + '.field[data-arg="email"]', "Click the “Email” field on the booking form"), Type(email),
                       Click(WIN + '.popup[data-select="service"]', "Click the “Service” pop-up button on the booking form"),
                       Click(f'.menu-item:has(.mi-label:text-is("{service}"))', f"Click “{service}” in the list"),
                       Reveal(WIN + f'.bw-slot[data-arg="{slot}"]'),
                       Click(WIN + f'.bw-slot[data-arg="{slot}"]', f"Click the “{slot}” time button on the booking form"),
                       Reveal(WIN + ".bw-go"),
                       Click(WIN + ".bw-go", "Click the “Book appointment” button")],
                check=check)


@task("browser.go_to_address", "typing")
def go_to_address(S):
    s = S.apps["browser"]
    target = S.rng.choice(unmarked(s, simple_pages(s)))
    here = S.rng.choice([START, START, S.rng.choice([b["url"] for b in s["bookmarks"]])])
    show(S, here)
    return Spec(request=say(S.rng, f"Open {shown(target)} in the browser.", f"Take me to the page at {shown(target)} please."),
                steps=[Click(WIN + ".bw-addr input", "Click the address field at the top of the browser window"), Type(shown(target)), Key("enter")],
                check=lambda st, init: verdict(cond(front_tab(st).get("url") == target, f"the page in front is {front_tab(st).get('url')}"),
                                               only(st, init, *NAV, *NEW_TAB)))


@task("browser.open_favourite", "single")
def open_favourite(S):
    s = S.apps["browser"]
    b = S.rng.choice(s["bookmarks"])
    here = S.rng.choice([START] + [u for u in simple_pages(s) if u != b["url"]])
    show(S, here)
    return Spec(request=say(S.rng, f"Open {b['title']} from my favourites.", f"Go to my “{b['title']}” favourite."),
                steps=[Click(WIN + f'.bw-bm[data-arg="{b["id"]}"]', f"Click “{b['title']}” in the favourites bar under the address field")],
                check=lambda st, init: verdict(cond(front_tab(st).get("url") == b["url"], f"the page in front is {front_tab(st).get('url')}"),
                                               only(st, init, *NAV, *NEW_TAB)))


@task("browser.save_job", "chain")
def save_job(S):
    s = S.apps["browser"]
    co = s["site"]["company"]
    if S.rng.random() < 0.4:
        s["saved"] = [S.rng.choice(co["jobs"])["id"]]
    j = S.rng.choice([j for j in co["jobs"] if j["id"] not in s["saved"]])
    show(S, co["careers"], back=[START, co["home"]])

    def check(st, init):
        now, before = st["apps"]["browser"]["saved"], init["apps"]["browser"]["saved"]
        return verdict(cond(j["id"] in now, f"the job “{j['title']}” is not saved"),
                       cond(now == before + [j["id"]], "the list of saved jobs changed in another way"),
                       only(st, init, "browser.saved", *NAV))
    return Spec(request=say(S.rng, f"Open the {j['title']} job on this careers page and save it.", f"Save the “{j['title']}” role from this list of jobs for me."),
                steps=[Reveal(WIN + f'.bw-job[data-arg="{j["url"]}"]'),
                       Click(WIN + f'.bw-job[data-arg="{j["url"]}"]', f"Click the role “{j['title']}” in the list of open roles", at=(0.15, 0.5)),
                       Click(WIN + ".bw-save", "Click the “Save job” button")],
                check=check)


@task("browser.subscribe_newsletter", "scroll")
def subscribe_newsletter(S):
    s = S.apps["browser"]
    news = s["site"]["news"]
    _, email = customer(S.rng)
    show(S, news["article"]["url"], back=[START, news["home"]])

    def check(st, init):
        n = st["apps"]["browser"]["forms"]["newsletter"]
        return verdict(cond(n["subscribed"] is True, "nobody was subscribed to the newsletter"),
                       cond(norm(n["email"]) == norm(email), f"the subscribed address is “{n['email']}”"),
                       only(st, init, "browser.forms.newsletter.*", *NAV))
    return Spec(request=say(S.rng, f"Sign {email} up for the newsletter at the bottom of this article.",
                            f"There is a newsletter sign-up at the end of this article. Subscribe with {email} please."),
                steps=[Reveal(WIN + ".bw-sub .field"),
                       Click(WIN + ".bw-sub .field", "Click the “Email address” field in the newsletter box at the bottom of the article"), Type(email),
                       Reveal(WIN + ".bw-subgo"),
                       Click(WIN + ".bw-subgo", "Click the “Subscribe” button")],
                check=check)


@task("browser.add_bookmark", "menu")
def add_bookmark(S):
    s = S.apps["browser"]
    st = s["site"]
    url = S.rng.choice(unmarked(s, simple_pages(s)) + [st["news"]["article"]["url"], S.rng.choice(st["company"]["jobs"])["url"]])
    show(S, url)

    def check(st, init):
        old = {b["id"] for b in init["apps"]["browser"]["bookmarks"]}
        new = [b for b in st["apps"]["browser"]["bookmarks"] if b["id"] not in old]
        return verdict(cond(new, "no favourite was added"),
                       cond(len(new) == 1, "more than one favourite was added"),
                       cond(new and new[0]["url"] == url, "the new favourite is not this page"),
                       only(st, init, "browser.bookmarks.+*", "browser.next", *NAV))
    return Spec(request=say(S.rng, "Add this page to my favourites.", "Bookmark the page I'm looking at."),
                steps=[Click('.mb-item:text-is("Bookmarks")', "Click “Bookmarks” in the menu bar"),
                       Click('.menu-item:has(.mi-label:text-is("Add Bookmark"))', "Click “Add Bookmark” in the menu")],
                check=check)


@task("browser.close_tab", "shortcut")
def close_tab(S):
    s = S.apps["browser"]
    urls = S.rng.sample(simple_pages(s) + [s["site"]["news"]["article"]["url"]], 3)
    t = show(S, *urls, active=S.rng.randrange(3))

    def check(st, init):
        b = st["apps"]["browser"]
        return verdict(cond(by_id(b["tabs"], t["id"]) is None, "that tab is still open"),
                       cond(len(b["tabs"]) == 2 and by_id(b["tabs"], b["active"]) is not None, "the other two tabs are not both open"),
                       only(st, init, f"browser.tabs.-{t['id']}", "browser.active"))
    return Spec(request=say(S.rng, "Close the tab I'm on and keep the other two open.", "Close the current tab."),
                steps=[Key("cmd+w")], check=check)


@task("browser.reminder_ticked", "already_done")
def reminder_ticked(S):
    s = S.apps["browser"]
    c = s["site"]["clinic"]
    b = s["forms"]["booking"]
    b["reminder"] = True
    if S.rng.random() < 0.5:
        b["name"], b["email"] = customer(S.rng)
    show(S, c["book"], back=[START, c["home"]])
    return Spec(request=say(S.rng, "Make sure the reminder box is ticked on this booking form.",
                            "I want a reminder the day before the appointment. Check that the option is switched on in this form."),
                steps=[], kind="already_done", check=lambda st, init: only(st, init, *NAV))


@task("browser.no_such_slot", "infeasible")
def no_such_slot(S):
    s = S.apps["browser"]
    c = s["site"]["clinic"]
    person, email = customer(S.rng)
    service = S.rng.choice(c["services"])
    offered = {x["t"] for x in c["slots"]}
    ghost = S.rng.choice([t for t in GRID + EVENING if t not in offered])
    show(S, c["book"], back=[START, c["home"]])

    def check(st, init):
        # Nothing may be booked. Fields filled in before noticing that the time is not offered are not held against the agent.
        return verdict(cond(st["apps"]["browser"]["forms"]["booking"]["submitted"] is False, "a booking was sent"),
                       only(st, init, *(f"browser.forms.booking.{k}" for k in ("name", "email", "service", "date", "slot", "reminder")), *NAV))
    return Spec(request=say(S.rng, f"Book “{service}” at {ghost} on this form for {person}, email {email}, and send it.",
                            f"Please fill in this booking form for me ({person}, {email}): the service is “{service}” and the time is {ghost}. Then book the appointment."),
                steps=[], kind="infeasible", check=check)
