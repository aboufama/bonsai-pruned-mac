import Foundation

/// Matching the words of a request against the names the Mac gives its controls (their
/// accessibility titles), so that "the Today button" finds the button titled "Today".
public enum Labels {
    static let filler: Set<String> = ["the", "a", "an", "button", "icon", "tab", "field", "box", "menu", "item", "link", "option",
                                      "control", "on", "in", "of", "to", "at", "for", "my", "this", "that", "please", "click", "press",
                                      "tap", "open", "select", "choose", "labeled", "labelled", "called", "named", "says", "which", "one"]

    /// The words that carry meaning, lower-cased.
    public static func words(_ text: String) -> [String] {
        text.lowercased().split(whereSeparator: { !$0.isLetter && !$0.isNumber }).map(String.init).filter { !filler.contains($0) }
    }

    /// The phrase as it is compared whole: lower-cased, filler dropped, single spaces.
    public static func phrase(_ text: String) -> String { words(text).joined(separator: " ") }

    /// How well a control's name fits what was asked for: 0 when it does not fit, up to 1 when
    /// they say the same thing. A name fits when all its words are among the target's words, or
    /// all the target's words are among the name's.
    public static func fit(target: String, name: String) -> Double {
        let t = Set(words(target)), n = Set(words(name))
        guard !t.isEmpty, !n.isEmpty else { return 0 }
        guard n.isSubset(of: t) || t.isSubset(of: n) else { return 0 }
        return Double(t.intersection(n).count) / Double(t.union(n).count)
    }
}
