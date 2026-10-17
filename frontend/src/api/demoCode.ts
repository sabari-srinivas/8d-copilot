/** The demo access code, stored for the tab's lifetime only (sessionStorage, not
 * localStorage) — a judge re-opening the link tomorrow should see the gate again,
 * not a code cached from today. Backend enforcement lives in
 * backend/agent/main.py's require_demo_code middleware; this module is just where
 * the frontend keeps the value once the gate screen has verified it. */
const KEY = "demo_code";

export function getDemoCode(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    // Storage can throw in locked-down embeds (private mode, iframes with storage
    // blocked) — degrade to "no code", which just means the gate re-asks.
    return null;
  }
}

export function setDemoCode(code: string): void {
  try {
    sessionStorage.setItem(KEY, code);
  } catch {
    // Non-fatal — see getDemoCode above.
  }
}

export function clearDemoCode(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // Non-fatal.
  }
}
