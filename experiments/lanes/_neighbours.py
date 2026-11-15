# Neighbour cases three times as often, and Apple's own apps twice as often again (15 Nov
# 04:25, after the tuned 9B clicked the arrow beside Calendar's "Today" button). A neighbour case has
# another labelled box close beside it in the same row (tools/neighbour_cases.py writes their ids to
# data/mac/neighbour_ids.json). For every pack that holds such cases, two more packs with only those
# cases are added (three more again for the cases whose source names one of Apple's apps).
# Defines emphasise(packs) -> packs; exec this file, then call it before shuffling.
import json as _json

_NB = set(_json.load(open(f"{lab.root}/data/mac/neighbour_ids.json"))["ids"])
_APPLE = ("calendar", "ical", "finder", "mail", "notes", "reminders", "safari", "system_preferences", "systempreferences",
          "system settings", "system_settings", "systemsettings", "messages", "mobilesms")


def emphasise(packs):
    out, n_all, n_hot, n_apple = [], 0, 0, 0
    for pack in packs:
        hot = [it for it in pack if it["id"] in _NB]
        apple = [it for it in hot if any(k in str(it.get("group", "")).lower() for k in _APPLE)]
        n_all += len(pack); n_hot += len(hot); n_apple += len(apple)
        out.append(pack)
        if hot:
            out += [hot, hot]
        if apple:
            out += [apple, apple, apple]
    print("emphasis: %d of %d cases are neighbour cases (%.0f%%), %d of them in Apple's apps; packs %d -> %d" % (
        n_hot, n_all, 100 * n_hot / max(n_all, 1), n_apple, len(packs), len(out)), flush=True)
    return out
