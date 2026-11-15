// Spoken requests, turned into text on the Mac itself by Argmax's WhisperKit (open-source SDK).
// Nothing leaves the machine: once the model is on disk it is loaded from there with the
// network switched off.
import AssistantCore
import Foundation
import WhisperKit

struct VoiceError: Error, CustomStringConvertible {
    let description: String
}

final class Voice {
    static let modelName = "base.en"                                          // about 150 MB
    /// Outside ~/Documents (the SDK's default place). Another
    /// folder can be named with --own-models, so the model can be copied in on another Mac.
    static let folder = Launch.ownModels ?? NSHomeDirectory() + "/Bonsai-demo/models/argmax"
    /// The sound file that stands in for the microphone, when one was given.
    static var micFile: String? { Launch.micFile }
    private var began = Date()
    private var fileSamples: [Float]?                                 // the sound file's samples, for the meter
    /// The loudest the meter has shown since listening began (0 to 1).
    private(set) var peak = 0.0

    /// How loud it is right now, from 0 to 1 (0 when not listening): the last tenth of a
    /// second of the recording; with a sound file in the microphone's place, the tenth of a
    /// second the file would be at by now.
    func level() -> Double {
        guard listening else { return 0 }
        var now = 0.0
        if let file = fileSamples {
            let at = min(file.count, Int(Date().timeIntervalSince(began) * 16000))
            now = PushToTalk.level(file[max(0, at - 1600)..<at])
        } else if let kit {
            now = PushToTalk.level(kit.audioProcessor.audioSamples.suffix(1600))
        }
        peak = max(peak, now)
        return now
    }

    private var kit: WhisperKit?
    private var loading: Task<WhisperKit, Error>?
    private(set) var listening = false

    /// The folder of the model if it is already on disk.
    static func localModel() -> String? {
        guard let walker = FileManager.default.enumerator(atPath: folder) else { return nil }
        for case let path as String in walker where path.hasSuffix("openai_whisper-" + modelName) {
            return folder + "/" + path
        }
        return nil
    }

    /// Loads the model: from disk when it is there, otherwise it is downloaded once.
    func prepare() async throws {
        if kit != nil { return }
        if loading == nil {
            loading = Task {
                try? FileManager.default.createDirectory(atPath: Voice.folder, withIntermediateDirectories: true)
                if let local = Voice.localModel() {
                    // Model and tokenizer both from our folder, nothing fetched. The tokenizer folder must
                    // be named: left out, the SDK looks under ~/Documents/huggingface and downloads it there.
                    return try await WhisperKit(WhisperKitConfig(model: Voice.modelName, modelFolder: local,
                                                                 tokenizerFolder: URL(fileURLWithPath: Voice.folder),
                                                                 verbose: false, logLevel: .error, download: false))
                }
                // Nothing is ever fetched with nobody at the keyboard: the folder is copied in instead.
                if Launch.unattended {
                    throw VoiceError(description: "the speech model is not in \(Voice.folder): copy the folder there (it is not downloaded unattended)")
                }
                return try await WhisperKit(WhisperKitConfig(model: Voice.modelName, downloadBase: URL(fileURLWithPath: Voice.folder),
                                                             verbose: false, logLevel: .error, download: true))
            }
        }
        do {
            kit = try await loading?.value
            loading = nil
        } catch {
            loading = nil
            throw VoiceError(description: "The speech model could not be loaded (\(error.localizedDescription)). "
                + "The first use downloads it (about 150 MB) and needs the network once.")
        }
    }

    private static let options = DecodingOptions(skipSpecialTokens: true, withoutTimestamps: true)

    private func text(of results: [TranscriptionResult]) -> String {
        results.map(\.text).joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Starts recording from the microphone (or, with a sound file given in its place, only
    /// notes that listening began: the file is what will be heard).
    func start() async throws {
        if let file = Voice.micFile {
            guard FileManager.default.fileExists(atPath: file) else {
                throw VoiceError(description: "The sound file given in place of the microphone does not exist: \(file)")
            }
            try await prepare()
            fileSamples = try? AudioProcessor.loadAudioAsFloatArray(fromPath: file)
            peak = 0
            began = Date()
            listening = true
            return
        }
        guard !Launch.unattended else {
            throw VoiceError(description: "The microphone is not used with nobody at the keyboard: give a sound file with --mic-file")
        }
        guard await AudioProcessor.requestRecordPermission() else {
            throw VoiceError(description: "The microphone is not allowed for the app this was started from (Terminal, or Claude if started in its "
                + "terminal panel): allow it in System Settings > Privacy & Security > Microphone")
        }
        try await prepare()
        guard let kit else { return }
        if listening { kit.audioProcessor.stopRecording() }               // a recording that was never ended
        try kit.audioProcessor.startRecordingLive(inputDeviceID: nil, callback: nil)
        fileSamples = nil
        peak = 0
        began = Date()
        listening = true
    }

    /// What was heard: the words, the seconds of sound, the seconds it took to read them, and
    /// the seconds of the sound that have a voice in them.
    typealias Heard = (text: String, heard: Double, seconds: Double, voiced: Double, peak: Double)

    /// Reads a recording. One with too little voice in it is not read at all (a speech model
    /// makes words out of silence), and comes back with no text.
    private func read(_ samples: [Float]) async throws -> Heard {
        let voiced = PushToTalk.voicedSeconds(samples)
        let length = Double(samples.count) / 16000
        let loudest = max(peak, PushToTalk.level(samples[...]))
        guard PushToTalk.caught(voiced: voiced), let kit else { return ("", length, 0, voiced, loudest) }
        let start = Date()
        let results: [TranscriptionResult] = try await kit.transcribe(audioArray: samples, decodeOptions: Voice.options)
        var words = PushToTalk.clean(text(of: results))
        // A short command ("Open Notes", under a second of sound) can come back as nothing:
        // the same clip with silence before and after it is read once more.
        if words.isEmpty, length < 3 {
            let again: [TranscriptionResult] = try await kit.transcribe(audioArray: PushToTalk.padded(samples, to: max(1.5, length + 1.0)), decodeOptions: Voice.options)
            words = PushToTalk.clean(text(of: again))
            paddedRead = true
        } else {
            paddedRead = false
        }
        return (words, length, Date().timeIntervalSince(start), voiced, loudest)
    }

    /// Stops recording and returns what was said.
    /// Whether the last clip was read a second time with silence around it.
    private(set) var paddedRead = false

    func finish() async throws -> Heard {
        guard listening, let kit else { return ("", 0, 0, 0, 0) }
        listening = false
        if let file = Voice.micFile { return try await read(try AudioProcessor.loadAudioAsFloatArray(fromPath: file)) }
        kit.audioProcessor.stopRecording()
        return try await read(Array(kit.audioProcessor.audioSamples))
    }

    /// True once something has been said and about 1.2 s of quiet has followed. (The SDK gives
    /// one loudness value per tenth of a second; above 0.3 counts as voice, as in its own examples.)
    var saidAndQuiet: Bool {
        if Voice.micFile != nil { return listening && Date().timeIntervalSince(began) > 1.0 }       // a file has no pauses to wait for
        guard listening, let kit else { return false }
        let loudness = kit.audioProcessor.relativeEnergy
        guard loudness.count >= 14, loudness.contains(where: { $0 > 0.3 }) else { return false }
        return loudness.suffix(12).allSatisfy { $0 < 0.3 }
    }

    func cancel() {
        guard listening else { return }
        listening = false
        if Voice.micFile == nil { kit?.audioProcessor.stopRecording() }
    }

    /// What is said in a recording and when: the speech model's stretches of speech with
    /// their times, for subtitles. `samples`: one channel, 16,000 a second.
    func captions(_ samples: [Float]) async throws -> [Subtitle] {
        try await prepare()
        guard let kit else { return [] }
        let options = DecodingOptions(skipSpecialTokens: true, withoutTimestamps: false)
        let results: [TranscriptionResult] = try await kit.transcribe(audioArray: samples, decodeOptions: options)
        return results.flatMap(\.segments).map { Subtitle(start: Double($0.start), end: Double($0.end), text: Subtitles.clean($0.text)) }.filter { !$0.text.isEmpty }
    }

    /// A sound file as text, read the same way as a recording (for checking the speech model
    /// without a microphone, and for a batch run's --voice-file).
    func transcribe(file: String) async throws -> Heard {
        guard FileManager.default.fileExists(atPath: file) else { throw VoiceError(description: "There is no sound file at \(file)") }
        try await prepare()
        return try await read(try AudioProcessor.loadAudioAsFloatArray(fromPath: file))
    }
}
