"""Multi-step forms: onboarding steppers, a classic installer, a web checkout, a survey."""
from ..data import COMPANIES, PROJECTS
from ..overlays import FORM_FIELDS
from ..splits import PATTERN, owner, pool
from ..ui import esc, CHEV_R, TICK
from ..vocab import C

NAME = "wizard"
KIND = "either"
VARIANTS = {"stepper_top": "train", "sidebar_steps": "train", "installer": "train", "checkout": "dev", "survey": "test"}

C("wz.skip", "Skip for now|Skip this step|Do this later", "", "move on without filling this part in|leave this part empty and carry on|pass over this part of the setup")
C("wz.savedraft", "Save draft|Save and exit|Finish later", "", "keep what I have entered and come back another time|store my progress and leave the setup|pause here without losing my answers")
C("wz.agree", "I accept the terms|I agree to the license|I have read the agreement", "", "confirm that I consent to the legal conditions|tick the box saying I consent to the conditions|give my consent to the legal text")
C("wz.promo", "Apply code|Redeem|Use coupon", "", "have the discount I typed taken off the total|get the voucher I entered deducted|activate the discount I entered")
C("wz.place", "Place order|Pay now|Complete purchase", "lock|shield-check|credit-card", "finalize the transaction and be charged|confirm that I am buying these things|hand over my payment for what is in the basket")
C("wz.editcart", "Edit cart|Change items|Modify basket", "shopping-cart|shopping-bag|shopping-basket|package-open", "go and alter what I am buying|revise the products before paying|adjust what I am about to buy")
C("wz.qtyup", "Increase quantity|Add one|One more", "", "buy an extra unit of {o}|raise the number of {o} by one|bump the count of {o} up", o="this product")
C("wz.qtydown", "Decrease quantity|Remove one|One fewer", "", "buy one unit less of {o}|lower the number of {o} by one|bring the count of {o} down", o="this product")
C("wz.install", "Install|Install now|Begin installation", "", "start copying the program onto this computer|have the setup put the software on my disk|let the setup program do its work")
C("wz.submit", "Submit|Send answers|Submit responses", "", "hand in the questionnaire now that it is filled in|turn in my completed form|send off what I filled in")


def _pool(name, text):
    items = [x.strip() for x in text.replace("\n", "|").split("|") if x.strip()] if isinstance(text, str) else list(text)
    pool(name, items, "train")   # claim labels at import so ownership never depends on run order
    return items


pool("form.fields", FORM_FIELDS, "train")
STEPS = {
    "onb": _pool("wz.steps.onb", """Create account|Personal profile|Team|Workspace|Billing|Integrations|Review|Verification|Preferences|Plan|Security|Invite
Company details|Contact info|Branding|Notifications setup|Permissions|Data import|Goals|Launch|Basics|Experience|Availability|Tax details|Identity check"""),
    "inst": _pool("wz.steps.inst", """Welcome|License|Components|Destination|Shortcuts|Ready to install|Finishing up|Install type|User information|Prerequisites
Additional tasks|Copying files|Setup options|Before you begin|Completed"""),
    "shop": _pool("wz.steps.shop", """Cart|Shipping|Payment|Confirm|Address|Delivery|Summary|Your details|Billing info|Place the order|Information|Basket
Review order|Sign in|Done|Bag|Delivery options|Pay|Order review|Receipt"""),
}
PLANS = _pool("wz.plans", "Starter|Team plan|Business|Enterprise|Free tier|Pro|Scale|Basic|Plus|Premium|Growth|Solo|Studio|Agency|Unlimited")
OPTS = {
    "onb": _pool("wz.opts.onb", """Subscribe to product updates|Enable two-step verification|Share anonymous usage data|Remember this device|Import sample data
Invite teammates later|Join the beta program|Allow remote assistance|Use recommended settings|Send me a weekly digest|Make my profile public|Sync my calendar
Show me a guided tour|Enable keyboard shortcuts|Connect my email"""),
    "inst": _pool("wz.opts.inst", """Create a desktop shortcut|Launch when setup finishes|Add to PATH|Install for all users|Associate file types|Show tips on startup
Create a Start menu entry|Check for updates automatically|Enable crash reports|Pin to taskbar|Add a context menu entry|Register as default app
Download optional fonts|Keep previous settings|Start with the system"""),
    "shop": _pool("wz.opts.shop", """Use billing address for shipping|Gift wrap this order|Text me delivery updates|Email me a receipt|Leave at the door
Include a gift note|Round up for charity|Save my details for next time|Signature on delivery|Combine with my open order|Add delivery insurance
Recyclable packaging only|Send tracking link by email|This is a business purchase|Subscribe and save"""),
}
ADDR = _pool("wz.addr", """Recipient first name|Recipient last name|Address line 1|Recipient name|Street and number|Address line 2|District|Landmark|Town or city
House name|Floor|Building name|Province|ZIP or postcode|County|PO box|Door code|Care of|Contact phone|Prefecture|Entrance|Unit number|Delivery notes
Email for receipt|Ward|Suburb|Block|Estate|Apartment or unit|Parish""")
COMPS = _pool("wz.comps", """Core files|Documentation|Command line tools|Desktop integration|Language packs|Sample projects|Browser extension|Developer SDK
Legacy plugins|Spell checker|Cloud sync agent|Print drivers|Fonts pack|Templates|Offline help|Debug symbols|Shell completions|Media codecs|Update service|Theme pack""")
TYPES = _pool("wz.types", "Typical|Custom install|Complete install|Minimal|Full|Portable|Recommended|Advanced setup|Compact|Server|Workstation|Developer|Kiosk|Network|Repair")
SHIP = _pool("wz.ship", """Standard delivery|Express delivery|Next-day delivery|Pickup point|Economy shipping|Same-day courier|Store pickup|International priority
Locker delivery|Scheduled delivery|Freight|Two-day shipping|Weekend delivery|Green delivery|Parcel shop""")
TOPICS = _pool("wz.topics", """Onboarding|Pricing|Performance|Customer support|Documentation quality|Mobile app|Reliability|Integrations offered|Reporting tools|Ease of setup
Search|Collaboration|Security features|Design|Value for money|Release pace|Training material|Account management|Accessibility options|Community""")
DEPTS = _pool("wz.depts", "Engineering|Marketing|Sales|Finance|Operations|Design|Legal|Customer care|People|Research|Product|Security|Data|Procurement|Facilities")
COUNTRIES = _pool("wz.countries", "Germany|United States|Japan|France|Brazil|Canada|India|Spain|Australia|Netherlands|Sweden|Mexico|Italy|Kenya|South Korea|Poland|Norway|Chile|Portugal|Ireland")
SCALES = [
    ("How much do you agree that the product saves you time?", ["Strongly disagree", "Disagree", "Neither", "Agree", "Strongly agree"]),
    ("Overall, how satisfied are you with the service?", ["Very dissatisfied", "Dissatisfied", "Neutral", "Satisfied", "Very satisfied"]),
    ("How often do you use the mobile app?", ["Never", "Rarely", "Sometimes", "Often", "Always"]),
    ("How likely are you to renew next year?", ["Not at all likely", "Slightly likely", "Moderately likely", "Very likely", "Extremely likely"]),
    ("How would you rate the quality of support?", ["Poor", "Fair", "Good", "Very good", "Excellent"]),
    ("How frequently do you export reports?", ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"]),
    ("How easy was it to get started?", ["Very difficult", "Difficult", "Manageable", "Easy", "Very easy"]),
    ("How important is offline access to you?", ["Not important", "Slightly important", "Important", "Fairly important", "Essential"]),
    ("How much of your work happens in the product?", ["None of it", "A little", "About half", "Most of it", "Nearly all"]),
    ("Did the product meet your expectations?", ["Fell short", "Almost", "Met them", "Exceeded them", "Far exceeded them"]),
    ("How clear was the pricing?", ["Very unclear", "Unclear", "Somewhat clear", "Clear", "Very clear"]),
    ("How fast does the app feel?", ["Very slow", "Slow", "Acceptable", "Fast", "Very fast"]),
    ("How do you feel about the recent redesign?", ["Dislike it a lot", "Dislike it", "No opinion", "Like it", "Love it"]),
    ("How well does the search find what you need?", ["Not at all well", "Not so well", "Fairly well", "Quite well", "Extremely well"]),
    ("How would you describe the learning curve?", ["Very steep", "Steep", "Moderate", "Gentle", "Barely any"]),
]
SCALE_SPLIT = {}
for _i, (_q, _opts) in enumerate(SCALES):   # each scale, with all its answer labels, belongs to one split
    _s = PATTERN[_i % 5]
    SCALE_SPLIT[_q] = (_s, [o for o in _opts if owner(o, _s) == _s])

OKTICK = TICK.replace("<svg", '<svg style="width:13px;height:13px;stroke:currentColor;fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round"')
CSS = """
.wz-num{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:.9em;border:1.5px solid var(--bd2);color:var(--fg1);flex:none;background:var(--bg)}
.wz-num.done{background:var(--ac);border-color:var(--ac);color:var(--acf)}.wz-num.cur{border-color:var(--ac);color:var(--ac)}
.wz-num svg{width:13px;height:13px;stroke:currentColor;fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.wz-line{flex:1 1 0;height:2px;background:var(--bd);min-width:18px}.wz-line.done{background:var(--ac)}
.wz-plan{flex:1 1 0;border:1.5px solid var(--bd);border-radius:max(6px,var(--r2));padding:12px;display:flex;flex-direction:column;gap:4px}
.wz-plan.on{border-color:var(--ac);background:var(--acs)}
.wz-opt{display:flex;align-items:center;gap:6px;padding:0 12px;height:calc(var(--ch) + 6px);border:1px solid var(--bd2);border-radius:999px;white-space:nowrap}
.wz-opt.on{border-color:var(--ac);background:var(--acs2)}
.wz-nps{width:34px;height:34px;border:1px solid var(--bd2);border-radius:var(--r);display:flex;align-items:center;justify-content:center}
.wz-nps.on{background:var(--ac);color:var(--acf);border-color:var(--ac)}
.wz-banner{width:190px;flex:none;background:linear-gradient(160deg,var(--ac),var(--sdk));color:#fff;padding:22px 18px;display:flex;flex-direction:column;gap:8px}
"""


def _value(ctx, label):
    d, rng, low = ctx.d, ctx.rng, label.lower()
    if rng.random() < 0.35:
        return ""
    words = set(low.replace("-", " ").split())
    if "initial" in low:
        return rng.choice("ABDJKLMRST")
    if "project" in low:
        return d.one("projects", PROJECTS)
    if "user" in low or "alias" in low or "nick" in low:
        return d.person().split()[0].lower() + str(rng.randint(2, 99))
    if "name" in low or "owner" in low or "manager" in low or "holder" in low or "assignee" in low:
        return d.person()
    if "email" in low or "reply" in low:
        return d.email_of(d.person())
    if "phone" in low or "mobile" in low or "fax" in low:
        return f"+1 555 01{rng.randint(10, 99)}"
    if "date" in low:
        return d.date(True)
    if "company" in low:
        return d.one("company", COMPANIES)
    if "city" in low or "location" in low or "town" in low:
        return rng.choice(["Lisbon", "Denver", "Osaka", "Leeds", "Tampere"])
    if words & {"code", "id", "number", "zip", "postcode"}:
        return str(rng.randint(10000, 99999))
    return ""


def _fields(ctx, region, k, cols=2, names=None):
    d, rng = ctx.d, ctx.rng
    out = []
    for i, name in enumerate(names or d.take("form.fields", FORM_FIELDS, k)):
        if name.lower() in ("country", "region", "time zone", "category", "priority", "team", "department"):
            opts = d.take("wz.countries", COUNTRIES, 5) if name.lower() in ("country", "region", "time zone") else d.take("wz.depts", DEPTS, 5)
            out.append(ctx.select(name, opts[0] if opts else "Select…", options=opts, region=region))
        else:
            area = 64 if name.lower() in ("notes", "description", "summary", "short bio") else 0
            f = ctx.field(name, _value(ctx, name), ph="", region=region, area=area, focus=i == 1)
            out.append(f'<div style="grid-column:1/-1">{f}</div>' if area else f)
    return f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:12px 16px">{"".join(out)}</div>'


def _checks(ctx, region, k, kind="onb"):
    return "".join(ctx.check(o, ctx.rng.random() < 0.4, region=region) for o in ctx.d.take("wz.opts." + kind, OPTS[kind], k))


def _plans(ctx, region, k=3):
    rng, cards = ctx.rng, []
    sel = rng.randrange(k)
    for i, p in enumerate(ctx.d.take("wz.plans", PLANS, k)):
        attr = ctx.reg("radio", "plan", p, region=region, state=i == sel, refs=[f"the {p} plan card", f"the plan option called {p}"])
        cards.append(f'<div class="wz-plan{" on" if i == sel else ""}"{attr}><div class="row"><span class="b f1">{esc(p)}</span><div class="chk rd{" on" if i == sel else ""}"><span class="box"></span></div></div>'
                     f'<span class="xl b">${rng.choice([0, 9, 19, 29, 49, 99])}<span class="sm mut"> / month</span></span><span class="sm mut">{rng.choice(["Up to 3 seats", "Unlimited projects", "Priority support", "Single sign-on", "10 GB storage"])}</span></div>')
    return f'<div class="row g12 str">{"".join(cards)}</div>'


def _steps_h(ctx, steps, cur, region):
    out = []
    for i, s in enumerate(steps):
        attr = ctx.reg("step", "step", s, region=region)
        num = TICK if i < cur else str(i + 1)
        out.append(f'<div class="row g8"{attr}><span class="wz-num{" done" if i < cur else " cur" if i == cur else ""}">{num}</span><span class="{"b" if i == cur else "mut"} nw">{esc(s)}</span></div>')
        if i < len(steps) - 1:
            out.append(f'<div class="wz-line{" done" if i < cur else ""}"></div>')
    return f'<div class="row g10">{"".join(out)}</div>'


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    brand = d.one("company", COMPANIES)
    tall = H >= 1000
    sk = "inst" if variant == "installer" else "shop" if variant == "checkout" else "onb"
    all_steps = d.take("wz.steps." + sk, STEPS[sk], 9)
    steps = all_steps[:rng.randint(4, 6 if W > 1400 else 5)]
    if variant == "installer":
        spec["web"] = False      # an installer is always a small desktop window floating over the desktop
        ww, wh = min(rng.choice([760, 820, 900]), W - 160), min(rng.choice([540, 580, 640]), H - 150)
        side, gap = (W - ww) // 2, H - wh
        spec["floating"], spec["inset"] = True, f"{int(gap * 0.42)}px {side}px {max(20, int(gap * 0.58) - 60)}px {side}px"
    elif variant in ("checkout", "survey"):
        spec["web"] = True       # these two are web pages
    cur = rng.randint(1, max(1, len(steps) - 2))
    logo = f'<div class="thumb" style="width:26px;height:26px;border-radius:7px;--c1:var(--ac);--c2:var(--acs2)"></div><span class="b lg nw">{esc(brand)}</span>'
    foot_r = "the button bar"
    menus = ["mb.file", "mb.edit", "mb.view", "mb.window", "mb.help"]
    compact, title = False, f"{brand} setup"
    ctx.ctxmenu, ctx.ctxobj = ["cut", "copy", "paste", "-", "selectall", "clear"], "this field"

    if variant == "stepper_top":
        hr = "the header"
        head = f'<div class="row g10 px16 bb fn" style="height:54px">{logo}<div class="sp"></div>{ctx.tbtn("help", hr, cls="ghost", icon=True)}{ctx.tbtn("wz.savedraft", hr, cls="ghost")}{ctx.ibtn("dlg.close", hr, anchor="icon")}</div>'
        bar = f'<div class="row cen bb bg1 fn" style="padding:16px 24px"><div style="width:min(100%,{rng.choice([820, 900, 980])}px)">{_steps_h(ctx, steps, cur, "the progress bar")}</div></div>'
        fr = "the form"
        body = (f'<div class="col g16" style="width:min(92%,{rng.choice([680, 760, 840])}px);padding:28px 0"><div class="col g4"><span class="fnt sm up">Step {cur + 1} of {len(steps)}</span>'
                f'<span class="xxl b">Tell us about your {esc(rng.choice(["organization", "team", "business", "project"]))}</span><span class="mut">You can change these details later from the admin area.</span></div>'
                f'{_fields(ctx, fr, rng.randint(5, 8) + (2 if tall else 0))}{_plans(ctx, fr) if tall else ""}<div class="col g8">{_checks(ctx, fr, rng.randint(2, 3))}</div>'
                f'<div class="row g8 bt" style="padding-top:16px">{ctx.tbtn("prev", foot_r)}<div class="sp"></div>{ctx.tbtn("wz.skip", foot_r, cls="ghost")}{ctx.tbtn("next", foot_r, cls="pri lgb")}</div></div>')
        html = f'{head}{bar}<div class="row cen top f1 clip">{body}</div>'
    elif variant == "sidebar_steps":
        sr = "the step list"
        srows = []
        for i, s in enumerate(all_steps[:max(len(steps), H // 110)]):
            attr = ctx.reg("step", "step", s, region=sr)
            state = "Completed" if i < cur else "In progress" if i == cur else "Not started"
            srows.append(f'<div class="row g10 px16 fn" style="height:52px;{"background:var(--acs);" if i == cur else ""}"{attr}><span class="wz-num{" done" if i < cur else " cur" if i == cur else ""}">{TICK if i < cur else i + 1}</span>'
                         f'<div class="col"><span class="{"b" if i == cur else "m"}">{esc(s)}</span><span class="xs fnt">{state}</span></div></div>')
        side = (f'<div class="side br" style="width:{rng.choice([250, 280, 300])}px"><div class="row g10 p16">{logo}</div><div class="col f1 clip">{"".join(srows)}</div>'
                f'<div class="col g6 p12 bt">{ctx.tbtn("help", sr, cls="ghost", icon=True)}{ctx.tbtn("wz.savedraft", sr, cls="ghost")}</div></div>')
        fr = "the form"
        tog = "".join(f'<div class="bb">{ctx.toggle_row(o, rng.random() < 0.5, region=fr, cls="py8")}</div>' for o in d.take("wz.opts.onb", OPTS["onb"], 6)[3:6])
        aside = ""
        if W >= 1600:
            recap = "".join(f'<div class="row g8 py4"><span class="ok">{OKTICK}</span><span class="mut">{esc(x)}</span></div>'
                            for x in ["Email address confirmed", "Workspace region selected", "Two teammates invited"])
            aside = (f'<div class="col g12" style="width:{rng.choice([320, 360])}px;flex:none"><div class="card p16 col g6"><span class="b">Your setup so far</span>{recap}'
                     f'<div class="prog" style="margin-top:6px"><div style="width:{100 * cur // len(steps)}%"></div></div><span class="xs fnt">About {rng.randint(2, 9)} minutes left</span></div>'
                     f'<div class="card p16 col g8"><span class="b">Stuck on something?</span><span class="mut sm">Our team usually answers within a few hours on weekdays.</span>'
                     f'<div class="row g8">{ctx.tbtn("dlg.learn", "the side card", cls="sm")}{ctx.ibtn("comment", "the side card", obj="the setup team", cls="bdr")}</div></div></div>')
        main = (f'<div class="col f1"><div class="row cen top g24 f1 clip" style="padding:28px 40px"><div class="col g16" style="flex:1 1 0;max-width:900px"><div class="col g4"><span class="xxl b">Set up your workspace</span>'
                f'<span class="mut">A few details so we can tailor things. Fields marked optional can be left empty.</span></div>'
                f'<div class="col g16">{_fields(ctx, fr, rng.randint(4, 6) + (2 if tall else 0))}<span class="b">Choose how you want to start</span>{_plans(ctx, fr)}'
                f'<div class="card px16">{tog}</div><div class="col g8">{_checks(ctx, fr, 2)}</div></div></div>{aside}</div>'
                f'<div class="row g8 bt bg1 fn" style="padding:12px 40px">{ctx.tbtn("prev", foot_r)}<div class="sp"></div>{ctx.tbtn("wz.skip", foot_r, cls="ghost")}{ctx.tbtn("next", foot_r, cls="pri")}</div></div>')
        html = f'<div class="row str f1">{side}{main}</div>'
    elif variant == "installer":
        title = f"{brand.split()[0]} {rng.randint(2, 9)}.{rng.randint(0, 9)} Setup"
        fr = "the installer page"
        comps = "".join(f'<div class="row g8 px8 fn" style="height:calc(var(--rh) + 2px)">{ctx.check(c, rng.random() < 0.6, region=fr, cls="f1")}<span class="fnt sm">{rng.randint(2, 480)} MB</span></div>'
                        for c in d.take("wz.comps", COMPS, rng.randint(5, 8)))
        types = "".join(ctx.check(t, i == 0, region=fr, radio=True, noun="install type") for i, t in enumerate(d.take("wz.types", TYPES, 3)))
        dest = ctx.field("Destination folder", rng.choice(["C:\\Program Files\\" + brand.split()[0], "/opt/" + brand.split()[0].lower(), "~/Applications/" + brand.split()[0]]), region=fr, cls="mono")
        page = (f'<div class="col g12 f1 clip p20"><div class="col g2"><span class="xl b">Choose what to set up</span><span class="mut">Select the parts of {esc(brand)} you want on this computer.</span></div>'
                f'<div class="row g16 wrap">{types}</div><div class="col ba rad bg clip" style="max-height:{rng.choice([190, 230, 270])}px">{comps}</div>'
                f'<div class="row g8" style="align-items:flex-end"><div class="f1">{dest}</div>{ctx.tbtn("dlg.browse", fr)}</div>'
                f'<span class="mut sm">Space required: {rng.uniform(0.4, 3.9):.1f} GB · Space available: {rng.randint(20, 400)} GB</span><div class="col g6">{_checks(ctx, fr, 2, "inst")}</div></div>')
        banner = (f'<div class="wz-banner"><div class="thumb" style="width:44px;height:44px;border-radius:12px;--c1:#fff;--c2:rgba(255,255,255,.4)"></div><span class="xl b">{esc(brand)}</span>'
                  f'<span class="sm" style="opacity:.85">Setup assistant</span><div class="sp"></div>' + "".join(
                      f'<div class="row g6 sm" style="opacity:{1 if i == cur else .7}"><span>{"●" if i == cur else "○"}</span><span{ctx.reg("step", "step", s, region="the banner")}>{esc(s)}</span></div>' for i, s in enumerate(steps)) + "</div>")
        agree = ctx.check(ctx.lab("wz.agree"), rng.random() < 0.5, region=foot_r, cid="wz.agree") if ctx.has("wz.agree") else ""
        foot = (f'<div class="row g8 bt bg1 fn" style="padding:10px 14px">{agree}<div class="sp"></div>{ctx.tbtn("prev", foot_r)}{ctx.tbtn(rng.choice(["next", "wz.install"]), foot_r, cls="pri")}'
                f'<div style="width:8px"></div>{ctx.tbtn("cancel", foot_r)}</div>')
        html = f'<div class="row str f1">{banner}<div class="col f1">{page}</div></div>{foot}'
        menus = []
    elif variant == "checkout":
        hr = "the header"
        crumbs = "".join(f'<span class="{"b" if i == cur else "mut"}"{ctx.reg("step", "step", s, region=hr)}>{esc(s)}</span>' + (f'<span class="fnt">{CHEV_R}</span>' if i < len(steps) - 1 else "") for i, s in enumerate(steps[:4]))
        who = d.person()
        aattr = ctx.reg("button", "avatar", ctx.lab("account"), ui="icon", cid="account", region=hr, anchor="account") if ctx.has("account") else ""
        head = f'<div class="row g10 px16 bb fn" style="height:56px">{logo}<div class="sp"></div><div class="row g8">{crumbs}</div><div class="sp"></div>{ctx.ibtn("help", hr)}{ctx.ibtn("wz.editcart", hr)}<span{aattr}>{ctx.av(who, 28)}</span></div>'
        fr = "the checkout form"
        ship = "".join(f'<div class="row g8 px12 ba rad fn" style="height:calc(var(--ch) + 14px)">{ctx.check(s, i == 0, region=fr, radio=True, noun="shipping option", cls="f1")}<span class="m">{d.money(2, 30) if i else "Free"}</span></div>'
                       for i, s in enumerate(d.take("wz.ship", SHIP, 3)))
        pay = (f'<div style="display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px">{ctx.field("Card number", "", ph="•••• •••• •••• ••••", region=fr)}{ctx.field("Expiry date", "", ph="MM / YY", region=fr)}'
               f'{ctx.field("Security code", "", ph="•••", region=fr)}</div>')
        left = (f'<div class="col g16" style="flex:1 1 0;max-width:680px;padding:24px 0"><span class="b lg">Contact and delivery address</span>{_fields(ctx, fr, 0, names=d.take("wz.addr", ADDR) + [n for n in ("Country", "Company") if owner(n, ctx.split) == ctx.split])}'
                f'<span class="b lg">Delivery method</span><div class="col g8">{ship}</div><span class="b lg">Payment details</span>{pay}<div class="col g8">{_checks(ctx, fr, 2, "shop")}</div>'
                f'<div class="row g8">{ctx.tbtn("wz.editcart", fr, cls="ghost", icon=True)}<div class="sp"></div>{ctx.tbtn("wz.place", fr, cls="pri lgb", icon=True)}</div></div>')
        sr, items, sub = "the order summary", [], 0.0
        for p in d.products(rng.randint(2, 4)):
            price = round(rng.uniform(8, 240), 2)
            sub += price
            qd = ctx.reg("button", "button", ctx.lab("wz.qtydown"), ui="icon", cid="wz.qtydown", region=sr, row=p) if ctx.has("wz.qtydown") else ""
            qu = ctx.reg("button", "button", ctx.lab("wz.qtyup"), ui="icon", cid="wz.qtyup", region=sr, row=p) if ctx.has("wz.qtyup") else ""
            pattr = ctx.reg("row", "product", p, region=sr, anchor="row")
            items.append(f'<div class="row g10 py8 bb">{ctx.thumb(44, 44, 6)}<div class="col f1 g4"><span class="m"{pattr}>{esc(p)}</span><div class="row g8"><div class="step" style="height:22px"><div{qd}>−</div>'
                         f'<div class="v">{rng.randint(1, 3)}</div><div{qu}>+</div></div>{ctx.ibtn("delete", sr, row=p, obj=p, cls="s")}</div></div><span class="m">${price:,.2f}</span></div>')
        promo = f'<div class="row g8" style="align-items:flex-end"><div class="f1">{ctx.field("Discount code", "", ph="", region=sr)}</div>{ctx.tbtn("wz.promo", sr)}</div>'
        ship_cost, tax = round(rng.uniform(3, 15), 2), round(sub * 0.08, 2)
        totals = "".join(f'<div class="row {"b lg" if k == "Total" else "mut"}"><span class="f1">{k}</span><span>${v:,.2f}</span></div>'
                         for k, v in [("Subtotal", sub), ("Delivery", ship_cost), ("Estimated tax", tax), ("Total", sub + ship_cost + tax)])
        right = f'<div class="col g12 card p16" style="width:{rng.choice([360, 400, 440])}px;margin-top:24px;flex:none"><span class="b lg">In your basket</span>{"".join(items)}{promo}<div class="col g6">{totals}</div></div>'
        html = f'{head}<div class="row cen top g24 f1 clip bg1" style="padding:0 24px">{left}{right}</div>'
        ctx.ctxmenu, ctx.ctxobj = ["delete", "fav", "share", "-", "info"], "this product"
        menus = []
    else:  # survey
        qr = "the questionnaire"
        mine = [(q, opts) for q, (s, opts) in SCALE_SPLIT.items() if s == ctx.split and len(opts) >= 3]
        rng.shuffle(mine)
        cards = []
        for q, opts in mine[:3 if tall else 2]:
            pick = rng.randrange(len(opts))
            row = "".join(f'<div class="wz-opt{" on" if i == pick else ""}"{ctx.reg("radio", "answer", o, region=qr, state=i == pick)}><div class="chk rd{" on" if i == pick else ""}"><span class="box"></span></div>'
                          f'<span>{esc(o)}</span></div>' for i, o in enumerate(opts))
            cards.append(f'<div class="card p16 col g10"><span class="m lg">{esc(q)}</span><div class="row g8 wrap">{row}</div></div>')
        npick = rng.randint(5, 10)
        nps = "".join(f'<div class="wz-nps{" on" if n == npick else ""}"{ctx.reg("radio", "rating", f"rating {n}", region=qr, refs=[f"the number {n} on the 0 to 10 recommendation scale", f"rating {n} on the recommendation scale"])}>{n}</div>' for n in range(11))
        cards.insert(1, f'<div class="card p16 col g10"><span class="m lg">How likely are you to recommend {esc(brand)} to a colleague?</span><div class="row g6">{nps}</div>'
                        f'<div class="row xs fnt"><span>Not likely</span><div class="sp"></div><span>Certain to</span></div></div>')
        topics = "".join(f'<div style="width:33%">{ctx.check(t, rng.random() < 0.3, region=qr)}</div>' for t in d.take("wz.topics", TOPICS, 6))
        cards.append(f'<div class="card p16 col g10"><span class="m lg">Which areas should we improve first? Select all that apply.</span><div class="row wrap" style="row-gap:10px">{topics}</div></div>')
        countries = d.take("wz.countries", COUNTRIES, 5)
        cards.append(f'<div class="card p16 col g10"><span class="m lg">A little about you</span><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'
                     f'{ctx.select("Country of residence", "Choose a country", options=countries, region=qr)}{ctx.field("Your role", "", ph="e.g. operations lead", region=qr)}</div>'
                     f'{ctx.field("Additional comments", "", ph="", region=qr, area=70)}</div>')
        done = rng.randint(2, 7)
        head = (f'<div class="col g8 px16 bb fn" style="padding-top:12px;padding-bottom:12px"><div class="row g10">{logo}<span class="mut">· Customer feedback {rng.choice([2025, 2026])}</span><div class="sp"></div>'
                f'<span class="sm mut">Page {done} of 9</span>{ctx.tbtn("wz.savedraft", "the header", cls="ghost sm")}</div><div class="prog"><div style="width:{done * 11}%"></div></div></div>')
        foot = (f'<div class="row cen bt bg1 fn" style="padding:12px 0"><div class="row g8" style="width:min(92%,780px)">{ctx.tbtn("prev", foot_r)}<div class="sp"></div>{ctx.tbtn("wz.skip", foot_r, cls="ghost")}'
                f'{ctx.tbtn(rng.choice(["next", "wz.submit"]), foot_r, cls="pri")}</div></div>')
        html = f'{head}<div class="row cen top f1 clip bg1"><div class="col g12" style="width:min(92%,780px);padding:20px 0">{"".join(cards)}</div></div>{foot}'
        title, menus = f"{brand} — Feedback", []
    return {"title": title, "body": f'<div class="col f1">{html}</div>', "menus": menus, "app": "Setup", "css": CSS, "compact": compact,
            "url": brand.lower().split()[0] + ".example.com/" + ("checkout" if variant == "checkout" else "survey" if variant == "survey" else "onboarding")}
