import Foundation

/// Finding the thing a request means among the controls the Mac itself can name, before any
/// screenshot is read. The Mac knows the name and the place of most buttons, fields, menu
/// items and Dock icons (Accessibility); when the words of a request are such a name, the
/// place is known at once.
public enum NameSearch {
    /// Words that say what kind of thing is meant, or where, or ask for it: not part of a name.
    static let filler: Set<String> = [
        "the", "a", "an", "this", "that", "my", "your", "please", "where", "wheres", "is", "are", "show", "me", "find", "locate", "point", "at", "to", "out",
        "click", "press", "tap", "hit", "select", "choose", "open", "go", "on", "in", "of", "for", "and", "or", "button", "icon", "field", "box", "menu", "tab",
        "link", "key", "control", "item", "option", "toolbar", "window", "sidebar", "bar", "one", "which", "it", "how", "do", "i", "can", "you", "highlight",
        "what", "whats", "s", "there", "here", "up", "top", "bottom", "left", "right", "corner", "side", "near", "next", "beside", "between", "under", "above",
        "below", "called", "named", "labelled", "labeled", "says", "with", "text", "label", "app", "dock"]

    /// A word as it is compared: lower case, and without a final s ("sends" and "Send" meet).
    static func plain(_ word: Substring) -> String {
        let w = word.lowercased()
        return w.count > 3 && w.hasSuffix("s") ? String(w.dropLast()) : w
    }

    static func allWords(_ text: String) -> [String] {
        text.replacingOccurrences(of: "’", with: "").replacingOccurrences(of: "'", with: "").split(whereSeparator: { !$0.isLetter && !$0.isNumber }).map(plain)
    }

    /// The words of a request that could be a name.
    public static func words(_ text: String) -> [String] { allWords(text).filter { !filler.contains($0) } }

    /// What a pointing request is after, without the asking: "where is the share button?" is "the share button".
    public static func target(of request: String) -> String {
        var t = request.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: "?.!")))
        if let m = Commands.match(#"^(?:where(?:'s|\s+is|\s+are)?|show\s+me(?:\s+where)?|point\s+(?:at|to|out)|find|locate|highlight|which\s+(?:one\s+)?is|how\s+do\s+i\s+(?:find|get\s+to|open))\s+(.+)$"#, t) { t = m[1] }
        return t
    }

    public enum Found: Equatable {
        case one(Int)                // the one control meant: its place in the list
        case several([Int])          // more than one could be meant: someone has to choose
        case none                    // no name fits: the screen has to be looked at
    }

    /// Which of the named controls a target means. One control whose name is exactly the
    /// target's words; failing that, one whose name holds them all. Several of either kind,
    /// or only names that share a word with the target, are candidates to choose among.
    public static func search(_ target: String, in names: [String]) -> Found {
        let wanted = words(target)
        guard !wanted.isEmpty else { return .none }
        var exact: [Int] = [], holds: [Int] = [], shares: [Int] = []
        for (i, name) in names.enumerated() where !name.isEmpty {
            let all = allWords(name)
            if all == wanted || all.filter({ !filler.contains($0) }) == wanted {
                exact.append(i)
            } else if Set(wanted).isSubset(of: Set(all)) {
                holds.append(i)
            } else if !Set(wanted).isDisjoint(with: Set(all)) {
                shares.append(i)
            }
        }
        if exact.count == 1 { return .one(exact[0]) }
        if exact.count > 1 { return .several(exact) }
        if holds.count == 1 { return .one(holds[0]) }
        if holds.count > 1 { return .several(holds) }
        return shares.isEmpty ? .none : .several(Array(shares.prefix(24)))
    }
}
