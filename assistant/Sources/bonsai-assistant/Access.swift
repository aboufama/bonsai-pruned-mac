// What the Mac itself knows about the controls on screen (the accessibility tree): used to put
// a click on the control the model pointed at rather than a few points beside it, and to find
// a control by its name without reading the screen at all. Needs the Accessibility permission
// the app already has for clicking. Nothing read here is stored anywhere but the app's own log.
import AppKit
import ApplicationServices
import AssistantCore

struct Control {
    let frame: CGRect                // screen points, origin top left (as clicks use)
    let role: String
    let name: String                 // its title, else its description, else its text
    var center: CGPoint { CGPoint(x: frame.midX, y: frame.midY) }
}

enum Access {
    static let pressable: Set<String> = ["AXButton", "AXMenuItem", "AXMenuBarItem", "AXMenuButton", "AXPopUpButton", "AXCheckBox",
                                         "AXRadioButton", "AXLink", "AXTextField", "AXTextArea", "AXSearchField", "AXComboBox",
                                         "AXTab", "AXDisclosureTriangle", "AXSlider", "AXIncrementor", "AXCell", "AXDockItem",
                                         "AXToolbarButton", "AXSegment"]

    private static func value(_ element: AXUIElement, _ attribute: String) -> AnyObject? {
        var out: AnyObject?
        return AXUIElementCopyAttributeValue(element, attribute as CFString, &out) == .success ? out : nil
    }

    private static func element(_ element: AXUIElement, _ attribute: String) -> AXUIElement? {
        guard let v = value(element, attribute), CFGetTypeID(v) == AXUIElementGetTypeID() else { return nil }
        return (v as! AXUIElement)
    }

    private static func children(_ element: AXUIElement) -> [AXUIElement] {
        (value(element, kAXChildrenAttribute) as? [AXUIElement]) ?? []
    }

    private static func frame(_ element: AXUIElement) -> CGRect? {
        guard let p = value(element, kAXPositionAttribute), let s = value(element, kAXSizeAttribute),
              CFGetTypeID(p) == AXValueGetTypeID(), CFGetTypeID(s) == AXValueGetTypeID() else { return nil }
        var origin = CGPoint.zero, size = CGSize.zero
        guard AXValueGetValue(p as! AXValue, .cgPoint, &origin), AXValueGetValue(s as! AXValue, .cgSize, &size),
              size.width > 0, size.height > 0 else { return nil }
        return CGRect(origin: origin, size: size)
    }

    private static func control(_ element: AXUIElement) -> Control? {
        guard let frame = frame(element) else { return nil }
        let role = (value(element, kAXRoleAttribute) as? String) ?? ""
        let texts = [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute, kAXHelpAttribute]
            .compactMap { value(element, $0) as? String }.filter { !$0.isEmpty }
        return Control(frame: frame, role: role, name: texts.first ?? "")
    }

    private static func distance(_ p: CGPoint, _ r: CGRect) -> CGFloat {
        hypot(max(r.minX - p.x, 0, p.x - r.maxX), max(r.minY - p.y, 0, p.y - r.maxY))
    }

    /// Where to click, given the model's point: the control near the point whose name fits the
    /// words asked for; else the pressable control under the point; else the point itself.
    /// Returns the place and a few words for the log on which of the three it was.
    static func snap(_ point: CGPoint, target: String) -> (CGPoint, String) {
        let system = AXUIElementCreateSystemWide()
        AXUIElementSetMessagingTimeout(system, 0.35)
        var hit: AXUIElement?
        guard AXUIElementCopyElementAtPosition(system, Float(point.x), Float(point.y), &hit) == .success, let under = hit else {
            return (point, "the model's point (no control found under it)")
        }
        // the control under the point, what it sits in, and its neighbours
        var around: [AXUIElement] = [under]
        var up: AXUIElement? = under
        for _ in 0..<3 {
            guard let parent = up.flatMap({ element($0, kAXParentAttribute) }) else { break }
            around.append(parent)
            around.append(contentsOf: children(parent).prefix(80))
            up = parent
        }
        let near = around.compactMap(control).filter { distance(point, $0.frame) <= 60 && $0.frame.width <= 600 && $0.frame.height <= 220 }
        let named = near.map { ($0, Labels.fit(target: target, name: $0.name)) }.filter { $0.1 > 0 }
            .sorted { $0.1 != $1.1 ? $0.1 > $1.1 : distance(point, $0.0.frame) < distance(point, $1.0.frame) }
        if let best = named.first?.0 {
            return (best.center, "the control named \"\(best.name)\" (\(best.role)) beside the model's point")
        }
        let held = near.filter { pressable.contains($0.role) && $0.frame.contains(point) && $0.frame.width <= 320 && $0.frame.height <= 120 }
            .min { $0.frame.width * $0.frame.height < $1.frame.width * $1.frame.height }
        if let held {
            return (held.center, "the centre of the \(held.role) under the model's point" + (held.name.isEmpty ? "" : " (\"\(held.name)\")"))
        }
        return (point, "the model's point (no matching or pressable control near it)")
    }

    /// The one pressable control in the front window (or the front app's menu bar) whose name
    /// is exactly the phrase asked for; nil when there is none or more than one.
    static func find(named target: String) -> Control? {
        let wanted = Labels.phrase(target)
        guard !wanted.isEmpty, let app = NSWorkspace.shared.frontmostApplication else { return nil }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.35)
        var queue: [AXUIElement] = []
        if let window = element(root, kAXFocusedWindowAttribute) ?? element(root, kAXMainWindowAttribute) { queue.append(window) }
        if let bar = element(root, kAXMenuBarAttribute) { queue.append(contentsOf: children(bar)) }
        let deadline = Date().addingTimeInterval(0.6)
        var seen = 0
        var matches: [Control] = []
        while !queue.isEmpty, seen < 3000, Date() < deadline, matches.count < 2 {
            let next = queue.removeFirst()
            seen += 1
            if let c = control(next), pressable.contains(c.role), Labels.phrase(c.name) == wanted {
                if !matches.contains(where: { $0.frame == c.frame }) { matches.append(c) }
            }
            queue.append(contentsOf: children(next).prefix(200))
        }
        guard matches.count == 1, let only = matches.first,
              let screen = NSScreen.screens.first?.frame, CGRect(origin: .zero, size: screen.size).contains(only.center) else { return nil }
        return only
    }

    // MARK: the front window as a list, and its menus, for planning from text

    struct ScreenList {
        let app: String
        let window: String
        let controls: [ListedControl]
        /// What the list itself leaves out, for telling whether a step changed anything: how
        /// long each field's text really is and how it ends (the list shows 40 characters),
        /// and which element has the keyboard. Never shown to the model, never logged.
        var detail = ""
    }

    /// The length and the end of a text, as a mark of whether it changed.
    private static func mark(_ text: String) -> String { "\(text.count):\(text.suffix(24))" }

    private static let words: [String: String] = [
        "AXButton": "button", "AXToolbarButton": "button", "AXSegment": "button", "AXMenuButton": "popup", "AXPopUpButton": "popup",
        "AXCheckBox": "checkbox", "AXRadioButton": "radio", "AXTextField": "text field", "AXSearchField": "text field",
        "AXComboBox": "text field", "AXTextArea": "text area", "AXLink": "link", "AXTab": "tab", "AXMenuItem": "menu item",
        "AXDisclosureTriangle": "arrow", "AXSlider": "slider", "AXIncrementor": "stepper", "AXCell": "cell"]

    private static func short(_ text: String, _ limit: Int) -> String {
        let one = text.split(whereSeparator: { $0.isNewline }).joined(separator: " ").trimmingCharacters(in: .whitespaces)
        return one.count <= limit ? one : String(one.prefix(limit - 1)) + "…"
    }

    /// The controls of the front window that can be pressed or typed into: the items of an
    /// open menu first, then the named ones in reading order, then unnamed fields; eighty at
    /// most, numbered from 1.
    static func screenList() -> ScreenList {
        let deep = deepList()
        var list = deep
        if deep.controls.count < 3 {
            let before = plainList()
            if before.controls.count > deep.controls.count { list = before }
        }
        if let focus = focus() { list.detail += "\u{3}" + focus.role + "|" + focus.place + "|" + mark(focus.value) }
        return list
    }

    /// The list as it was made before the deeper reading: one attribute at a time, no borrowed
    /// names. Kept as a fallback for a window where the deeper reading finds almost nothing.
    private static func plainList() -> ScreenList {
        guard let app = NSWorkspace.shared.frontmostApplication else { return ScreenList(app: "", window: "", controls: []) }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.4)
        let window = element(root, kAXFocusedWindowAttribute) ?? element(root, kAXMainWindowAttribute)
        let title = window.flatMap { value($0, kAXTitleAttribute) as? String } ?? ""
        let screen = CGRect(origin: .zero, size: NSScreen.screens.first?.frame.size ?? .zero)
        typealias Found = (role: String, name: String, value: String, frame: CGRect)
        var named: [Found] = [], unnamed: [Found] = [], menuItems: [Found] = []
        var marks: [String] = []
        let deadline = Date().addingTimeInterval(0.9)

        func note(_ e: AXUIElement) -> Bool {                        // false: do not look inside it
            guard let role = value(e, kAXRoleAttribute) as? String, let word = words[role] else { return true }
            guard let f = frame(e), f.width >= 5, f.height >= 5, screen.intersects(f) else { return true }
            if (value(e, kAXEnabledAttribute) as? Bool) == false { return true }
            let raw = value(e, kAXValueAttribute)
            var name = (value(e, kAXTitleAttribute) as? String) ?? ""
            if name.isEmpty { name = (value(e, kAXDescriptionAttribute) as? String) ?? "" }
            if name.isEmpty { name = (value(e, kAXPlaceholderValueAttribute) as? String) ?? (value(e, kAXHelpAttribute) as? String) ?? "" }
            let editable = word == "text field" || word == "text area"
            var state = ""
            if word == "checkbox" || word == "radio" || word == "tab" {
                state = ((raw as? NSNumber)?.intValue ?? 0) != 0 ? "selected" : ""
            } else if editable || word == "popup" {
                state = short((raw as? String) ?? "", 40)
                if editable { marks.append(mark((raw as? String) ?? "")) }
            }
            if name.isEmpty && !editable { return true }             // an unnamed button says nothing in a list
            let found: Found = (word, short(name, 48), state, f)
            if role == "AXMenuItem" { menuItems.append(found) } else if name.isEmpty { unnamed.append(found) } else { named.append(found) }
            return !editable
        }

        var queue: [AXUIElement] = window.map { [$0] } ?? []
        var seen = 0
        while !queue.isEmpty, seen < 4000, Date() < deadline {
            let next = queue.removeFirst()
            seen += 1
            if note(next) { queue.append(contentsOf: children(next).prefix(250)) }
        }
        if let bar = element(root, kAXMenuBarAttribute) {            // an open menu: its items can be pressed
            for item in children(bar).prefix(14) where (value(item, kAXSelectedAttribute) as? Bool) == true {
                for menu in children(item) {
                    for entry in children(menu).prefix(40) { _ = note(entry) }
                }
            }
        }

        func inOrder(_ list: [Found]) -> [Found] {
            list.sorted { abs($0.frame.minY - $1.frame.minY) > 8 ? $0.frame.minY < $1.frame.minY : $0.frame.minX < $1.frame.minX }
        }
        func unique(_ list: [Found]) -> [Found] {
            var out: [Found] = []
            for f in list where !out.contains(where: { $0.role == f.role && $0.name == f.name && $0.frame == f.frame }) { out.append(f) }
            return out
        }
        let chosen = Array((unique(menuItems) + inOrder(unique(named)) + inOrder(unique(unnamed))).prefix(Planner.maxControls))
        let controls = chosen.enumerated().map { ListedControl(id: $0.offset + 1, role: $0.element.role, name: $0.element.name,
                                                               value: $0.element.value, frame: $0.element.frame) }
        return ScreenList(app: app.localizedName ?? "", window: title, controls: controls, detail: marks.joined(separator: "\u{2}"))
    }

    /// The deeper reading: every element in one round trip, controls without a name of their
    /// own named by the label beside them or the text inside them.
    private static func deepList() -> ScreenList {
        guard let app = NSWorkspace.shared.frontmostApplication else { return ScreenList(app: "", window: "", controls: []) }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.4)
        let window = element(root, kAXFocusedWindowAttribute) ?? element(root, kAXMainWindowAttribute)
        let title = window.flatMap { value($0, kAXTitleAttribute) as? String } ?? ""
        let screen = CGRect(origin: .zero, size: NSScreen.screens.first?.frame.size ?? .zero)
        typealias Found = (role: String, name: String, value: String, frame: CGRect)
        var named: [Found] = [], unnamed: [Found] = [], menuItems: [Found] = []
        var marks: [String] = []
        let deadline = Date().addingTimeInterval(1.4)

        /// What is read of every element, in one round trip each.
        struct Seen {
            let element: AXUIElement
            let role: String
            let frame: CGRect?
            let enabled: Bool
            let title: String, described: String, placeholder: String, help: String
            let raw: AnyObject?
            var text: String { role == "AXStaticText" ? ((raw as? String) ?? title) : "" }
        }
        func see(_ e: AXUIElement) -> Seen {
            let v = values(e, [kAXRoleAttribute, kAXPositionAttribute, kAXSizeAttribute, kAXEnabledAttribute, kAXTitleAttribute,
                               kAXDescriptionAttribute, kAXValueAttribute, kAXPlaceholderValueAttribute, kAXHelpAttribute])
            var frame: CGRect?
            if let p = v[1], let s = v[2], CFGetTypeID(p) == AXValueGetTypeID(), CFGetTypeID(s) == AXValueGetTypeID() {
                var origin = CGPoint.zero, size = CGSize.zero
                if AXValueGetValue(p as! AXValue, .cgPoint, &origin), AXValueGetValue(s as! AXValue, .cgSize, &size), size.width > 0, size.height > 0 {
                    frame = CGRect(origin: origin, size: size)
                }
            }
            return Seen(element: e, role: (v[0] as? String) ?? "", frame: frame, enabled: (v[3] as? Bool) ?? true, title: (v[4] as? String) ?? "",
                        described: (v[5] as? String) ?? "", placeholder: (v[7] as? String) ?? "", help: (v[8] as? String) ?? "", raw: v[6])
        }

        /// A name for a control that has none of its own, from the text inside it (a row of a
        /// sidebar is a cell around a text): the first text within two levels.
        func textInside(_ e: AXUIElement) -> String {
            var level = children(e).prefix(8).map(see)
            for _ in 0..<2 {
                if let t = level.first(where: { !$0.text.isEmpty }) { return t.text }
                level = level.prefix(4).flatMap { children($0.element).prefix(6).map(see) }
            }
            return level.first(where: { !$0.text.isEmpty })?.text ?? ""
        }

        /// Lists one element. `label`: the text that stands beside it, for a control that has
        /// no name of its own (a switch, a pop-up or a slider in a row of settings).
        func note(_ s: Seen, label: String) {
            guard let word = words[s.role], let f = s.frame, f.width >= 5, f.height >= 5, screen.intersects(f), s.enabled else { return }
            var name = !s.title.isEmpty ? s.title : s.described
            if name.isEmpty { name = !s.placeholder.isEmpty ? s.placeholder : s.help }
            let editable = word == "text field" || word == "text area"
            if name.isEmpty, !editable, word == "cell" || word == "button" { name = textInside(s.element) }
            if name.isEmpty { name = label }
            var state = ""
            if word == "checkbox" || word == "radio" || word == "tab" {
                state = ((s.raw as? NSNumber)?.intValue ?? 0) != 0 ? "selected" : ""
            } else if editable || word == "popup" {
                state = short((s.raw as? String) ?? "", 40)
                if editable { marks.append(mark((s.raw as? String) ?? "")) }
            } else if word == "slider", let n = s.raw as? NSNumber {
                state = String(format: "%.2f", n.doubleValue)
            }
            if name.isEmpty && !editable { return }                  // an unnamed button says nothing in a list
            let found: Found = (word, short(name, 48), state, f)
            if s.role == "AXMenuItem" { menuItems.append(found) } else if name.isEmpty { unnamed.append(found) } else { named.append(found) }
        }

        // Breadth first, each element together with the label it inherits. The label of a
        // child no taller than a row is the text beside it (same height on the screen), else
        // the only text among its siblings when they are few (a row made of a text and a
        // control), else what its parent inherited.
        var queue: [(Seen, String)] = window.map { [(see($0), "")] } ?? []
        var seen = 0
        while !queue.isEmpty, seen < 5000, Date() < deadline {
            let (now, inherited) = queue.removeFirst()
            seen += 1
            note(now, label: inherited)
            let word = words[now.role]
            if word == "text field" || word == "text area" || now.role == "AXStaticText" || now.role == "AXImage" { continue }
            let kids = children(now.element).prefix(250).map(see)
            let texts = kids.filter { !$0.text.isEmpty && $0.frame != nil }
            let others = kids.count - texts.count
            for kid in kids where kid.text.isEmpty {
                var label = inherited
                if let f = kid.frame, f.height <= 64 {                 // a control or a row, not a whole pane
                    let beside = texts.filter { abs($0.frame!.midY - f.midY) <= max(12, f.height / 2) }
                        .min { abs($0.frame!.midX - f.midX) < abs($1.frame!.midX - f.midX) }
                    if let beside { label = beside.text } else if texts.count == 1, others <= 3 { label = texts[0].text }
                }
                queue.append((kid, label))
            }
        }
        if let bar = element(root, kAXMenuBarAttribute) {            // an open menu: its items can be pressed
            for item in children(bar).prefix(14) where (value(item, kAXSelectedAttribute) as? Bool) == true {
                for menu in children(item) {
                    for entry in children(menu).prefix(40) { note(see(entry), label: "") }
                }
            }
        }

        func inOrder(_ list: [Found]) -> [Found] {
            list.sorted { abs($0.frame.minY - $1.frame.minY) > 8 ? $0.frame.minY < $1.frame.minY : $0.frame.minX < $1.frame.minX }
        }
        func unique(_ list: [Found]) -> [Found] {
            var out: [Found] = []
            for f in list where !out.contains(where: { $0.role == f.role && $0.name == f.name && $0.frame == f.frame }) { out.append(f) }
            return out
        }
        let chosen = Array((unique(menuItems) + inOrder(unique(named)) + inOrder(unique(unnamed))).prefix(Planner.maxControls))
        let controls = chosen.enumerated().map { ListedControl(id: $0.offset + 1, role: $0.element.role, name: $0.element.name,
                                                               value: $0.element.value, frame: $0.element.frame) }
        return ScreenList(app: app.localizedName ?? "", window: title, controls: controls, detail: marks.joined(separator: "\u{2}"))
    }

    /// A check of the reading itself, in counts only: the front window's first few hundred
    /// elements, their roles read one attribute at a time and read in one round trip, and how
    /// many of them are of a kind that is listed.
    static func readingCheck() -> String {
        guard let app = NSWorkspace.shared.frontmostApplication else { return "no app in front" }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.4)
        guard let window = element(root, kAXFocusedWindowAttribute) ?? element(root, kAXMainWindowAttribute) else { return "the app in front has no window Accessibility can see" }
        var queue = [window], nodes = 0, same = 0, differ = 0, listable = 0, namedListable = 0, texts = 0
        let deadline = Date().addingTimeInterval(1.5)
        while !queue.isEmpty, nodes < 600, Date() < deadline {
            let next = queue.removeFirst()
            nodes += 1
            let single = (value(next, kAXRoleAttribute) as? String) ?? ""
            let batch = values(next, [kAXRoleAttribute, kAXTitleAttribute, kAXDescriptionAttribute])
            if single == ((batch[0] as? String) ?? "") { same += 1 } else { differ += 1 }
            if single == "AXStaticText" { texts += 1 }
            if words[single] != nil {
                listable += 1
                if !((batch[1] as? String) ?? "").isEmpty || !((batch[2] as? String) ?? "").isEmpty { namedListable += 1 }
            }
            queue.append(contentsOf: children(next).prefix(250))
        }
        return "\(nodes) elements read: role the same both ways for \(same), different for \(differ); \(listable) of a listed kind, \(namedListable) of those with a name of their own; \(texts) texts"
    }

    /// Several attributes of an element in one round trip (nil where it has none).
    private static func values(_ element: AXUIElement, _ attributes: [String]) -> [AnyObject?] {
        var out: CFArray?
        guard AXUIElementCopyMultipleAttributeValues(element, attributes as CFArray, AXCopyMultipleAttributeOptions(rawValue: 0), &out) == .success,
              let list = out as? [AnyObject], list.count == attributes.count else { return Array(repeating: nil, count: attributes.count) }
        return list.map { v -> AnyObject? in
            if v is NSNull { return nil }
            if CFGetTypeID(v) == AXValueGetTypeID(), AXValueGetType(v as! AXValue) == .axError { return nil }
            return v
        }
    }

    private static func plain(_ text: String) -> String {
        text.lowercased().replacingOccurrences(of: "…", with: "").replacingOccurrences(of: "...", with: "").trimmingCharacters(in: .whitespaces)
    }

    /// Chooses an item of the front app's menu bar by its path ("File > New Message"), through
    /// the names of the menus, with no screenshot. False when the path does not exist.
    static func menu(path: String) -> Bool {
        let parts = path.split(separator: ">").map { plain(String($0)) }.filter { !$0.isEmpty }
        guard !parts.isEmpty, let app = NSWorkspace.shared.frontmostApplication else { return false }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.6)
        guard var current = element(root, kAXMenuBarAttribute) else { return false }
        for (i, part) in parts.enumerated() {
            var items = children(current)
            if items.count == 1, (value(items[0], kAXRoleAttribute) as? String) == "AXMenu" { items = children(items[0]) }
            let titled = { (e: AXUIElement) in plain((value(e, kAXTitleAttribute) as? String) ?? "") }
            guard let next = items.first(where: { titled($0) == part }) ?? items.first(where: { !titled($0).isEmpty && titled($0).hasPrefix(part) })
            else { return false }
            if i == parts.count - 1 { return AXUIElementPerformAction(next, kAXPressAction as CFString) == .success }
            current = next
        }
        return false
    }
}

// MARK: what is selected, what the mouse is on, and where windows are

extension Access {
    /// What the mouse pointer is on, in a few words (the button "Send"), for questions about
    /// "this". `point`: screen points, origin top left.
    static func underMouse(_ point: CGPoint) -> String? {
        let system = AXUIElementCreateSystemWide()
        AXUIElementSetMessagingTimeout(system, 0.35)
        var hit: AXUIElement?
        guard AXUIElementCopyElementAtPosition(system, Float(point.x), Float(point.y), &hit) == .success else { return nil }
        var current = hit
        for _ in 0..<4 {
            guard let now = current else { break }
            let role = (value(now, kAXRoleAttribute) as? String) ?? ""
            let title = (value(now, kAXTitleAttribute) as? String) ?? ""
            let described = (value(now, kAXDescriptionAttribute) as? String) ?? ""
            let help = (value(now, kAXHelpAttribute) as? String) ?? ""
            var name = !title.isEmpty ? title : described
            if name.isEmpty, role == "AXStaticText" { name = (value(now, kAXValueAttribute) as? String) ?? "" }
            if let word = words[role], !name.isEmpty || !help.isEmpty {
                var text = "the \(word)" + (name.isEmpty ? "" : " \"\(short(name, 60))\"")
                if !help.isEmpty, help != name { text += " (its help text: \"\(short(help, 90))\")" }
                return text
            }
            current = element(now, kAXParentAttribute)
        }
        return nil
    }

    /// The element that has the keyboard in the front app.
    struct Focus {
        let role: String
        let line: Bool               // a field of one line (a text field, a search field, a combo box; not a password field)
        let inWeb: Bool              // it is part of a web page
        let value: String
        let place: String            // where it is, as a mark of which element it is
        var frame: CGRect? = nil     // and on the screen, for the pointer to go to
    }

    static func focus() -> Focus? {
        guard let app = NSWorkspace.shared.frontmostApplication, app.processIdentifier != ProcessInfo.processInfo.processIdentifier else { return nil }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.4)
        guard let focused = element(root, kAXFocusedUIElementAttribute) else { return nil }
        let role = (value(focused, kAXRoleAttribute) as? String) ?? ""
        let secure = (value(focused, kAXSubroleAttribute) as? String) == "AXSecureTextField"
        var inWeb = false
        var up = element(focused, kAXParentAttribute)
        for _ in 0..<14 {
            guard let now = up else { break }
            if (value(now, kAXRoleAttribute) as? String) == "AXWebArea" { inWeb = true; break }
            up = element(now, kAXParentAttribute)
        }
        let f = frame(focused)
        return Focus(role: role, line: ["AXTextField", "AXSearchField", "AXComboBox"].contains(role) && !secure, inWeb: inWeb,
                     value: secure ? "" : ((value(focused, kAXValueAttribute) as? String) ?? ""),
                     place: f.map { "\(Int($0.minX)),\(Int($0.minY))" } ?? "", frame: f)
    }

    /// The text selected in the front app, when the app itself says what it is; nil otherwise.
    static func selectedText() -> String? {
        guard let app = NSWorkspace.shared.frontmostApplication, app.processIdentifier != ProcessInfo.processInfo.processIdentifier else { return nil }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.4)
        guard let focused = element(root, kAXFocusedUIElementAttribute),
              let text = value(focused, kAXSelectedTextAttribute) as? String, !text.isEmpty else { return nil }
        return text
    }

    private static func window(pid: pid_t) -> AXUIElement? {
        let root = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(root, 0.6)
        return element(root, kAXFocusedWindowAttribute) ?? element(root, kAXMainWindowAttribute)
            ?? (value(root, kAXWindowsAttribute) as? [AXUIElement])?.first
    }

    /// The items of one of the front app's menus, read without opening it, as a list of
    /// controls. `name`: the menu's title in any case ("file"); "": the menu that is open
    /// now, or failing that the menus of the menu bar. Nil when there is no such menu.
    static func menuList(named name: String) -> (title: String, controls: [ListedControl])? {
        guard let app = NSWorkspace.shared.frontmostApplication else { return nil }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.6)
        guard let bar = element(root, kAXMenuBarAttribute) else { return nil }
        let menus = Array(children(bar).prefix(16))
        let titled = { (e: AXUIElement) in (value(e, kAXTitleAttribute) as? String) ?? "" }
        func items(of menu: AXUIElement) -> [String] {
            var inner = children(menu)
            if inner.count == 1, (value(inner[0], kAXRoleAttribute) as? String) == "AXMenu" { inner = children(inner[0]) }
            return inner.prefix(60).filter { (value($0, kAXEnabledAttribute) as? Bool) != false }.map(titled).filter { !$0.isEmpty }
        }
        var title = "", names: [String] = []
        let wanted = plain(name)
        if wanted.isEmpty {
            if let open = menus.first(where: { (value($0, kAXSelectedAttribute) as? Bool) == true }) {
                title = titled(open)
                names = items(of: open)
            } else {
                title = "menu bar"
                names = menus.map(titled).filter { !$0.isEmpty && $0 != "Apple" }
            }
        } else if let menu = menus.first(where: { plain(titled($0)) == wanted })
                    ?? menus.first(where: { !titled($0).isEmpty && plain(titled($0)).hasPrefix(wanted) }) {
            title = titled(menu)
            names = items(of: menu)
        } else {
            return nil
        }
        guard !names.isEmpty else { return nil }
        return (title, names.prefix(40).enumerated().map { ListedControl(id: $0.offset + 1, role: "menu item", name: short($0.element, 48)) })
    }

    /// Everything on screen the Mac can name and place, for finding a thing by its name with
    /// no screenshot: the front window's controls (an open menu's items first), the menus of
    /// the menu bar, and the icons of the Dock.
    static func everything() -> ScreenList {
        let front = screenList()
        var found: [(role: String, name: String, value: String, frame: CGRect)] = front.controls.map { ($0.role, $0.name, $0.value, $0.frame) }
        let screen = CGRect(origin: .zero, size: NSScreen.screens.first?.frame.size ?? .zero)
        if let app = NSWorkspace.shared.frontmostApplication {
            let root = AXUIElementCreateApplication(app.processIdentifier)
            AXUIElementSetMessagingTimeout(root, 0.4)
            if let bar = element(root, kAXMenuBarAttribute) {
                for item in children(bar).prefix(16) {
                    if let title = value(item, kAXTitleAttribute) as? String, !title.isEmpty, title != "Apple", let f = frame(item), screen.intersects(f) {
                        found.append(("menu item", title, "", f))
                    }
                }
            }
        }
        if let dock = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == "com.apple.dock" }) {
            let root = AXUIElementCreateApplication(dock.processIdentifier)
            AXUIElementSetMessagingTimeout(root, 0.4)
            for list in children(root).prefix(4) {
                for item in children(list).prefix(80) where (value(item, kAXRoleAttribute) as? String) == "AXDockItem" {
                    if let title = value(item, kAXTitleAttribute) as? String, !title.isEmpty, let f = frame(item), screen.intersects(f) {
                        found.append(("button", title, "", f))
                    }
                }
            }
        }
        let controls = found.enumerated().map { ListedControl(id: $0.offset + 1, role: $0.element.role, name: $0.element.name, value: $0.element.value, frame: $0.element.frame) }
        return ScreenList(app: front.app, window: front.window, controls: controls)
    }

    /// Where a menu's title is in the front app's menu bar.
    static func menuTitlePoint(_ menu: String) -> CGPoint? {
        guard let app = NSWorkspace.shared.frontmostApplication else { return nil }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.5)
        guard let bar = element(root, kAXMenuBarAttribute) else { return nil }
        let wanted = plain(menu)
        let titled = { (e: AXUIElement) in plain((value(e, kAXTitleAttribute) as? String) ?? "") }
        guard !wanted.isEmpty, let item = children(bar).first(where: { titled($0) == wanted }), let f = frame(item), f.minY < 60 else { return nil }
        return CGPoint(x: f.midX, y: f.midY)
    }

    /// Where an item of a menu is while that menu is open on the screen.
    static func openMenuItemPoint(menu: String, item: String) -> CGPoint? {
        guard let app = NSWorkspace.shared.frontmostApplication else { return nil }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.5)
        guard let bar = element(root, kAXMenuBarAttribute) else { return nil }
        let titled = { (e: AXUIElement) in plain((value(e, kAXTitleAttribute) as? String) ?? "") }
        guard let top = children(bar).first(where: { titled($0) == plain(menu) }) else { return nil }
        var entries = children(top)
        if entries.count == 1, (value(entries[0], kAXRoleAttribute) as? String) == "AXMenu" { entries = children(entries[0]) }
        let wanted = plain(item)
        let screen = CGRect(origin: .zero, size: NSScreen.screens.first?.frame.size ?? .zero)
        guard let found = entries.first(where: { titled($0) == wanted }) ?? entries.first(where: { !titled($0).isEmpty && titled($0).hasPrefix(wanted) }),
              (value(found, kAXEnabledAttribute) as? Bool) != false, let f = frame(found), f.height > 6, screen.contains(CGPoint(x: f.midX, y: f.midY)) else { return nil }
        return CGPoint(x: f.midX, y: f.midY)
    }

    /// One of the front window's own buttons (close, minimize, zoom): its centre.
    static func windowButton(_ kind: String) -> CGPoint? {
        guard let app = NSWorkspace.shared.frontmostApplication, let window = window(pid: app.processIdentifier) else { return nil }
        let attribute = kind == "close" ? kAXCloseButtonAttribute : kind == "zoom" ? kAXZoomButtonAttribute : kAXMinimizeButtonAttribute
        guard let button = element(window, attribute), let f = frame(button) else { return nil }
        return CGPoint(x: f.midX, y: f.midY)
    }

    /// Whether what is on screen at a point belongs to the given app (nothing of another app lies over it).
    static func shows(_ point: CGPoint, of bundle: String) -> Bool {
        let system = AXUIElementCreateSystemWide()
        AXUIElementSetMessagingTimeout(system, 0.35)
        var hit: AXUIElement?
        guard AXUIElementCopyElementAtPosition(system, Float(point.x), Float(point.y), &hit) == .success, let hit else { return false }
        var pid: pid_t = 0
        AXUIElementGetPid(hit, &pid)
        return NSRunningApplication(processIdentifier: pid)?.bundleIdentifier == bundle
    }

    /// Where an app's icon sits in the Dock (its centre), when it is there and on screen.
    static func dockIcon(_ name: String) -> CGPoint? {
        guard let dock = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == "com.apple.dock" }) else { return nil }
        let root = AXUIElementCreateApplication(dock.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.4)
        let screen = CGRect(origin: .zero, size: NSScreen.screens.first?.frame.size ?? .zero)
        for list in children(root).prefix(4) {
            for item in children(list).prefix(80) where (value(item, kAXRoleAttribute) as? String) == "AXDockItem" {
                if (value(item, kAXTitleAttribute) as? String) == name, let f = frame(item), screen.contains(CGPoint(x: f.midX, y: f.midY)) {
                    return CGPoint(x: f.midX, y: f.midY)
                }
            }
        }
        return nil
    }

    /// Where a file's icon is on the Desktop (its centre), when the Finder shows it there.
    static func desktopIcon(_ fileName: String) -> CGPoint? {
        guard let finder = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == "com.apple.finder" }) else { return nil }
        let root = AXUIElementCreateApplication(finder.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.4)
        let screen = CGRect(origin: .zero, size: NSScreen.screens.first?.frame.size ?? .zero)
        let wanted = fileName.lowercased(), stem = (fileName as NSString).deletingPathExtension.lowercased()
        let deadline = Date().addingTimeInterval(0.9)
        var queue = children(root).filter { (value($0, kAXRoleAttribute) as? String) != "AXMenuBar" }.map { ($0, 0) }, seen = 0
        while !queue.isEmpty, seen < 1500, Date() < deadline {
            let (next, depth) = queue.removeFirst()
            seen += 1
            let v = values(next, [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute, kAXFilenameAttribute])
            let says = v.compactMap { ($0 as? String)?.lowercased() }
            if says.contains(where: { $0 == wanted || $0 == stem }), let f = frame(next), f.width < 400, screen.contains(CGPoint(x: f.midX, y: f.midY)) {
                return CGPoint(x: f.midX, y: f.midY)
            }
            if depth < 5 { queue.append(contentsOf: children(next).prefix(120).map { ($0, depth + 1) }) }
        }
        return nil
    }

    /// Presses the button that commits what was just typed in the front window: its default
    /// button, else a button titled Done, Save, Add or Create. Never one inside a web page.
    /// Returns the button's title, or nil when there is none.
    static func pressCommitButton() -> String? {
        guard let app = NSWorkspace.shared.frontmostApplication, app.processIdentifier != ProcessInfo.processInfo.processIdentifier,
              let window = window(pid: app.processIdentifier) else { return nil }
        if let button = element(window, kAXDefaultButtonAttribute), (value(button, kAXEnabledAttribute) as? Bool) != false,
           AXUIElementPerformAction(button, kAXPressAction as CFString) == .success {
            return (value(button, kAXTitleAttribute) as? String).flatMap { $0.isEmpty ? nil : $0 } ?? "the default button"
        }
        let wanted: Set<String> = ["Done", "Save", "Add", "Create"]
        var queue = [window], seen = 0
        let deadline = Date().addingTimeInterval(0.8)
        while !queue.isEmpty, seen < 2500, Date() < deadline {
            let next = queue.removeFirst()
            seen += 1
            let v = values(next, [kAXRoleAttribute, kAXTitleAttribute, kAXEnabledAttribute])
            let role = (v[0] as? String) ?? ""
            if role == "AXWebArea" || role == "AXToolbar" { continue }         // never a page's button, never a toolbar's
            if role == "AXButton", let title = v[1] as? String, wanted.contains(title), (v[2] as? Bool) != false {
                return AXUIElementPerformAction(next, kAXPressAction as CFString) == .success ? title : nil
            }
            queue.append(contentsOf: children(next).prefix(120))
        }
        return nil
    }

    /// The commands of the front app's menu bar that can be chosen now: each with its menu,
    /// its title and its mark (a tick), one level of submenus included.
    static func menuCommands() -> [(menu: String, title: String, mark: String)] {
        guard let app = NSWorkspace.shared.frontmostApplication else { return [] }
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.6)
        guard let bar = element(root, kAXMenuBarAttribute) else { return [] }
        var out: [(menu: String, title: String, mark: String)] = []
        let deadline = Date().addingTimeInterval(1.5)
        for top in children(bar).prefix(16).dropFirst() {                          // not the Apple menu
            let name = (value(top, kAXTitleAttribute) as? String) ?? ""
            var entries = children(top)
            if entries.count == 1, (value(entries[0], kAXRoleAttribute) as? String) == "AXMenu" { entries = children(entries[0]) }
            for entry in entries.prefix(60) where Date() < deadline {
                let v = values(entry, [kAXTitleAttribute, kAXEnabledAttribute, kAXMenuItemMarkCharAttribute])
                guard let title = v[0] as? String, !title.isEmpty, (v[1] as? Bool) != false else { continue }
                out.append((name, title, (v[2] as? String) ?? ""))
            }
        }
        return out
    }

    /// The title of the app's front window ("" when it has none).
    static func windowTitle(_ pid: pid_t) -> String {
        window(pid: pid).flatMap { value($0, kAXTitleAttribute) as? String } ?? ""
    }

    /// Chooses an item of a sidebar by its name: the row in the left part of the app's front
    /// window whose text is one of `names` (compared by letters and digits only) is selected,
    /// or pressed where selecting is not offered. False when there is no such row.
    /// `anywhere`: the right part of the window instead (a pane's own list of further panes).
    static func chooseInSidebar(_ pid: pid_t, names: [String], anywhere: Bool = false) -> Bool {
        guard let window = window(pid: pid), let bounds = frame(window) else { return false }
        let key = { (text: String) in
            text.lowercased().replacingOccurrences(of: "&", with: " ").split(whereSeparator: { !$0.isLetter && !$0.isNumber })
                .filter { $0 != "and" && $0 != "the" }.joined()
        }
        let wanted = Set(names.map(key).filter { !$0.isEmpty })
        let deadline = Date().addingTimeInterval(1.5)
        var queue = [window], seen = 0
        while !queue.isEmpty, seen < 4000, Date() < deadline {
            let next = queue.removeFirst()
            seen += 1
            let v = values(next, [kAXRoleAttribute, kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute])
            let texts = [v[1], v[2], v[3]].compactMap { $0 as? String }
            let edge = bounds.minX + min(320, bounds.width * 0.45)                // where the sidebar ends, roughly
            if texts.contains(where: { wanted.contains(key($0)) }), let f = frame(next), anywhere ? f.midX >= edge : f.midX < edge {
                // the row it belongs to, or the thing itself
                var target = next
                var up: AXUIElement? = next
                for _ in 0..<4 {
                    guard let now = up else { break }
                    if (value(now, kAXRoleAttribute) as? String) == "AXRow" { target = now; break }
                    up = element(now, kAXParentAttribute)
                }
                if AXUIElementSetAttributeValue(target, kAXSelectedAttribute as CFString, kCFBooleanTrue) == .success { return true }
                if AXUIElementPerformAction(target, kAXPressAction as CFString) == .success { return true }
                if AXUIElementPerformAction(next, kAXPressAction as CFString) == .success { return true }
                Events.click(at: CGPoint(x: f.midX, y: f.midY))
                return true
            }
            queue.append(contentsOf: children(next).prefix(200))
        }
        return false
    }

    /// Whether the app is the one in front, and whether it has a window.
    static func isFront(_ pid: pid_t) -> Bool { NSWorkspace.shared.frontmostApplication?.processIdentifier == pid }
    static func hasWindow(_ pid: pid_t) -> Bool { window(pid: pid) != nil }

    /// Brings an app and its window forward through Accessibility. This works where asking
    /// macOS politely does not: an app in the background (as this one always is) may not be
    /// allowed to hand the front to another app.
    static func raise(_ pid: pid_t) {
        let root = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(root, 0.8)
        _ = AXUIElementSetAttributeValue(root, kAXFrontmostAttribute as CFString, kCFBooleanTrue)
        if let window = window(pid: pid) {
            _ = AXUIElementPerformAction(window, kAXRaiseAction as CFString)
            _ = AXUIElementSetAttributeValue(window, kAXMainAttribute as CFString, kCFBooleanTrue)
        }
    }

    /// The buttons, by title, of a question the app is asking: a sheet, a dialog, or failing
    /// those a window that has a Cancel button. Nil when it is asking nothing.
    private static func question(_ pid: pid_t) -> [String: AXUIElement]? {
        let root = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(root, 0.6)
        func buttons(in top: AXUIElement) -> [String: AXUIElement] {
            var found: [String: AXUIElement] = [:]
            var queue = [top], seen = 0
            while !queue.isEmpty, seen < 400 {
                let next = queue.removeFirst()
                seen += 1
                if (value(next, kAXRoleAttribute) as? String) == "AXButton", let title = value(next, kAXTitleAttribute) as? String, !title.isEmpty, found[title] == nil {
                    found[title] = next
                }
                queue.append(contentsOf: children(next).prefix(40))
            }
            return found
        }
        let windows = Array(((value(root, kAXWindowsAttribute) as? [AXUIElement]) ?? []).prefix(8))
        for window in windows {
            let subrole = (value(window, kAXSubroleAttribute) as? String) ?? ""
            if subrole == "AXDialog" || subrole == "AXSystemDialog" { return buttons(in: window) }
            if let sheet = children(window).first(where: { (value($0, kAXRoleAttribute) as? String) == "AXSheet" }) { return buttons(in: sheet) }
        }
        for window in windows {
            let all = buttons(in: window)
            if all["Cancel"] != nil { return all }
        }
        return nil
    }

    /// Whether the app is asking something (a sheet, a dialog, a window with Cancel in it).
    static func hasDialog(_ pid: pid_t) -> Bool { question(pid) != nil }

    /// Presses the button with one of the given titles in the question the app is asking.
    /// False when it is asking nothing or has no such button.
    static func pressDialogButton(_ pid: pid_t, titles: [String]) -> Bool {
        guard let buttons = question(pid) else { return false }
        for title in titles {
            if let button = buttons[title] { return AXUIElementPerformAction(button, kAXPressAction as CFString) == .success }
        }
        return false
    }

    /// Whether some element of the app's front window says the given text (in its title, its
    /// description or its value). Looks for at most a second.
    static func frontWindowSays(_ pid: pid_t, _ text: String) -> Bool {
        guard let window = window(pid: pid), !text.isEmpty else { return false }
        let wanted = text.lowercased()
        let deadline = Date().addingTimeInterval(1.0)
        var queue = [window], seen = 0
        while !queue.isEmpty, seen < 3000, Date() < deadline {
            let next = queue.removeFirst()
            seen += 1
            let v = values(next, [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute])
            if v.contains(where: { ($0 as? String)?.lowercased().contains(wanted) == true }) { return true }
            queue.append(contentsOf: children(next).prefix(200))
        }
        return false
    }

    /// Whether any window of the app says the text (in a title, a description or a value).
    static func anyWindowSays(_ pid: pid_t, _ text: String) -> Bool {
        let root = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(root, 0.6)
        let wanted = text.lowercased()
        guard !wanted.isEmpty else { return false }
        let deadline = Date().addingTimeInterval(1.0)
        var queue = Array(((value(root, kAXWindowsAttribute) as? [AXUIElement]) ?? []).prefix(8)), seen = 0
        while !queue.isEmpty, seen < 3000, Date() < deadline {
            let next = queue.removeFirst()
            seen += 1
            let v = values(next, [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute])
            if v.contains(where: { ($0 as? String)?.lowercased().contains(wanted) == true }) { return true }
            queue.append(contentsOf: children(next).prefix(200))
        }
        return false
    }

    /// Where to scroll when a step does not say: the middle of the largest scrolling area of
    /// the front window (the mouse may be anywhere, and a scroll goes to what is under it).
    static func scrollPoint() -> CGPoint? {
        guard let app = NSWorkspace.shared.frontmostApplication, let window = window(pid: app.processIdentifier) else { return nil }
        let screen = CGRect(origin: .zero, size: NSScreen.screens.first?.frame.size ?? .zero)
        var best: CGRect?
        var queue = [window], seen = 0
        let deadline = Date().addingTimeInterval(0.5)
        while !queue.isEmpty, seen < 400, Date() < deadline {
            let next = queue.removeFirst()
            seen += 1
            if (value(next, kAXRoleAttribute) as? String) == "AXScrollArea", let f = frame(next)?.intersection(screen), !f.isEmpty,
               f.width * f.height > (best.map { $0.width * $0.height } ?? 0) { best = f }
            queue.append(contentsOf: children(next).prefix(30))
        }
        let area = best ?? frame(window)?.intersection(screen)
        return area.flatMap { $0.isEmpty ? nil : CGPoint(x: $0.midX, y: $0.midY) }
    }

    /// Where the named app's front window is, for checking that a move took.
    static func windowFrame(app name: String) -> CGRect? {
        let running = NSWorkspace.shared.runningApplications.first { $0.localizedName == name }
            ?? NSWorkspace.shared.runningApplications.first { $0.bundleURL?.deletingPathExtension().lastPathComponent == name }
        return running.flatMap { window(pid: $0.processIdentifier) }.flatMap(frame)
    }

    /// Moves and sizes a window. `frame`: screen points, origin top left.
    private static func setFrame(_ window: AXUIElement, _ frame: CGRect) -> Bool {
        var origin = frame.origin, size = frame.size
        guard let p = AXValueCreate(.cgPoint, &origin), let s = AXValueCreate(.cgSize, &size) else { return false }
        let moved = AXUIElementSetAttributeValue(window, kAXPositionAttribute as CFString, p)
        let sized = AXUIElementSetAttributeValue(window, kAXSizeAttribute as CFString, s)
        _ = AXUIElementSetAttributeValue(window, kAXPositionAttribute as CFString, p)      // a window that had to shrink first
        return moved == .success && sized == .success
    }

    /// Puts the front window of the named app into a part of the screen and brings it forward.
    /// Nil when it worked, else why not.
    static func place(app name: String, in frame: CGRect) -> String? {
        let running = NSWorkspace.shared.runningApplications.first { $0.localizedName == name }
            ?? NSWorkspace.shared.runningApplications.first { $0.bundleURL?.deletingPathExtension().lastPathComponent == name }
        guard let running else { return "\(name) is not open" }
        guard let window = window(pid: running.processIdentifier) else { return "\(name) has no window open" }
        guard setFrame(window, frame) else { return "the window of \(name) could not be moved" }
        _ = AXUIElementPerformAction(window, kAXRaiseAction as CFString)
        usleep(250_000)
        if let now = self.frame(window), abs(now.minX - frame.minX) > 40 || abs(now.minY - frame.minY) > 40 {
            return "the window of \(name) did not go where it was put"
        }
        return nil
    }

    /// Puts the front app's window into the left half, the right half or all of `area`.
    static func moveFrontWindow(to side: String, within area: CGRect) -> String? {
        guard let app = NSWorkspace.shared.frontmostApplication, let window = window(pid: app.processIdentifier) else { return "there is no window in front" }
        var frame = area
        if side == "left" || side == "right" {
            frame.size.width = area.width / 2
            if side == "right" { frame.origin.x = area.midX }
        } else if side == "center" {                              // its own size (no larger than the screen), in the middle
            guard let now = self.frame(window) else { return "this window could not be moved" }
            frame.size = CGSize(width: min(now.width, area.width), height: min(now.height, area.height))
            frame.origin = CGPoint(x: (area.midX - frame.width / 2).rounded(), y: (area.midY - frame.height / 2).rounded())
        }
        guard setFrame(window, frame) else { return "this window could not be moved" }
        usleep(250_000)
        if let now = self.frame(window), abs(now.minX - frame.minX) > 40 || abs(now.minY - frame.minY) > 40 { return "this window did not go where it was put" }
        return nil
    }
}
