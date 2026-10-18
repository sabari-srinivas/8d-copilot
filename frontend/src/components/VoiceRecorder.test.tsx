import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { VoiceNote } from "../api/types";

const transcribeVoiceNote = vi.fn();
vi.mock("../api/client", () => ({
  transcribeVoiceNote: (...args: unknown[]) => transcribeVoiceNote(...args),
}));

const NOTE: VoiceNote = {
  language: "ta-IN",
  language_name: "Tamil",
  transcript: "ரெண்டாவது லைன்ல ப்ரிட்ஜிங்",
  translation: "Bridging on line two",
  lot_or_line: "line 2",
  observations: ["Bridging recurring on line 2"],
  maintenance_mentions: ["Vendor attended the oven on Wednesday"],
  low_confidence_fields: [],
};

/** A `MediaRecorder` stand-in with manual control over when data and `onstop` fire —
 * jsdom has no media stack at all, so every test here drives this by hand. */
class FakeMediaRecorder {
  static instances: FakeMediaRecorder[] = [];
  static supported = ["audio/webm;codecs=opus"];
  static isTypeSupported = (type: string) => FakeMediaRecorder.supported.includes(type);

  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  state = "inactive";

  // Declared as fields and assigned in the body rather than as constructor parameter
  // properties: the build runs with `erasableSyntaxOnly`, which rejects that shorthand.
  stream: MediaStream;
  options?: { mimeType?: string };

  constructor(stream: MediaStream, options?: { mimeType?: string }) {
    this.stream = stream;
    this.options = options;
    FakeMediaRecorder.instances.push(this);
  }

  get mimeType() {
    return this.options?.mimeType ?? "audio/webm";
  }

  start() {
    this.state = "recording";
  }

  /** What a real recorder does on `.stop()`: flush a chunk, then fire `onstop`. */
  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["audio-bytes"], { type: this.mimeType }) });
    this.onstop?.();
  }

  /** Stop with no chunk ever delivered — a recording ended before the mic produced
   * anything, which yields a zero-byte blob. */
  stopWithNoData() {
    this.state = "inactive";
    this.onstop?.();
  }
}

const stopTrack = vi.fn();

function installMediaStack({ getUserMedia }: { getUserMedia?: ReturnType<typeof vi.fn> } = {}) {
  const stream = { getTracks: () => [{ stop: stopTrack }] } as unknown as MediaStream;
  // Only supply the default when the caller did not bring its own: overriding a
  // caller-supplied mock with `mockResolvedValue` here silently turned the
  // permission-denied test into a successful-recording test.
  const fn = getUserMedia ?? vi.fn().mockResolvedValue(stream);
  vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
  vi.stubGlobal("navigator", { ...navigator, mediaDevices: { getUserMedia: fn } });
  return { getUserMedia: fn, stream };
}

async function importRecorder() {
  // Imported after the globals are stubbed: `canRecordAudio` reads `navigator` at call
  // time, but the module must still see the stubbed MediaRecorder on first evaluation.
  return await import("./VoiceRecorder");
}

const recorder = () => FakeMediaRecorder.instances.at(-1)!;

beforeEach(() => {
  FakeMediaRecorder.instances = [];
  FakeMediaRecorder.supported = ["audio/webm;codecs=opus"];
  transcribeVoiceNote.mockReset().mockResolvedValue(NOTE);
  stopTrack.mockReset();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("VoiceRecorder", () => {
  it("records on the first click and stops on the second — one toggling button", async () => {
    installMediaStack();
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));

    // Recording is announced in words, not only by the colour of a dot.
    expect(await screen.findByText("Recording")).toBeTruthy();
    const stop = screen.getByRole("button", { name: /stop recording/i });

    fireEvent.click(stop);
    expect(await screen.findByText(/transcribing with gemini/i)).toBeTruthy();
  });

  it("shows the transcribing step before the transcript, not instead of it", async () => {
    installMediaStack();
    // Hold the call open so the intermediate state is observable rather than raced past.
    let resolve: (n: VoiceNote) => void = () => {};
    transcribeVoiceNote.mockReturnValue(new Promise<VoiceNote>((r) => (resolve = r)));
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");
    fireEvent.click(screen.getByRole("button", { name: /stop recording/i }));

    expect(await screen.findByText(/transcribing with gemini/i)).toBeTruthy();
    expect(screen.queryByText(NOTE.transcript)).toBeNull();

    resolve(NOTE);
    expect(await screen.findByText(NOTE.transcript)).toBeTruthy();
    expect(screen.queryByText(/transcribing with gemini/i)).toBeNull();
  });

  it("renders the transcript, the English translation and what it extracted", async () => {
    installMediaStack();
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");
    fireEvent.click(screen.getByRole("button", { name: /stop recording/i }));

    expect(await screen.findByText(NOTE.transcript)).toBeTruthy();
    expect(screen.getByText(/Bridging on line two/)).toBeTruthy();
    // Named in two places on purpose — the status line ("Heard Tamil") and the panel's
    // own label — so this matches all of them rather than asserting a single node.
    expect(screen.getAllByText(/Tamil/).length).toBeGreaterThan(0);
    expect(screen.getByText(NOTE.observations[0])).toBeTruthy();
    expect(screen.getByText(NOTE.maintenance_mentions[0])).toBeTruthy();
    // CR #2: model-produced text says so. A verdict must never carry this label; a
    // transcript always must.
    expect(screen.getByText("AI transcript")).toBeTruthy();
  });

  it("hands the recorded blob to the form under a name matching the recorded type", async () => {
    installMediaStack();
    const onAudioChange = vi.fn();
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={onAudioChange} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");
    fireEvent.click(screen.getByRole("button", { name: /stop recording/i }));

    await waitFor(() => expect(onAudioChange).toHaveBeenCalled());
    const [blob, filename] = onAudioChange.mock.calls[0];
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.size).toBeGreaterThan(0);
    expect(filename).toBe("voice-note.webm");
  });

  it("still hands over the audio when transcription fails", async () => {
    installMediaStack();
    transcribeVoiceNote.mockRejectedValue(new Error("429 Too Many Requests"));
    const onAudioChange = vi.fn();
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={onAudioChange} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");
    fireEvent.click(screen.getByRole("button", { name: /stop recording/i }));

    // The preview is a convenience; the investigation re-reads the audio server-side, so
    // a quota refusal here must not silently drop the recording from the submission.
    await waitFor(() => expect(onAudioChange).toHaveBeenCalledWith(expect.any(Blob), "voice-note.webm"));
    expect((await screen.findByRole("alert")).textContent).toMatch(/could not transcribe/i);
  });

  it("releases the microphone when recording stops", async () => {
    installMediaStack();
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");
    fireEvent.click(screen.getByRole("button", { name: /stop recording/i }));

    // Stopping the recorder does NOT release the mic; the tracks must be stopped
    // explicitly or the browser keeps showing its "this page is listening" indicator.
    expect(stopTrack).toHaveBeenCalled();
  });

  it("releases the microphone if the page is left mid-recording", async () => {
    installMediaStack();
    const { VoiceRecorder } = await importRecorder();
    const { unmount } = render(<VoiceRecorder onAudioChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");
    unmount();

    expect(stopTrack).toHaveBeenCalled();
  });

  it("explains a blocked microphone as a permission choice, not a malfunction", async () => {
    const getUserMedia = vi.fn().mockRejectedValue(
      new DOMException("denied", "NotAllowedError"),
    );
    installMediaStack({ getUserMedia });
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/blocked/i);
    expect(transcribeVoiceNote).not.toHaveBeenCalled();
  });

  it("reports an empty recording instead of posting a zero-byte blob", async () => {
    installMediaStack();
    const onAudioChange = vi.fn();
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={onAudioChange} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");
    recorder().stopWithNoData();

    expect((await screen.findByRole("alert")).textContent).toMatch(/nothing was recorded/i);
    expect(transcribeVoiceNote).not.toHaveBeenCalled();
    expect(onAudioChange).toHaveBeenLastCalledWith(null, "");
  });

  it("discarding clears both the transcript and the audio held for the form", async () => {
    installMediaStack();
    const onAudioChange = vi.fn();
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={onAudioChange} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");
    fireEvent.click(screen.getByRole("button", { name: /stop recording/i }));
    await screen.findByText(NOTE.transcript);

    fireEvent.click(screen.getByRole("button", { name: /discard/i }));

    expect(screen.queryByText(NOTE.transcript)).toBeNull();
    expect(onAudioChange).toHaveBeenLastCalledWith(null, "");
  });

  it("falls back to the browser's own choice when no preferred codec is supported", async () => {
    FakeMediaRecorder.supported = [];
    installMediaStack();
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");

    // No mimeType forced — a browser that supports none of our preferences must be left
    // to pick its own rather than handed a string it will reject.
    expect(recorder().options).toBeUndefined();
  });

  it("picks Safari's audio/mp4 when the webm options are unavailable", async () => {
    FakeMediaRecorder.supported = ["audio/mp4"];
    installMediaStack();
    const { VoiceRecorder } = await importRecorder();
    render(<VoiceRecorder onAudioChange={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    await screen.findByText("Recording");

    expect(recorder().options?.mimeType).toBe("audio/mp4");
  });
});

describe("canRecordAudio", () => {
  it("is false where there is no media stack, so the form can offer a file picker", async () => {
    vi.stubGlobal("navigator", { ...navigator, mediaDevices: undefined });
    vi.stubGlobal("MediaRecorder", undefined);
    const { canRecordAudio } = await importRecorder();
    expect(canRecordAudio()).toBe(false);
  });

  it("is true once getUserMedia and MediaRecorder both exist", async () => {
    installMediaStack();
    const { canRecordAudio } = await importRecorder();
    expect(canRecordAudio()).toBe(true);
  });
});
