/** Display-only name formatting.
 *
 * Customer and plant names carry a "(fictional)" qualifier in the data — `data/
 * constants.py`, and from there BigQuery, the complaint rows and the 8D text. That
 * qualifier is the honesty label: these companies do not exist, and the README and the
 * deck both say so.
 *
 * The owner asked for the words out of the chrome, so this strips them at the point of
 * render and nowhere else. The data is untouched, which matters — the 8D a judge reads
 * still quotes the customer exactly as the record spells it, so nothing downstream of a
 * tool result is being quietly rewritten to look better. See CLAUDE.md rule 5 and
 * docs/CHANGE_REQUESTS.md #17.
 */

/** `Hoshino Denso (fictional)` -> `Hoshino Denso`. Leaves anything else alone, including
 * a name that never carried the qualifier, and collapses the double space a mid-string
 * removal would otherwise leave behind. */
export function plainName(name: string): string {
  return name
    .replace(/\s*\((?:fictional|fictitious)\)/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}
