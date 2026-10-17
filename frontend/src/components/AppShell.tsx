import { useEffect, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { getHealth } from "../api/client";

// CR #1: "New" dropped on purpose. Customers raise complaints; Priya receives and
// investigates them, she does not file one herself — the /new route stays (the inbox
// still navigates there with ?complaint=…) but it is no longer a destination reachable
// with nothing selected (see NewInvestigation.tsx's redirect).
const NAV_ITEMS = [
  { to: "/", label: "Inbox", icon: InboxIcon },
  { to: "/memory", label: "Memory", icon: MemoryIcon },
];

/** Carries the §7 header and footer on every screen: a sidebar nav above 768px,
 * a bottom tab bar below it. One shell, one place that knows the plant name and
 * the signed-in user — nothing else should hard-code them. */
/** True when the backend is replaying a recorded run instead of calling models.
 * Surfaced in the header so a viewer is never unsure whether a run is live — the same
 * honesty rule as labelling the synthetic data. */
function useReplayCase(): string | null {
  const [replay, setReplay] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((h) => { if (!cancelled) setReplay(h.replay ?? null); })
      .catch(() => { /* health is advisory; a failure must not break the shell */ });
    return () => { cancelled = true; };
  }, []);
  return replay;
}

export function AppShell({ children }: { children: ReactNode }) {
  const replayCase = useReplayCase();
  return (
    <div className="min-h-dvh flex flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:flex focus:items-center focus:rounded focus:bg-[var(--card)] focus:px-3 focus:text-sm focus:border tap-target"
        style={{ borderColor: "var(--line)" }}
      >
        Skip to content
      </a>

      <header
        className="sticky top-0 z-20 flex items-center gap-3 px-4 h-14 border-b shrink-0"
        style={{ borderColor: "var(--line)", background: "var(--paper)" }}
      >
        <span
          className="grid place-items-center h-8 w-8 rounded-lg text-white text-xs font-bold shrink-0"
          style={{ background: "var(--green)" }}
          aria-hidden="true"
        >
          8D
        </span>
        <span className="text-sm opacity-70 truncate">
          Sree Electronics (fictional), Chennai
        </span>
        {replayCase && (
          <span
            className="shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium"
            style={{ borderColor: "var(--amber)", color: "var(--amber)" }}
            title={`Replaying the recorded run "${replayCase}" — no model calls`}
          >
            Replay
          </span>
        )}
        <span className="ml-auto flex items-center gap-2 text-sm shrink-0">
          <span className="hidden sm:inline">Priya R. · Quality Engineer</span>
          <span
            className="grid place-items-center h-8 w-8 rounded-full text-white text-xs font-semibold"
            style={{ background: "var(--green)" }}
            aria-hidden="true"
          >
            PR
          </span>
          <span className="sr-only">Signed in as Priya R., Quality Engineer</span>
        </span>
      </header>

      <div className="flex-1 flex w-full">
        <nav
          aria-label="Primary"
          className="hidden md:flex flex-col gap-1 w-56 shrink-0 border-r px-3 py-4"
          style={{ borderColor: "var(--line)" }}
        >
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 h-11 text-sm font-medium transition-colors ${
                  isActive ? "text-white" : "opacity-80 hover:opacity-100"
                }`
              }
              style={({ isActive }) => ({
                background: isActive ? "var(--green)" : "transparent",
              })}
            >
              <Icon />
              {label}
            </NavLink>
          ))}
        </nav>

        <main id="main" className="flex-1 min-w-0 px-4 py-5 max-w-[1280px] w-full mx-auto">
          {children}
        </main>
      </div>

      <footer
        className="px-4 py-2 text-[11px] opacity-50 border-t shrink-0"
        style={{ borderColor: "var(--line)" }}
      >
        Synthetic demo data · Built with Gemini on Google Cloud
      </footer>

      <nav
        aria-label="Primary"
        className="md:hidden sticky bottom-0 z-20 flex border-t shrink-0"
        style={{ borderColor: "var(--line)", background: "var(--paper)" }}
      >
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center gap-0.5 h-14 text-[11px] font-medium ${
                isActive ? "" : "opacity-70"
              }`
            }
            style={({ isActive }) => ({ color: isActive ? "var(--green)" : undefined })}
          >
            <Icon />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function InboxIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M3 13h5l1.5 3h5L16 13h5M4 13l1.6-6.4A2 2 0 0 1 7.5 5h9a2 2 0 0 1 1.9 1.6L20 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function MemoryIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 19.5V6a2 2 0 0 1 2-2h12.5v15.5M6 4v15.5M6 19.5h12.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
