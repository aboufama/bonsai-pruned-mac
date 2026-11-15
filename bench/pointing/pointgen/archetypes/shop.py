"""E-commerce admin: order and product tables, a customer drawer and a dense inventory grid."""
from ..data import COMPANIES, PRODUCT_A, PRODUCT_B
from ..overlays import FORM_FIELDS
from ..splits import pool
from ..ui import esc, CHEV_D
from ..vocab import C, P

NAME = "shop"
KIND = "web"
VARIANTS = {"orders_table": "train", "products": "train", "customer_detail": "dev", "inventory_dense": "test"}

NAV = P("shop.nav", [
    ("Orders", "see what customers have bought", "shopping-cart|receipt"),
    ("Products", "manage the things I sell", "package|tag"),
    ("Customers", "look up the people who buy from me", "contact|users-round"),
    ("Inventory", "check how many units are on the shelves", "boxes|warehouse"),
    ("Discounts", "set up coupon codes and sales", "badge-percent|ticket-percent"),
    ("Insights", "see sales trends and charts", "chart-column|chart-spline"),
    ("Marketing", "run promotions and email blasts", "megaphone|mails"),
    ("Shipping", "manage carriers and delivery rates", "truck|package-check"),
    ("Payouts", "see when money reaches my bank", "landmark|wallet"),
    ("Returns", "handle things customers sent back", "package-open|undo-dot"),
    ("Gift cards", "issue prepaid store credit", "gift|ticket"),
    ("Collections", "group merchandise into browsable sets", "gallery-vertical|folders"),
    ("Reviews", "moderate what buyers wrote", "message-square-text|star-half"),
    ("Abandoned carts", "follow up on checkouts that were never finished", "shopping-bag|shopping-basket"),
    ("Suppliers", "manage the vendors I buy stock from", "factory|handshake"),
    ("Purchase orders", "track stock I have requested from vendors", "clipboard-list|notebook-tabs"),
    ("Transfers", "move stock between locations", "arrow-left-right|forklift"),
    ("Online store", "edit the storefront customers see", "store|shopping-cart"),
    ("Point of sale", "manage in-person checkout", "scan-barcode|calculator"),
    ("Staff accounts", "control which employees can sign in", "user-cog|id-card"),
    ("Subscriptions", "manage recurring customer plans", "calendar-sync|repeat-2"),
    ("Draft orders", "finish sales I started on a customer's behalf", "file-pen|notebook-pen"),
    ("Locations", "manage my warehouses and shops", "map-pin|building-2"),
    ("Bundles", "sell several things together as one", "package-plus|group"),
    ("Fulfillment", "pick, pack and send out purchases", "package-search|container"),
    ("Loyalty", "manage the rewards points scheme", "heart-handshake|award"),
    ("Fraud review", "inspect purchases flagged as suspicious", "shield-alert|scan-eye"),
    ("Price lists", "set different prices per market", "circle-dollar-sign|banknote"),
    ("Storefront themes", "change the look of the public shop", "palette|paintbrush"),
    ("Sales channels", "connect marketplaces and social shops", "share-2|waypoints"),
])
SELECTS = P("shop.sel", [
    ("Payment status", "show only purchases in a certain money state"), ("Fulfillment status", "show only purchases at a certain delivery stage"),
    ("Sales channel", "show only purchases that came through one outlet"), ("Date placed", "limit the list to a period of time"),
    ("Tagged with", "show only entries carrying a certain keyword"), ("Vendor", "show only merchandise from one maker"),
    ("Product type", "show only one kind of merchandise"), ("Stock level", "show only entries that are plentiful, scarce or gone"),
    ("Warehouse", "choose which storage site the counts refer to"), ("Customer group", "show only one segment of buyers"),
    ("Rows per page", "choose how many lines the table lists at once"), ("Delivery method", "show only one way of getting parcels to buyers"),
    ("Risk level", "show only purchases with a certain fraud score"), ("Price range", "show only merchandise within some cost bracket"),
    ("Published state", "show only visible or only concealed listings"), ("Saved view", "switch to one of my stored table setups"),
    ("Bulk actions", "do something to every ticked line at once"), ("Currency shown", "pick the money unit amounts are displayed in"),
    ("Assigned staff", "show only entries handled by one employee"), ("Marketplace", "show only listings synced to one external site"),
])
OPTIONS = {
    "Payment status": ["Any", "Paid", "Pending", "Refunded", "Voided"], "Fulfillment status": ["Any", "Unfulfilled", "Partially fulfilled", "Fulfilled"],
    "Sales channel": ["All channels", "Online store", "Point of sale", "Wholesale", "Marketplace"], "Date placed": ["Today", "Last 7 days", "Last 30 days", "This year"],
    "Tagged with": ["Any tag", "wholesale", "gift", "priority", "preorder"], "Vendor": ["All vendors", "In-house", "Northwind", "Atlas"],
    "Product type": ["All types", "Apparel", "Accessories", "Home", "Outdoor"], "Stock level": ["Any", "In stock", "Low stock", "Out of stock"],
    "Warehouse": ["All sites", "Berlin hub", "Austin depot", "Osaka store"], "Customer group": ["Everyone", "Repeat buyers", "Wholesale", "Newsletter"],
    "Rows per page": ["25", "50", "100", "250"], "Delivery method": ["Any", "Standard", "Express", "Local pickup"], "Risk level": ["Any", "Low", "Medium", "High"],
    "Price range": ["Any price", "Under $25", "$25 to $100", "Over $100"], "Published state": ["Any", "Visible", "Concealed"],
    "Saved view": ["Default", "Needs attention", "Wholesale only", "This week"], "Bulk actions": ["Choose…", "Add tags", "Change vendor", "Set prices"],
    "Currency shown": ["USD", "EUR", "GBP", "JPY"], "Assigned staff": ["Anyone", "Me", "Unassigned"], "Marketplace": ["All", "Bazaar", "Craftly", "Shopline"],
}
TOGGLES = P("shop.tog", [
    ("Accepts marketing", "{enable} sending promotional mail to this buyer"), ("Tax exempt", "{enable} leaving sales tax off this buyer's purchases"),
    ("VIP customer", "turn {on} the flag that marks this buyer as especially valuable"), ("Track quantity", "{enable} counting units for this listing"),
    ("Continue selling when sold out", "{enable} taking purchases even with nothing left on the shelf"), ("Charge tax", "{enable} adding sales tax to this listing"),
    ("Requires shipping", "turn {on} the flag saying this is a physical parcel"), ("Notify customer", "{enable} emailing the buyer about this update"),
    ("Restock items", "{enable} putting returned units back into the count"), ("Allow store credit", "{enable} letting this buyer pay with balance"),
    ("Wholesale pricing", "turn {on} trade prices for this buyer"), ("Send review request", "{enable} asking the buyer for feedback after delivery"),
    ("Hide from search", "turn {on} keeping this listing out of storefront lookups"), ("Gift wrap available", "{enable} offering paper and ribbon at checkout"),
    ("Age verification", "{enable} asking buyers to confirm they are adults"),
])
C("shop.neworder", "Create order|New order|Add order", "", "start a purchase on behalf of a customer|enter a sale by hand|key in a fresh sale manually")
C("shop.addproduct", "Add product|New product|Create listing", "", "put another thing up for sale|set up a fresh entry in the catalog|register one more thing to sell")
C("shop.addcustomer", "Add customer|New customer|Create contact", "", "register a buyer by hand|enter a fresh buyer record|set up a profile for someone who has not bought yet")
C("shop.archive", "Archive|Archive selected|Shelve", "archive|archive-x|package-x",
  "take {o} out of the active list but keep the records|put {o} into cold storage without deleting anything|retire {o} from the live list", o="the ticked entries")
C("shop.publish", "Publish|Make visible|Set live", "", "make {o} show up in the storefront|let shoppers see {o}|put {o} on sale to the public", o="the ticked entries")
C("shop.fulfill", "Mark as fulfilled|Fulfill items|Mark shipped", "", "record that {o} went out the door|flag {o} as dispatched|note that {o} left the warehouse", o="the ticked purchases")
C("shop.capture", "Capture payment|Collect payment|Charge card", "", "take the money that was authorized for {o}|bill the buyer for {o}|collect what is owed on {o}", o="the ticked purchases")
C("shop.refund", "Refund|Issue refund|Return money", "", "give the buyer their cash back for {o}|pay the buyer back for {o}|reverse the charge on {o}", o="this purchase")
C("shop.label", "Print label|Create shipping label|Buy postage", "ticket|barcode|qr-code",
  "produce the carrier sticker for {o}|get the address sticker for the parcel of {o}|generate the parcel sticker for {o}", o="this purchase")
C("shop.email", "Send email|Email customer|Write to buyer", "mail|mail-plus|at-sign|mail-open|mail-check|mails", "compose a message to {o}|get in touch with {o} in writing|drop {o} a line", o="this person")
C("shop.view", "View details|Open record|See full entry", "eye|scan-search|square-arrow-out-up-right|arrow-up-right", n="view|open record|full entry",
  intents="look at everything recorded for {o}|bring up the complete page for {o}|inspect all the fields of {o}", o="this entry")
C("shop.cols", "Edit columns|Choose columns|Customize table", "columns-3|table-properties|columns-2|columns-4", "decide which fields the table displays|pick the fields that appear across the table|add or drop fields from the table")
C("pg.prev", "Previous results|Earlier batch|Prior set", "move-left|square-arrow-left|arrow-left-from-line",
  "see the lines that came before these|flip to the preceding screenful of the table|go one screenful toward the beginning of the table")
C("pg.next", "Next results|Later batch|Following set", "move-right|square-arrow-right|arrow-right-from-line",
  "see the lines that come after these|flip to the subsequent screenful of the table|go one screenful toward the finish of the table")
C("shop.inc", "Increase quantity|Add one unit|Raise count", "", "bump the on-hand figure for {o} up by one|raise the tally for {o} a notch|count one more of {o}", o="this row")
C("shop.dec", "Decrease quantity|Remove one unit|Lower count", "", "bring the on-hand figure for {o} down by one|drop the tally for {o} a notch|count one fewer of {o}", o="this row")
C("shop.savestock", "Save counts|Apply adjustments|Commit stock", "", "store the quantities I just edited|make my edited quantities official|write the edited quantities to the ledger")

TABS = ["All", "Unfulfilled", "Unpaid", "Open", "Closed", "Paid", "Pending", "Shipped", "Delivered", "Cancelled", "Refunded", "On hold", "Processing",
        "Returned", "Archived", "Draft", "Active", "Scheduled", "Out of stock", "Low stock", "Backordered", "Flagged", "Awaiting pickup", "Partially paid",
        "Disputed", "Completed", "Failed", "Expired", "Published", "Unlisted", "Needs review", "Local delivery", "Subscriptions only", "Wholesale",
        "High value", "First-time buyers", "Repeat buyers", "Gift orders", "International", "Rush"]
COLS = ["Order", "Date", "Customer", "Total", "Payment", "Fulfillment", "Items", "Channel", "Delivery", "Tags", "Destination", "Vendor", "Category",
        "Price", "Stock", "Updated", "Created", "Margin", "Weight", "Barcode", "SKU", "On hand", "Committed", "Available", "Incoming", "Reorder point",
        "Supplier", "Bin", "Unit cost", "Variant", "Orders placed", "Total spent", "Last order", "Buyer segment", "Email status", "Home city", "Product",
        "Listing status", "Lead time", "Sell-through"]
PAY = [("Payment received", "g"), ("Awaiting payment", "y"), ("Part refunded", ""), ("Authorized", "a")]
FUL = [("Sent out", "g"), ("In transit", "a"), ("Packed", ""), ("Label printed", "y"), ("Queued", "")]
LIST = [("Live", "g"), ("Hidden draft", ""), ("Sold out", "r"), ("Preorder", "a")]
CATS = ["Apparel", "Home goods", "Outdoor", "Kitchen", "Travel", "Office", "Audio", "Footwear", "Accessories"]
CITIES = ["Lisbon", "Austin", "Osaka", "Leeds", "Turin", "Accra", "Tampere", "Quito", "Perth", "Gdansk"]

CSS = """
.shop-th{color:var(--fg1);font-weight:600;font-size:.9em;white-space:nowrap}
.shop-st{display:inline-flex;border:1px solid var(--bd2);border-radius:var(--r);height:calc(var(--ch) - 4px);align-items:stretch;background:var(--inp)}
.shop-st>div{display:flex;align-items:center;justify-content:center;min-width:20px;font-weight:600;color:var(--fg1)}
.shop-st .v{min-width:36px;border-left:1px solid var(--bd);border-right:1px solid var(--bd);color:var(--fg);font-weight:400}
.shop-pg{min-width:calc(var(--ch) - 2px);height:calc(var(--ch) - 2px);padding:0 6px;border-radius:var(--r);display:flex;align-items:center;justify-content:center;border:1px solid var(--bd)}
.shop-pg.on{background:var(--ac);color:var(--acf);border-color:var(--ac)}
.shop-in{height:calc(var(--ch) - 2px);font-size:.92em}
.shop-cell{height:calc(var(--rh) - 6px);padding:0 6px;font-size:.95em}
"""


def _products(ctx, k):
    """Product names: each base noun of this split in several adjective variants."""
    rng = ctx.rng
    names = [f"{a} {b}" for b in ctx.d.take("product.b", PRODUCT_B) for a in rng.sample(PRODUCT_A, 5)]
    rng.shuffle(names)
    return names[:k]


def _fval(ctx, label, who):
    """A plausible value for a form field, judged from its caption."""
    rng, d, low = ctx.rng, ctx.d, label.lower()
    if "mail" in low or "reply" in low:
        return d.email_of(who)
    if "phone" in low or "mobile" in low or "fax" in low:
        return f"+1 555 01{rng.randint(10, 99)}"
    if "date" in low or "window" in low:
        return d.date(True)
    if "name" in low or "holder" in low or "owner" in low or "manager" in low or "contact" in low or "assignee" in low:
        return who
    if "company" in low or "team" in low or "department" in low:
        return rng.choice(["Operations", "Wholesale", "Retail East", "Support"])
    if "city" in low or "location" in low or "region" in low or "country" in low or "zone" in low or "address" in low or "building" in low:
        return rng.choice(CITIES)
    if "code" in low or " id" in low or "number" in low or "order" in low or "postal" in low or "initial" in low or "unit" in low:
        return rng.choice(["A-204", "88213", "QX-17", "40-1193", "7C"])
    return rng.choice(["Standard", "Net 30", "Prefers email", "Wholesale tier", "—"])


def _sel(ctx, cid, region):
    label = ctx.lab(cid)
    opts = OPTIONS[label]
    attr = ctx.reg("select", "dropdown", label, cid=cid, region=region, anchor="select")
    ctx.options[ctx.last] = list(opts)
    return f'<div class="inp shop-in fn"{attr}><span class="fnt">{esc(label)}</span><span class="nw m">{esc(ctx.rng.choice(opts))}</span>{CHEV_D}</div>'


def _th(ctx, label, region, style, owned, cls=""):
    """Column header; a sort target only when this split owns the caption."""
    attr = ctx.reg("button", "column header", label, region=region) if label in owned else ""
    return f'<div class="td shop-th {cls}" style="{style}"{attr}>{esc(label)}</div>'


def _pager(ctx, region, total):
    rng = ctx.rng
    cur = rng.randint(1, 4)
    nums = ""
    for n in list(range(1, 6)) + [total]:
        attr = ctx.reg("button", "page", f"Page {n}", region=region, refs=[f"page {n} in the pagination", f"the page {n} button below the table"])
        nums += ('<span class="mut">…</span>' if n == total else "") + f'<div class="shop-pg{" on" if n == cur else ""}"{attr}>{n}</div>'
    return f'<div class="row g4">{ctx.ibtn("pg.prev", region, cls="s bdr")}{nums}{ctx.ibtn("pg.next", region, cls="s bdr")}</div>'


def _acct(ctx, region, who):
    attr = ctx.reg("button", "avatar", "Account menu", ui="icon", cid="account", region=region, anchor="account")
    return f'<div{attr}>{ctx.av(who, 28)}</div>'


def _side(ctx, navs, region, brand, sel=0):
    rng = ctx.rng
    items = "".join(ctx.navc(c, region, on=i == sel, noun="page", count=rng.randint(2, 48) if rng.random() < 0.25 else None) for i, c in enumerate(navs))
    logo = f'<div class="row g8 p12"><div class="thumb" style="width:26px;height:26px;border-radius:7px;--c1:var(--ac);--c2:var(--acs2)"></div><span class="b lg el">{esc(brand)}</span></div>'
    return (f'<div class="side br{" dk" if rng.random() < 0.35 else ""}" style="width:{rng.choice([210, 226, 244])}px">{logo}<div class="col g2">{items}</div><div class="sp"></div>'
            f'<div class="col g2 py8 bt">{ctx.navc("settings", region, noun="link")}{ctx.navc("help", region, noun="link")}</div></div>')


def _topbar(ctx, region, who):
    return (f'<div class="row g8 px16 bb" style="height:50px;flex:none">{ctx.search(region, w=340, cls="soft", kbd="⌘K")}<div class="sp"></div>{ctx.ibtn("notif", region)}'
            f'{ctx.ibtn("apps", region)}{_acct(ctx, region, who)}</div>')


def _foot(ctx, region, sel, total):
    rng = ctx.rng
    return (f'<div class="row g12 px12 bt" style="height:calc(var(--ch) + 14px);flex:none"><span class="mut sm">Showing {rng.randint(1, 3) * 25 - 24}–{rng.randint(4, 8) * 25} of {rng.randint(260, 4800):,}</span>'
            f'<div class="sp"></div>{sel}{_pager(ctx, region, total)}</div>')


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    nrows = max(8, (H - 330) // (24 if H < 1000 else 28)) + 4
    navs = ctx.pick(NAV, rng.randint(8, 12))
    sels = ctx.pick(SELECTS, 6)
    rng.shuffle(sels)
    tabs = d.take("shop.tabs", TABS, rng.randint(4, 6))
    owned = set(pool("shop.cols", COLS, ctx.split))
    brand = d.one("company", COMPANIES)
    me = d.person()
    people = d.people(nrows + 2)
    ctx.ctxmenu = ["shop.view", "edit", "duplicate", "-", "shop.label", "print", "shop.email", "-", "tagit", "shop.archive", "delete"]
    ctx.ctxobj = "this entry"
    tb, tbl, pg = "the toolbar", "the table", "the pagination"

    if variant == "orders_table":
        head = (f'<div class="row g8" style="flex:none"><span class="xl b">Sales ledger</span><div class="sp"></div>{ctx.tbtn("export", tb, icon=True)}{ctx.tbtn("import", tb, icon=True)}'
                f'{ctx.tbtn("shop.neworder", tb, cls="pri")}</div>')
        filt = (f'<div class="row g8 p8 bb" style="flex:none">{ctx.search(tbl, w=240)}{"".join(_sel(ctx, c, tbl) for c in sels[:3])}'
                f'<div class="sp"></div>{ctx.ibtn("filter", tbl, cls="bdr")}{ctx.ibtn("sort", tbl, cls="bdr")}{ctx.ibtn("shop.cols", tbl, cls="bdr")}</div>')
        cw = [("Order", "width:92px"), ("Date", "width:128px"), ("Customer", "flex:1 1 0"), ("Total", "width:96px"), ("Payment", "width:150px"), ("Fulfillment", "width:130px"), ("Items", "width:70px")]
        hdr = f'<div class="tr h"><div class="td" style="width:36px">{ctx.box("Select all orders", False, region=tbl, refs=["the select-all checkbox in the table header", "the checkbox that selects every order"])}</div>' \
              + "".join(_th(ctx, c, tbl, st, owned, "r" if c in ("Total", "Items") else "") for c, st in cw) + '<div class="td" style="width:104px"></div></div>'
        rows, num = [], rng.randint(1040, 9200)
        for i in range(nrows):
            num -= rng.randint(1, 3)
            lab, who = f"#{num}", people[i]
            attr = ctx.reg("row", "order", lab, region=tbl, anchor="row", refs=[f"order {lab}", f"the row for order {lab}", f"the {lab} order"])
            obj = f"order {lab}"
            chk = ctx.box(f"Select {lab}", rng.random() < 0.15, region=tbl, row=obj, refs=[f"the checkbox for order {lab}", f"the checkbox next to {lab}"])
            pay, ful = rng.choice(PAY), rng.choice(FUL)
            acts = ctx.ibtn("shop.label", tbl, row=obj, obj=obj, cls="s") + ctx.ibtn("shop.view", tbl, row=obj, obj=obj, cls="s") + ctx.ibtn("more", tbl, row=obj, obj=obj, cls="s", anchor="more")
            rows.append(f'<div class="tr{" sel" if i == 2 else ""}"{attr}><div class="td" style="width:36px">{chk}</div><div class="td b" style="width:92px">{lab}</div>'
                        f'<div class="td mut" style="width:128px">{d.date()}, {d.time()}</div><div class="td f">{ctx.av(who, 20)}<span class="el">{esc(who)}</span></div>'
                        f'<div class="td r" style="width:96px">{d.money(12, 900)}</div><div class="td" style="width:150px"><span class="pill {pay[1]}">{pay[0]}</span></div>'
                        f'<div class="td" style="width:130px"><span class="pill {ful[1]}">{ful[0]}</span></div><div class="td r mut" style="width:70px">{rng.randint(1, 9)}</div>'
                        f'<div class="td r" style="width:104px;gap:0">{acts}</div></div>')
        card = (f'<div class="card col f1 clip">{ctx.tabs(tabs, active=0, region="the status tabs")}{filt}{hdr}<div class="col f1 clip">{"".join(rows)}</div>'
                f'{_foot(ctx, pg, _sel(ctx, sels[3], pg) if len(sels) > 3 else "", rng.randint(12, 90))}</div>')
        body = f'<div class="row str f1">{_side(ctx, navs, "the sidebar", brand)}<div class="col f1">{_topbar(ctx, "the top bar", me)}<div class="col f1 clip g12 p16 bg1">{head}{card}</div></div></div>'
    elif variant == "products":
        prods = _products(ctx, nrows)
        head = (f'<div class="row g8" style="flex:none"><span class="xl b">Catalog</span><span class="pill">{rng.randint(80, 900)} listings</span><div class="sp"></div>{ctx.tbtn("import", tb)}{ctx.tbtn("export", tb)}'
                f'{ctx.tbtn("shop.addproduct", tb, cls="pri")}</div>')
        bulk = (f'<div class="row g8 p8 bb bg3" style="flex:none">{ctx.box("Select all products", True, region="the bulk action bar", refs=["the select-all checkbox in the bulk action bar"])}'
                f'<span class="m">{rng.randint(2, 6)} selected</span><div class="vsep"></div>{ctx.tbtn("shop.publish", "the bulk action bar", cls="sm")}{ctx.tbtn("shop.archive", "the bulk action bar", cls="sm")}'
                f'{ctx.tbtn("tagit", "the bulk action bar", cls="sm", obj="the ticked entries")}{ctx.tbtn("delete", "the bulk action bar", cls="sm dng", obj="the ticked entries")}<div class="sp"></div>'
                f'{ctx.search(tbl, w=220, cls="soft")}{_sel(ctx, sels[0], tbl) if sels else ""}{_sel(ctx, sels[1], tbl) if len(sels) > 1 else ""}{ctx.ibtn("view.list", tbl, cls="s", on=True)}{ctx.ibtn("view.grid", tbl, cls="s")}</div>')
        cw = [("Product", "flex:1 1 0"), ("Listing status", "width:120px"), ("Stock", "width:150px"), ("Category", "width:130px"), ("Vendor", "width:170px"), ("Price", "width:90px")]
        hdr = '<div class="tr h"><div class="td" style="width:36px"></div>' + "".join(_th(ctx, c, tbl, st, owned, "r" if c == "Price" else "") for c, st in cw) + '<div class="td" style="width:96px"></div></div>'
        vend = d.take("company", COMPANIES, 5)
        rows = []
        for i, name in enumerate(prods):
            attr = ctx.reg("row", "product", name, region=tbl, anchor="row")
            obj = f"the {name}"
            chk = ctx.box(f"Select {name}", i in (1, 2, 4), region=tbl, row=obj, refs=[f"the checkbox for the {name}", f"the checkbox next to {name}"])
            st = rng.choice(LIST)
            stock = rng.randint(0, 420)
            acts = ctx.ibtn("edit", tbl, row=obj, obj=obj, cls="s") + ctx.ibtn("duplicate", tbl, row=obj, obj=obj, cls="s") + ctx.ibtn("more", tbl, row=obj, obj=obj, cls="s", anchor="more")
            rows.append(f'<div class="tr"{attr} style="min-height:calc(var(--rh) + 12px)"><div class="td" style="width:36px">{chk}</div><div class="td f">{ctx.thumb(30, 30, 5)}<span class="el m">{esc(name)}</span></div>'
                        f'<div class="td" style="width:120px"><span class="pill {st[1]}">{st[0]}</span></div><div class="td {"err" if stock < 10 else "mut"}" style="width:150px">{stock} in {rng.randint(1, 6)} variants</div>'
                        f'<div class="td mut" style="width:130px">{rng.choice(CATS)}</div><div class="td mut" style="width:170px"><span class="el">{esc(rng.choice(vend))}</span></div>'
                        f'<div class="td r" style="width:90px">{d.money(8, 320)}</div><div class="td r" style="width:96px;gap:0">{acts}</div></div>')
        card = (f'<div class="card col f1 clip">{ctx.tabs(tabs, active=0, region="the status tabs")}{bulk}{hdr}<div class="col f1 clip">{"".join(rows)}</div>'
                f'{_foot(ctx, pg, _sel(ctx, sels[2], pg) if len(sels) > 2 else "", rng.randint(8, 40))}</div>')
        body = f'<div class="row str f1">{_side(ctx, navs, "the sidebar", brand, 1)}<div class="col f1">{_topbar(ctx, "the top bar", me)}<div class="col f1 clip g12 p16 bg1">{head}{card}</div></div></div>'
    elif variant == "customer_detail":
        rl, dr = "the icon rail", "the customer drawer"
        rail = "".join(ctx.ibtn(c, rl, on=i == 2) for i, c in enumerate(ctx.pick(NAV, 8, icon=True)))
        rail = f'<div class="rail br">{ctx.ibtn("home", rl)}{rail}<div class="sp"></div>{ctx.ibtn("settings", rl)}{_acct(ctx, rl, me)}</div>'
        head = (f'<div class="row g8 p12 bb" style="flex:none"><span class="lg b">Buyer directory</span><div class="sp"></div>{ctx.search(tbl, w=220, cls="soft")}{_sel(ctx, sels[0], tbl) if sels else ""}'
                f'{ctx.ibtn("filter", tbl, cls="bdr")}{ctx.tbtn("shop.addcustomer", tbl, cls="pri")}</div>')
        cw = [("Customer", "flex:1 1 0"), ("Home city", "width:110px"), ("Orders placed", "width:110px"), ("Total spent", "width:110px")]
        hdr = '<div class="tr h"><div class="td" style="width:36px"></div>' + "".join(_th(ctx, c, tbl, st, owned, "r" if "spent" in c or "placed" in c else "") for c, st in cw) + "</div>"
        rows, pick, pick_tid = [], rng.randrange(3, 7), 0
        for i, who in enumerate(people[:nrows]):
            attr = ctx.reg("row", "customer", who, region=tbl, anchor="row")
            if i == pick:
                pick_tid = ctx.last
            chk = ctx.box(f"Select {who}", False, region=tbl, row=who, refs=[f"the checkbox for {who}", f"the checkbox next to {who}"])
            rows.append(f'<div class="tr{" sel" if i == pick else ""}"{attr} style="min-height:calc(var(--rh) + 14px)"><div class="td" style="width:36px">{chk}</div>'
                        f'<div class="td f">{ctx.av(who, 26)}<div class="col" style="min-width:0"><span class="el m">{esc(who)}</span><span class="el mut xs">{esc(d.email_of(who))}</span></div></div>'
                        f'<div class="td mut" style="width:110px">{rng.choice(CITIES)}</div><div class="td r" style="width:110px">{rng.randint(1, 60)}</div><div class="td r" style="width:110px">{d.money(40, 9000)}</div></div>')
        listing = f'<div class="col f1">{head}{hdr}<div class="col f1 clip">{"".join(rows)}</div>{_foot(ctx, pg, _sel(ctx, sels[1], pg) if len(sels) > 1 else "", rng.randint(6, 30))}</div>'
        who = people[pick]
        acts = (f'<div class="row g6 wrap">{ctx.tbtn("shop.email", dr, cls="sm", icon=True, obj=who)}{ctx.tbtn("shop.neworder", dr, cls="sm")}{ctx.tbtn("shop.refund", dr, cls="sm", obj="the latest purchase")}'
                f'{ctx.ibtn("more", dr, cls="s bdr", anchor="more", obj="this customer")}</div>')
        fields = "".join(ctx.field(f, _fval(ctx, f, who), region=dr) for f in d.take("form.fields", FORM_FIELDS, 4))
        togs = "".join(ctx.toggle_row(ctx.lab(c), rng.random() < 0.5, region=dr, cid=c, cls="py4") for c in ctx.pick(TOGGLES, 3))
        recent, num = "", rng.randint(2000, 9000)
        for _ in range(3 if H < 1000 else 5):
            num -= rng.randint(3, 40)
            lab = f"#{num}"
            attr = ctx.reg("row", "order", lab, region=dr, refs=[f"order {lab} in the customer drawer", f"the {lab} order in the drawer"])
            st = rng.choice(FUL)
            recent += f'<div class="row g8 py4 bb"{attr}><span class="b">{lab}</span><span class="mut sm">{d.date()}</span><div class="sp"></div><span class="pill {st[1]}">{st[0]}</span><span style="width:70px" class="rt">{d.money(12, 600)}</span></div>'
        drawer = (f'<div class="side bl bg" style="width:{min(460, int(W * 0.3))}px"><div class="row g10 p16 bb">{ctx.av(who, 44)}<div class="col f1" style="min-width:0"><span class="lg b el" data-o="{pick_tid}">{esc(who)}</span>'
                  f'<span class="mut sm">Customer for {rng.randint(2, 60)} months</span></div>{ctx.ibtn("edit", dr, obj="this customer profile")}{ctx.ibtn("close.panel", dr, obj="the customer drawer")}</div>'
                  f'<div class="col g12 p16 f1 clip">{acts}<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 12px">{fields}</div>'
                  f'{ctx.field("Internal note", "", ph="Add a note about this customer…", region=dr, area=54)}<div class="col">{togs}</div>'
                  f'<div class="b" style="margin-top:4px">Recent purchases</div><div class="col">{recent}</div></div>'
                  f'<div class="row g8 p12 bt">{ctx.tbtn("delete", dr, cls="ghost dng", obj="this customer")}<div class="sp"></div>{ctx.tbtn("save", dr, cls="pri")}</div></div>')
        body = f'<div class="row str f1">{rail}{listing}{drawer}</div>'
    else:  # inventory_dense
        tn = "the top navigation"
        links = "".join(ctx.navc(c, tn, noun="link", icon_html="", on=i == 2) for i, c in enumerate(navs[:6 if W < 1500 else 9]))
        top = (f'<div class="row g8 px12 bb bg2" style="height:44px;flex:none"><div class="thumb" style="width:22px;height:22px;border-radius:6px;--c1:var(--ac);--c2:var(--acs2)"></div><span class="b">{esc(brand.split()[0])}</span>'
               f'<div class="row g2" style="margin-left:10px">{links}</div><div class="sp"></div>{ctx.search(tn, w=200, cls="soft")}{ctx.ibtn("notif", tn)}{ctx.ibtn("settings", tn)}{_acct(ctx, tn, me)}</div>')
        bar = (f'<div class="tb">{"".join(_sel(ctx, c, tb) for c in sels[:4])}<div class="sp"></div>{ctx.ibtn("filter", tb)}{ctx.ibtn("shop.cols", tb)}{ctx.ibtn("refresh", tb, obj="the stock figures")}'
               f'<div class="vsep"></div>{ctx.tbtn("import", tb, cls="sm")}{ctx.tbtn("export", tb, cls="sm")}{ctx.tbtn("shop.savestock", tb, cls="sm pri")}</div>')
        avail = W - (sum(int(x[:-2]) for x in spec["inset"].split()[1::2]) if spec["floating"] else 0)
        wide = avail >= 1500
        cw = [("SKU", "width:92px"), ("Product", "flex:1 1 0;min-width:210px")] + ([("Variant", "width:110px")] if wide else []) + [("Bin", "width:64px"), ("On hand", "width:104px"),
              ("Committed", "width:84px"), ("Available", "width:80px")] + ([("Incoming", "width:80px")] if wide else []) + [("Reorder point", "width:104px"),
              ("Supplier", f"width:{170 if wide else 150}px"), ("Unit cost", "width:80px")]
        hdr = '<div class="tr h"><div class="td" style="width:32px"></div>' + "".join(_th(ctx, c, tbl, st, owned, "r" if c in ("Committed", "Available", "Incoming", "Unit cost") else "") for c, st in cw) + '<div class="td" style="width:64px"></div></div>'
        sup = d.take("company", COMPANIES, 6)
        rows = []
        for i, name in enumerate(_products(ctx, nrows + 6)):
            attr = ctx.reg("row", "product", name, region=tbl, anchor="row", refs=[f"the row for the {name}", f"the {name} row"])
            sku = f"{''.join(w[0] for w in name.split()[:2]).upper()}-{rng.randint(1000, 9899)}"
            on, com, inc = rng.randint(0, 600), rng.randint(0, 40), rng.choice([0, 0, 24, 48, 120])
            chk = ctx.box(f"Select {name}", rng.random() < 0.1, region=tbl, row=name, refs=[f"the checkbox for the {name}", f"the checkbox on the {name} row"])
            dec = ctx.reg("button", "button", f"Decrease {name}", ui="icon", cid="shop.dec", region=tbl, row=name, obj=f"the {name}",
                          refs=[f"the minus button for the {name}", f"the − stepper on the {name} row"])
            inc_ = ctx.reg("button", "button", f"Increase {name}", ui="icon", cid="shop.inc", region=tbl, row=name, obj=f"the {name}",
                           refs=[f"the plus button for the {name}", f"the + stepper on the {name} row"])
            step = f'<div class="shop-st"><div{dec}>−</div><div class="v">{on}</div><div{inc_}>+</div></div>'
            ro = ctx.reg("field", "field", f"Reorder point {name}", region=tbl, row=name, refs=[f"the reorder point field for the {name}", f"the reorder point box on the {name} row"])
            sp = ctx.reg("select", "dropdown", f"Supplier {name}", region=tbl, row=name, refs=[f"the supplier dropdown for the {name}", f"the supplier dropdown on the {name} row"])
            low = on - com < 20
            lowpill = '<span class="pill r">Low</span>' if low else ""
            variant_cell = f'<div class="td mut" style="width:110px">{rng.choice(["Default", "Small", "Large", "Black", "Olive", "Set of 2"])}</div>' if wide else ""
            incoming_cell = f'<div class="td r mut" style="width:80px">{inc or "—"}</div>' if wide else ""
            rows.append(f'<div class="tr z"{attr}><div class="td" style="width:32px">{chk}</div><div class="td mono xs mut" style="width:92px">{sku}</div><div class="td f" style="min-width:210px"><span class="el">{esc(name)}</span>'
                        f'{lowpill}</div>{variant_cell}'
                        f'<div class="td mono xs" style="width:64px">{rng.choice("ABCDEF")}{rng.randint(1, 24)}-{rng.randint(1, 6)}</div><div class="td" style="width:104px">{step}</div>'
                        f'<div class="td r mut" style="width:84px">{com}</div><div class="td r {"err b" if low else ""}" style="width:80px">{on - com}</div>{incoming_cell}'
                        f'<div class="td" style="width:104px"><div class="inp shop-cell"{ro} style="width:70px"><span class="el f1">{rng.choice([10, 20, 25, 50, 100])}</span></div></div>'
                        f'<div class="td" style="width:{170 if wide else 150}px"><div class="inp shop-cell f1"{sp}><span class="el f1">{esc(rng.choice(sup))}</span>{CHEV_D}</div></div>'
                        f'<div class="td r mut" style="width:80px">{d.money(2, 90)}</div><div class="td r" style="width:64px;gap:0">{ctx.ibtn("history", tbl, row=f"the {name}", obj=f"the stock of the {name}", cls="s")}'
                        f'{ctx.ibtn("more", tbl, row=f"the {name}", obj=f"the {name}", cls="s", anchor="more")}</div></div>')
        tabsrow = ctx.tabs(tabs, active=1, region="the status tabs")
        foot = _foot(ctx, pg, _sel(ctx, sels[4], pg) if len(sels) > 4 else "", rng.randint(9, 60))
        body = f'<div class="col f1">{top}{tabsrow}{bar}{hdr}<div class="col f1 clip">{"".join(rows)}</div>{foot}</div>'
    return {"title": f"{brand} · Admin", "body": body, "menus": [], "url": f"admin.{brand.split()[0].lower()}.example.com/{variant.split('_')[0]}", "app": "Store admin", "css": CSS}
