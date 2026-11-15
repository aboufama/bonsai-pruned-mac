import Foundation

/// Places that can be opened by their name alone, with no model and no clicking: a pane of
/// System Settings, a folder, a well-known web site. Used for requests typed by the user, and
/// to make sense of an `open_app` or `open_url` step whose text is not an app or an address.
public enum Places {
    // MARK: System Settings

    public struct Pane: Equatable {
        public let name: String
        public let id: String
        /// The link macOS itself uses to open System Settings at this pane.
        public var url: String { Places.settingsScheme + id }
    }

    public static let settingsScheme = "x-apple.systempreferences:"

    /// The panes, with their identifiers as read from /System/Library/ExtensionKit/Extensions on
    /// macOS 15.6, and what else people call them. Compared with the same folder of macOS 26.6:
    /// Siri, Time Machine, Trackpad and the others found there have the same identifiers; many
    /// panes are no longer in that folder but their links still open them (Wi-Fi, Network,
    /// Sound, General, Appearance, Displays, Wallpaper, Lock Screen, Storage); VPN and Screen
    /// Saver have no pane of their own there (see `moved`); a pane for hardware the Mac lacks
    /// (Trackpad) is not shown at all. So a link is never trusted: the app checks the window.
    static let panes: [(name: String, id: String, also: [String])] = [
        ("Wi-Fi", "com.apple.wifi-settings-extension", ["wifi", "wireless", "wi fi"]),
        ("Bluetooth", "com.apple.BluetoothSettings", []),
        ("Network", "com.apple.Network-Settings.extension", ["internet", "ethernet"]),
        ("VPN", "com.apple.NetworkExtensionSettingsUI.NESettingsUIExtension", []),
        ("Notifications", "com.apple.Notifications-Settings.extension", ["notification"]),
        ("Sound", "com.apple.Sound-Settings.extension", ["audio", "sounds", "volume"]),
        ("Focus", "com.apple.Focus-Settings.extension", ["do not disturb"]),
        ("Screen Time", "com.apple.Screen-Time-Settings.extension", []),
        ("General", "com.apple.systempreferences.GeneralSettings", []),
        ("Appearance", "com.apple.Appearance-Settings.extension", ["dark mode", "theme"]),
        ("Accessibility", "com.apple.Accessibility-Settings.extension", []),
        ("Control Center", "com.apple.ControlCenter-Settings.extension", ["control centre", "menu bar"]),
        ("Siri", "com.apple.Siri-Settings.extension", ["apple intelligence and siri", "siri and spotlight"]),
        ("Spotlight", "com.apple.Spotlight-Settings.extension", []),
        ("Privacy & Security", "com.apple.settings.PrivacySecurity.extension", ["privacy", "security"]),
        ("Desktop & Dock", "com.apple.Desktop-Settings.extension", ["dock", "desktop", "dock and desktop"]),
        ("Displays", "com.apple.Displays-Settings.extension", ["display", "monitor", "monitors", "screen", "resolution"]),
        ("Wallpaper", "com.apple.Wallpaper-Settings.extension", ["desktop picture", "background"]),
        ("Screen Saver", "com.apple.ScreenSaver-Settings.extension", ["screensaver"]),
        ("Battery", "com.apple.Battery-Settings.extension", ["power", "energy", "energy saver"]),
        ("Lock Screen", "com.apple.Lock-Screen-Settings.extension", []),
        ("Touch ID & Password", "com.apple.Touch-ID-Settings.extension", ["touch id", "login password"]),
        ("Users & Groups", "com.apple.Users-Groups-Settings.extension", ["users", "accounts"]),
        ("Internet Accounts", "com.apple.Internet-Accounts-Settings.extension", []),
        ("Game Center", "com.apple.Game-Center-Settings.extension", []),
        ("Keyboard", "com.apple.Keyboard-Settings.extension", ["keyboard shortcuts", "shortcuts", "dictation"]),
        ("Mouse", "com.apple.Mouse-Settings.extension", []),
        ("Trackpad", "com.apple.Trackpad-Settings.extension", []),
        ("Printers & Scanners", "com.apple.Print-Scan-Settings.extension", ["printers", "printer", "scanners"]),
        ("Software Update", "com.apple.Software-Update-Settings.extension", ["updates", "update"]),
        ("Storage", "com.apple.settings.Storage", ["disk space"]),
        ("Date & Time", "com.apple.Date-Time-Settings.extension", ["time zone", "clock"]),
        ("Language & Region", "com.apple.Localization-Settings.extension", ["language", "region"]),
        ("Sharing", "com.apple.Sharing-Settings.extension", []),
        ("Time Machine", "com.apple.Time-Machine-Settings.extension", ["backup", "backups"]),
        ("Login Items", "com.apple.LoginItems-Settings.extension", ["login items and extensions"]),
        ("About", "com.apple.SystemProfiler.AboutExtension", ["about this mac"]),
        ("Apple Account", "com.apple.systempreferences.AppleIDSettings", ["apple id", "icloud"]),
        ("AirDrop & Handoff", "com.apple.AirDrop-Handoff-Settings.extension", ["airdrop", "handoff"]),
        ("Family", "com.apple.Family-Settings.extension", ["family sharing"]),
        ("Transfer or Reset", "com.apple.Transfer-Reset-Settings.extension", ["erase all content and settings", "factory reset"]),
        ("Wallet & Apple Pay", "com.apple.WalletSettingsExtension", ["wallet", "apple pay"]),
        ("Game Controllers", "com.apple.Game-Controller-Settings.extension", ["game controller", "controllers"]),
    ]

    /// A name reduced to its letters and digits, without "and": "Wi-Fi" and "wifi" are the
    /// same, and so are "Privacy & Security" and "privacy and security".
    static func key(_ text: String) -> String {
        let words = text.lowercased().replacingOccurrences(of: "&", with: " ").split(whereSeparator: { !$0.isLetter && !$0.isNumber })
        return words.filter { $0 != "and" && $0 != "the" }.joined()
    }

    /// The pane a name means, or nil. Words such as "settings", "pane" and "System Settings >"
    /// around the name are ignored.
    public static func pane(_ said: String) -> Pane? {
        var t = said.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".\"'")))
        if let m = Commands.match(#"^(?:system\s+)?(?:settings|preferences)\s*(?:>|→|:|/|-)\s*(.+)$"#, t) { t = m[1] }
        if let m = Commands.match(#"^settings:\s*(.+)$"#, t) { t = m[1] }
        while let m = Commands.match(#"^(.+?)\s+(?:system\s+settings|system\s+preferences|settings|preferences|prefs|pane|section|panel)$"#, t) { t = m[1] }
        let wanted = key(t)
        guard !wanted.isEmpty else { return nil }
        for p in panes where key(p.name) == wanted || p.also.contains(where: { key($0) == wanted }) { return Pane(name: p.name, id: p.id) }
        return nil
    }

    /// What the window of System Settings may be titled when a pane is showing, besides the
    /// pane's own name and the other names in `panes` (macOS 26 calls Control Center "Menu
    /// Bar", Battery "Energy" on a desktop Mac, and so on).
    static let titles: [String: [String]] = [
        "Control Center": ["Menu Bar"], "Battery": ["Energy", "Energy Saver"], "Touch ID & Password": ["Login Password", "Password"],
        "Login Items": ["Login Items & Extensions"], "Siri": ["Apple Intelligence & Siri", "Siri & Spotlight"],
        "Desktop & Dock": ["Dock & Desktop"], "Apple Account": ["Sign in", "Apple ID", "iCloud"],
    ]

    /// The names a pane goes by, in the sidebar of System Settings and in its window's title.
    public static func names(of pane: Pane) -> [String] {
        [pane.name] + (panes.first { $0.name == pane.name }?.also ?? []) + (titles[pane.name] ?? [])
    }

    /// Whether a window title of System Settings is this pane's. The Apple Account pane is
    /// titled with the person's name, so any title counts for it.
    public static func shows(_ pane: Pane, title: String) -> Bool {
        if pane.name == "Apple Account" { return true }
        let wanted = key(title)
        return !wanted.isEmpty && names(of: pane).contains { key($0) == wanted }
    }

    /// Where a pane's settings are kept on a macOS that has no pane of that name (macOS 26.6
    /// has no Screen Saver or VPN pane). That pane is opened as a start for the planner; the
    /// step itself is not counted as done.
    public static func moved(_ pane: Pane) -> Pane? {
        let to = ["Screen Saver": "Wallpaper", "VPN": "Network"][pane.name]
        return to.flatMap { name in panes.first { $0.name == name } }.map { Pane(name: $0.name, id: $0.id) }
    }

    /// The pane a settings link opens, by its identifier (for saying what is being opened).
    public static func pane(ofLink link: String) -> Pane? {
        guard link.lowercased().hasPrefix(settingsScheme) else { return nil }
        let id = String(link.dropFirst(settingsScheme.count)).split(separator: "?").first.map(String.init) ?? ""
        return panes.first { $0.id.lowercased() == id.lowercased() }.map { Pane(name: $0.name, id: $0.id) }
    }

    // MARK: folders

    /// The folders known by name. "music" and "home" are also apps, so on their own they are
    /// left to mean the app.
    public static let folders = ["desktop", "documents", "downloads", "applications", "pictures", "movies", "music", "home"]

    /// The folder some words mean: one of `folders`, or a path that starts with ~ or /. Nil
    /// when they mean neither. "Folder", "directory" and "in Finder" around a name are ignored;
    /// `bare` says whether a name with none of these counts ("downloads" yes, "music" no).
    public static func folder(_ said: String) -> String? {
        var t = said.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: "\"'")))
        if t.lowercased().hasPrefix("file://") { t = String(t.dropFirst(7)).removingPercentEncoding ?? String(t.dropFirst(7)) }
        if t.hasPrefix("~") || t.hasPrefix("/") { return t.count > 1 || t == "~" ? t : nil }
        var marked = false
        if let m = Commands.match(#"^(.+?)\s+in\s+(?:the\s+)?finder$"#, t) { t = m[1]; marked = true }
        if let m = Commands.match(#"^(?:my\s+|the\s+)?(.+?)\s+(?:folder|directory)$"#, t) { t = m[1]; marked = true }
        if let m = Commands.match(#"^(?:my\s+|the\s+)(.+)$"#, t) { t = m[1] }
        let name = t.lowercased()
        guard folders.contains(name) else { return nil }
        return marked || (name != "music" && name != "home") ? name : nil
    }

    // MARK: web sites

    static let sites: [String: String] = [
        "google": "https://www.google.com", "youtube": "https://www.youtube.com", "gmail": "https://mail.google.com",
        "googlemaps": "https://maps.google.com", "googledocs": "https://docs.google.com", "googledrive": "https://drive.google.com",
        "googlecalendar": "https://calendar.google.com", "googletranslate": "https://translate.google.com",
        "github": "https://github.com", "wikipedia": "https://www.wikipedia.org", "amazon": "https://www.amazon.com",
        "reddit": "https://www.reddit.com", "twitter": "https://x.com", "x": "https://x.com", "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com", "linkedin": "https://www.linkedin.com", "netflix": "https://www.netflix.com",
        "spotify": "https://open.spotify.com", "twitch": "https://www.twitch.tv", "apple": "https://www.apple.com",
        "nytimes": "https://www.nytimes.com", "newyorktimes": "https://www.nytimes.com", "bbc": "https://www.bbc.com",
        "cnn": "https://www.cnn.com", "espn": "https://www.espn.com", "imdb": "https://www.imdb.com", "ebay": "https://www.ebay.com",
        "yahoo": "https://www.yahoo.com", "bing": "https://www.bing.com", "duckduckgo": "https://duckduckgo.com",
        "stackoverflow": "https://stackoverflow.com", "hackernews": "https://news.ycombinator.com", "chatgpt": "https://chatgpt.com",
        "claude": "https://claude.ai", "whatsapp": "https://web.whatsapp.com", "outlook": "https://outlook.live.com",
        "huggingface": "https://huggingface.co", "arxiv": "https://arxiv.org", "lmstudio": "https://lmstudio.ai",
        "cornell": "https://www.cornell.edu", "weather": "https://weather.com", "zoom": "https://zoom.us",
    ]

    /// The address of a site named in words ("YouTube", "the New York Times website"), or nil.
    /// A single unknown word is taken as a .com address only when the words say it is a site.
    public static func site(named said: String) -> String? {
        var t = said.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".\"'")))
        var saysSite = false
        if let m = Commands.match(#"^(.+?)\s+in\s+(?:the\s+|my\s+|a\s+)?(?:browser|safari|chrome|web\s+browser)$"#, t) { t = m[1]; saysSite = true }
        if let m = Commands.match(#"^(?:the\s+)?(.+?)(?:'s)?\s+(?:website|web\s+site|site|web\s+page|homepage|home\s+page)$"#, t) { t = m[1]; saysSite = true }
        if let m = Commands.match(#"^the\s+(.+)$"#, t) { t = m[1] }
        if let address = Recipes.site(t) { return address }                // "apple.com" is already an address: exactly that
        let wanted = key(t)
        if let known = sites[wanted] { return known }
        if saysSite, !wanted.isEmpty, !t.contains(" "), wanted.count <= 30 { return "https://www.\(wanted).com" }
        return nil
    }

    /// The browsers a request may name ("open apple.com in Safari").
    public static let browsers: Set<String> = ["Safari", "Google Chrome", "Brave Browser", "Firefox", "Microsoft Edge", "Arc", "Opera", "Vivaldi",
                                               "Chromium", "Orion", "DuckDuckGo", "Zen"]

    // MARK: an `open` that names no app

    public enum Place: Equatable {
        case link(String)            // a settings pane or a web site
        case folder(String)          // one of `folders`, or a path
    }

    /// What the text of an `open_app` or `open_url` step may mean when it is neither an app on
    /// this Mac nor an address: a settings pane, a folder, a site by its name.
    public static func resolve(_ text: String) -> Place? {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if t.lowercased().hasPrefix(settingsScheme) { return .link(t) }
        if let pane = pane(t) { return .link(pane.url) }
        if let folder = folder(t) { return .folder(folder) }
        if let site = site(named: t) { return .link(site) }
        return nil
    }
}
