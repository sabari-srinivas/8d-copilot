import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

export interface Crumb {
  label: string;
  to?: string;
}

/** A plain trail of where the current screen sits in the app, e.g.
 * "Complaints › Investigation inv_123 › Review". Pure presentation -- no state, no
 * fetch, no navigation side effect -- so it can be dropped above any screen
 * (including the investigation flow) without touching that screen's own logic. The
 * last crumb is always the current page and is never a link. */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs mb-2 flex-wrap opacity-80">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={`${item.label}-${i}`} className="flex items-center gap-1">
            {i > 0 && <ChevronRight size={11} className="opacity-40" aria-hidden="true" />}
            {item.to && !isLast ? (
              <Link to={item.to} className="hover:underline hover:opacity-100">
                {item.label}
              </Link>
            ) : (
              <span aria-current={isLast ? "page" : undefined} className={isLast ? "font-semibold" : undefined}>
                {item.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
