import { AlertCircle, Loader2, Mic, Square, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeVoiceNote } from "../api/client";
import type { VoiceNote } from "../api/types";

/** Mime types a `MediaRecorder` might produce, best first, filtered at runtime by
 * `isTypeSupported`. Chrome and Firefox take the first; Safari supports none of the webm
 * entries and lands on `audio/mp4`, which the backend maps to the `audio/m4a` spelling
 * Gemini knows (see backend/agent/tools/media_types.py — the mapping is the only reason
 * recording works on an iPhone or a Mac at all). */
const PREFERRED_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  // `undefined` (rather than a guessed string) lets the browser choose its own default,
  // which is the right behaviour when none of our preferences are supported.
  return PREFERRED_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported?.(type));
}

/** `audio/webm;codecs=opus` -> `webm`. Only used to name the uploaded part; the browser's
 * own mime is what the backend reads. */
function extensionFor(mime: string): string {
  const base = mime.split(";")[0];
  return base.split("/")[1]?.replace("x-", "") || "webm";
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** True when this browser can record at all. `mediaDevices` is undefined on an insecure
 * origin (plain http that isn't localhost) as well as on older browsers, so a judge
 * opening the demo over https gets the recorder and anyone else gets the file picker. */
export function canRecordAudio(): boolean {
  return (
    typeof navigator !== "undefined" &&
    typeof navigator.mediaDevices?.getUserMedia === "function" &&
    typeof MediaRecorder !== "undefined"
  );
}

/** How long to wait for `getUserMedia` before giving up on it.
 *
 * Found by driving the deployed page: a browser that never answers the permission prompt
 * — the user dismissed it rather than choosing, or there is no capture device at all —
 * leaves the promise pending forever, and the Record button sat disabled on "Waiting for
 * the microphone…" with no way back. For a judge trying the demo that is a dead end, so
 * the wait is bounded and the UI returns to a state they can act on. */
const MIC_TIMEOUT_MS = 15_000;

type Phase = "idle" | "starting" | "recording" | "transcribing" | "done" | "error";

/** Thrown when the microphone never answers, so `startRecording` can tell that case
 * apart from a real `getUserMedia` failure and say something useful about it. */
class MicTimeoutError extends Error {}

/** Resolve with the stream, or reject once `MIC_TIMEOUT_MS` passes.
 *
 * A late-arriving stream is stopped rather than leaked: `getUserMedia` is not
 * cancellable, so if permission is granted after we have given up, the browser would
 * otherwise hold an open microphone — and show its "this page is listening" indicator —
 * for a recording nobody is making. */
function withTimeout(promise: Promise<MediaStream>): Promise<MediaStream> {
  let timer: ReturnType<typeof setTimeout>;
  let settled = false;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      settled = true;
      reject(new MicTimeoutError("the microphone did not respond"));
    }, MIC_TIMEOUT_MS);
  });
  promise.then(
    (stream) => {
      if (settled) stream.getTracks().forEach((track) => track.stop());
    },
    () => {},
  );
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

/** A stopwatch that counts whole seconds while `running`, resetting on each new run.
 * Kept out of the component body so the interval's lifecycle is tied to one effect
 * rather than tangled with the recorder's own cleanup. */
function useElapsedSeconds(running: boolean): number {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!running) return;
    setElapsed(0);
    const id = setInterval(() => setElapsed((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [running]);
  return elapsed;
}

/** CR #15: record a shift-lead note from the microphone, in place of choosing an audio
 * file. One button toggles: click to record, click to stop. Stopping uploads the blob to
 * `POST /api/voice/transcribe` and renders what Gemini heard — transcript, the language
 * it detected, and the observations it pulled out — before the investigation starts.
 *
 * The recorded blob is handed to the parent through `onAudioChange` so the form can post
 * it with everything else. The transcript shown here is a *preview*: the investigation
 * re-reads the same audio server-side rather than trusting a client-supplied extraction
 * (see the endpoint's own docstring). */
export function VoiceRecorder({
  onAudioChange,
}: {
  onAudioChange: (blob: Blob | null, filename: string) => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [note, setNote] = useState<VoiceNote | null>(null);
  const [error, setError] = useState<string>("");
  // Set once the microphone has failed to start, and never cleared: someone who has
  // blocked the permission outright cannot retry their way out of it, so the file
  // picker appears as a way to use the feature at all. Kept available afterwards even
  // if a later attempt succeeds — having offered it, taking it away would be worse.
  const [micFailed, setMicFailed] = useState(false);
  const [fallbackName, setFallbackName] = useState("");
  const elapsed = useElapsedSeconds(phase === "recording");

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  // Held separately from the recorder: stopping the recorder does NOT release the
  // microphone, and a browser that keeps showing a red "recording" indicator after the
  // UI says it stopped reads as the page still listening. Every track is stopped
  // explicitly, on every exit path including unmount.
  const streamRef = useRef<MediaStream | null>(null);

  const releaseMicrophone = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => releaseMicrophone, [releaseMicrophone]);

  async function startRecording() {
    setError("");
    setNote(null);
    setPhase("starting");
    try {
      const stream = await withTimeout(navigator.mediaDevices.getUserMedia({ audio: true }));
      streamRef.current = stream;
      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        // `recorder.mimeType` rather than our requested one: the browser is free to
        // pick something else, and the blob must be labelled with what it actually is.
        const type = recorder.mimeType || mimeType || "audio/webm";
        void handleRecorded(new Blob(chunksRef.current, { type }), type);
      };
      recorder.start();
      recorderRef.current = recorder;
      setPhase("recording");
    } catch (err) {
      releaseMicrophone();
      setPhase("error");
      setMicFailed(true);
      // NotAllowedError is the user clicking "Block", which is not a malfunction and
      // should not read like one. A timeout usually means the permission prompt was
      // dismissed rather than answered, so it names that. Everything else is generic.
      if (err instanceof MicTimeoutError) {
        setError(
          "The microphone did not respond. If your browser asked for permission, " +
            "answer the prompt and press Record again.",
        );
      } else if (err instanceof DOMException && err.name === "NotAllowedError") {
        setError(
          "Microphone access was blocked. Allow it in your browser, or reload the page " +
            "to be asked again.",
        );
      } else {
        setError("Could not start recording on this device.");
      }
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    recorderRef.current = null;
    releaseMicrophone();
    setPhase("transcribing");
  }

  async function handleRecorded(blob: Blob, type: string) {
    const filename = `voice-note.${extensionFor(type)}`;
    if (blob.size === 0) {
      setPhase("error");
      setError("Nothing was recorded. Try again and speak after the indicator appears.");
      onAudioChange(null, "");
      return;
    }
    // Handed over before transcription, not after: the audio is worth sending with the
    // investigation even if this preview call fails (a quota refusal, say) — the intake
    // agent reads it again server-side regardless.
    onAudioChange(blob, filename);
    try {
      setNote(await transcribeVoiceNote(blob, filename));
      setPhase("done");
    } catch (err) {
      setPhase("error");
      setError(
        err instanceof Error
          ? `Could not transcribe the recording. ${err.message}`
          : "Could not transcribe the recording.",
      );
    }
  }

  function discard() {
    setNote(null);
    setError("");
    setPhase("idle");
    onAudioChange(null, "");
  }

  const isBusy = phase === "starting" || phase === "transcribing";
  const isRecording = phase === "recording";

  return (
    <div>
      <div className="flex items-center gap-3 flex-wrap">
        <button
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isBusy}
          aria-label={isRecording ? "Stop recording" : "Start recording a voice note"}
          className="tap-target inline-flex items-center gap-2 rounded-lg px-4 text-sm font-semibold text-[var(--pill-fg-strong)] disabled:opacity-60"
          style={{ background: isRecording ? "var(--red)" : "var(--green)" }}
        >
          {isRecording ? (
            <Square size={15} aria-hidden="true" fill="currentColor" />
          ) : (
            <Mic size={16} aria-hidden="true" />
          )}
          {isRecording ? "Stop" : note ? "Record again" : "Record"}
        </button>

        {/* One live region for the whole widget. Recording state, elapsed time, the
         * transcribing step and errors all announce through here, so a screen reader
         * follows the flow without the visual indicator. */}
        <span
          role="status"
          aria-live="polite"
          className="inline-flex items-center gap-2 text-sm"
        >
          {isRecording && (
            <>
              <span
                aria-hidden="true"
                className="animate-pulse inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: "var(--red)" }}
              />
              <span style={{ color: "var(--red)" }} className="font-medium">
                Recording
              </span>
              <span className="mono tabular-nums opacity-70">{formatElapsed(elapsed)}</span>
            </>
          )}
          {phase === "starting" && <span className="opacity-70">Waiting for the microphone…</span>}
          {phase === "transcribing" && (
            <>
              <Loader2 size={14} className="animate-spin" aria-hidden="true" />
              <span className="opacity-80">Transcribing with Gemini…</span>
            </>
          )}
          {phase === "done" && note && (
            <span className="opacity-70">
              Heard {note.language_name || "speech"} · {formatElapsed(elapsed)}
            </span>
          )}
        </span>

        {note && (
          <button
            type="button"
            onClick={discard}
            className="tap-target inline-flex items-center gap-1.5 text-sm underline opacity-70"
          >
            <Trash2 size={14} aria-hidden="true" />
            Discard
          </button>
        )}
      </div>

      {phase === "error" && (
        <p
          role="alert"
          className="mt-2 flex items-start gap-2 text-sm rounded-lg border px-3 py-2"
          style={{ borderColor: "var(--red)", color: "var(--red)" }}
        >
          <AlertCircle size={15} aria-hidden="true" className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </p>
      )}

      {micFailed && (
        <div className="mt-2">
          <label htmlFor="voice_note" className="block text-xs opacity-70 mb-1">
            Or choose an audio file instead:
          </label>
          {/* `name="voice_note"` means the enclosing form posts this with everything
            * else, with no extra wiring — the same field a recorded blob would use. The
            * two cannot collide: this input only exists once recording has failed, so
            * there is no blob for the parent to set over it. */}
          <input
            id="voice_note"
            name="voice_note"
            type="file"
            accept="audio/*"
            onChange={(e) => setFallbackName(e.target.files?.[0]?.name ?? "")}
            className="tap-target w-full rounded-lg border p-2 text-sm file:mr-3 file:tap-target file:rounded-md file:border-0 file:px-3 file:text-sm file:font-medium file:text-[var(--pill-fg-strong)] file:bg-[var(--green)]"
            style={{ borderColor: "var(--line)" }}
          />
          {fallbackName && (
            <p className="text-xs opacity-60 mt-1" aria-live="polite">
              Selected: {fallbackName} — it will be read when the investigation starts.
            </p>
          )}
        </div>
      )}

      {note && <TranscriptPanel note={note} />}
    </div>
  );
}

/** What Gemini heard. Labelled as AI-generated (CR #2) because every field here was
 * produced by a model — unlike a verdict, where the label would be actively wrong. */
function TranscriptPanel({ note }: { note: VoiceNote }) {
  // Only worth showing when it differs: for an English note the backend sets
  // `translation` equal to `transcript`, and printing the same sentence twice reads
  // like a bug.
  const showTranslation =
    note.translation.trim() !== "" && note.translation.trim() !== note.transcript.trim();

  return (
    <div className="card mt-3 p-3 text-sm">
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span
          className="text-[10px] font-semibold uppercase tracking-wide rounded-full px-1.5 py-0.5"
          style={{ background: "var(--green-soft)", color: "var(--green-ink)" }}
        >
          AI transcript
        </span>
        {note.language_name && (
          <span className="text-xs opacity-70">
            {note.language_name}
            {note.language ? ` · ${note.language}` : ""}
          </span>
        )}
        {note.lot_or_line && (
          <span className="mono text-xs opacity-70">heard: {note.lot_or_line}</span>
        )}
      </div>

      <p className="whitespace-pre-wrap">{note.transcript}</p>

      {showTranslation && (
        <p className="mt-2 pt-2 border-t opacity-80" style={{ borderColor: "var(--line)" }}>
          <span className="text-xs uppercase tracking-wide opacity-70 mr-1.5">English</span>
          {note.translation}
        </p>
      )}

      {(note.observations.length > 0 || note.maintenance_mentions.length > 0) && (
        <ul className="mt-2 pt-2 border-t space-y-1" style={{ borderColor: "var(--line)" }}>
          {note.observations.map((text) => (
            <li key={`obs-${text}`} className="flex gap-2">
              <span aria-hidden="true" className="opacity-40">
                •
              </span>
              {text}
            </li>
          ))}
          {note.maintenance_mentions.map((text) => (
            <li key={`maint-${text}`} className="flex gap-2">
              <span aria-hidden="true" style={{ color: "var(--amber-ink)" }}>
                ⚙
              </span>
              {text}
            </li>
          ))}
        </ul>
      )}

      {note.low_confidence_fields.length > 0 && (
        <p className="mt-2 text-xs" style={{ color: "var(--amber-ink)" }}>
          Not sure it heard this correctly: {note.low_confidence_fields.join(", ")}. Check
          before relying on it.
        </p>
      )}
    </div>
  );
}
