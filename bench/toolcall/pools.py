"""Seeded value pools. Every base list is partitioned between the three splits
by position (see `part`), so a name, city, title word, etc. that can appear in
`test` can never appear in `dev` or `train`.
"""

SPLITS = ("dev", "test", "train")


def part(seq, split):
    """Deterministic partition of a list: index % 4 == 0 -> dev, 1 -> test, 2 or 3 -> train."""
    seq = list(seq)
    if split == "dev":
        return seq[0::4]
    if split == "test":
        return seq[1::4]
    if split == "train":
        return [x for i, x in enumerate(seq) if i % 4 >= 2]
    raise ValueError(split)


def W(s):
    return [x.strip() for x in s.split("|")]


BASE = {
    "first": W("Mirelle|Odo|Tamsin|Bartholomew|Quilla|Fenwick|Isolde|Garrick|Linnea|Thaddeus|Ottoline|Caspian|"
               "Wrenna|Leopold|Saffron|Ignatius|Delphine|Rufus|Marigold|Ansel|Briony|Cormac|Elowen|Jasper|"
               "Perpetua|Lucian|Rosalind|Emrys|Clementine|Alaric|Henrietta|Phineas|Verity|Barnaby|Celestine|"
               "Dashiell|Eulalia|Florian|Guinevere|Horatio|Imogen|Jericho|Kerensa|Lysander|Minerva|Nicodemus|"
               "Ophira|Percival|Zinnia|Wilfred|Araminta|Evander|Sunniva|Montgomery|Tabitha|Ulric"),
    "last": W("Brambleworth|Quillfeather|Underhollow|Fizzlewick|Thistlewood|Marrowby|Pennywhistle|Cinderfall|"
              "Windlemere|Hollowbrook|Dapplegrim|Stonebarrow|Mossgrove|Bramblethorn|Nettlecombe|Quickwater|"
              "Larkspurrow|Tumblestone|Wickerby|Foxglover|Greywether|Puddlefoot|Sallowmere|Tanglewood|"
              "Umberfield|Vandersnoot|Yarrowmead|Applethwaite|Briarlock|Cobblewick|Dunmorrow|Emberlyn|"
              "Fernhollow|Glimmerstone|Harrowgate|Inkwell|Juniperton|Knottingley|Lanternby|Mistlethorpe|"
              "Nightingrove|Orchardson|Plumridge|Quibbleton|Rushwater|Snoddington|Thornbury|Underwick|"
              "Velloway|Wobblestone|Zephyrine|Ashcombe|Birchwhistle|Copperpot|Dewsbury|Elderkin"),
    "company_a": W("Brindle|Nimbus|Larkfield|Quartzline|Maplewick|Driftwood|Copperleaf|Starling|Halcyon|"
                   "Pinecrest|Ironbark|Saffronia|Tidewater|Glassmere|Foxhollow|Lumenfield|Thornfield|Oakline|"
                   "Riverbend|Silverpine|Wavecrest|Emberfield|Cloudberry|Marlowe|Northgate|Peregrine|Kestrel|"
                   "Juniper|Harborlight|Bluefinch|Stonewell|Amberly"),
    "company_b": W("Logistics|Robotics|Foods|Analytics|Textiles|Outfitters|Labs|Holdings|Bakery|Freight|"
                   "Studios|Pharma|Motors|Systems|Publishing|Ventures|Dairy|Optics|Hardware|Travel|"
                   "Ceramics|Brewing|Aerospace|Timber"),
    "legal": W("Ltd|Inc|Co|GmbH|LLC|Group|Partners|Works"),
    "city_pre": W("Port|Lake|Mount|North|South|East|West|New|Fort|Saint|Upper|Lower|Glen|Old|Cape|Great"),
    "city": W("Velmora|Castellan|Thornwick|Aldermoor|Brightwater|Carrowmere|Dunhallow|Elmsworth|Farrowgate|"
              "Glimmerford|Hartwell|Islemoor|Kestrelford|Larkhaven|Marrowick|Nettlebridge|Oakhampton|Pellam|"
              "Quarrydale|Redmarsh|Silverfen|Tallowick|Umberton|Vexley|Wrenfield|Yarrowby|Zellwick|Ambergate|"
              "Bellhaven|Crowmere|Dovecote|Eastmere|Fallowmead|Greenholt|Hazelmoor|Ivybridge|Jadecliff|"
              "Kingsmere|Lowfield|Mistral Bay"),
    "street": W("Larch|Bramble|Tanner|Mill|Cobbler|Heron|Foundry|Orchard|Quarry|Lantern|Ferry|Abbey|Sparrow|"
                "Willow|Chandler|Mason|Thimble|Saddler|Bellfounder|Gosling|Tinker|Hawthorn|Wheelwright|Curlew"),
    "street_kind": W("Lane|Road|Street|Avenue|Way|Close|Row|Terrace"),
    "topic": W("budget|roadmap|onboarding|vendor|launch|hiring|design|security|inventory|pricing|marketing|"
               "payroll|migration|compliance|branding|logistics|training|research|support|analytics|"
               "procurement|facilities|partnership|retention|quality|audit|strategy|outreach|localization|"
               "accessibility|warranty|packaging"),
    "meet": W("review|sync|kickoff|check-in|retrospective|workshop|briefing|planning session|walkthrough|"
              "standup|debrief|roundtable|town hall|demo|huddle|deep dive"),
    "subj": W("update|question|proposal|summary|reminder|feedback|follow-up|agenda|checklist|timeline|"
              "estimate|handover|invitation|announcement|request|status"),
    "adj": W("ceramic|wool|bamboo|stainless|cordless|folding|waterproof|vintage|ergonomic|insulated|magnetic|"
             "portable|recycled|linen|walnut|copper|enamel|quilted|wireless|compact|solar|leather|canvas|"
             "titanium|striped|rustic|inflatable|padded"),
    "product": W("kettle|blanket|desk lamp|backpack|notebook|water bottle|tent|headphones|keyboard|mug|"
                 "umbrella|toaster|bookshelf|yoga mat|wall clock|frying pan|sleeping bag|speaker|office chair|"
                 "picture frame|plant pot|door mat|tool box|bike helmet|cutting board|laundry basket|"
                 "shoe rack|garden hose"),
    "music_a": W("Glass|Paper|Midnight|Velvet|Copper|Hollow|Silver|Wandering|Electric|Quiet|Crimson|Northern|"
                 "Golden|Restless|Faded|Lunar|Salt|Neon|Borrowed|Distant"),
    "music_b": W("Harbour|Lanterns|Orchard|Tides|Static|Meadow|Engine|Avenue|Signal|Garden|Horizon|Carousel|"
                 "Echo|Satellite|Parade|Rooftops|Compass|Thunder|Postcard|Embers"),
    "band": W("Circuit|Collective|Parade|Assembly|Quartet|Machine|Society|Club|Union|Orchestra|Trio|Project|"
              "Committee|Ensemble|Brigade|Syndicate"),
    "band_a": W("Wren|Thistle|Marble|Falcon|Cinder|Juniper|Otter|Velvet|Paper|Lantern|Pebble|Comet|Saddle|"
                "Bramble|Tundra|Plume"),
    "pl_a": W("Rainy Day|Road Trip|Morning Run|Deep Focus|Sunday Brunch|Late Night|Garden Party|Winter Cabin|"
              "Summer Porch|Study Hall|Gym Hour|Slow Dance|Kitchen Disco|Long Drive|Quiet Evening|Beach Walk"),
    "pl_b": W("Mix|Favourites|Classics|Rotation|Essentials|Vibes|Anthems|Sessions"),
    "message": W(
        "running about ten minutes late|the invoice is attached|can we move this to next week|"
        "thanks for the quick turnaround|I left the keys at the front desk|the shipment arrived safely|"
        "please review the draft when you can|see you at the usual place|the printer on the second floor is jammed again|"
        "happy to help with the handover|let me know if anything changes|the report is ready for sign-off|"
        "I will be working from home|dinner is on me this time|do not forget the charger|the client loved the demo|"
        "we are out of oat milk|call me when you land|parking is behind the building|the door code has changed|"
        "the budget was approved|I have forwarded the contract|the slides need one more pass|lunch is in the fridge|"
        "the meeting room is double booked|great job on the launch|the heating engineer is coming by|"
        "I owe you a coffee|the tickets are booked|your parcel is with the neighbour|the build is green again|"
        "we should celebrate soon|please water the plants|the cat has been fed|backup finished without errors|"
        "the form still needs a signature|traffic is terrible on the ring road|I found your scarf|"
        "the venue confirmed our booking|new badge photos are due"),
    "note": W(
        "buy more printer paper|ask the landlord about the boiler|renew the library card|"
        "compare quotes for the roof repair|book a dentist check-up|return the borrowed ladder|"
        "draft the welcome speech|order a new bike tyre|check the smoke alarm batteries|plan the picnic menu|"
        "back up the holiday photos|repot the fern|update the emergency contact list|find a recipe for lentil soup|"
        "label the storage boxes|send the signed lease|defrost the freezer|replace the hallway bulb|"
        "look into evening pottery classes|cancel the unused gym membership|measure the window for curtains|"
        "tune the piano|pick up the dry cleaning|sharpen the kitchen knives|clean out the gutters|"
        "wrap the birthday present|oil the garden gate|sort the recycling"),
    "review": W(
        "sturdy and well made|arrived earlier than expected|smaller than it looks in the photos|"
        "does exactly what it promises|the colour faded after a month|great value for the price|"
        "instructions were confusing|would happily buy again|a bit noisy but works fine|"
        "packaging was damaged on arrival|far better than my old one|not worth the hype|"
        "comfortable and easy to clean|stopped working after a week|a lovely gift idea|setup took two minutes"),
    "memo": W("rent share|concert tickets|birthday gift|pizza night|taxi home|book club dues|team lunch|"
              "camping gear|utility bill|groceries run|movie night|parking fee|wedding present|ski trip deposit|"
              "coffee beans|bowling night|train fare|garden supplies|vet visit|football kit|museum tickets|"
              "firewood order|paint and brushes|picnic supplies"),
    "room": W("living room|kitchen|bedroom|hallway|garage|office|nursery|attic|basement|dining room|porch|study|"
              "laundry room|guest room|pantry|conservatory|workshop|bathroom|playroom|library nook"),
    "place": W("Home|Gym|Grandma's house|Climbing wall|Dentist|Allotment|Pottery studio|Dog park|Bike shop|"
               "Rehearsal room|Bakery|Tailor|Swimming pool|Chess club|Vet clinic|Boathouse"),
    "issue": W("Login button unresponsive on mobile|Export to CSV drops the last row|Dark mode text is unreadable|"
               "Search results are not sorted|Typo on the pricing page|Crash when uploading large files|"
               "Password reset email never arrives|Tooltip overlaps the menu|Slow load on the dashboard|"
               "Wrong currency symbol at checkout|Calendar shows the wrong week|Avatar upload fails silently|"
               "Broken link in the footer|Notifications arrive twice|Table header does not stick|"
               "Date picker ignores the locale|Print layout cuts off the totals|Session expires too early|"
               "Filter resets after refresh|Chart legend is misaligned|Autosave loses the last sentence|"
               "Map pins disappear when zooming|Audio keeps playing after logout|Drag and drop flickers"),
    "word": W("lantern|harbor|pebble|falcon|quartz|thistle|ember|willow|comet|bramble|saddle|kelp|marble|cinder|"
              "otter|plume|raven|spindle|tundra|velvet|walnut|yonder|zephyr|anchor|beacon|cobalt|dahlia|fjord|"
              "garnet|heron|indigo|jasper|kite|lotus|magnet|nectar"),
    "ext": W("pdf|docx|xlsx|csv|txt|png|pptx|md"),
    "filenoun": W("summary|notes|plan|draft|report|export|backup|minutes|outline|figures|brief|schedule"),
    "foldernoun": W("files|archive|drafts|contracts|photos|reports|invoices|templates|scans|receipts|"
                    "handbooks|proposals"),
    "projnoun": W("Redesign|Migration|Rollout|Pilot|Audit|Relaunch|Expansion|Cleanup|Refresh|Overhaul|"
                  "Upgrade|Study"),
    "dish": W("mushroom risotto|lentil soup|lemon tart|roast vegetables|tomato bruschetta|pumpkin curry|"
              "apple crumble|garlic flatbread|spinach lasagne|barley stew|pear salad|onion tart|chickpea wrap|"
              "plum cake|beet burger|noodle bowl|fig pastry|corn chowder|herb omelette|rice pudding"),
    "rest_a": W("Copper|Salty|Golden|Hungry|Crooked|Velvet|Smoky|Humble|Laughing|Blue|Wandering|Rusty|"
                "Jolly|Sleepy|Brass|Mossy"),
    "rest_b": W("Spoon|Olive|Ladle|Fig|Anchor|Skillet|Radish|Lantern|Pear|Thistle|Goose|Kettle|Walnut|"
                "Turnip|Pepper|Clove"),
    "notenoun": W("ideas|checklist|thoughts|log|plan|wishlist|questions|outline|recap|scratchpad|agenda|"
                  "to-dos"),
    "chnoun": W("team|alerts|random|help|news|standup|social|planning|leads|ops|lounge|updates"),
    "show_a": W("The Last|Midnight|Chasing the|Beyond the|Tales of the|Under the|Return to the|Secrets of the|"
                "Letters from the|Children of the|Whispers in the|Maps of the|Summer at the|Echoes of the|"
                "Nobody at the|Keepers of the"),
    "show_b": W("Lighthouse|Orchard|Caravan|Glacier|Bakery|Observatory|Tramline|Marsh|Foundry|Pavilion|"
                "Reservoir|Archive|Greenhouse|Viaduct|Carnival|Almanac"),
    "book_a": W("Silent|Clockwork|Salt|Paper|Hidden|Burning|Glass|Iron|Winter|Hollow|Scarlet|Seventh|"
                "Forgotten|Crooked|Amber|Drowned"),
    "statusmsg": W("back after lunch|heads down on a deadline|out walking the dog|in a workshop all day|"
                   "reviewing contracts|on a train with patchy signal|pairing with a colleague|"
                   "at the dentist|deep in spreadsheets|covering the front desk|writing documentation|"
                   "packing for the conference"),
    "question": W(
        "How satisfied are you overall?|What should we improve first?|How did you hear about us?|"
        "Would you recommend us to a friend?|How easy was the sign-up?|Which feature do you use most?|"
        "What almost stopped you from buying?|How would you rate the support you received?|"
        "What is missing from the product?|How often do you use it?|Was the price fair?|"
        "What did you like least?|How clear were the instructions?|What would make you come back?|"
        "How long did delivery take?|Is there anything else you want to tell us?"),
    "carrier": W("QV|ZX|XK|YQ|VZ|KJ|JX|QZ|WQ|ZK|XQ|VX"),
    "sheetnoun": W("tracker|totals|log|forecast|roster|ledger|overview|plan|pipeline|register|tally|planner"),
    "prefix": W("feature|fix|chore|hotfix|docs|refactor|test|release"),
}

_UP = "ABCDEFGHJKLMNPQRSTUVWXYZ"


class Pools:
    def __init__(self, split):
        self.split = split
        for name, lst in BASE.items():
            setattr(self, name, part(lst, split))

    # ---- composite generators -------------------------------------------
    def mk_person(self, rng):
        return f"{rng.choice(self.first)} {rng.choice(self.last)}"

    def mk_company(self, rng):
        return f"{rng.choice(self.company_a)} {rng.choice(self.company_b)} {rng.choice(self.legal)}"

    def mk_email(self, rng):
        dom = (rng.choice(self.company_a) + rng.choice(self.company_b)).lower()
        return f"{rng.choice(self.first).lower()}.{rng.choice(self.last).lower()}@{dom}.example"

    def mk_city(self, rng):
        base = rng.choice(self.city)
        if " " not in base and rng.random() < 0.35:
            return f"{rng.choice(self.city_pre)} {base}"
        return base

    def text(self, pool, rng):
        return getattr(self, "t_" + pool)(rng)

    @staticmethod
    def _cap(s):
        return s[:1].upper() + s[1:]

    def t_meeting(self, r):
        return f"{self._cap(r.choice(self.topic))} {r.choice(self.meet)}"

    def t_subject(self, r):
        return f"{self._cap(r.choice(self.topic))} {r.choice(self.subj)}"

    def t_message(self, r):
        return r.choice(self.message)

    def t_note(self, r):
        return r.choice(self.note)

    def t_question(self, r):
        return r.choice(self.question)

    def t_review(self, r):
        return r.choice(self.review)

    def t_memo(self, r):
        return r.choice(self.memo)

    def t_query(self, r):
        return f"{r.choice(self.adj)} {r.choice(self.product)}"

    t_product = t_query

    def t_folder(self, r):
        return f"{self._cap(r.choice(self.topic))} {r.choice(self.foldernoun)}"

    def t_path_dir(self, r):
        return f"/{r.choice(self.word)}/{r.choice(self.foldernoun)}"

    def t_filename(self, r):
        return f"{r.choice(self.topic)}_{r.choice(self.filenoun)}.{r.choice(self.ext)}"

    def t_path(self, r):
        return f"/{r.choice(self.word)}/{r.choice(self.foldernoun)}/{self.t_filename(r)}"

    def t_room(self, r):
        return r.choice(self.room)

    def t_song(self, r):
        return f"{r.choice(self.music_a)} {r.choice(self.music_b)}"

    def t_artist(self, r):
        return f"The {r.choice(self.band_a)} {r.choice(self.band)}"

    def t_playlist(self, r):
        return f"{r.choice(self.pl_a)} {r.choice(self.pl_b)}"

    def t_place(self, r):
        return r.choice(self.place)

    def t_repo(self, r):
        return f"{r.choice(self.word)}-{r.choice(self.filenoun)}"

    def t_issue(self, r):
        return r.choice(self.issue)

    def t_username(self, r):
        return f"{r.choice(self.first)[0]}{r.choice(self.last)}".lower() + str(r.randint(2, 99))

    def t_branch(self, r):
        return f"{r.choice(self.prefix)}/{r.choice(self.word)}-{r.choice(self.topic)}"

    def t_coupon(self, r):
        return f"{r.choice(self.word).upper()}{r.choice([5, 10, 15, 20, 25, 30, 40])}"

    def t_project(self, r):
        return f"{self._cap(r.choice(self.word))} {r.choice(self.projnoun)}"

    def t_dish(self, r):
        return r.choice(self.dish)

    def t_restaurant(self, r):
        return f"The {r.choice(self.rest_a)} {r.choice(self.rest_b)}"

    def t_notetitle(self, r):
        return f"{self._cap(r.choice(self.topic))} {r.choice(self.notenoun)}"

    def t_tag(self, r):
        return r.choice(self.word)

    def t_channel(self, r):
        return f"#{r.choice(self.topic)}-{r.choice(self.chnoun)}"

    def t_statusmsg(self, r):
        return r.choice(self.statusmsg)

    def t_show(self, r):
        return f"{r.choice(self.show_a)} {r.choice(self.show_b)}"

    def t_book(self, r):
        return f"The {r.choice(self.book_a)} {r.choice(self.show_b)}"

    def t_flightno(self, r):
        return f"{r.choice(self.carrier)}{r.randint(100, 2999)}"

    def t_pnr(self, r):
        return "".join(r.choice(_UP + "23456789") for _ in range(6))

    def t_projkey(self, r):
        return r.choice(self.word)[:4].upper()

    def t_ticketkey(self, r):
        return f"{self.t_projkey(r)}-{r.randint(11, 4999)}"

    def t_sheet(self, r):
        return f"{self._cap(r.choice(self.topic))} {r.choice(self.sheetnoun)}"

    def t_cell(self, r):
        return f"{r.choice('ABCDEFGH')}{r.randint(2, 60)}"

    def t_column(self, r):
        return r.choice("ABCDEFGHJK")

    def t_range(self, r):
        c1 = r.choice("ABCD")
        c2 = chr(ord(c1) + r.randint(1, 4))
        r1 = r.randint(1, 5)
        return f"{c1}{r1}:{c2}{r1 + r.randint(5, 40)}"

    def t_word(self, r):
        return r.choice(self.word)

    def t_phone(self, r):
        return f"+1-555-01{r.randint(10, 99)}"

    def t_isbn(self, r):
        return f"978-1-{r.randint(1000, 9999)}-{r.randint(1000, 9999)}-{r.randint(0, 9)}"

    def t_last4(self, r):
        return str(r.randint(1000, 9999))

    def t_street(self, r):
        return f"{r.randint(1, 240)} {r.choice(self.street)} {r.choice(self.street_kind)}"

    def t_zip(self, r):
        return str(r.randint(10000, 98999))

    def t_plate(self, r):
        return f"{r.choice(_UP)}{r.choice(_UP)}{r.randint(10, 99)} {r.choice(_UP)}{r.choice(_UP)}{r.choice(_UP)}"

    def t_host(self, r):
        return f"{r.choice(self.word)}-{r.choice(self.prefix)}-{r.randint(1, 48):02d}"

    def t_table(self, r):
        return f"{r.choice(self.topic)}_{r.choice(self.sheetnoun)}"

    def t_course(self, r):
        return f"{self._cap(r.choice(self.adj))} {self._cap(r.choice(self.topic))} {r.choice(['101', '201', 'Basics', 'Seminar', 'Lab', 'Studio'])}"

    def t_headline(self, r):
        return f"{r.choice(self.topic)} {r.choice(self.subj)}"

    def t_handle(self, r):
        return "@" + r.choice(self.word) + "_" + r.choice(self.first).lower()

    def t_plant(self, r):
        return f"{r.choice(self.adj)} {r.choice(self.word)}"
