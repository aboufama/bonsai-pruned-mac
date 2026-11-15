// What needs no model: which apps are on this Mac (the Dock's first), what people call them,
// and opening an app or a link through the system.
import AppKit
import AssistantCore

enum Apps {
    /// What people say, and the app they mean.
    static let aliases: [String: String] = [
        "chrome": "Google Chrome", "brave": "Brave Browser", "edge": "Microsoft Edge", "settings": "System Settings",
        "system preferences": "System Settings", "preferences": "System Settings", "vscode": "Visual Studio Code",
        "vs code": "Visual Studio Code", "code": "Visual Studio Code", "word": "Microsoft Word", "excel": "Microsoft Excel",
        "powerpoint": "Microsoft PowerPoint", "imessage": "Messages", "texts": "Messages", "app store": "App Store",
        "zoom": "zoom.us", "email": "Mail", "browser": "Safari", "files": "Finder", "lmstudio": "LM Studio"]

    static let browsers: Set<String> = ["Safari", "Google Chrome", "Brave Browser", "Firefox", "Microsoft Edge", "Arc", "Opera", "Vivaldi",
                                        "Chromium", "Orion", "DuckDuckGo", "Zen"]

    /// Every app found in the usual folders, by name.
    static let installed: [String: URL] = {
        var found: [String: URL] = ["Finder": URL(fileURLWithPath: "/System/Library/CoreServices/Finder.app")]
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        for folder in ["/Applications", "/Applications/Utilities", "/System/Applications", "/System/Applications/Utilities", home + "/Applications"] {
            for item in (try? FileManager.default.contentsOfDirectory(atPath: folder)) ?? [] where item.hasSuffix(".app") {
                let name = String(item.dropLast(4))
                if found[name] == nil { found[name] = URL(fileURLWithPath: folder + "/" + item) }
            }
        }
        return found
    }()

    /// The apps kept in the Dock, in its order.
    static let dock: [String] = {
        let path = FileManager.default.homeDirectoryForCurrentUser.path + "/Library/Preferences/com.apple.dock.plist"
        guard let plist = NSDictionary(contentsOfFile: path), let tiles = plist["persistent-apps"] as? [[String: Any]] else { return [] }
        return tiles.compactMap { ($0["tile-data"] as? [String: Any])?["file-label"] as? String }.filter { !$0.isEmpty }
    }()

    /// The names given to the planner: the Dock's apps first, then the others, sixty at most.
    static let list: [String] = {
        var names = ["Finder"] + dock.filter { $0 != "Finder" }
        for name in installed.keys.sorted() where !names.contains(name) && names.count < 60 { names.append(name) }
        return names
    }()

    /// The app a spoken or typed name means, as macOS shows it; nil when there is none.
    /// "The Finder app" and "Finder.app" mean Finder.
    static func resolve(_ said: String) -> String? {
        AppNames.resolve(said, names: Array(installed.keys), aliases: aliases)
    }

    /// The same for a name a planner wrote, where a slip of a letter or two is still the app
    /// that was meant.
    static func nearest(_ said: String) -> String? {
        AppNames.resolve(said, names: Array(installed.keys), aliases: aliases, nearest: true)
    }

    /// Opens an app, or brings it to the front. True when it worked.
    static func open(_ name: String) async -> Bool {
        guard let url = installed[name] ?? resolve(name).flatMap({ installed[$0] }) else { return false }
        return await withCheckedContinuation { done in
            NSWorkspace.shared.openApplication(at: url, configuration: NSWorkspace.OpenConfiguration()) { app, _ in
                done.resume(returning: app != nil)
            }
        }
    }

    /// Opens an app (or brings it forward) and does not come back until it is in front, with a
    /// window if it shows one: first by asking macOS, then, if it is still behind after a
    /// moment, through Accessibility. `front` false: it was opened but never came forward.
    static func openInFront(_ name: String) async -> (opened: Bool, front: Bool, window: Bool) {
        guard let url = installed[name] ?? resolve(name).flatMap({ installed[$0] }) else { return (false, false, false) }
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.activates = true
        let running: NSRunningApplication? = await withCheckedContinuation { done in
            NSWorkspace.shared.openApplication(at: url, configuration: configuration) { app, _ in done.resume(returning: app) }
        }
        guard let running else { return (false, false, false) }
        let pid = running.processIdentifier
        let wait = { (seconds: Double, until: @escaping () -> Bool) async in
            for _ in 0..<Int(seconds / 0.2) where !until() { try? await Task.sleep(nanoseconds: 200_000_000) }
        }
        await wait(1.6) { Access.isFront(pid) }
        for _ in 0..<2 where !Access.isFront(pid) {                       // still behind: once through macOS, once through Accessibility
            running.activate()
            await Task.detached { Access.raise(pid) }.value
            await wait(1.6) { Access.isFront(pid) }
        }
        await wait(2.4) { Access.hasWindow(pid) }                          // a just-started app needs a moment for its window
        if Access.isFront(pid), Access.hasWindow(pid) { await Task.detached { Access.raise(pid) }.value }      // its window forward too
        return (true, Access.isFront(pid), Access.hasWindow(pid))
    }

    /// Opens a link (a web address, or mailto: for an email draft) in the named app, or in the
    /// default one for that kind of link. True when it worked.
    static func open(link: String, in app: String?) async -> Bool {
        var text = link.trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.contains(":") { text = "https://" + text }
        guard let url = URL(string: text) ?? text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed).flatMap(URL.init(string:)) else { return false }
        if let app, let appURL = installed[app] ?? resolve(app).flatMap({ installed[$0] }) {
            return await withCheckedContinuation { done in
                NSWorkspace.shared.open([url], withApplicationAt: appURL, configuration: NSWorkspace.OpenConfiguration()) { opened, _ in
                    done.resume(returning: opened != nil)
                }
            }
        }
        return NSWorkspace.shared.open(url)
    }
}
