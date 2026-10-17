import { ArrowLeft, Inbox as InboxIcon } from "lucide-react";
import { Link } from "react-router-dom";

/** CR #3: Evidence, Review and Done had no way out except the browser back button
 * (Evidence had no navigation at all). Every one of them gets this: back to the live
 * investigation trace, plus a route straight to the complaint list ("/" is the
 * dashboard now, not the inbox — this must point at the renamed "/complaints"). */
export function BackNav({ investigationId }: { investigationId: string | undefined }) {
  return (
    <nav aria-label="Back" className="flex items-center gap-4 text-sm mb-3">
      {investigationId && (
        <Link
          to={`/inv/${investigationId}`}
          className="tap-target inline-flex items-center gap-1 font-medium underline"
          style={{ color: "var(--green)" }}
        >
          <ArrowLeft size={15} aria-hidden="true" />
          Back to investigation
        </Link>
      )}
      <Link to="/complaints" className="tap-target inline-flex items-center gap-1 opacity-70 underline">
        <InboxIcon size={15} aria-hidden="true" />
        Complaints
      </Link>
    </nav>
  );
}
