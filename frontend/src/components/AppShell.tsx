import {
  ChevronDown,
  ClipboardCheck,
  Database as MemoryIcon,
  Factory,
  History,
  Inbox as InboxIcon,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { getHealth, listComplaints } from "../api/client";
import type { Complaint } from "../api/types";

// The five tabs read left to right as the quality engineer's actual working sequence:
// see the state, pick the work, act on it, remember it, check the evidence. "/" is
// the dashboard now -- Complaints (the old inbox) moved to its own route.
const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/complaints", label: "Complaints", icon: InboxIcon },
  { to: "/capa", label: "CAPA", icon: ClipboardCheck },
  { to: "/memory", label: "Memory", icon: MemoryIcon },
  { to: "/plant", label: "Plant", icon: Factory },
] as const;

const COLLAPSE_KEY = "sidebar_collapsed";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === "true";
  } catch {
    return false;
  }
}

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

/** The sidebar's "Complaints" row with its own expand/collapse -- a dropdown of two
 * groups (open complaints; past investigations), each a direct link, so a quality
 * engineer can jump straight to one complaint without going through the Complaints
 * screen first. Collapsed by default; independent of the sidebar's own collapse state
 * (only rendered at all when the sidebar itself is expanded). */
/** The two views the Complaints screen can show, and the only things the sidebar
 * dropdown lists (CR #17). `?view=past` is what the page branches on — a query param
 * rather than a second route, so a judge who lands on `/complaints` with no param gets
 * the open list, which is the screen's job. */
const COMPLAINT_VIEWS = [
  {
    to: "/complaints",
    view: "open",
    label: "Open complaints",
    count: (n: { open: number; past: number }) => n.open,
  },
  {
    to: "/complaints?view=past",
    view: "past",
    label: "Past investigations",
    count: (n: { open: number; past: number }) => n.past,
  },
];

function ComplaintsNavItem({ collapsedSidebar }: { collapsedSidebar: boolean }) {
  // Starts expanded: the dropdown is now two short entries rather than a spill of every
  // complaint, so showing them costs nothing and saves a click on the one nav item a
  // judge is most likely to want.
  const [open, setOpen] = useState(true);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const location = useLocation();
  const active = location.pathname === "/complaints";
  // Anything other than `past` is the open list — the same defaulting the page does, so
  // the highlighted entry and the rendered view can never disagree.
  const currentView =
    new URLSearchParams(location.search).get("view") === "past" ? "past" : "open";

  useEffect(() => {
    listComplaints().then(setComplaints).catch(() => setComplaints([]));
  }, []);

  const openComplaints = complaints.filter((c) => c.status === "open");
  const pastComplaints = complaints.filter((c) => c.status === "closed");

  if (collapsedSidebar) {
    return (
      <NavLink
        to="/complaints"
        title="Complaints"
        className={({ isActive }) =>
          `tap-target flex items-center justify-center rounded-md h-10 transition-colors ${
            isActive ? "text-[var(--pill-fg-strong)]" : "opacity-75 hover:opacity-100 hover:bg-[var(--surface-hover)]"
          }`
        }
        style={({ isActive }) => ({ background: isActive ? "var(--green)" : "transparent" })}
      >
        <InboxIcon size={17} aria-hidden="true" />
        <span className="sr-only">Complaints</span>
      </NavLink>
    );
  }

  return (
    <div>
      <div
        className={`flex items-center rounded-md pr-1 ${
          active ? "text-[var(--pill-fg-strong)]" : "opacity-75 hover:opacity-100 hover:bg-[var(--surface-hover)]"
        }`}
        style={{ background: active ? "var(--green)" : "transparent" }}
      >
        <NavLink to="/complaints" className="flex items-center gap-2.5 px-3 h-10 text-sm font-medium flex-1 min-w-0">
          <InboxIcon size={17} aria-hidden="true" />
          Complaints
        </NavLink>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={open ? "Collapse complaints list" : "Expand complaints list"}
          className="tap-target grid place-items-center h-8 w-8 rounded shrink-0 hover:bg-black/10"
        >
          <ChevronDown size={14} className="transition-transform" style={{ transform: open ? "rotate(180deg)" : undefined }} aria-hidden="true" />
        </button>
      </div>

      {/* CR #17: two entries, not two lists. The dropdown previously spilled every
        * complaint and every past investigation into the sidebar, which made a
        * navigation control into a second copy of the page it navigates to. These are
        * views; the detail belongs in the main section. */}
      {open && (
        <ul className="pl-3 pb-1 flex flex-col text-sm">
          {COMPLAINT_VIEWS.map(({ to, view, label, count }) => {
            // Not NavLink's own `isActive`: it matches on pathname and ignores the
            // query string, so both entries would highlight at once on /complaints.
            const isCurrent = active && currentView === view;
            return (
              <li key={to}>
                <Link
                  to={to}
                  aria-current={isCurrent ? "page" : undefined}
                  className={`tap-target flex items-center gap-2 px-2 rounded text-xs ${
                    isCurrent
                      ? "font-semibold"
                      : "opacity-75 hover:opacity-100 hover:bg-[var(--surface-hover)]"
                  }`}
                  style={{ color: isCurrent ? "var(--green)" : undefined }}
                >
                  <span className="truncate">{label}</span>
                  <span className="mono text-[11px] opacity-60 ml-auto shrink-0">
                    {count({ open: openComplaints.length, past: pastComplaints.length })}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** Carries the header and footer on every screen: a sidebar nav above 768px, a
 * bottom tab bar below it. One shell, one place that knows the plant name and the
 * signed-in user — nothing else should hard-code them. */
export function AppShell({ children }: { children: ReactNode }) {
  const replayCase = useReplayCase();
  const [collapsed, setCollapsed] = useState(readCollapsed);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(COLLAPSE_KEY, String(next));
      } catch {
        /* storage can throw in locked-down embeds; collapse still works for this load */
      }
      return next;
    });
  }

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
        className="sticky top-0 z-20 flex items-center gap-3 px-4 h-12 border-b shrink-0"
        style={{ borderColor: "var(--line)", background: "var(--paper)" }}
      >
        <span
          className="mono grid place-items-center h-7 w-7 rounded-md text-[var(--pill-fg-strong)] text-[11px] font-bold shrink-0"
          style={{ background: "var(--green)" }}
          aria-hidden="true"
        >
          8D
        </span>
        <span className="text-sm opacity-70 truncate">
          Sree Electronics, Chennai
        </span>
        {/* No "demo data" chip and no "(fictional)" qualifier here — the owner asked for
         * both out of the chrome (CR #5, CR #17). The honesty claim lives in the README
         * and the deck's data slide instead. See CLAUDE.md rule 5. */}
        {replayCase && (
          <span
            className="shrink-0 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium"
            style={{ borderColor: "var(--amber)", color: "var(--amber-ink)" }}
            title={`Replaying the recorded run "${replayCase}" — no model calls`}
          >
            <History size={12} aria-hidden="true" />
            Replay
          </span>
        )}
      </header>

      <div className="flex-1 flex w-full">
        <nav
          aria-label="Primary"
          // No width transition here: animating `width` is a layout property, not
          // transform/opacity, so it stays untransitioned (snaps instantly) per the
          // product's own motion rule (index.css's prefers-reduced-motion block,
          // 150-300ms transform/opacity only) rather than adding a new kind of
          // animation this app doesn't otherwise use.
          className={`hidden md:flex flex-col shrink-0 border-r py-3 ${
            collapsed ? "w-14 px-1.5" : "w-56 px-2"
          }`}
          style={{ borderColor: "var(--line)" }}
        >
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={`tap-target grid place-items-center rounded-md mb-2 hover:bg-[var(--surface-hover)] ${collapsed ? "w-full" : "self-end"}`}
          >
            {collapsed ? <PanelLeftOpen size={17} aria-hidden="true" /> : <PanelLeftClose size={17} aria-hidden="true" />}
          </button>

          <div className="flex flex-col gap-0.5 flex-1 overflow-y-auto">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) =>
              to === "/complaints" ? (
                <ComplaintsNavItem key={to} collapsedSidebar={collapsed} />
              ) : (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  title={collapsed ? label : undefined}
                  className={({ isActive }) =>
                    `tap-target flex items-center gap-2.5 rounded-md px-3 h-10 text-sm font-medium transition-colors ${
                      collapsed ? "justify-center px-0" : ""
                    } ${isActive ? "text-[var(--pill-fg-strong)]" : "opacity-75 hover:opacity-100 hover:bg-[var(--surface-hover)]"}`
                  }
                  style={({ isActive }) => ({
                    background: isActive ? "var(--green)" : "transparent",
                  })}
                >
                  <Icon size={17} aria-hidden="true" />
                  {!collapsed && label}
                  {collapsed && <span className="sr-only">{label}</span>}
                </NavLink>
              ),
            )}
          </div>

          {/* Persona, bottom-left of the sidebar — moved out of the header. */}
          <div
            className={`flex items-center gap-2 border-t pt-2.5 mt-2 ${collapsed ? "justify-center" : ""}`}
            style={{ borderColor: "var(--line)" }}
          >
            <span
              className="grid place-items-center h-7 w-7 rounded-full text-[var(--pill-fg-strong)] text-[11px] font-semibold shrink-0"
              style={{ background: "var(--green)" }}
              aria-hidden="true"
            >
              PR
            </span>
            {!collapsed && (
              <span className="text-xs leading-tight min-w-0">
                <span className="block font-medium truncate">Priya R.</span>
                <span className="block opacity-60 truncate">Quality Engineer</span>
              </span>
            )}
            <span className="sr-only">Signed in as Priya R., Quality Engineer</span>
          </div>
        </nav>

        <main id="main" className="flex-1 min-w-0 px-3 py-4 max-w-[1280px] w-full mx-auto">
          {children}
        </main>
      </div>

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
              `tap-target flex-1 flex flex-col items-center justify-center gap-0.5 min-w-0 py-1.5 text-[10px] font-medium leading-tight ${
                isActive ? "" : "opacity-70"
              }`
            }
            style={({ isActive }) => ({ color: isActive ? "var(--green)" : undefined })}
          >
            <Icon size={18} aria-hidden="true" />
            <span className="truncate max-w-full px-0.5">{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
