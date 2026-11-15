"""Email clients: folder sidebar, message list, reading pane, compose form."""
from ..data import LOREM, SUBJECTS
from ..ui import CHEV_L, CHEV_R, esc
from ..vocab import C, P

NAME = "email"
KIND = "either"
VARIANTS = {"three_pane": "train", "stacked": "train", "wide_table": "train", "compose": "dev", "rail_conversation": "test"}

C("mail.compose", "Compose|New message|Write", "square-pen|mail-plus|pen-line", "start an email to someone from scratch|begin drafting a fresh email|open a blank email I can fill in and dispatch")
C("mail.reply", "Reply|Respond|Answer", "reply|corner-up-left|message-square-reply", "write back to the sender of {o}|send my response to whoever wrote {o}|get back to the person who sent {o}", o="this email")
C("mail.replyall", "Reply all|Respond to all|Answer everyone", "reply-all|messages-square|message-circle-reply", "write back to every recipient of {o} at once|send my response to the whole group copied on {o}|get back to all the people who received {o}", o="this email")
C("mail.forward", "Forward email|Pass along|Send onward", "forward|corner-up-right|arrow-big-right", "hand {o} over to a person who was not on it|relay {o} to a different recipient|share {o} with a third party by mail", o="this email")
C("mail.archive", "Archive|File away|Move to archive", "archive|archive-restore|package|folder-archive", "tuck {o} out of the inbox without deleting it|store {o} out of sight for safekeeping|clear {o} from my inbox but keep it on record", o="this email")
C("mail.spam", "Report spam|Mark as junk|Block sender", "octagon-alert|shield-alert|ban", "flag {o} as unwanted bulk mail|tell the service that {o} is unsolicited garbage|make sure mail like {o} stops reaching me", o="this email")
C("mail.unread", "Mark as unread|Mark unread|Keep as new", "mail-open|mail-dot|mail-question-mark", "make {o} look like I have not opened it yet|restore the bold not-yet-opened state of {o}|have {o} show up again as not seen", o="this email")
C("mail.snooze", "Snooze|Remind me later|Postpone", "alarm-clock|clock-arrow-up|timer-reset", "have {o} come back to the top at a time I choose|hide {o} for now and make it return in a while|defer {o} until I have time to deal with it", o="this email")
C("mail.flag", "Flag|Mark important|Follow up", "flag|flag-triangle-right|circle-alert", "put a marker on {o} so I act on it soon|highlight {o} as needing my attention|single out {o} as high priority", o="this email")
C("mail.discard", "Discard draft|Throw away draft|Cancel message", "", "abandon what I have typed and close the composer|scrap this unfinished email|give up on writing this email")
C("mail.schedule", "Send later|Schedule send|Delay delivery", "calendar-clock|clock-arrow-right|hourglass", "have this email go out at a time I pick instead of now|queue this email for a future moment|set a departure time for this email")
C("mail.quick", "Quick reply|Write a response|Type your answer", "", "type a short answer right underneath the open email|jot a fast response below what I am reading|respond inline without opening the full composer")
C("mail.to", "To|Recipients|Send to", "", "fill in who should receive what I am writing|enter the address of the person this is going to|specify the addressee")
C("mail.cc", "Cc|Copy to|Carbon copy", "", "add a person who should get this for their information only|include an extra reader who is not the main addressee|loop a bystander in on this email")
C("mail.subject", "Subject|Subject line|Topic", "", "give this email a headline|type the title the addressee will see in their inbox|say in a few words what this email is about")
C("mail.f.inbox", "Inbox|Incoming|Received", "inbox|mailbox|mails", "see the emails that have arrived for me|look at my newly arrived mail|check what people have sent me")
C("mail.f.sent", "Sent|Sent mail|Outbox", "send|send-horizontal|mail-check", "review the emails I already dispatched|look at mail that went out from me|see what I wrote to other people earlier")
C("mail.f.drafts", "Drafts|Unfinished|Saved drafts", "file-pen|file-pen-line|notebook-pen", "find the emails I began but never dispatched|get back to a half-written email|see messages I have not completed yet")
C("mail.f.starred", "Starred|Favorites|Important", "star|heart|bookmark", "see only the emails I marked as special|list the emails I singled out to keep handy|show the emails I highlighted earlier")
C("mail.f.trash", "Deleted items|Bin|Recycle bin", "folder-x|archive-x|octagon-x", "look through the emails I threw away|recover something I got rid of by mistake|see what is waiting to be purged for good")
C("mail.f.spam", "Spam|Junk|Quarantine", "shield-x|shield-ban|shield-off", "check the suspicious mail that was filtered out|see whether a real email was caught by the filter|look at the unsolicited bulk mail held aside")
C("mail.f.all", "All mail|Everything|Full archive", "library|layers|database", "see every email regardless of folder|browse the complete history of my correspondence|list each email I ever kept")
C("mail.f.scheduled", "Scheduled|Send queue|Timed sends", "calendar-clock|clock-arrow-right|hourglass", "see the emails waiting to go out at a set time|check which emails are due to depart in future|review mail lined up for future delivery")
APPS = P("mail.app", [
    ("Mail", "get to my emails", "mails"), ("Agenda", "see what is on my schedule", "calendar-range"),
    ("Contacts", "look up the entries in my address book", "contact"), ("To-dos", "see my checklist of things to finish", "list-todo"),
    ("Sticky notes", "open my jotted memos", "sticky-note"), ("Cloud files", "browse the documents stored online", "folder-sync"),
    ("People", "browse my colleagues' profiles", "contact-round"), ("Meetings", "join or set up a video conference", "presentation"),
    ("Newsletters", "read the bulletins I subscribe to", "newspaper"), ("Rules", "manage automatic sorting of incoming mail", "workflow"),
    ("Templates", "reuse a canned email", "layout-template"), ("Signatures", "edit the sign-off placed under my emails", "signature"),
    ("Chat", "talk to someone in real time", "message-square-dot"), ("Bookings", "let others reserve time with me", "calendar-check"),
    ("Reminders", "see the nudges I set for myself", "alarm-clock-check"), ("Voice memos", "listen to recorded audio notes", "voicemail"),
    ("Boards", "open my planning boards", "folder-kanban"), ("Insights", "see statistics about my correspondence", "chart-no-axes-combined"),
    ("Tracking", "see whether my emails were opened", "radar"), ("Encryption keys", "manage the certificates used to sign my mail", "key-square"),
    ("Out of office", "set up an automatic away response", "plane"), ("Mailing lists", "manage the groups I send bulletins to", "megaphone"),
])
FMT = P("mail.fmt", [
    ("Bold", "make the selected words heavier", "bold"), ("Italic", "slant the selected words", "italic"),
    ("Underline", "draw a line beneath the selected words", "underline"), ("Strikethrough", "cross out the selected words", "strikethrough"),
    ("Bulleted list", "turn the lines into points with dots", "list"), ("Numbered list", "turn the lines into counted steps", "list-ordered"),
    ("Insert link", "turn the selected words into a clickable web address", "link|link-2"), ("Insert picture", "put a photo into the body of what I am writing", "image-up"),
    ("Insert emoji", "add a smiley to what I am writing", "sticker"), ("Block quote", "set the paragraph off as a citation", "text-quote"),
    ("Text color", "change the hue of the letters", "baseline"), ("Highlight", "put a marker-pen background behind the words", "highlighter"),
    ("Align left", "line the paragraph up against the left edge", "align-left"), ("Align center", "put the paragraph in the middle of the line", "align-center"),
    ("Indent more", "push the paragraph further to the right", "indent-increase"), ("Indent less", "pull the paragraph back toward the left margin", "indent-decrease"),
    ("Clear formatting", "strip all styling from the selected words", "remove-formatting"), ("Heading", "turn the line into a large title", "heading"),
    ("Insert table", "add a grid of rows and columns to the body", "table-properties"), ("Insert signature", "append my sign-off block", "feather"),
])
LABELS = ["Work", "Personal", "Travel", "Receipts", "Family", "Finance", "Clients", "Urgent", "Waiting on", "Read later", "Subscriptions",
          "Team updates", "Recruiting", "Vendors", "Legal review", "Side project", "School", "Health", "Purchases", "Events 2026"]
VIEWS = ["All", "Unread", "Flagged", "Focused", "Other", "Primary", "Promotions", "Social", "Mentions", "Has attachments", "To me",
         "VIP", "Today", "This week", "Pinned"]
ACTIONS = ["mail.reply", "mail.replyall", "mail.forward", "|", "mail.archive", "delete", "mail.spam", "|", "mail.unread", "mail.snooze",
           "mail.flag", "move", "tagit", "|", "print"]
FOLDERS = ["mail.f.inbox", "mail.f.starred", "mail.f.sent", "mail.f.drafts", "mail.f.scheduled", "mail.f.all", "mail.f.spam", "mail.f.trash"]

CSS = """
.em-row{display:flex;align-items:flex-start;gap:8px;padding:7px 10px;border-bottom:1px solid var(--bd);flex:none}
.em-row.sel{background:var(--acs);box-shadow:inset 3px 0 0 var(--ac)}
.em-snip{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.em-chip{display:inline-flex;align-items:center;gap:6px;height:calc(var(--ch) + 4px);padding:0 4px 0 8px;border:1px solid var(--bd);border-radius:var(--r);background:var(--bg1)}
.em-tok{display:inline-flex;align-items:center;height:1.6em;padding:0 8px;border-radius:999px;background:var(--bg4);font-size:.92em;white-space:nowrap}
.em-body p{margin:0 0 .9em;line-height:1.55;max-width:760px}
"""


def _emails(ctx, n):
    d, rng = ctx.d, ctx.rng
    people = d.people(n)
    base = d.take("mail.subjects", SUBJECTS)
    subjects = base + [f"{pre} {s}" for pre in ("Re:", "Fwd:", "RE:") for s in base]
    out = []
    for i in range(min(n, len(subjects))):
        s, p = subjects[i], people[i]
        out.append({"sender": p, "subject": s, "snippet": rng.choice(LOREM), "time": d.time() if i < 5 else d.date(),
                    "unread": rng.random() < 0.3, "attach": rng.random() < 0.25, "row": f"the email from {p}",
                    "refs": [f"the email from {p}", f"the message from {p}", f'the email with the subject "{s}"', f"{p}'s email"]})
    rng.shuffle(out)
    return out


def _avatar(ctx, me, region, size=26):
    if not ctx.has("account"):
        return ctx.av(me, size)
    attr = ctx.reg("button", "avatar", ctx.lab("account"), ui="icon", cid="account", region=region, anchor="account")
    return f'<div class="row"{attr}>{ctx.av(me, size)}</div>'


def _folders(ctx, region, w, sel=0, dk=False, compose=True):
    rng, d = ctx.rng, ctx.d
    top = f'<div class="col p8">{ctx.tbtn("mail.compose", region, cls="pri lgb", icon=True)}</div>' if compose else ""
    nav = "".join(ctx.navc(c, region, on=i == sel, noun="folder", count=rng.choice([None, None, rng.randint(1, 148)]))
                  for i, c in enumerate(ctx.avail(FOLDERS)))
    labels = "".join(ctx.nav(l, region, noun="label", icon_html=f'<span class="dot" style="background:{d.color()};margin:0 4px"></span>')
                     for l in d.take("mail.labels", LABELS, rng.randint(3, 6)))
    used = rng.randint(12, 88)
    store = (f'<div class="col g4 p12 bt"><div class="prog"><div style="width:{used}%"></div></div>'
             f'<span class="xs mut">{used * 0.15:.1f} GB of 15 GB used</span></div>')
    return (f'<div class="side br{" dk" if dk else ""}" style="width:{w}px">{top}<div class="col g2">{nav}</div>'
            f'<div class="row"><div class="hd sp">Labels</div>{ctx.ibtn("add", region, cls="s", obj="my labels", anchor=None)}</div>'
            f'<div class="col g2">{labels}</div><div class="sp"></div>{store}</div>')


def _row2(ctx, e, region, sel=False, checks=False):
    """Two-line list entry: sender and time, subject, preview."""
    attr = ctx.reg("row", "email", e["subject"], region=region, anchor="row", refs=e["refs"])
    lead = ctx.box(f'Select {e["subject"]}', False, region=region, row=e["row"],
                   refs=[f'the checkbox for {e["row"]}', f"the checkbox next to {e['sender']}'s email"]) if checks else ctx.av(e["sender"], 28)
    clip = ctx.deco("paperclip", "file-plus-2", "image-plus", "link-2", size=12) if e["attach"] else ""
    star = ctx.ibtn("fav", region, row=e["row"], obj=e["row"], cls="s", anchor=None)
    w = "b" if e["unread"] else ""
    return (f'<div class="em-row{" sel" if sel else ""}"{attr}>{lead}<div class="col f1" style="min-width:0;gap:1px">'
            f'<div class="row g6"><span class="el f1 {w}">{esc(e["sender"])}</span>{clip}<span class="xs mut nw">{esc(e["time"])}</span></div>'
            f'<span class="el {w or "m"}">{esc(e["subject"])}</span><span class="em-snip mut sm">{esc(e["snippet"])}</span></div>{star}</div>')


def _row1(ctx, e, region, sel=False, wide=False):
    """One-line table entry."""
    rng = ctx.rng
    attr = ctx.reg("row", "email", e["subject"], region=region, anchor="row", refs=e["refs"])
    box = ctx.box(f'Select {e["subject"]}', sel, region=region, row=e["row"],
                  refs=[f'the checkbox for {e["row"]}', f"the checkbox next to {e['sender']}'s email"])
    star = ctx.ibtn("fav", region, row=e["row"], obj=e["row"], cls="s", anchor=None)
    w = "b" if e["unread"] else ""
    clip = ctx.deco("paperclip", "file-plus-2", "image-plus", "link-2", size=12) if e["attach"] else ""
    extra = ""
    if wide:
        tag = rng.choice(["", "", '<span class="pill a">Client</span>', '<span class="pill y">Pending</span>', '<span class="pill g">Paid</span>'])
        extra = f'<div class="td" style="width:90px">{tag}</div><div class="td mut r" style="width:70px">{rng.randint(4, 890)} KB</div>'
    return (f'<div class="tr{" sel" if sel else ""}"{attr}><div class="td" style="width:62px;gap:2px">{box}{star}</div>'
            f'<div class="td {w}" style="width:{190 if wide else 160}px"><span class="el">{esc(e["sender"])}</span></div>'
            f'<div class="td f"><span class="el {w}" style="flex:none;max-width:60%">{esc(e["subject"])}</span><span class="em-snip mut">— {esc(e["snippet"])}</span></div>'
            f'<div class="td" style="width:24px;padding:0">{clip}</div>{extra}<div class="td mut r nw" style="width:86px">{esc(e["time"])}</div></div>')


def _actions(ctx, region, labels=False):
    out = []
    for cid in ACTIONS:
        if cid == "|":
            out.append('<div class="vsep"></div>')
        elif labels and cid in ("mail.reply", "mail.replyall", "mail.forward", "mail.archive", "delete"):
            out.append(ctx.tbtn(cid, region, cls="ghost", icon=True, obj="this email"))
        else:
            out.append(ctx.ibtn(cid, region, obj="this email"))
    return "".join(out) + ctx.ibtn("more", region, obj="this email", anchor="more")


def _reading(ctx, e, region, toolbar="icons", quick=True):
    rng, d = ctx.rng, ctx.d
    tb = f'<div class="tb plain">{_actions(ctx, region, toolbar == "labels")}</div>' if toolbar else ""
    others = d.people(4)[1:3]
    badge = rng.choice(["", '<span class="pill">External</span>', '<span class="pill a">Encrypted</span>'])
    head = f'<div class="row g10"><span class="xl b f1">{esc(e["subject"])}</span>{badge}</div>'
    meta = (f'<div class="row g10">{ctx.av(e["sender"], 36)}<div class="col f1"><div class="row g6"><span class="b">{esc(e["sender"])}</span>'
            f'<span class="mut sm">&lt;{esc(d.email_of(e["sender"]))}&gt;</span></div><span class="mut sm">to me, {esc(others[0].split()[0])}, {esc(others[1].split()[0])}</span></div>'
            f'<span class="mut sm nw">{d.date(True)}, {d.time()}</span></div>')
    body = "".join(f"<p>{esc(t)}</p>" for t in ["Hi all,"] + rng.sample(LOREM, rng.randint(3, 5)) + ["Best,", e["sender"].split()[0]])
    chips = []
    for name, _ in d.mixed_files(rng.randint(0, 3)):
        attr = ctx.reg("row", "attachment", name, region=region)
        dl = ctx.ibtn("download", region, row=name, obj=f"the attachment {name}", cls="s", anchor=None)
        chips.append(f'<div class="em-chip"{attr}>{ctx.deco("file", "file-text", "file-image", "file-chart-column", "file-archive", blank=True)}<span>{esc(name)}</span><span class="mut xs">{d.size()}</span>{dl}</div>')
    atts = f'<div class="row g8 wrap">{"".join(chips)}</div>' if chips else ""
    reply = ""
    if quick and ctx.has("mail.quick"):
        ph = ctx.lab("mail.quick")
        attr = ctx.reg("field", "box", ph, cid="mail.quick", region=region)
        reply = (f'<div class="row g8"><div class="inp f1" style="height:calc(var(--ch) + 10px)"{attr}><span class="ph">{esc(ph)}…</span></div>'
                 f'{ctx.ibtn("attach", region, obj="my answer")}{ctx.tbtn("send", region, cls="pri", obj="my answer")}</div>')
    return (f'<div class="col f1 clip">{tb}<div class="col g12 f1 clip p20 em-body">{head}{meta}<div class="hsep"></div><div>{body}</div>{atts}'
            f'<div class="sp"></div>{reply}</div></div>')


def _listhead(ctx, region, title=True):
    rng, d = ctx.rng, ctx.d
    views = d.take("mail.views", VIEWS, rng.randint(2, 3))
    seg = ctx.seg(views, 0, region=region, noun="filter")
    tools = ctx.ibtn("filter", region) + ctx.ibtn("sort", region) + ctx.ibtn("refresh", region, obj="the message list")
    return f'<div class="row g6 p8 bb">{seg}<div class="sp"></div>{tools}</div>'


def _topbar(ctx, me, region="the top bar"):
    rng = ctx.rng
    logo = '<div class="thumb" style="width:24px;height:24px;border-radius:6px;--c1:var(--ac);--c2:var(--acs2)"></div>'
    return (f'<div class="row g10 bb bg1 px12" style="height:calc(var(--ch) + 22px)">{ctx.ibtn("sidebar.toggle", region)}{logo}'
            f'<span class="b lg">{rng.choice(["Postbox", "Mailroom", "Courier", "Letterbird", "Pigeon Mail"])}</span><div style="width:24px"></div>'
            f'{ctx.search(region, w=min(560, 380 + rng.randint(0, 180)), cls="rnd soft")}<div class="sp"></div>'
            f'{ctx.ibtn("help", region)}{ctx.ibtn("settings", region)}{ctx.ibtn("apps", region)}{_avatar(ctx, me, region)}</div>')


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    me = d.person()
    n = H // 46 + 4
    emails = _emails(ctx, n)
    sel = rng.randrange(min(6, len(emails)))
    sw = rng.choice([200, 220, 240]) + (30 if W > 1900 else 0)
    dk = rng.random() < 0.25
    ctx.ctxmenu = ["mail.reply", "mail.replyall", "mail.forward", "-", "mail.unread", "mail.flag", "mail.snooze", "tagit", "-",
                   "mail.archive", "move", "mail.spam", "delete"]
    ctx.ctxobj = "this email"
    ctx.menus["mb.message"] = ["mail.compose", "-", "mail.reply", "mail.replyall", "mail.forward", "-", "mail.unread", "mail.flag",
                               "mail.snooze", "-", "mail.archive", "mail.spam", "move", "delete"]
    top = _topbar(ctx, me) if spec["web"] or rng.random() < 0.4 else ""
    status = (f'<div class="sbar"><span class="si">{ctx.deco("wifi", "cloud-check", "circle-check", "plug-zap", "refresh-cw")}Connected</span>'
              f'<span>{rng.randint(120, 9800):,} messages, {rng.randint(1, 60)} unread</span><div class="sp"></div><span>Last synced {d.time()}</span></div>')

    if variant == "three_pane":
        lw = rng.choice([340, 380, 420]) + (60 if W > 1900 else 0) - (60 if W < 1400 else 0)
        checks = rng.random() < 0.3
        rows = "".join(_row2(ctx, e, "the message list", i == sel, checks=checks) for i, e in enumerate(emails))
        lst = f'<div class="col br" style="width:{lw}px">{_listhead(ctx, "the message list")}<div class="col f1 clip rel">{rows}{ctx.scroll(4, 24)}</div></div>'
        if not top:
            lst = lst.replace('<div class="row g6 p8 bb">', f'<div class="p8 bb">{ctx.search("the message list", cls="soft")}</div><div class="row g6 p8 bb">', 1)
        main = f'<div class="row str f1">{_folders(ctx, "the sidebar", sw, dk=dk)}{lst}{_reading(ctx, emails[sel], "the reading pane")}</div>'
        body = f'<div class="col f1">{top}{main}{status if rng.random() < 0.5 else ""}</div>'
    elif variant == "stacked":
        tb = (f'<div class="tb">{ctx.tbtn("mail.compose", "the toolbar", cls="pri", icon=True)}<div class="vsep"></div>{_actions(ctx, "the toolbar", labels=W >= 1500)}'
              f'<div class="sp"></div>{ctx.search("the toolbar", w=240) if not top else ""}</div>')
        k = max(5, int(H * 0.36) // 28)
        hdr = ('<div class="tr h"><div class="td" style="width:62px"></div><div class="td" style="width:160px">From</div><div class="td f">Subject</div>'
               '<div class="td" style="width:24px;padding:0"></div><div class="td r" style="width:86px">Received</div></div>')
        rows = "".join(_row1(ctx, e, "the message list", i == sel) for i, e in enumerate(emails[:k]))
        lst = f'<div class="col clip bb" style="flex:none">{hdr}{rows}</div>'
        right = f'<div class="col f1 clip">{lst}{_reading(ctx, emails[sel], "the reading pane", toolbar=None)}</div>'
        body = f'<div class="col f1">{top}{tb}<div class="row str f1">{_folders(ctx, "the sidebar", sw, dk=dk, compose=False)}{right}</div>{status}</div>'
    elif variant == "wide_table":
        bulk = (f'<div class="tb plain">{ctx.box("Select all emails", False, region="the toolbar", refs=["the select-all checkbox", "the checkbox that selects every email"])}'
                f'<div class="vsep"></div>{_actions(ctx, "the toolbar")}<div class="sp"></div><span class="mut sm nw">1–{len(emails)} of {rng.randint(300, 4000):,}</span>'
                f'<span class="row g8 mut">{CHEV_L}{CHEV_R}</span>{ctx.ibtn("settings", "the toolbar") if not top else ""}</div>')
        views = d.take("mail.views", VIEWS, rng.randint(3, 4))
        tabs = ctx.tabs(views, 0, region="the tab bar", noun="tab")
        rows = "".join(_row1(ctx, e, "the message list", False, wide=True) for e in emails)
        table = f'<div class="col f1 clip rel">{rows}{ctx.scroll(2, 30)}</div>'
        side2 = ""
        if W >= 1500:
            evs = "".join(f'<div class="li" style="align-items:flex-start;padding:6px 12px"><span class="dot" style="background:{d.color()};margin-top:5px"></span>'
                          f'<div class="col"><span class="m">{esc(t)}</span><span class="mut xs">{d.time()} · {rng.choice(["Room 4", "Video call", "Cafeteria", "HQ 2F"])}</span></div></div>'
                          for t in ["Standup", "Vendor sync", "Lunch", "Planning", "Dentist", "Review"][:rng.randint(3, 6)])
            side2 = (f'<div class="side bl" style="width:250px"><div class="row p12 bb"><span class="b sp">Up next</span>{ctx.ibtn("close.panel", "the side panel", cls="s", obj="the side panel")}</div>'
                     f'{evs}<div class="sp"></div><div class="p12">{ctx.tbtn("mail.schedule", "the side panel", cls="w100")}</div></div>')
        main = f'<div class="col f1 clip">{bulk}{tabs}{table}</div>'
        body = f'<div class="col f1">{top}<div class="row str f1">{_folders(ctx, "the sidebar", sw, dk=dk)}{main}{side2}</div>{status}</div>'
    elif variant == "compose":
        lw = rng.choice([300, 330, 360])
        rows = "".join(_row2(ctx, e, "the message list", False) for e in emails)
        lst = f'<div class="col br" style="width:{lw}px">{_listhead(ctx, "the message list")}<div class="col f1 clip">{rows}</div></div>'
        region = "the compose form"
        to = d.people(6)[3:3 + rng.randint(1, 2)]

        def line(cid, inner, tail=""):
            if not ctx.has(cid):
                return ""
            attr = ctx.reg("field", "field", ctx.lab(cid), cid=cid, region=region)
            tid = ctx.last
            return (f'<div class="row g10 bb" style="min-height:calc(var(--ch) + 12px)"><span class="mut" style="width:86px" data-o="{tid}">{esc(ctx.lab(cid))}</span>'
                    f'<div class="row g6 f1" style="align-self:stretch"{attr}>{inner}</div>{tail}</div>')
        toks = "".join(f'<span class="em-tok">{esc(p)}</span>' for p in to)
        fmt = "".join(ctx.ibtn(c, region, cls="s") for c in ctx.pick(FMT, 12, icon=True))
        text = "".join(f"<p>{esc(t)}</p>" for t in ["Hello " + to[0].split()[0] + ","] + rng.sample(LOREM, rng.randint(2, 4)))
        subj = rng.choice(["Following up on our call", "Revised numbers attached", "Quick question about Thursday", "Notes and next steps"])
        foot = (f'<div class="row g8 p12 bt">{ctx.tbtn("send", region, cls="pri", icon=True, obj="this email")}{ctx.tbtn("mail.schedule", region, caret=True)}'
                f'{ctx.ibtn("attach", region, obj="this email")}{ctx.ibtn("link", region, func=False)}<div class="sp"></div><span class="mut sm">Draft saved {d.time()}</span>'
                f'{ctx.tbtn("mail.discard", region, cls="ghost dng")}</div>')
        form = (f'<div class="col f1 clip"><div class="row g8 px16 bb bg1" style="height:calc(var(--ch) + 16px)"><span class="b f1">New email</span>'
                f'{ctx.ibtn("fullscreen", region, cls="s")}{ctx.ibtn("close.panel", region, cls="s", obj="the composer")}</div>'
                f'<div class="col px16">{line("mail.to", toks)}{line("mail.cc", "")}{line("mail.subject", f"<span>{esc(subj)}</span>")}</div>'
                f'<div class="row g2 px12 bb" style="min-height:calc(var(--ch) + 10px)">{fmt}</div><div class="f1 clip p16 em-body">{text}</div>{foot}</div>')
        body = f'<div class="col f1">{top}<div class="row str f1">{_folders(ctx, "the sidebar", sw, dk=dk)}{lst}{form}</div></div>'
    else:  # rail_conversation
        rail = "".join(ctx.ibtn(c, "the app rail", on=i == 0) for i, c in enumerate(ctx.pick(APPS, 7, icon=True)))
        rail = f'<div class="rail br">{rail}<div class="sp"></div>{ctx.ibtn("settings", "the app rail")}{_avatar(ctx, me, "the app rail", 28) if not top else ""}</div>'
        lw = rng.choice([320, 360, 400])
        fl = "".join(ctx.navc(c, "the folder strip", on=i == 0, noun="folder", icon_html="") for i, c in enumerate(ctx.avail(FOLDERS)[:4]))
        rows = "".join(_row2(ctx, e, "the message list", i == sel) for i, e in enumerate(emails))
        lst = (f'<div class="col br" style="width:{lw}px"><div class="row g8 p8">{ctx.search("the message list", cls="soft f1")}{ctx.ibtn("mail.compose", "the message list", cls="fill")}</div>'
               f'<div class="row bb" style="padding:0 2px 6px">{fl}</div><div class="col f1 clip">{rows}</div></div>')
        e = emails[sel]
        thread = d.people(9)[5:5 + rng.randint(2, 4)]
        earlier = []
        for p in thread:
            attr = ctx.reg("row", "reply", f"{p} earlier reply", region="the conversation", direct=True,
                           refs=[f"the collapsed reply from {p}", f"{p}'s earlier reply in the thread"])
            earlier.append(f'<div class="row g10 bb py8"{attr}>{ctx.av(p, 26)}<span class="m" style="width:150px">{esc(p)}</span>'
                           f'<span class="em-snip mut f1">{esc(rng.choice(LOREM))}</span><span class="mut xs nw">{d.date()}</span></div>')
        head = (f'<div class="row g8 px16 bb" style="min-height:calc(var(--ch) + 18px)"><span class="lg b f1">{esc(e["subject"])}</span><span class="pill">{len(thread) + 1} messages</span>'
                f'{ctx.ibtns(["mail.archive", "delete", "mail.unread", "mail.snooze", "print"], "the conversation header", obj="this conversation")}{ctx.ibtn("more", "the conversation header", anchor="more")}</div>')
        last = (f'<div class="col g10 py8"><div class="row g10">{ctx.av(e["sender"], 32)}<div class="col f1"><span class="b">{esc(e["sender"])}</span><span class="mut sm">to me</span></div>'
                f'<span class="mut sm">{d.time()}</span>{ctx.ibtn("mail.reply", "the conversation", cls="s", obj="this email")}{ctx.ibtn("mail.forward", "the conversation", cls="s", obj="this email")}</div>'
                f'<div class="em-body">{"".join(f"<p>{esc(t)}</p>" for t in rng.sample(LOREM, 3))}</div></div>')
        box = ""
        if ctx.has("mail.quick"):
            attr = ctx.reg("field", "box", ctx.lab("mail.quick"), cid="mail.quick", region="the conversation")
            box = (f'<div class="card col" style="margin:0 16px 14px"><div class="p12" style="min-height:70px"{attr}><span class="fnt">{esc(ctx.lab("mail.quick"))}…</span></div>'
                   f'<div class="row g4 p8 bt">{"".join(ctx.ibtn(c, "the reply box", cls="s") for c in ctx.pick(FMT, 6, icon=True))}{ctx.ibtn("attach", "the reply box", cls="s", obj="my answer")}'
                   f'<div class="sp"></div>{ctx.tbtn("mail.replyall", "the reply box", cls="ghost")}{ctx.tbtn("send", "the reply box", cls="pri", obj="my answer")}</div></div>')
        conv = f'<div class="col f1 clip">{head}<div class="col f1 clip px16">{"".join(earlier)}{last}</div>{box}</div>'
        body = f'<div class="col f1">{top}<div class="row str f1">{rail}{lst}{conv}</div></div>'
    return {"title": rng.choice(["Inbox", "Mail", "Postbox"]) + f" — {d.email_of(me)}", "body": body, "css": CSS, "app": "Mail",
            "menus": ["mb.file", "mb.edit", "mb.view", "mb.message", "mb.window", "mb.help"], "url": "mail.example.com/inbox"}
