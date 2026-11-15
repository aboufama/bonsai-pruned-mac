// What the Mac can be asked or told directly, with no model: a few facts about it (for
// answering questions), whether it is on the network, dark mode, the volume, folders, a
// calendar event, and the clipboard used to read and replace the selected text.
import AppKit
import AssistantCore
import CoreAudio
import CoreWLAN
import IOKit.ps
import Network

enum Mac {
    // MARK: the network

    private static var monitor: NWPathMonitor?
    private static var known: Bool?
    static var online: Bool { known ?? true }

    /// Tells `changed` (on the main queue) at start and whenever the Mac goes on or off the network.
    static func watchNetwork(_ changed: @escaping (Bool) -> Void) {
        let watcher = NWPathMonitor()
        watcher.pathUpdateHandler = { path in
            let on = path.status == .satisfied
            DispatchQueue.main.async {
                guard on != known else { return }
                known = on
                changed(on)
            }
        }
        watcher.start(queue: DispatchQueue(label: "bonsai.network"))
        monitor = watcher
    }

    // MARK: facts, for answering questions without looking at the screen

    static var isDark: Bool { NSApp.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua }

    /// A few sentences about the Mac as it is now. Call on the main thread.
    static func facts(now: Date = Date()) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "EEEE d MMMM yyyy, HH:mm"
        var parts = ["It is \(f.string(from: now))."]
        if let wifi = CWWiFiClient.shared().interface() { parts.append("Wi-Fi is \(wifi.powerOn() ? "on" : "off").") }
        parts.append(online ? "The Mac is connected to the internet." : "The Mac is not connected to the internet.")
        parts.append("Dark mode is \(isDark ? "on" : "off").")
        if let sound = volume() { parts.append("The volume is at \(sound.level)%" + (sound.muted ? " and the sound is muted." : ".")) }
        if let power = battery() { parts.append(power) }
        return parts.joined(separator: " ")
    }

    /// One of those facts as an answer to a question about it. Call on the main thread.
    static func say(_ fact: Talk.Fact, now: Date = Date()) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        switch fact {
        case .wifi:
            guard let wifi = CWWiFiClient.shared().interface() else { return "This Mac has no Wi-Fi." }
            return "Wi-Fi is \(wifi.powerOn() ? "on" : "off"), and the Mac is \(online ? "connected" : "not connected") to the internet."
        case .internet: return online ? "Yes, the Mac is connected to the internet." : "No, the Mac is not connected to the internet."
        case .battery: return battery() ?? "This Mac has no battery; it runs on mains power."
        case .time:
            f.dateFormat = "h:mm a"
            return "It is \(f.string(from: now))."
        case .date:
            f.dateFormat = "EEEE, d MMMM yyyy"
            return "Today is \(f.string(from: now))."
        case .appearance: return "Dark mode is \(isDark ? "on" : "off")."
        case .volume:
            guard let sound = volume() else { return "The volume of this sound output cannot be read." }
            return "The volume is at \(sound.level)%" + (sound.muted ? ", and the sound is muted." : ".")
        }
    }

    static func battery() -> String? {
        guard let info = IOPSCopyPowerSourcesInfo()?.takeRetainedValue(),
              let list = IOPSCopyPowerSourcesList(info)?.takeRetainedValue() as? [CFTypeRef] else { return nil }
        for source in list {
            guard let d = IOPSGetPowerSourceDescription(info, source)?.takeUnretainedValue() as? [String: Any],
                  let now = d[kIOPSCurrentCapacityKey] as? Int, let full = d[kIOPSMaxCapacityKey] as? Int, full > 0 else { continue }
            let plugged = (d[kIOPSPowerSourceStateKey] as? String) == kIOPSACPowerValue
            return "The battery is at \(now * 100 / full)%, \(plugged ? "plugged in" : "on battery")."
        }
        return nil
    }

    // MARK: the volume (Core Audio: the main volume of the sound output in use)

    private static let mainVolume = AudioObjectPropertySelector(0x766D_7663)        // 'vmvc', the volume the menu bar shows

    private static func address(_ selector: AudioObjectPropertySelector, output: Bool = true) -> AudioObjectPropertyAddress {
        AudioObjectPropertyAddress(mSelector: selector, mScope: output ? kAudioDevicePropertyScopeOutput : kAudioObjectPropertyScopeGlobal,
                                   mElement: kAudioObjectPropertyElementMain)
    }

    private static func outputDevice() -> AudioDeviceID? {
        var id = AudioDeviceID(0)
        var size = UInt32(MemoryLayout<AudioDeviceID>.size)
        var where_ = address(kAudioHardwarePropertyDefaultOutputDevice, output: false)
        guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &where_, 0, nil, &size, &id) == noErr, id != 0 else { return nil }
        return id
    }

    static func volume() -> (level: Int, muted: Bool)? {
        guard let device = outputDevice() else { return nil }
        var level = Float32(0)
        var size = UInt32(MemoryLayout<Float32>.size)
        var where_ = address(mainVolume)
        guard AudioObjectGetPropertyData(device, &where_, 0, nil, &size, &level) == noErr else { return nil }
        var muted = UInt32(0)
        size = UInt32(MemoryLayout<UInt32>.size)
        where_ = address(kAudioDevicePropertyMute)
        let hasMute = AudioObjectGetPropertyData(device, &where_, 0, nil, &size, &muted) == noErr
        return (Int((level * 100).rounded()), hasMute && muted != 0)
    }

    private static func setMuted(_ on: Bool, _ device: AudioDeviceID) -> Bool {
        var value: UInt32 = on ? 1 : 0
        var where_ = address(kAudioDevicePropertyMute)
        return AudioObjectSetPropertyData(device, &where_, 0, nil, UInt32(MemoryLayout<UInt32>.size), &value) == noErr
    }

    /// "mute", "unmute", "up", "down" or a number from 0 to 100. Nil when it worked, else why not.
    static func setVolume(_ what: String) -> String? {
        guard let device = outputDevice() else { return "there is no sound output" }
        if what == "mute" || what == "unmute" {
            guard setMuted(what == "mute", device) else { return "this sound output cannot be muted from here" }
            return volume()?.muted == (what == "mute") ? nil : "the sound did not \(what)"
        }
        guard let now = volume() else { return "this sound output has no volume of its own" }
        let target = what == "up" ? min(100, now.level + 15) : what == "down" ? max(0, now.level - 15) : min(100, max(0, Int(what) ?? now.level))
        var level = Float32(target) / 100
        var where_ = address(mainVolume)
        guard AudioObjectSetPropertyData(device, &where_, 0, nil, UInt32(MemoryLayout<Float32>.size), &level) == noErr else {
            return "the volume of this sound output cannot be set from here"
        }
        if target > 0, now.muted { _ = setMuted(false, device) }
        guard let after = volume(), abs(after.level - target) <= 3 else { return "the volume did not change to \(target)%" }     // heard, not hoped
        return nil
    }

    // MARK: dark mode

    /// Switches the Mac to dark or light. The system's own switch is used (the one System
    /// Settings calls); if this macOS does not have it, System Events is asked instead, which
    /// macOS lets through only after its own permission question.
    /// Whether the Mac is dark now, asked of the system itself (not of this app's own look,
    /// which follows a moment later); nil when this macOS cannot be asked.
    static func darkNow() -> Bool? {
        typealias Ask = @convention(c) () -> Bool
        guard let library = dlopen("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight", RTLD_LAZY),
              let symbol = dlsym(library, "SLSGetAppearanceThemeLegacy") else { return nil }
        return unsafeBitCast(symbol, to: Ask.self)()
    }

    static func setAppearance(dark: Bool) -> String? {
        typealias Switch = @convention(c) (Bool) -> Void
        if let library = dlopen("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight", RTLD_LAZY),
           let symbol = dlsym(library, "SLSSetAppearanceThemeLegacy") {
            unsafeBitCast(symbol, to: Switch.self)(dark)
            usleep(300_000)
            if let now = darkNow(), now != dark { return "the Mac did not switch to \(dark ? "dark" : "light") mode" }
            return nil
        }
        let script = "tell application \"System Events\" to tell appearance preferences to set dark mode to \(dark)"
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        process.arguments = ["-e", script]
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice
        guard (try? process.run()) != nil else { return "dark mode could not be switched" }
        process.waitUntilExit()
        return process.terminationStatus == 0 ? nil : "dark mode could not be switched (macOS did not allow it)"
    }

    // MARK: the Dock

    /// The Dock's plain settings, written where the Dock keeps them; the Dock is then started
    /// again so that it reads them (it comes back by itself). The setting is read back.
    /// `what`: autohide (on, off), position (left, bottom, right), magnification (on, off),
    /// size (small, medium, large, bigger, smaller, or a percentage).
    static func setDock(_ what: String, _ value: String) -> String? {
        let domain = "com.apple.dock" as CFString
        let read = { (key: String) in CFPreferencesCopyAppValue(key as CFString, domain) }
        var key = "", wanted: CFPropertyList = kCFBooleanTrue
        switch what {
        case "autohide", "magnification":
            key = what
            wanted = value == "on" ? kCFBooleanTrue : kCFBooleanFalse
        case "position":
            guard ["left", "bottom", "right"].contains(value) else { return "the Dock can be on the left, the bottom or the right" }
            key = "orientation"
            wanted = value as CFString
        case "size":
            key = "tilesize"
            let now = (read("tilesize") as? NSNumber)?.doubleValue ?? 48
            let named: [String: Double] = ["small": 32, "medium": 56, "large": 88, "bigger": now + 16, "smaller": now - 16]
            let size = named[value] ?? (Double(value).map { 16 + $0 / 100 * 112 } ?? now)
            wanted = NSNumber(value: min(128, max(16, size.rounded())))
        default: return "that is not a setting of the Dock I can change directly"
        }
        CFPreferencesSetAppValue(key as CFString, wanted, domain)
        guard CFPreferencesAppSynchronize(domain) else { return "the Dock's setting could not be written" }
        let restart = Process()
        restart.executableURL = URL(fileURLWithPath: "/usr/bin/killall")
        restart.arguments = ["Dock"]
        restart.standardOutput = FileHandle.nullDevice
        restart.standardError = FileHandle.nullDevice
        guard (try? restart.run()) != nil else { return "the Dock could not be started again to take the setting" }
        restart.waitUntilExit()
        usleep(900_000)
        guard let after = read(key), CFEqual(after, wanted) else { return "the Dock's setting did not change" }
        return nil
    }

    // MARK: folders

    static func folder(_ place: String) -> URL? {
        let files = FileManager.default
        switch place {
        case "desktop": return files.urls(for: .desktopDirectory, in: .userDomainMask).first
        case "documents": return files.urls(for: .documentDirectory, in: .userDomainMask).first
        case "downloads": return files.urls(for: .downloadsDirectory, in: .userDomainMask).first
        case "applications": return URL(fileURLWithPath: "/Applications")
        case "pictures": return files.urls(for: .picturesDirectory, in: .userDomainMask).first
        case "movies": return files.urls(for: .moviesDirectory, in: .userDomainMask).first
        case "music": return files.urls(for: .musicDirectory, in: .userDomainMask).first
        case "home": return files.homeDirectoryForCurrentUser
        default:
            guard place.hasPrefix("~") || place.hasPrefix("/") else { return nil }
            let path = (place as NSString).expandingTildeInPath
            return files.fileExists(atPath: path) ? URL(fileURLWithPath: path) : nil
        }
    }

    /// Makes a folder (never over one that exists: "Demo 2") and shows it in the Finder.
    /// What "bring up the presentation" shows: the file or link named for this run, else the
    /// newest deck in ~/Bonsai-demo/demo or beside the program (a Keynote or PowerPoint file,
    /// a PDF, a web page, a picture). The user's own folders are not searched.
    static func presentation() -> String? {
        if let named = Launch.presentation {
            if named.contains("://") { return named }
            let path = (named as NSString).expandingTildeInPath
            return FileManager.default.fileExists(atPath: path) ? path : nil
        }
        let kinds = ["key", "pptx", "pdf", "html", "png", "jpg", "jpeg"]
        // a file called Presentation on the Desktop comes first: its icon can be seen and clicked
        let desk = NSHomeDirectory() + "/Desktop"
        if let onDesk = ((try? FileManager.default.contentsOfDirectory(atPath: desk)) ?? []).filter({ name in
            let lower = name.lowercased()
            return lower.hasPrefix("presentation") && kinds.contains((lower as NSString).pathExtension)
        }).sorted().first { return desk + "/" + onDesk }
        let folders = [NSHomeDirectory() + "/Bonsai-demo/demo", (CommandLine.arguments.first.map { ($0 as NSString).deletingLastPathComponent } ?? "") + "/demo",
                       CommandLine.arguments.first.map { ($0 as NSString).deletingLastPathComponent } ?? ""]
        for folder in folders where !folder.isEmpty {
            let files = ((try? FileManager.default.contentsOfDirectory(atPath: folder)) ?? []).filter { name in
                let lower = name.lowercased()
                return kinds.contains((lower as NSString).pathExtension) && ["presentation", "slides", "deck"].contains { lower.contains($0) }
            }
            let ranked = files.sorted { a, b in
                let ka = kinds.firstIndex(of: (a.lowercased() as NSString).pathExtension) ?? 9, kb = kinds.firstIndex(of: (b.lowercased() as NSString).pathExtension) ?? 9
                return ka != kb ? ka < kb : a < b
            }
            if let first = ranked.first { return folder + "/" + first }
        }
        return nil
    }

    /// The folder `newFolder` made last, for a request that goes on "…, then put the file inside it".
    static var lastFolder: URL?

    /// The item of that name in a folder: exactly, else the only one that differs in case.
    private static func item(_ name: String, in folder: URL) -> URL? {
        let exact = folder.appendingPathComponent(name)
        if FileManager.default.fileExists(atPath: exact.path) { return exact }
        let same = ((try? FileManager.default.contentsOfDirectory(atPath: folder.path)) ?? []).filter { $0.lowercased() == name.lowercased() }
        return same.count == 1 ? folder.appendingPathComponent(same[0]) : nil
    }

    /// Renames a file in a folder. Nil when the new name is there and the old one is gone.
    static func renameFile(_ name: String, in place: String, to new: String) -> String? {
        guard let folder = folder(place) else { return "there is no \(place) folder" }
        guard let from = item(name, in: folder) else { return "there is no \(name) in \(place)" }
        let to = folder.appendingPathComponent(new)
        guard !FileManager.default.fileExists(atPath: to.path) else { return "there is already a \(new) in \(place)" }
        do { try FileManager.default.moveItem(at: from, to: to) } catch { return "\(name) could not be renamed (\(error.localizedDescription))" }
        return FileManager.default.fileExists(atPath: to.path) && !FileManager.default.fileExists(atPath: from.path) ? nil : "\(name) was not renamed"
    }

    /// Moves a file into a folder: a named one (documents), one of that name beside the file,
    /// or ("it") the folder made last. Nil when the file is there and no longer where it was.
    static func moveFile(_ name: String, from place: String, into destination: String) -> String? {
        let files = FileManager.default
        let made = destination == "it" ? lastFolder : nil
        if destination == "it", made == nil { return "it is not clear which folder is meant" }
        guard let source = place.isEmpty ? (made?.deletingLastPathComponent() ?? folder("desktop")) : folder(place) else { return "there is no \(place) folder" }
        guard let from = item(name, in: source) else { return "there is no \(name) in \(place.isEmpty ? source.lastPathComponent : place)" }
        if ["trash", "bin"].contains(destination.lowercased()) {                 // the Trash: the system's own way, so it can be put back
            do { try files.trashItem(at: from, resultingItemURL: nil) } catch { return "\(name) could not be moved to the Trash (\(error.localizedDescription))" }
            return files.fileExists(atPath: from.path) ? "\(name) was not moved to the Trash" : nil
        }
        var target: URL? = made
        if target == nil { target = item(destination, in: source) ?? Places.folder(destination).flatMap { folder($0) } }
        var isFolder: ObjCBool = false
        guard let into = target, files.fileExists(atPath: into.path, isDirectory: &isFolder), isFolder.boolValue else { return "there is no folder called \(destination)" }
        let to = into.appendingPathComponent(from.lastPathComponent)
        guard !files.fileExists(atPath: to.path) else { return "there is already a \(from.lastPathComponent) in \(into.lastPathComponent)" }
        do { try files.moveItem(at: from, to: to) } catch { return "\(name) could not be moved (\(error.localizedDescription))" }
        return files.fileExists(atPath: to.path) && !files.fileExists(atPath: from.path) ? nil : "\(name) was not moved"
    }

    static func newFolder(named name: String, in place: String) -> String? {
        guard let parent = folder(place) else { return "there is no \(place) folder" }
        var clean = name.replacingOccurrences(of: "/", with: "-").replacingOccurrences(of: ":", with: "-").trimmingCharacters(in: .whitespaces)
        if clean.isEmpty || clean.hasPrefix(".") { clean = "New Folder" }
        var url = parent.appendingPathComponent(clean)
        var n = 2
        while FileManager.default.fileExists(atPath: url.path) {
            url = parent.appendingPathComponent("\(clean) \(n)")
            n += 1
        }
        do {
            try FileManager.default.createDirectory(at: url, withIntermediateDirectories: false)
        } catch {
            return "the folder could not be made (\(error.localizedDescription))"
        }
        var isFolder: ObjCBool = false
        lastFolder = url
        guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isFolder), isFolder.boolValue else {
            return "the folder \(url.lastPathComponent) is not there after making it"
        }
        NSWorkspace.shared.activateFileViewerSelecting([url])
        return nil
    }

    /// Shows a folder in the Finder (a named one, or a path); a path to a file shows the file
    /// selected in its folder.
    static func reveal(_ place: String) -> String? {
        let isPath = place.hasPrefix("~") || place.hasPrefix("/")
        guard let url = folder(place) else { return isPath ? "there is nothing at \(place)" : "there is no \(place) folder" }
        var isFolder: ObjCBool = false
        if FileManager.default.fileExists(atPath: url.path, isDirectory: &isFolder), !isFolder.boolValue {
            NSWorkspace.shared.activateFileViewerSelecting([url])
            return nil
        }
        let finder = URL(fileURLWithPath: "/System/Library/CoreServices/Finder.app")
        NSWorkspace.shared.open([url], withApplicationAt: finder, configuration: NSWorkspace.OpenConfiguration(), completionHandler: nil)
        return nil
    }

    // MARK: a calendar event

    /// Reads the day and time out of the words ("with Sam tomorrow at 3pm") and writes a
    /// calendar file with a one-hour event. The app then opens it in Calendar and sees it
    /// through (see AppController). `problem` says why no file was written.
    static func calendarFile(kind: String, rest: String) -> (path: String?, title: String, problem: String?) {
        // The day and time as the request says them; with none, the next full hour (an event
        // made by hand in Calendar starts today too).
        let ns = rest as NSString
        var start = Skills.nextHour(after: Date())
        var phrase = ""
        if let detector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.date.rawValue),
           let found = detector.firstMatch(in: rest, range: NSRange(location: 0, length: ns.length)), let date = found.date,
           Skills.saysWhen(ns.substring(with: found.range)) {
            start = date
            phrase = ns.substring(with: found.range)
        }
        let title = Skills.eventTitle(kind: kind, rest: rest, datePhrase: phrase)
        let folder = NSHomeDirectory() + "/Library/Caches/BonsaiAssistant"
        let path = folder + "/event.ics"
        do {
            try FileManager.default.createDirectory(atPath: folder, withIntermediateDirectories: true)
            try Skills.calendarFile(title: title, start: start).write(toFile: path, atomically: true, encoding: .utf8)
        } catch {
            return (nil, title, "the event could not be written (\(error.localizedDescription))")
        }
        return (path, title, nil)
    }

    // MARK: the screen and the clipboard

    /// The part of the main screen that windows may use, in screen points with the origin top left.
    static func usableScreen() -> CGRect {
        guard let screen = NSScreen.screens.first else { return .zero }
        let v = screen.visibleFrame
        return CGRect(x: v.minX, y: screen.frame.height - v.maxY, width: v.width, height: v.height)
    }

    /// What is on the clipboard, to be put back.
    static func clipboard() -> [NSPasteboardItem] {
        (NSPasteboard.general.pasteboardItems ?? []).map { item in
            let copy = NSPasteboardItem()
            for type in item.types {
                if let data = item.data(forType: type) { copy.setData(data, forType: type) }
            }
            return copy
        }
    }

    static func restore(_ items: [NSPasteboardItem]) {
        NSPasteboard.general.clearContents()
        if !items.isEmpty { NSPasteboard.general.writeObjects(items) }
    }
}
