import { useState } from "react";
import { USE_MOCKS } from "../api/client";
import { getDemoCode, setDemoCode } from "../api/demoCode";

/** Blocks the app behind the demo access code until a correct one is entered, then
 * remembers it in sessionStorage for the rest of the tab's life (see demoCode.ts).
 * No-ops in mock mode (USE_MOCKS=true) — there is no real backend to check against,
 * and local development must stay unaffected per CLAUDE.md / the deploy plan.
 *
 * Verifies the code by calling a real gated endpoint (GET /api/complaints) rather
 * than trusting the input blindly: DEMO_ACCESS_CODE may be unset on the server (the
 * check is then disabled entirely on the backend), in which case any input — even
 * an empty one — correctly unlocks the gate, matching the server's own behaviour.
 */
export function AccessGate({ children }: { children: React.ReactNode }) {
  const [unlocked, setUnlocked] = useState(() => USE_MOCKS || !!getDemoCode());
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  if (unlocked) return <>{children}</>;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setChecking(true);
    setError(null);
    try {
      const base = import.meta.env.VITE_API_URL ?? "";
      const res = await fetch(`${base}/api/complaints`, {
        headers: { "X-Demo-Code": code },
      });
      if (!res.ok) throw new Error("rejected");
      setDemoCode(code);
      setUnlocked(true);
    } catch {
      setError("That code didn't work. Check it and try again.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: "var(--paper)", color: "var(--ink)" }}
    >
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-xl border p-6 flex flex-col gap-4"
        style={{ background: "var(--card)", borderColor: "var(--line)" }}
      >
        <div>
          <h1 className="text-lg font-semibold">8D Copilot</h1>
          <p className="text-sm opacity-70 mt-1">Enter the demo access code to continue.</p>
        </div>
        <label className="flex flex-col gap-1 text-sm">
          <span className="sr-only">Access code</span>
          <input
            type="password"
            inputMode="text"
            autoFocus
            autoComplete="off"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Access code"
            className="rounded-md border px-3 py-2 text-sm"
            style={{ borderColor: "var(--line)", background: "var(--paper)", color: "var(--ink)" }}
          />
        </label>
        {error && (
          <p role="alert" className="text-sm" style={{ color: "var(--red)" }}>
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={checking || !code}
          className="rounded-md px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          style={{ background: "var(--green)" }}
        >
          {checking ? "Checking…" : "Continue"}
        </button>
      </form>
    </div>
  );
}
