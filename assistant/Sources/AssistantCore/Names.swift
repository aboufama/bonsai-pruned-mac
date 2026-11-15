import Foundation

/// Which app a name means. People, and a planner, say "the Finder app", "Finder.app", "my
/// calendar app" or a name with a slip in it; macOS knows the app only by its exact name.
public enum AppNames {
    /// A name without the words around it, in lower case: "the Finder app" -> "finder".
    public static func bare(_ said: String) -> String {
        var t = said.lowercased().trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".\"'“”")))
        var changed = true
        while changed {
            changed = false
            for lead in ["the ", "my ", "a ", "an ", "apple's ", "apple "] where t.hasPrefix(lead) && t.count > lead.count {
                t = String(t.dropFirst(lead.count))
                changed = true
            }
            for tail in [" app", " application", " program", ".app", " window"] where t.hasSuffix(tail) && t.count > tail.count {
                t = String(t.dropLast(tail.count))
                changed = true
            }
            t = t.trimmingCharacters(in: .whitespaces)
        }
        return t
    }

    /// The number of single-character changes between two words.
    static func distance(_ a: String, _ b: String) -> Int {
        let x = Array(a), y = Array(b)
        if x.isEmpty { return y.count }
        if y.isEmpty { return x.count }
        var row = Array(0...y.count)
        for i in 1...x.count {
            var previous = row[0]
            row[0] = i
            for j in 1...y.count {
                let above = row[j]
                row[j] = min(row[j] + 1, row[j - 1] + 1, previous + (x[i - 1] == y[j - 1] ? 0 : 1))
                previous = above
            }
        }
        return row[y.count]
    }

    /// The app a name means, as macOS shows it: the exact name, a known other name for it, a
    /// name that starts with it, a name that has it as a word; then the same without "the" and
    /// "app" around it. `nearest`: failing all those, the name a slip or two away ("Remiders").
    public static func resolve(_ said: String, names: [String], aliases: [String: String] = [:], nearest: Bool = false) -> String? {
        let whole = said.lowercased().trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".\"'")))
        guard !whole.isEmpty else { return nil }
        let short = bare(said)
        for s in whole == short || short.isEmpty ? [whole] : [whole, short] {
            if let exact = names.first(where: { $0.lowercased() == s }) { return exact }
            if let known = aliases[s], names.contains(known) { return known }
        }
        for s in whole == short || short.isEmpty ? [whole] : [whole, short] {
            let starts = names.filter { $0.lowercased().hasPrefix(s) }.sorted { $0.count < $1.count }
            if let first = starts.first { return first }
            let within = names.filter { $0.lowercased().split(separator: " ").contains(Substring(s)) }.sorted { $0.count < $1.count }
            if let first = within.first { return first }
        }
        guard nearest, !short.isEmpty else { return nil }
        let allowed = short.count >= 8 ? 2 : short.count >= 5 ? 1 : 0
        guard allowed > 0 else { return nil }
        let close = names.map { ($0, distance($0.lowercased(), short)) }.filter { $0.1 <= allowed }
            .sorted { $0.1 != $1.1 ? $0.1 < $1.1 : $0.0.count < $1.0.count }
        return close.first?.0
    }

    /// Words of a task that mean an app without naming it.
    static let hints: [(pattern: String, app: String)] = [
        (#"\bremind(?:ers?)?\b"#, "Reminders"), (#"\bnotes?\b(?!\.\p{L})"#, "Notes"), (#"\bcontacts?\b"#, "Contacts"),
        (#"\b(?:calendar|event|meeting|appointment)\b"#, "Calendar"), (#"\be-?mails?\b"#, "Mail"),
        (#"\b(?:terminal|shell|command\s+line)\b"#, "Terminal"), (#"\bcalculat\w*\b"#, "Calculator"),
        (#"\bsystem\s+(?:settings|preferences)\b"#, "System Settings"), (#"\bsticky\s+notes?\b|\bstickies\b"#, "Stickies"),
    ]

    /// The apps a task speaks of: those it names (whole words, outside quotation marks), or,
    /// when it names none, those its words mean ("remind me" is Reminders, "a note" is Notes).
    public static func named(in task: String, among apps: [String]) -> [String] {
        let text = Commands.unquoted(task).lowercased()
        var found = apps.filter { name in
            let escaped = NSRegularExpression.escapedPattern(for: name.lowercased())
            return Commands.match("(?<![\\p{L}\\p{N}.])" + escaped + "(?![\\p{L}\\p{N}]|\\.\\p{L})", text) != nil      // not "notes.txt"
        }
        found = found.filter { name in !found.contains { $0 != name && $0.lowercased().contains(name.lowercased()) } }
        if !found.isEmpty { return found }
        var meant: [String] = []
        for hint in hints where apps.contains(hint.app) && !meant.contains(hint.app) && Commands.match(hint.pattern, text) != nil {
            meant.append(hint.app)
        }
        if meant.contains("Stickies") { meant.removeAll { $0 == "Notes" } }          // "a sticky note" is not the Notes app
        return meant
    }
}
