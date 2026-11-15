"""Mail: start state and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
"""
from ..oracle import Click, Drag, Reveal, Type
from . import pools
from .base import Spec, by_id, cond, norm, only, say, task, unchanged, verdict

SIZE = (1040, 640)
WIN = '.win[data-app="mail"] '
BOXES = [{"id": "inbox", "name": "Inbox", "icon": "inbox"}, {"id": "drafts", "name": "Drafts", "icon": "doc"}, {"id": "sent", "name": "Sent", "icon": "send"},
         {"id": "junk", "name": "Junk", "icon": "x"}, {"id": "trash", "name": "Trash", "icon": "trash"}, {"id": "archive", "name": "Archive", "icon": "archive"}]
REPLIES = ["Thanks, that works for me.", "Got it, I will take a look tonight.", "Sounds good, see you then.", "Can we move this to next week?",
           "Yes please, count me in.", "Sorry, I can't make it this time.", "Received, thank you.", "Let's talk about it on Monday."]
SUBJECTS = ["Keys for the weekend", "Running late tomorrow", "Draft of the agenda", "Parking permit", "Lunch order", "Change of address",
            "Printer in room 4", "Holiday cover", "Recipe you asked for", "Bike for sale"]
BODIES = ["The spare key is with the neighbour at number 9.", "I will be about twenty minutes late, please start without me.",
          "Here is the first draft. Tell me what is missing.", "Could you send me the form again? I cannot find it.",
          "I am ordering at noon. Send me what you want before then.", "From the first of the month please use the new address."]


def default(rng):
    names = pools.people(rng, 30)
    me = names.pop()
    topics = rng.sample(pools.MAIL_TOPICS, len(pools.MAIL_TOPICS))
    when = (["9:41 AM", "9:12 AM", "8:30 AM", "7:55 AM", "Yesterday", "Yesterday", "Yesterday", "Thursday", "Thursday", "Wednesday", "Tuesday", "Monday"] +
            [f"{d} {m}" for m, days in (("Nov", [6, 5, 3, 2, 1]), ("Oct", [30, 28, 27, 24, 21, 19, 15, 12, 9, 6, 2])) for d in days])
    messages = []

    def add(box, who, topic, i, **kw):
        m = {"id": f"m{len(messages) + 1}", "box": box, "from": who, "email": pools.email_of(who, rng), "to": me, "subject": topic[0], "body": topic[1],
             "date": when[min(i, len(when) - 1)], "ts": 1000 - i * 10 - len(messages), "unread": False, "flagged": False}
        m.update(kw)
        messages.append(m)
        return m

    for i in range(22):
        add("inbox", names[i], topics[i], i, unread=(i < 6 and rng.random() < 0.6) or rng.random() < 0.1, flagged=rng.random() < 0.12)
    for i in range(2):
        add("archive", names[22 + i], topics[22 + i], 14 + i * 3)
    add("junk", names[24], topics[24], 6)
    add("trash", names[25], topics[25], 9)
    for i in range(3):
        who = names[rng.randrange(22)]
        m = add("sent", me, (rng.choice(SUBJECTS), rng.choice(BODIES)), 3 + i * 4)
        m["to"] = who
    return {"boxes": BOXES, "messages": messages, "me": {"name": me, "email": pools.email_of(me, rng)}, "next": 1,
            "ui": {"box": "inbox", "sel": None, "search": "", "compose": None}}


def inbox(s):
    return sorted([m for m in s["messages"] if m["box"] == "inbox"], key=lambda m: -m["ts"])


def row(m):
    return WIN + f'.m-row[data-arg="{m["id"]}"]'


def message(st, i):
    return by_id(st["apps"]["mail"]["messages"], i)


def sent_new(st, init):
    old = {m["id"] for m in init["apps"]["mail"]["messages"]}
    return [m for m in st["apps"]["mail"]["messages"] if m["id"] not in old and m["box"] == "sent"]


def pick_row(S, m):
    return Click(row(m), f"Click the email from {m['from']} in the message list")


@task("mail.archive", "chain")
def archive(S):
    m = S.rng.choice(inbox(S.apps["mail"])[:6])
    S.open("mail")
    return Spec(request=say(S.rng, f"Archive the email from {m['from']}.", f"Move {m['from']}'s email about “{m['subject']}” to the Archive."),
                steps=[pick_row(S, m), Click(WIN + '.toolbar [data-act="archive"]', "Click the Archive button (the box icon) in the Mail toolbar")],
                check=lambda st, init: verdict(cond(message(st, m["id"])["box"] == "archive", "the email is not in Archive"),
                                               only(st, init, f"mail.messages.{m['id']}.box")))


@task("mail.flag", "chain")
def flag(S):
    s = S.apps["mail"]
    m = S.rng.choice([x for x in inbox(s)[:6]])
    m["flagged"] = False
    S.open("mail")
    return Spec(request=say(S.rng, f"Flag the email from {m['from']}.", f"Put a flag on the “{m['subject']}” email."),
                steps=[pick_row(S, m), Click(WIN + '.toolbar [data-act="flag"]', "Click the Flag button in the Mail toolbar")],
                check=lambda st, init: verdict(cond(message(st, m["id"])["flagged"] is True, "the email is not flagged"),
                                               only(st, init, f"mail.messages.{m['id']}.flagged")))


@task("mail.delete_old", "scroll")
def delete_old(S):
    m = S.rng.choice(inbox(S.apps["mail"])[12:])
    S.open("mail")
    return Spec(request=say(S.rng, f"Delete the email from {m['from']}.", f"Move the email with the subject “{m['subject']}” to the Trash."),
                steps=[Reveal(row(m)), pick_row(S, m), Click(WIN + '.toolbar [data-act="trash"]', "Click the Trash button in the Mail toolbar")],
                check=lambda st, init: verdict(cond(message(st, m["id"])["box"] == "trash", "the email is not in the Trash"),
                                               only(st, init, f"mail.messages.{m['id']}.box")))


@task("mail.reply", "typing")
def reply(S):
    m = S.rng.choice(inbox(S.apps["mail"])[:6])
    text = S.rng.choice(REPLIES)
    S.open("mail")

    def check(st, init):
        new = sent_new(st, init)
        return verdict(cond(len(new) == 1, "no reply was sent" if not new else "more than one email was sent"),
                       cond(new and norm(new[0]["to"]) == norm(m["email"]), "the reply did not go to the sender"),
                       cond(new and norm(new[0]["body"]) == norm(text), "the text of the reply is different"),
                       cond(new and new[0]["subject"].lower().startswith("re:"), "it is not a reply"),
                       only(st, init, "mail.messages.+*", "mail.next"))
    return Spec(request=say(S.rng, f"Reply to {m['from']}'s email with: {text}", f"Answer the email from {m['from']}. Write “{text}” and send it."),
                steps=[pick_row(S, m), Click(WIN + '.toolbar [data-act="reply"]', "Click the Reply button (the arrow pointing left) in the Mail toolbar"),
                       Type(text), Click(WIN + '.m-compose [data-act="send"]', "Click the Send button of the new message")],
                check=check)


@task("mail.compose", "typing")
def compose(S):
    s = S.apps["mail"]
    who = pools.person(S.rng)
    addr = pools.email_of(who, S.rng)
    subject, body = S.rng.choice(SUBJECTS), S.rng.choice(BODIES)
    S.open("mail")

    def check(st, init):
        new = sent_new(st, init)
        return verdict(cond(len(new) == 1, "no email was sent" if not new else "more than one email was sent"),
                       cond(new and norm(new[0]["to"]) == norm(addr), f"it went to “{new[0]['to'] if new else ''}”"),
                       cond(new and norm(new[0]["subject"]) == norm(subject), "the subject is different"),
                       cond(new and norm(new[0]["body"]) == norm(body), "the text is different"),
                       only(st, init, "mail.messages.+*", "mail.next"))
    return Spec(request=say(S.rng, f"Send an email to {addr} with the subject “{subject}” and the text “{body}”",
                            f"Write a new email to {addr}. Subject: {subject}. Message: {body} Then send it."),
                steps=[Click(WIN + '.toolbar [data-act="compose"]', "Click the New Message button (the square with a pencil) in the Mail toolbar"),
                       Type(addr),
                       Click(WIN + '.m-compose [data-focus="subject"]', "Click the Subject field of the new message"), Type(subject),
                       Click(WIN + ".m-compose textarea", "Click the empty text area of the new message, below the From line"), Type(body),
                       Click(WIN + '.m-compose [data-act="send"]', "Click the Send button of the new message")],
                check=check)


@task("mail.forward", "chain")
def forward(S):
    m = S.rng.choice(inbox(S.apps["mail"])[:6])
    addr = pools.email_of(pools.person(S.rng), S.rng)
    S.open("mail")

    def check(st, init):
        new = sent_new(st, init)
        return verdict(cond(len(new) == 1, "nothing was sent" if not new else "more than one email was sent"),
                       cond(new and norm(new[0]["to"]) == norm(addr), f"it went to “{new[0]['to'] if new else ''}”"),
                       cond(new and m["body"][:40] in new[0]["body"] and m["subject"] in new[0]["subject"], "the forwarded email is not in it"),
                       only(st, init, "mail.messages.+*", "mail.next"))
    return Spec(request=say(S.rng, f"Forward the email from {m['from']} to {addr}.", f"Send {m['from']}'s email on to {addr}."),
                steps=[pick_row(S, m), Click(WIN + '.toolbar [data-act="forward"]', "Click the Forward button (the arrow pointing right) in the Mail toolbar"),
                       Type(addr), Click(WIN + '.m-compose [data-act="send"]', "Click the Send button of the new message")],
                check=check)


@task("mail.mark_unread", "menu")
def mark_unread(S):
    m = S.rng.choice(inbox(S.apps["mail"])[:6])
    m["unread"] = False
    S.open("mail")
    return Spec(request=say(S.rng, f"Mark the email from {m['from']} as unread.", f"Make {m['from']}'s email show as unread again."),
                steps=[Click(row(m), f"Right-click the email from {m['from']} in the message list", button="right"),
                       Click('.menu-item:has-text("Mark as Unread")', "Click “Mark as Unread” in the menu")],
                check=lambda st, init: verdict(cond(message(st, m["id"])["unread"] is True, "the email is not marked as unread"),
                                               only(st, init, "mail.messages.*.unread", volatile=())))


@task("mail.open_sent", "single")
def open_sent(S):
    box = S.rng.choice([b for b in BOXES if b["id"] in ("sent", "archive", "junk", "trash")])
    S.open("mail")
    words = {"sent": "the emails I have sent", "archive": "my archived emails", "junk": "the junk mail", "trash": "the deleted emails"}[box["id"]]
    return Spec(request=say(S.rng, f"Show me {words}.", f"Open the {box['name']} mailbox."),
                steps=[Click(WIN + f'.sb-item[data-arg="{box["id"]}"]', f"Click “{box['name']}” in the Mail sidebar")],
                check=lambda st, init: verdict(cond(st["apps"]["mail"]["ui"]["box"] == box["id"], f"the {box['name']} mailbox is not showing"),
                                               unchanged(st, init)))


@task("mail.move_by_drag", "drag")
def move_by_drag(S):
    m = S.rng.choice(inbox(S.apps["mail"])[:6])
    box = S.rng.choice([b for b in BOXES if b["id"] in ("junk", "archive")])
    S.open("mail")
    return Spec(request=say(S.rng, f"Move the email from {m['from']} to the {box['name']} mailbox.", f"Put {m['from']}'s email in {box['name']}."),
                steps=[Drag(row(m), WIN + f'.sb-item[data-arg="{box["id"]}"]', f"the email from {m['from']} in the message list", f"“{box['name']}” in the Mail sidebar")],
                check=lambda st, init: verdict(cond(message(st, m["id"])["box"] == box["id"], f"the email is not in {box['name']}"),
                                               only(st, init, f"mail.messages.{m['id']}.box")))


@task("mail.already_flagged", "already_done")
def already_flagged(S):
    s = S.apps["mail"]
    m = S.rng.choice(inbox(s)[:5])
    m["flagged"] = True
    S.open("mail")
    return Spec(request=say(S.rng, f"Flag the email from {m['from']}.", f"Make sure the email from {m['from']} has a flag on it."),
                steps=[], kind="already_done", check=unchanged)


@task("mail.no_such_sender", "infeasible")
def no_such_sender(S):
    s = S.apps["mail"]
    used = {w for m in s["messages"] for w in (m["from"] + " " + m["to"]).split()}
    ghost = S.rng.choice([f for f in pools.FIRST if f not in used]) + " " + S.rng.choice([l for l in pools.LAST if l not in used])
    S.open("mail")
    return Spec(request=say(S.rng, f"Archive the email from {ghost}.", f"Reply to {ghost}'s email and say I will call tomorrow."),
                steps=[], kind="infeasible", check=unchanged)
