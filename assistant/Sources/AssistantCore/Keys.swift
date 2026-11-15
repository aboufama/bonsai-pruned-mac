import Foundation

/// Key names as the model writes them (docs/ACTION_FORMAT.md) and the Mac's virtual key codes.
/// "backspace" is the Mac's delete key, "delete" is forward delete.
public enum Keys {
    public struct Combo: Equatable {
        public var keyCode: UInt16
        public var command = false, control = false, option = false, shift = false, function = false

        public init(keyCode: UInt16) { self.keyCode = keyCode }
    }

    static let modifiers: [String: String] = [
        "cmd": "cmd", "command": "cmd", "meta": "cmd", "super": "cmd", "win": "cmd", "⌘": "cmd",
        "ctrl": "ctrl", "control": "ctrl", "⌃": "ctrl",
        "alt": "alt", "option": "alt", "opt": "alt", "⌥": "alt",
        "shift": "shift", "⇧": "shift", "fn": "fn",
    ]

    static let codes: [String: UInt16] = {
        let t: [String: UInt16] = [
            "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12,
            "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23,
            "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34,
            "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46,
            ".": 47, "`": 50,
            "enter": 36, "return": 36, "tab": 48, "space": 49, "backspace": 51, "esc": 53, "escape": 53,
            "delete": 117, "del": 117, "forwarddelete": 117,
            "left": 123, "right": 124, "down": 125, "up": 126,
            "arrowleft": 123, "arrowright": 124, "arrowdown": 125, "arrowup": 126,
            "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
            "plus": 24, "equal": 24, "equals": 24, "minus": 27, "comma": 43, "period": 47, "slash": 44,
            "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100, "f9": 101,
            "f10": 109, "f11": 103, "f12": 111,
        ]
        return t
    }()

    /// The key names of a model answer, which may be a list (["cmd", "s"]) or one string
    /// ("cmd+s", "cmd s", "cmd, s").
    public static func names(from value: Any?) -> [String] {
        if let list = value as? [Any] {
            return list.map { "\($0)".trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
        }
        guard let s = value as? String else { return [] }
        let t = s.trimmingCharacters(in: .whitespacesAndNewlines)
        if t.count <= 1 { return t.isEmpty ? [] : [t] }
        if let d = t.data(using: .utf8), let list = try? JSONSerialization.jsonObject(with: d) as? [Any] {
            return names(from: list)
        }
        var parts = t.split(whereSeparator: { $0 == "+" || $0 == " " || $0 == "," }).map(String.init)
        if t.hasSuffix("++") || t == "+" { parts.append("+") }          // "cmd++" means cmd and the plus key
        return parts
    }

    /// One key with its modifiers, or nil when a name is unknown or there is not exactly one key
    /// besides the modifiers.
    public static func combo(_ names: [String]) -> Combo? {
        var combo = Combo(keyCode: 0)
        var key: UInt16?
        for raw in names {
            let n = raw.lowercased()
            if let m = modifiers[n] {
                switch m {
                case "cmd": combo.command = true
                case "ctrl": combo.control = true
                case "alt": combo.option = true
                case "shift": combo.shift = true
                default: combo.function = true
                }
                continue
            }
            let name = n == "+" ? "plus" : n
            guard let code = codes[name], key == nil else { return nil }
            if n == "+" || n == "plus" { combo.shift = true }
            key = code
        }
        guard let key else { return nil }
        combo.keyCode = key
        return combo
    }
}
