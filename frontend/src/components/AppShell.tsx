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
import { getHealth, listCapas, listComplaints } from "../api/client";
import type { CapaRecord, Complaint } from "../api/types";

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
function ComplaintsNavItem({ collapsedSidebar }: { collapsedSidebar: boolean }) {
  const [open, setOpen] = useState(false);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [capas, setCapas] = useState<CapaRecord[]>([]);
  const location = useLocation();
  const active = location.pathname === "/complaints";

  useEffect(() => {
    listComplaints().then(setComplaints).catch(() => setComplaints([]));
    listCapas().then(setCapas).catch(() => setCapas([]));
  }, []);

  const openComplaints = complaints.filter((c) => c.status === "open");
  const pastComplaints = complaints.filter((c) => c.status === "closed");
  const capaByComplaint = new Map(capas.map((c) => [c.complaint_id, c]));

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

      {open && (
        <div className="pl-3 pb-1 flex flex-col gap-2 text-sm">
          <div>
            <p className="stat-label px-2 pt-1.5">Open complaints ({openComplaints.length})</p>
            <ul className="flex flex-col">
              {openComplaints.map((c) => (
                <li key={c.complaint_id}>
                  <Link
                    to={`/new?complaint=${encodeURIComponent(c.complaint_id)}`}
                    className="tap-target flex flex-col justify-center px-2 rounded hover:bg-[var(--surface-hover)]"
                  >
                    <span className="truncate text-xs font-medium">{c.customer}</span>
                    <span className="mono text-[11px] opacity-60">{c.complaint_id}</span>
                  </Link>
                </li>
              ))}
              {openComplaints.length === 0 && <li className="px-2 text-xs opacity-50">None open</li>}
            </ul>
          </div>
          <div>
            <p className="stat-label px-2 pt-1">Past investigations ({pastComplaints.length})</p>
            <ul className="flex flex-col">
              {pastComplaints.map((c) => {
                const capa = capaByComplaint.get(c.complaint_id);
                return (
                  <li key={c.complaint_id}>
                    <Link
                      to={capa ? `/capa?highlight=${encodeURIComponent(capa.id)}` : "/complaints"}
                      className="tap-target flex flex-col justify-center px-2 rounded hover:bg-[var(--surface-hover)]"
                    >
                      <span className="truncate text-xs font-medium">{c.customer}</span>
                      <span className="mono text-[11px] opacity-60">{c.complaint_id}{capa ? ` → ${capa.id}` : ""}</span>
                    </Link>
                  </li>
                );
              })}
              {pastComplaints.length === 0 && <li className="px-2 text-xs opacity-50">None yet</li>}
            </ul>
          </div>
        </div>
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
          Sree Electronics (fictional), Chennai
        </span>
        {/* The footer's "Synthetic demo data" wording moved here, per the owner's
         * request to drop the footer line -- the honesty claim still needs a home,
         * just a quieter one. */}
        <span
          className="shrink-0 text-[10px] font-semibold uppercase tracking-wide rounded-full border px-1.5 py-0.5 opacity-60"
          style={{ borderColor: "var(--line-strong)" }}
          title="Every number in this product is synthetic demo data"
        >
          Demo data
        </span>
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
