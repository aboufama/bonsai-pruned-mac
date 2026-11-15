# Small targets and buttons three times as often (15 Nov 03:00, after the question whether
# common UI elements are trained on deliberately). A case counts when its target's smaller side is under
# EMPH_PX (24) px with the screenshot's long side at 1280 (32 as first ordered marked 86% of the mix), or when its source labels it a button, image or toolbar
# item (the accessibility role, or the words "button" / "icon" in a GroundCUA instruction). For every pack
# that holds such cases, two more packs with only those cases are added, so they are drawn three times
# as often as the rest. Defines emphasise(packs) -> packs; exec this file, then call it before shuffling.
_ROLES = ("AXButton", "AXImage", "AXToolbar", "AXMenuButton", "AXPopUpButton", "AXCheckBox", "AXRadioButton")


def _emph(it):
    b, (w, h) = it["bbox"], it.get("size") or (0, 0)
    small = w and min(b[2] - b[0], b[3] - b[1]) * 1280 / max(w, h) < globals().get("EMPH_PX", 24)
    role = it.get("role") in _ROLES and globals().get("EMPH_ROLES", False)
    words = "groundcua" in str(it.get("id")) and any(k in it["instruction"].lower() for k in ("button", "icon"))
    return bool(small or role or words)


def emphasise(packs):
    out, n_all, n_hot = [], 0, 0
    for pack in packs:
        hot = [it for it in pack if _emph(it)]
        n_all += len(pack); n_hot += len(hot)
        out.append(pack)
        if hot:
            out += [hot, hot]
    print("emphasis: %d of %d cases are small targets or buttons (%.0f%%); packs %d -> %d" % (
        n_hot, n_all, 100 * n_hot / max(n_all, 1), len(packs), len(out)), flush=True)
    return out
