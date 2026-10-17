import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

/** The five tabs read left to right as the quality engineer's working sequence: see
 * the state, pick the work, act on it, remember it, check the evidence. This strip
 * repeats that sequence at the top of each of the five main screens as both a
 * breadcrumb (where am I in the lifecycle) and a quick way to jump stages without
 * going back to the sidebar -- most useful on mobile, where the sidebar is gone. */
const LIFECYCLE_STAGES = [
  { to: "/", label: "Dashboard" },
  { to: "/complaints", label: "Complaints" },
  { to: "/capa", label: "CAPA" },
  { to: "/memory", label: "Memory" },
  { to: "/plant", label: "Plant" },
] as const;

export function LifecycleStrip({ current }: { current: (typeof LIFECYCLE_STAGES)[number]["label"] }) {
  return (
    <nav aria-label="Lifecycle" className="flex items-center gap-1 text-xs mb-3 overflow-x-auto pb-0.5">
      {LIFECYCLE_STAGES.map((s, i) => {
        const active = s.label === current;
        return (
          <span key={s.to} className="flex items-center gap-1 shrink-0">
            {i > 0 && <ChevronRight size={12} className="opacity-30" aria-hidden="true" />}
            <Link
              to={s.to}
              aria-current={active ? "page" : undefined}
              className="tap-target inline-flex items-center rounded-md px-2.5 text-xs transition-colors hover:bg-[var(--surface-hover)]"
              style={{
                color: active ? "var(--green-ink)" : undefined,
                fontWeight: active ? 700 : 500,
                opacity: active ? 1 : 0.65,
              }}
            >
              {s.label}
            </Link>
          </span>
        );
      })}
    </nav>
  );
}
