// The app: a leaf in the menu bar, a hotkey that opens the input bar, and the two things a
// request can become: "show me" (point at it) and "do it" (carry it out step by step).
import AppKit
import AssistantCore
import AVFoundation
import Carbon.HIToolbox

final class AppController: NSObject, NSApplicationDelegate, NSMenuDelegate {
    static let maxSteps = 12
    static let zoom: CGFloat = 3              // a second look sees a third of each side
    static let zoomSide = 1024                // and is shown at this many pixels on its longer side

    private enum HotKey {
        static let ask: UInt32 = 1, askToo: UInt32 = 2, escape: UInt32 = 3, ret: UInt32 = 4, enter: UInt32 = 5
        static let talk: UInt32 = 6, talkDo: UInt32 = 7
    }

    private let settings = Settings.shared
    private var statusItem: NSStatusItem!
    private let overlay = Overlay()
    private let bar = InputBar()
    private let log = LogWindow()
    private let client: LMClient
    private let pipeline: Pipeline
    private var models: [String] = []
    private let modelMenu = NSMenu()

    // LM Studio housekeeping
    static let contextLength = 8192            // a 1280 px screenshot is about 1,040 tokens; the step tool adds a few hundred
    private var studio: [StudioModel] = []     // the language models LM Studio has, when the server is LM Studio
    private var isStudio = false
    private var ready = false
    private var modelSees = true               // false: LM Studio lists the model without a vision file
    static let launcher = "the app this was started from (Terminal, or Claude if started in its terminal panel)"
    private var readiness = "LM Studio: checking…"
    private var preparing: Task<Void, Never>?
    private var preparations = 0
    private var startedServer = false          // this app started the server: it stops it on quit
    private var loadedByApp: [String] = []     // instances this app loaded: it unloads them on quit
    private var displaced: [(key: String, context: Int)] = []   // models it unloaded to make room: reloaded on quit
    private var signals: [DispatchSourceSignal] = []

    // reading ahead, and spoken requests
    private struct Ahead {
        let sent: Sent
        let started: Date
        let read: Task<Double?, Never>          // seconds the read took; nil if it failed
    }
    private var ahead: Ahead?
    private let voice = Voice()
    private var voiceShowOnly = false
    private var watcher: Timer?
    private var watched: Shot?                  // the last capture the watcher took
    private var watching = false

    /// `--smoke`: start, show each window once, get the server ready, quit after half a minute.
    /// No permission is asked for, the screen is not captured and no event is sent.
    private let smoke = CommandLine.arguments.contains("--smoke")
    private let speaker = AVSpeechSynthesizer()

    private var run: Task<Void, Never>?
    private var runID = 0
    private var confirm: CheckedContinuation<Bool, Never>?

    override init() {
        client = LMClient(base: LMClient.url(from: Settings.shared.server) ?? URL(string: "http://localhost:1234/v1")!)
        pipeline = Pipeline(client: client, model: Settings.shared.model)
        super.init()
        client.token = { Keychain.token() }        // read from the Keychain when a request is about to be sent
    }

    // MARK: start

    func applicationDidFinishLaunching(_ notification: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        let image = NSImage(systemSymbolName: "leaf.fill", accessibilityDescription: "Bonsai assistant")
        image?.isTemplate = true
        statusItem.button?.image = image
        let menu = NSMenu()
        menu.delegate = self
        statusItem.menu = menu
        rebuild(menu)

        bar.onSubmit = { [weak self] text, showOnly in self?.ask(text, showOnly: showOnly) }
        let first = HotKeys.shared.register(id: HotKey.ask, keyCode: kVK_Space, modifiers: controlKey | optionKey) { [weak self] in self?.toggleBar() }
        let second = HotKeys.shared.register(id: HotKey.askToo, keyCode: kVK_ANSI_B, modifiers: controlKey | optionKey) { [weak self] in self?.toggleBar() }
        HotKeys.shared.register(id: HotKey.talk, keyCode: kVK_ANSI_V, modifiers: controlKey | optionKey) { [weak self] in self?.toggleVoice(showOnly: false) }
        HotKeys.shared.register(id: HotKey.talkDo, keyCode: kVK_ANSI_V, modifiers: controlKey | optionKey | shiftKey) { [weak self] in self?.toggleVoice(showOnly: true) }

        let screen = Capture.allowed()
        if !screen, !smoke { Capture.ask() }
        let events = Events.allowed(prompt: !smoke)
        log.show(activate: false)
        log.add("Bonsai assistant started", [
            "server \(client.base.absoluteString) · image \(settings.imageSide) px · API token \(Keychain.hasToken ? "stored in the Keychain" : "none")",
            "hotkey: control-option-space \(first ? "ready" : "NOT available"), control-option-B \(second ? "ready" : "NOT available"); or Ask… in the leaf menu",
            "Return in the bar does what is asked (a question is answered by pointing); Command-Return only points; Esc stops",
            "speak instead of typing: control-option-V starts and ends a spoken request (with shift: only point); speech is read by Argmax WhisperKit \(Voice.modelName), "
                + (Voice.localModel() == nil ? "NOT on disk yet (the first use downloads it)" : "on disk"),
            "Screen Recording: \(screen ? "allowed" : "NOT allowed yet for \(AppController.launcher); needed for everything")",
            "Accessibility: \(events ? "allowed" : "NOT allowed yet for \(AppController.launcher); needed to click and type")",
            "this log is also written to \(log.path)",
        ])
        installEditMenu()
        for number in [SIGINT, SIGTERM] {                 // Ctrl-C in Terminal quits properly, so things are put back
            signal(number, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: number, queue: .main)
            source.setEventHandler { [weak self] in self?.quitSoon() }
            source.resume()
            signals.append(source)
        }
        prepareSoon()
        if Voice.localModel() != nil {                    // have the speech model in memory before it is needed
            Task { try? await self.voice.prepare() }
        }
        watcher = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in self?.watch() }
        if smoke { runSmoke() }
    }

    private func runSmoke() {
        log.add("SMOKE RUN: windows shown once, no capture, no events, quits by itself")
        let frame = NSScreen.screens.first?.frame ?? .zero
        overlay.status("Bonsai assistant: start-up check")
        overlay.point(at: CGPoint(x: frame.width * 0.5, y: frame.height * 0.4), label: "start-up check: the pointer")
        overlay.drag(from: CGPoint(x: frame.width * 0.4, y: frame.height * 0.5), to: CGPoint(x: frame.width * 0.6, y: frame.height * 0.55), label: "start-up check: a drag")
        overlay.setLabel("start-up check: a longer label that wraps over more than one line to see the pill grow")
        bar.show(model: readiness)
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
            self?.bar.hide()
            self?.overlay.hideAll()
            self?.log.add("SMOKE RUN: overlay, pointer, drag line, label and input bar were shown and hidden")
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 40) { [weak self] in
            self?.log.add("SMOKE RUN: quitting; status was: \(self?.readiness ?? "")")
            self?.quitSoon()
        }
    }

    /// Quits from the run loop itself. Quitting from inside a block of the main queue would
    /// leave that queue busy while the app waits for the tidying-up that runs on it: a deadlock.
    private func quitSoon() {
        RunLoop.main.perform(inModes: [.common]) { NSApp.terminate(nil) }
        CFRunLoopWakeUp(CFRunLoopGetMain())
    }

    /// Every two seconds, when asked to: if the screen has settled on something that has not
    /// been read yet, have the server read it, so that the next request finds it read.
    private func watch() {
        guard settings.watchScreen, settings.readAhead, !settings.labLayout, ready, run == nil, !watching,
              !voice.listening, !bar.isShown, Capture.allowed() else { return }
        watching = true
        Task { @MainActor in
            defer { self.watching = false }
            guard let now = try? await Capture.mainDisplay() else { return }
            let previous = self.watched
            self.watched = now
            guard let previous else { return }
            let moving = await Task.detached { ImageOps.differingPixels(previous.full, now.full) }.value
            guard moving < ImageOps.sameScreenBelow else { return }                   // still changing: wait
            if let early = self.ahead {
                let stale = await Task.detached { ImageOps.differingPixels(early.sent.shot.full, now.full) }.value
                if stale < ImageOps.sameScreenBelow { return }                        // already read (or being read)
            }
            guard self.run == nil, !self.bar.isShown, !self.voice.listening else { return }
            self.startReadAhead(with: now)
        }
    }

    /// An accessory app shows no menu bar, but paste and friends in its dialogs need these items.
    private func installEditMenu() {
        let main = NSMenu()
        let editItem = NSMenuItem()
        let edit = NSMenu(title: "Edit")
        edit.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = edit
        main.addItem(editItem)
        NSApp.mainMenu = main
    }

    // MARK: LM Studio housekeeping: server up, one model loaded, things put back on quit

    private func setReadiness(_ text: String, ready isReady: Bool, _ details: [String] = []) {
        let changed = text != readiness
        readiness = text
        ready = isReady
        statusItem.button?.toolTip = text
        if changed { log.add(text, details) }
    }

    /// Runs the preparation after any that is still running.
    private func prepareSoon() {
        let previous = preparing
        preparations += 1
        let mine = preparations
        preparing = Task { @MainActor [weak self] in
            await previous?.value
            guard let self else { return }
            await self.prepare()
            if self.preparations == mine { self.preparing = nil }
            self.fillModelMenu()
        }
    }

    /// The model used when none was picked in the menu: a tuned Bonsai before one as shipped,
    /// the 4B before the 9B (the 9B takes about 11 s to read a screenshot on this laptop), and
    /// only models that can see when the server says which can. Looked at again on every check
    /// of the server, so a tuned 4B becomes the default the moment it is there. A model picked
    /// in the menu stays.
    private func chooseDefaultModel(from list: [String], seeing: [String] = []) {
        guard !list.isEmpty else { return }
        if settings.modelChosenByUser, list.contains(settings.model) { return }
        let pool = seeing.isEmpty ? list : seeing
        let lower = { (s: String) in s.lowercased() }
        let tuned = { (s: String) in lower(s).contains("bonsai") && ["point", "tuned", "action"].contains { lower(s).contains($0) } }
        let pick = pool.first { tuned($0) && lower($0).contains("4b") }
            ?? pool.first { tuned($0) && lower($0).contains("9b") }
            ?? pool.first { tuned($0) }
            ?? pool.first { lower($0).contains("bonsai") && lower($0).contains("9b") && !lower($0).contains("mlx") }
            ?? pool.first { lower($0).contains("bonsai") } ?? pool[0]
        if pick != settings.model {
            settings.model = pick
            settings.modelChosenByUser = false
        }
    }

    /// Makes the server answer and the chosen model loaded, and says in one line how it went.
    @MainActor private func prepare() async {
        var listed: [StudioModel]?
        do {
            listed = try await client.studioModels()
        } catch let e as LMError where e.kind == .notFound {
            // Not LM Studio (for example PrismML's llama-server): nothing to start or load.
            isStudio = false
            studio = []
            modelSees = true
            do {
                models = try await client.models()
                chooseDefaultModel(from: models)
                setReadiness(models.isEmpty ? "Server: it lists no model" : "Server ready (not LM Studio): \(settings.model)", ready: !models.isEmpty)
            } catch {
                setReadiness("Server: \(error)", ready: false)
            }
            return
        } catch let e as LMError where e.kind == .unreachable {
            guard client.isLocal, StudioCLI.exists else {
                setReadiness("Server: no answer from \(client.base.absoluteString)", ready: false)
                return
            }
            setReadiness("LM Studio: starting the server…", ready: false)
            let code = await StudioCLI.run(["server", "start", "--port", "\(client.base.port ?? 1234)"])
            for _ in 0..<40 where listed == nil {
                listed = try? await client.studioModels()
                if listed == nil { try? await Task.sleep(nanoseconds: 500_000_000) }
            }
            guard listed != nil else {
                setReadiness("LM Studio: the server did not start (lms server start gave \(code)); open LM Studio once and start it there", ready: false)
                return
            }
            startedServer = true
        } catch {
            setReadiness("LM Studio: \(error)", ready: false)
            return
        }
        isStudio = true
        studio = (listed ?? []).filter { $0.type == "llm" }
        models = studio.map(\.key)
        chooseDefaultModel(from: models, seeing: studio.filter { $0.vision == true }.map(\.key))
        guard let entry = studio.first(where: { $0.key == settings.model }) else {
            setReadiness("LM Studio: it has no language model", ready: false)
            return
        }
        if entry.loaded.isEmpty {
            // 16 GB: one model at a time. Free the memory first, and remember what was there.
            for other in studio where other.key != entry.key {
                for id in other.loaded {
                    setReadiness("LM Studio: unloading \(id) to make room…", ready: false)
                    guard (try? await client.studioUnload(id)) != nil else { continue }
                    if let i = loadedByApp.firstIndex(of: id) {
                        loadedByApp.remove(at: i)
                    } else {
                        displaced.append((other.key, other.contextLength ?? AppController.contextLength))
                    }
                }
            }
            setReadiness("LM Studio: loading \(entry.key)…", ready: false)
            do {
                let loaded = try await client.studioLoad(entry.key, contextLength: AppController.contextLength)
                loadedByApp.append(loaded.instance)
                displaced.removeAll { $0.key == entry.key }
                log.add("    loaded in \(sec(loaded.seconds)), context \(AppController.contextLength) tokens")
            } catch {
                setReadiness("LM Studio: \(error)", ready: false)
                return
            }
            if let again = try? await client.studioModels() { studio = again.filter { $0.type == "llm" } }
        }
        pipeline.model = entry.key
        modelSees = entry.vision == true
        var line = "LM Studio: ready, \(entry.key) loaded"
        if entry.vision != true { line += " — NO vision file beside it: answers about the screen will be guesses" }
        setReadiness(line, ready: true, [startedServer ? "the server was started by this app and is stopped on quit" : ""])
    }

    /// A light refresh of the model list for the menu; changes nothing on the server.
    @MainActor private func refreshList() async {
        guard preparing == nil, isStudio, let again = try? await client.studioModels() else { return }
        studio = again.filter { $0.type == "llm" }
        models = studio.map(\.key)
        fillModelMenu()
    }

    /// Waits for a preparation that is running (or starts one) and says whether a request can go.
    @MainActor private func makeReady(id: Int) async -> Bool {
        if !ready || preparing != nil {
            if preparing == nil { prepareSoon() }
            let wait = preparing
            let ticker = Task { @MainActor [weak self] in
                while !Task.isCancelled, let self, self.runID == id {         // Esc ends the waiting display too
                    self.overlay.status(self.readiness)
                    try? await Task.sleep(nanoseconds: 300_000_000)
                }
            }
            await wait?.value
            ticker.cancel()
            guard alive(id) else { return false }
            guard ready else {
                overlay.status("⚠︎ " + readiness)
                await linger(10, id: id)
                return false
            }
        }
        guard modelSees else {
            let text = "\(settings.model) cannot see the screen: LM Studio has no vision file beside it. Pick another model in the leaf menu."
            overlay.status("⚠︎ " + text)
            log.add("NO VISION", [text])
            await linger(10, id: id)
            return false
        }
        pipeline.model = settings.model
        pipeline.plainStepPrompt = settings.plainStepPrompt
        pipeline.separateImage = !settings.labLayout
        return true
    }

    /// On quit, unless "keep loaded" is ticked: unload what this app loaded, reload what it
    /// unloaded to make room, stop the server if this app started it.
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        stop(note: nil)
        let nothing = loadedByApp.isEmpty && displaced.isEmpty && !startedServer
        guard isStudio, !settings.keepLoaded, !nothing else {
            if settings.keepLoaded { log.add("Quit: the model stays loaded and the server keeps running (keep loaded is ticked)") }
            return .terminateNow
        }
        Task { @MainActor in
            await self.preparing?.value
            for id in self.loadedByApp {
                let ok = (try? await self.client.studioUnload(id)) != nil
                self.log.add("Quit: " + (ok ? "unloaded \(id)" : "could not unload \(id)"))
            }
            if self.startedServer {
                let code = await StudioCLI.run(["server", "stop"])
                self.log.add("Quit: stopped the server this app started (lms server stop gave \(code))")
            } else {
                for model in self.displaced {
                    let ok = (try? await self.client.studioLoad(model.key, contextLength: model.context)) != nil
                    self.log.add("Quit: " + (ok ? "loaded \(model.key) again, as it was before" : "could not load \(model.key) again"))
                }
            }
            NSApp.reply(toApplicationShouldTerminate: true)
        }
        return .terminateLater
    }

    // MARK: menu

    func menuNeedsUpdate(_ menu: NSMenu) {
        guard menu === statusItem.menu else { return }
        rebuild(menu)
        Task { @MainActor in await self.refreshList() }
    }

    private func item(_ title: String, _ action: Selector?, on: Bool? = nil) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
        item.target = self
        if let on { item.state = on ? .on : .off }
        return item
    }

    private func rebuild(_ menu: NSMenu) {
        menu.removeAllItems()
        let state = item(readiness, nil)
        state.isEnabled = false
        menu.addItem(state)
        menu.addItem(.separator())
        menu.addItem(item("Ask…   (control-option-space)", #selector(toggleBar)))
        menu.addItem(item(voice.listening ? "Listening… end the spoken request   (control-option-V)" : "Speak a request   (control-option-V)", #selector(talkFromMenu)))
        menu.addItem(item("Stop   (Esc)", #selector(stopFromMenu)))
        menu.addItem(.separator())
        let model = item("Model: " + (settings.model.isEmpty ? "none" : settings.model), nil)
        model.submenu = modelMenu
        fillModelMenu()
        menu.addItem(model)
        let size = item("Image size: \(settings.imageSide) px", nil)
        let sizes = NSMenu()
        for side in [1280, 896] {
            let s = item("\(side) px on the longer side", #selector(pickSize(_:)), on: settings.imageSide == side)
            s.tag = side
            sizes.addItem(s)
        }
        size.submenu = sizes
        menu.addItem(size)
        menu.addItem(item("Server address…", #selector(editServer)))
        menu.addItem(item("API token…   (\(Keychain.hasToken ? "stored in the Keychain" : "none"))", #selector(editToken)))
        menu.addItem(item("Keep the model loaded on quit", #selector(toggleKeep), on: settings.keepLoaded))
        menu.addItem(.separator())
        menu.addItem(item("Read the screen as soon as the bar opens", #selector(toggleReadAhead), on: settings.readAhead))
        menu.addItem(item("Keep the screen read in the background (answers in about a second; uses power)", #selector(toggleWatch), on: settings.watchScreen))
        menu.addItem(item("Lab prompt layout (every question reads the screen again)", #selector(toggleLab), on: settings.labLayout))
        menu.addItem(item("Answer in a sentence", #selector(toggleSentence), on: settings.sentence))
        menu.addItem(item("Speak the answer", #selector(toggleSpeak), on: settings.speak))
        menu.addItem(item("Run steps without asking (off: each step waits for Return)", #selector(toggleContinuous), on: settings.continuous))
        menu.addItem(item("Do it: plain step prompt (for step-trained models)", #selector(togglePlain), on: settings.plainStepPrompt))
        menu.addItem(.separator())
        menu.addItem(item("Show log", #selector(showLog)))
        menu.addItem(item("Check permissions", #selector(checkPermissions)))
        menu.addItem(.separator())
        menu.addItem(item("Quit", #selector(quit)))
    }

    private func fillModelMenu() {
        modelMenu.removeAllItems()
        if models.isEmpty {
            let none = item(preparing != nil ? "Asking the server…" : "No models (see the first line of the menu)", nil)
            none.isEnabled = false
            modelMenu.addItem(none)
        }
        for id in models {
            var title = id
            if let entry = studio.first(where: { $0.key == id }) {
                if entry.vision != true { title += "   (no vision file)" }
                if !entry.loaded.isEmpty { title += "   · loaded" }
            }
            let m = item(title, #selector(pickModel(_:)), on: id == settings.model)
            m.representedObject = id
            modelMenu.addItem(m)
        }
        modelMenu.addItem(.separator())
        modelMenu.addItem(item("Check the server again", #selector(refreshFromMenu)))
    }

    @objc private func toggleBar() {
        if bar.isShown {
            bar.hide()
        } else {
            bar.show(model: ready ? settings.model : readiness)
            startReadAhead()
        }
    }
    @objc private func talkFromMenu() { toggleVoice(showOnly: false) }
    @objc private func toggleReadAhead() { settings.readAhead.toggle() }
    @objc private func toggleWatch() {
        settings.watchScreen.toggle()
        log.add(settings.watchScreen ? "The screen is read in the background whenever it has changed and settled"
                                     : "The screen is read only when the bar opens or a request is made")
    }
    @objc private func toggleLab() {
        settings.labLayout.toggle()
        log.add(settings.labLayout ? "Prompt layout: screenshot and question in one message (as measured in the lab; no read is reused)"
                                   : "Prompt layout: the screenshot in its own message (its read is reused for further questions)")
    }

    // MARK: reading ahead

    /// Captures the screen now and has the server read it while the request is still being typed
    /// or spoken. Only with the screenshot in its own message: otherwise the read cannot be reused.
    private func startReadAhead(with shot: Shot? = nil) {
        guard ready, settings.readAhead, !settings.labLayout else { return }
        if shot == nil, settings.watchScreen, ahead != nil { return }       // the watcher keeps the read current
        ahead?.read.cancel()
        ahead = nil
        pipeline.model = settings.model
        pipeline.separateImage = true
        Task { @MainActor in
            guard let sent = try? await self.look(reuse: shot) else { return }
            let pipeline = self.pipeline
            let read = Task { () -> Double? in (try? await pipeline.readAhead(imageURL: sent.url))?.seconds }
            self.ahead = Ahead(sent: sent, started: Date(), read: read)
        }
    }

    /// The first look of a request: the screenshot that was read ahead if the screen still shows
    /// the same thing (waiting for that read to finish), a new capture otherwise.
    @MainActor private func firstLook(id: Int) async throws -> (sent: Sent, note: String?) {
        guard let early = ahead else { return (try await look(), nil) }
        ahead = nil
        let now = try await Capture.mainDisplay()
        let differing = await Task.detached { ImageOps.differingPixels(early.sent.shot.full, now.full) }.value
        guard differing < ImageOps.sameScreenBelow else {
            early.read.cancel()
            return (try await look(reuse: now), "the screen changed since it was read ahead (\(differing) differing pixels): read again")
        }
        let waitStart = Date()
        let seconds = await early.read.value
        let waited = Date().timeIntervalSince(waitStart)
        let lead = waitStart.timeIntervalSince(early.started)
        guard let seconds else { return (early.sent, "the read ahead failed; the screen is read now") }
        return (early.sent, "read ahead: started \(sec(lead)) before the request, took \(sec(seconds)), waited \(sec(waited)) for it")
    }

    // MARK: spoken requests (Argmax WhisperKit)

    /// control-option-V: the first press starts listening, the second ends it and asks.
    private func toggleVoice(showOnly: Bool) {
        if voice.listening {
            Task { @MainActor in await self.finishVoice() }
            return
        }
        stop(note: nil)
        voiceShowOnly = showOnly
        bar.hide()
        overlay.status(Voice.localModel() == nil ? "Getting the speech model (once, about 150 MB)…" : "Starting to listen…")
        HotKeys.shared.register(id: HotKey.escape, keyCode: kVK_Escape) { [weak self] in
            self?.voice.cancel()
            self?.stop(note: nil)
            self?.log.add("Spoken request cancelled")
        }
        Task { @MainActor in
            do {
                try await self.voice.start()
                self.overlay.status("Listening…   control-option-V again: \(showOnly ? "only point" : "do it")   ·   Esc: cancel")
                self.startReadAhead()
            } catch {
                self.overlay.status("⚠︎ \(error)")
                self.log.add("VOICE ERROR", ["\(error)"])
                HotKeys.shared.unregister(id: HotKey.escape)
                try? await Task.sleep(nanoseconds: 8_000_000_000)
                if !self.voice.listening && self.run == nil { self.overlay.hideAll() }
            }
        }
    }

    @MainActor private func finishVoice() async {
        overlay.status("Reading what you said…")
        do {
            let heard = try await voice.finish()
            log.add("VOICE  \"\(heard.text)\"", ["Argmax WhisperKit \(Voice.modelName): \(sec(heard.heard)) of sound read in \(sec(heard.seconds))"])
            guard !heard.text.isEmpty else {
                overlay.status("I heard nothing")
                HotKeys.shared.unregister(id: HotKey.escape)
                try? await Task.sleep(nanoseconds: 4_000_000_000)
                if run == nil { overlay.hideAll() }
                return
            }
            ask(heard.text, showOnly: voiceShowOnly)
        } catch {
            overlay.status("⚠︎ \(error)")
            log.add("VOICE ERROR", ["\(error)"])
            HotKeys.shared.unregister(id: HotKey.escape)
        }
    }
    @objc private func stopFromMenu() { stop(note: "Stopped from the menu") }
    @objc private func pickModel(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String else { return }
        guard id != settings.model || !ready else { return }
        stop(note: "Stopped: the model was changed")
        settings.model = id
        settings.modelChosenByUser = true
        log.add("Model: \(id)")
        ready = false
        prepareSoon()                               // unloads the previous model, loads this one
    }
    @objc private func pickSize(_ sender: NSMenuItem) {
        settings.imageSide = sender.tag
        log.add("Image size: \(sender.tag) px on the longer side")
    }
    @objc private func refreshFromMenu() { prepareSoon() }
    @objc private func toggleKeep() { settings.keepLoaded.toggle() }

    /// The token is typed here by the user, stored in the Keychain and nowhere else.
    @objc private func editToken() {
        let stored = Keychain.hasToken
        let alert = NSAlert()
        alert.messageText = "API token"
        alert.informativeText = "Only needed when LM Studio's server is set to require one (Developer > Server Settings > Manage Tokens). "
            + "It is kept in the macOS Keychain, sent with each request, and never written to the log. "
            + (stored ? "A token is stored now." : "No token is stored.")
        let field = NSSecureTextField(frame: CGRect(x: 0, y: 0, width: 320, height: 24))
        field.placeholderString = stored ? "a new token replaces the stored one" : "paste the token"
        alert.accessoryView = field
        alert.addButton(withTitle: "Save")
        alert.addButton(withTitle: "Cancel")
        if stored { alert.addButton(withTitle: "Remove the token") }
        NSApp.activate(ignoringOtherApps: true)
        alert.window.initialFirstResponder = field
        let choice = alert.runModal()
        if choice == .alertFirstButtonReturn {
            let typed = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !typed.isEmpty else { return }
            log.add(Keychain.set(typed) ? "API token stored in the Keychain" : "The API token could not be stored in the Keychain")
        } else if choice == .alertThirdButtonReturn {
            Keychain.set(nil)
            log.add("API token removed from the Keychain")
        } else {
            return
        }
        ready = false
        prepareSoon()
    }
    @objc private func toggleSentence() { settings.sentence.toggle() }
    @objc private func toggleSpeak() { settings.speak.toggle() }
    @objc private func toggleContinuous() {
        settings.continuous.toggle()
        log.add("Do it: " + (settings.continuous ? "steps run without asking (Esc stops)" : "each step waits for Return"))
    }
    @objc private func togglePlain() { settings.plainStepPrompt.toggle() }
    @objc private func showLog() { log.show(activate: true) }
    @objc private func quit() { NSApp.terminate(nil) }

    @objc private func checkPermissions() {
        let screen = Capture.allowed()
        if !screen { Capture.ask() }
        let events = Events.allowed(prompt: true)
        log.add("Permissions", ["Screen Recording: \(screen ? "allowed" : "NOT allowed; after allowing it, quit and start again")",
                                "Accessibility: \(events ? "allowed" : "NOT allowed for \(AppController.launcher); needed to click and type")"])
        log.show(activate: true)
    }

    @objc private func editServer() {
        let alert = NSAlert()
        alert.messageText = "Server address"
        alert.informativeText = "An OpenAI-compatible server. LM Studio's is http://localhost:1234/v1"
        let field = NSTextField(frame: CGRect(x: 0, y: 0, width: 320, height: 24))
        field.stringValue = settings.server
        alert.accessoryView = field
        alert.addButton(withTitle: "Save")
        alert.addButton(withTitle: "Cancel")
        NSApp.activate(ignoringOtherApps: true)
        alert.window.initialFirstResponder = field
        guard alert.runModal() == .alertFirstButtonReturn, let url = LMClient.url(from: field.stringValue) else { return }
        settings.server = url.absoluteString
        client.base = url
        log.add("Server address: \(url.absoluteString)")
        ready = false
        prepareSoon()
    }

    // MARK: starting and stopping a request

    /// A request from the bar or the microphone. A question is answered by pointing; anything
    /// else is carried out: straight away when it spells its steps out ("click …, then type …"),
    /// otherwise with the model planning one step at a time. `showOnly` never acts.
    private func ask(_ request: String, showOnly: Bool) {
        stop(note: nil)
        runID += 1
        let id = runID
        Events.cancelled = false
        HotKeys.shared.register(id: HotKey.escape, keyCode: kVK_Escape) { [weak self] in self?.stop(note: "Stopped with Esc") }
        run = Task { @MainActor [weak self] in
            guard let self, await self.makeReady(id: id) else { return }
            if showOnly || Commands.isQuestion(request) {
                await self.showMe(request, id: id)
            } else {
                await self.doIt(request, scripted: Commands.plan(request), id: id)
            }
        }
    }

    /// Esc: everything stops at once. Nothing more is asked, shown, spoken or done.
    private func stop(note: String?) {
        let wasRunning = run != nil
        run?.cancel()
        run = nil
        runID += 1
        Events.cancelled = true
        if let waiting = confirm {
            confirm = nil
            waiting.resume(returning: false)
        }
        speaker.stopSpeaking(at: .immediate)
        for id in [HotKey.escape, HotKey.ret, HotKey.enter] { HotKeys.shared.unregister(id: id) }
        overlay.hideAll()
        if let note, wasRunning { log.add(note) }
    }

    private func alive(_ id: Int) -> Bool { id == runID && !Task.isCancelled }

    /// Leaves the result on screen for a while, then clears it and gives Esc back to other apps.
    @MainActor private func linger(_ seconds: Double, id: Int) async {
        try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
        guard alive(id) else { return }
        HotKeys.shared.unregister(id: HotKey.escape)
        overlay.hideAll()
        run = nil
    }

    @MainActor private func fail(_ error: Error, id: Int) async {
        if error is CancellationError || !alive(id) { return }
        overlay.hidePointer()
        overlay.status("⚠︎ \(error)")
        log.add("ERROR", ["\(error)"])
        if error is LMError { ready = false }          // look at the server again before the next request
        await linger(9, id: id)
    }

    private func say(_ text: String) {
        guard settings.speak, !text.isEmpty else { return }
        speaker.speak(AVSpeechUtterance(string: text))
    }

    private func sec(_ x: Double) -> String { String(format: "%.2f s", x) }
    private func pt(_ p: CGPoint) -> String { String(format: "(%.1f, %.1f)", p.x, p.y) }
    private func grid(_ p: CGPoint) -> String { String(format: "(%.0f, %.0f)", p.x, p.y) }

    // MARK: looking

    private struct Sent {
        let shot: Shot
        let image: CGImage
        let url: String
        let seconds: Double                // shrinking and encoding
        var size: String { "\(image.width) x \(image.height) px" }
    }

    /// Captures the main display (or takes a capture already made) and prepares what is sent.
    @MainActor private func look(reuse: Shot? = nil) async throws -> Sent {
        if !Capture.allowed() { Capture.ask() }
        let shot: Shot
        if let reuse { shot = reuse } else { shot = try await Capture.mainDisplay() }
        let side = settings.imageSide
        let start = Date()
        let prepared: (CGImage, String)? = await Task.detached(priority: .userInitiated) {
            let small = ImageOps.shrunk(shot.full, longSide: side)
            guard let url = ImageOps.dataURL(small) else { return nil }
            return (small, url)
        }.value
        guard let prepared else { throw CaptureError(description: "The screenshot could not be encoded") }
        return Sent(shot: shot, image: prepared.0, url: prepared.1, seconds: Date().timeIntervalSince(start))
    }

    private func screenNote(_ sent: Sent) -> String {
        "image \(sent.size) of a \(Int(sent.shot.region.width)) x \(Int(sent.shot.region.height)) pt display (\(String(format: "%.1f", sent.shot.scale)) px per pt)"
    }

    // MARK: show me

    @MainActor private func showMe(_ request: String, id: Int) async {
        let start = Date()
        overlay.status("Looking…")
        do {
            overlay.status("\(pipeline.model) is reading the screen…")
            let (sent, aheadNote) = try await firstLook(id: id)
            guard alive(id) else { return }
            let out = try await pipeline.point(imageURL: sent.url, instruction: request)
            guard alive(id) else { return }
            let total = Date().timeIntervalSince(start)
            let timing = "capture \(sec(sent.shot.seconds)) · model \(sec(out.chat.seconds)) · total \(sec(total))"
            var lines = ["model \(pipeline.model) · \(screenNote(sent))",
                         "capture \(sec(sent.shot.seconds)) · shrink and encode \(sec(sent.seconds)) · model \(sec(out.chat.seconds)) (\(out.chat.tokenNote)) · total \(sec(total))",
                         "model wrote: \(out.chat.written)"]
            if let aheadNote { lines.append(aheadNote) }
            if let note = out.note { lines.append("note: \(note)") }

            guard let g = out.answer.point else {
                let refused = out.answer == .refusal
                lines.append(refused ? "the model says it is not on this screen" : "no point could be read from the answer")
                log.add("SHOW ME  \"\(request)\"", lines)
                overlay.hidePointer()
                overlay.status(refused ? "\(pipeline.model): that is not on this screen · \(timing)"
                                       : "\(pipeline.model) gave no point (\(out.chat.written.prefix(50))) · \(timing)")
                if refused { say("I can't find that on this screen.") }
                await linger(8, id: id)
                return
            }
            let p = Geometry.screenPoint(grid: g, region: sent.shot.region)
            lines.append("point: grid \(grid(g)) -> screen \(pt(p)) pt")
            log.add("SHOW ME  \"\(request)\"", lines)
            overlay.point(at: p, label: request)
            overlay.status("\(pipeline.model) · \(timing)")

            if settings.sentence {
                let answer = try await pipeline.sentence(imageURL: sent.url, request: request)
                guard alive(id) else { return }
                let text = answer.content.trimmingCharacters(in: .whitespacesAndNewlines)
                log.add("    sentence (\(sec(answer.seconds)), \(answer.tokenNote)): \(text.isEmpty ? answer.written : text)")
                if !text.isEmpty {
                    overlay.setLabel(text)
                    overlay.status("\(pipeline.model) · \(timing) · sentence \(sec(answer.seconds))")
                    say(text)
                }
            }
            await linger(14, id: id)
        } catch {
            await fail(error, id: id)
        }
    }

    // MARK: do it

    /// Waits for Return (true) or Esc (false). Return is a global hotkey only while this waits,
    /// so the app the step will act on keeps the keyboard.
    @MainActor private func waitForReturn() async -> Bool {
        HotKeys.shared.register(id: HotKey.ret, keyCode: kVK_Return) { [weak self] in self?.answer(true) }
        HotKeys.shared.register(id: HotKey.enter, keyCode: kVK_ANSI_KeypadEnter) { [weak self] in self?.answer(true) }
        let ok = await withCheckedContinuation { (c: CheckedContinuation<Bool, Never>) in confirm = c }
        HotKeys.shared.unregister(id: HotKey.ret)
        HotKeys.shared.unregister(id: HotKey.enter)
        return ok
    }

    private func answer(_ ok: Bool) {
        guard let waiting = confirm else { return }
        confirm = nil
        waiting.resume(returning: ok)
    }

    /// Shows a proposed step and waits for the go-ahead (or, in continuous running, a moment).
    @MainActor private func approve(_ title: String, timing: String, id: Int) async -> Bool {
        if settings.continuous {
            overlay.status("\(title)\n\(timing) · running without asking · Esc stops")
            try? await Task.sleep(nanoseconds: 900_000_000)
            return alive(id)
        }
        overlay.status("\(title)\nReturn: do it · Esc: cancel · \(timing)")
        let ok = await waitForReturn()
        return ok && alive(id)
    }

    /// Carries out one step through system events. `p` and `q` are screen points.
    @MainActor private func perform(_ step: Step, at p: CGPoint?, to q: CGPoint?) async {
        // The log window is left out of what the model sees, so a target can lie under it:
        // take it out of the way, or the click would land on the log.
        if let frame = log.frameOnScreen, let height = NSScreen.screens.first?.frame.height {
            let covered = [p, q].compactMap { $0 }.contains { frame.contains(Geometry.appKitPoint(quartz: $0, mainScreenHeight: height)) }
            if covered {
                log.hide()
                log.add("    (the log window was over the target and has been hidden; Show log in the leaf menu brings it back)")
                try? await Task.sleep(nanoseconds: 150_000_000)
            }
        }
        let combo = Keys.combo(step.keys)
        let pressesEscape = step.action == .key && combo?.keyCode == UInt16(kVK_Escape)
        if pressesEscape { HotKeys.shared.unregister(id: HotKey.escape) }       // or our own Esc would stop us
        await Task.detached(priority: .userInitiated) {
            switch step.action {
            case .click: if let p { Events.click(at: p) }
            case .double_click: if let p { Events.click(at: p, count: 2) }
            case .right_click: if let p { Events.click(at: p, right: true) }
            case .drag: if let p, let q { Events.drag(from: p, to: q) }
            case .type: Events.type(step.text ?? "")
            case .key: if let combo { Events.key(combo) }
            case .scroll: Events.scroll(step.direction ?? "down", at: p)
            case .done: break
            }
        }.value
        if pressesEscape {
            HotKeys.shared.register(id: HotKey.escape, keyCode: kVK_Escape) { [weak self] in self?.stop(note: "Stopped with Esc") }
        }
    }

    /// Asks where a target is on a prepared screenshot; logs the answer; returns the screen point.
    @MainActor private func find(_ target: String, url: String, region: CGRect, what: String) async throws -> (CGPoint?, Double) {
        let out = try await pipeline.point(imageURL: url, instruction: target)
        let p = out.answer.point.map { Geometry.screenPoint(grid: $0, region: region) }
        var line = "    \(what) \"\(target)\" (\(sec(out.chat.seconds)), \(out.chat.tokenNote)): model wrote \(out.chat.written)"
        if let g = out.answer.point, let p { line += " -> grid \(grid(g)) -> screen \(pt(p)) pt" } else { line += " -> NO POINT" }
        log.add(line, [out.note.map { "note: \($0)" } ?? ""])
        return (p, out.chat.seconds)
    }

    /// The screenshot a step works on: the one read ahead for the first look, a new one after.
    @MainActor private func stepLook(first: Bool, carried: Shot?, id: Int) async throws -> (Sent, String?) {
        if first { return try await firstLook(id: id) }
        return (try await look(reuse: carried), nil)
    }

    /// Carries a request out step by step. `scripted`: the steps the request itself spells out;
    /// without them the model is asked for the next step on every new screen.
    @MainActor private func doIt(_ goal: String, scripted: [Step]? = nil, id: Int) async {
        log.add("DO IT  \"\(goal)\"", [
            "model \(pipeline.model) · " + (scripted.map { "\($0.count) step(s) as asked: " + $0.map(\.historyLine).joined(separator: "; ") }
                                           ?? "the model plans, up to \(AppController.maxSteps) steps"),
            settings.continuous ? "steps run without asking (Esc stops)" : "each step waits for Return"])
        guard Events.allowed(prompt: true) else {
            let text = "To click and type, allow Accessibility for \(AppController.launcher): System Settings > Privacy & Security > Accessibility. Then ask again."
            overlay.status("⚠︎ " + text)
            log.add("NOT ALLOWED TO ACT", [text])
            await linger(14, id: id)
            return
        }
        var history: [String] = []
        var unusable = 0
        var carried: Shot?
        var queue = scripted
        var looked = false
        var ending = "Stopped after \(AppController.maxSteps) steps without the model saying done"
        do {
            steps: for n in 1...AppController.maxSteps {
                try Task.checkCancellation()
                overlay.hidePointer()
                let start = Date()
                var sent: Sent?
                var asked = 0.0
                let step: Step
                if var rest = queue {
                    guard !rest.isEmpty else {
                        ending = "Done (\(n - 1) step\(n == 2 ? "" : "s"))"
                        say("Done.")
                        break steps
                    }
                    step = rest.removeFirst()
                    queue = rest
                    var lines = ["step: \(step.historyLine)"]
                    if step.isClick || step.action == .drag || (step.action == .scroll && step.target != nil) {
                        overlay.status("Step \(n): \(step.historyLine)\n\(pipeline.model) is reading the screen…")
                        let look = try await stepLook(first: !looked, carried: carried, id: id)
                        looked = true
                        carried = nil
                        guard alive(id) else { return }
                        sent = look.0
                        lines.append("\(screenNote(look.0)) · capture \(sec(look.0.shot.seconds)) · shrink and encode \(sec(look.0.seconds))")
                        if let note = look.1 { lines.append(note) }
                    }
                    log.add("Step \(n) (as asked)", lines)
                } else {
                    overlay.status("Step \(n): \(pipeline.model) is reading the screen…")
                    let look = try await stepLook(first: !looked, carried: carried, id: id)
                    looked = true
                    carried = nil
                    sent = look.0
                    let out = try await pipeline.nextStep(imageURL: look.0.url, goal: goal, history: history)
                    guard alive(id) else { return }
                    asked = out.chat.seconds
                    var lines = ["\(screenNote(look.0)) · capture \(sec(look.0.shot.seconds)) · shrink and encode \(sec(look.0.seconds))",
                                 "step request (\(sec(out.chat.seconds)), \(out.chat.tokenNote)): model wrote \(out.chat.written)"]
                    if let note = look.1 { lines.append(note) }
                    if let note = out.note { lines.append("note: \(note)") }

                    guard let planned = out.step, planned.problem() == nil else {
                        lines.append("NOT USABLE as a step: " + (out.step?.problem() ?? "no action could be read"))
                        log.add("Step \(n)", lines)
                        unusable += 1
                        if unusable >= 2 {
                            ending = "Stopped: the model's answers could not be used as steps (see the log)"
                            break steps
                        }
                        try await Task.sleep(nanoseconds: 800_000_000)
                        continue
                    }
                    step = planned
                    lines.append("step: \(step.historyLine)")
                    log.add("Step \(n)", lines)

                    if step.action == .done {
                        let text = (step.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                        ending = "Done" + (text.isEmpty ? "" : ": \(text)") + " (\(n - 1) step\(n == 2 ? "" : "s"))"
                        say(text.isEmpty ? "Done." : text)
                        break steps
                    }
                }

                // where: a second request on the same screenshot, with the pointing prompt
                var p: CGPoint?, q: CGPoint?
                var pointing = 0.0
                if let sent, step.isClick || step.action == .drag || (step.action == .scroll && step.target != nil) {
                    let found = try await find(step.target ?? "", url: sent.url, region: sent.shot.region, what: "pointing at")
                    (p, pointing) = found
                    if step.action == .drag, let end = step.targetEnd {
                        let foundEnd = try await find(end, url: sent.url, region: sent.shot.region, what: "pointing at the end")
                        q = foundEnd.0
                        pointing += foundEnd.1
                    }
                    guard alive(id) else { return }
                    if (step.isClick && p == nil) || (step.action == .drag && (p == nil || q == nil)) {
                        ending = "Stopped at step \(n): the model could not point at \(step.target ?? "the target")"
                        break steps
                    }
                }

                let title = "Step \(n): \(step.historyLine)"
                let timing = (asked > 0 ? "step \(sec(asked)) · " : "") + (pointing > 0 ? "pointing \(sec(pointing)) · " : "") + "total \(sec(Date().timeIntervalSince(start)))"
                if step.action == .drag, let p, let q {
                    overlay.drag(from: p, to: q, label: step.historyLine)
                } else if let p {
                    overlay.point(at: p, label: step.historyLine)
                }
                guard await approve(title, timing: timing, id: id) else {
                    if alive(id) { stop(note: "Cancelled at step \(n)") }
                    return
                }
                guard Events.allowed(prompt: true) else {
                    ending = "Accessibility is not allowed for \(AppController.launcher): allow it in System Settings > Privacy & Security > Accessibility, then ask again"
                    break steps
                }
                overlay.status("\(title)\ndoing it…")
                await perform(step, at: p, to: q)
                guard alive(id) else { return }
                history.append(step.historyLine)
                log.add("    done: \(step.historyLine)" + (p.map { " at screen \(pt($0)) pt" } ?? ""))
                try await Task.sleep(nanoseconds: 900_000_000)                    // let the screen settle
                if !step.isClick { carried = nil }

                // After a click that changed nothing: one zoomed second look around the first point.
                // Not before typing: a click that only puts the caret in a field changes almost nothing.
                if step.isClick, let first = p, let target = step.target, let sent, queue?.first?.action != .type {
                    let after = try await Capture.mainDisplay()
                    let differing = await Task.detached { ImageOps.differingPixels(sent.shot.full, after.full) }.value
                    guard alive(id) else { return }
                    if differing >= ImageOps.unchangedBelow {
                        carried = after                                           // it is the next step's screenshot
                        continue
                    }
                    log.add("    the screen did not change after the click (\(differing) differing pixels): zoomed second look")
                    let window = Geometry.zoomWindow(around: first, in: after.region, zoom: AppController.zoom)
                    let pixels = Geometry.pixelRect(points: window, displayOrigin: after.region.origin, scale: after.scale)
                    let region = Geometry.pointsRect(pixels: pixels, displayOrigin: after.region.origin, scale: after.scale)
                    let url: String? = await Task.detached {
                        ImageOps.zoomed(after.full, pixelRect: pixels, longSide: AppController.zoomSide).flatMap { ImageOps.dataURL($0) }
                    }.value
                    guard let url else { continue }
                    overlay.status("\(title)\nnothing changed: looking closer…")
                    let (second, seconds) = try await find(target, url: url, region: region, what: "second look at")
                    guard alive(id) else { return }
                    guard let second, hypot(second.x - first.x, second.y - first.y) >= 3 else {
                        log.add("    the second look gives the same place; going on")
                        continue
                    }
                    overlay.point(at: second, label: "second look: \(step.historyLine)")
                    guard await approve("Step \(n), second look: \(step.historyLine)", timing: "pointing \(sec(seconds))", id: id) else {
                        if alive(id) { stop(note: "Cancelled at step \(n), second look") }
                        return
                    }
                    await perform(step, at: second, to: nil)
                    guard alive(id) else { return }
                    log.add("    done again at screen \(pt(second)) pt")
                    try await Task.sleep(nanoseconds: 900_000_000)
                }
            }
            guard alive(id) else { return }
            overlay.hidePointer()
            overlay.status(ending)
            log.add(ending)
            await linger(10, id: id)
        } catch {
            await fail(error, id: id)
        }
    }
}
