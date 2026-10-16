# Past 8D — Tombstoning on 0402 Resistors (CAPA-0098)

Plant: Sree Electronics (fictional), Chennai

Product: ECU-PCB-7 | Customer: Hoshino Denso (fictional) | Complaint: C-2026-024 | Lot: L2389

## D1

**Team.** SMT process engineer (lead), quality engineer, production shift supervisor, and a supplier quality representative from the solder paste supplier. The team had process ownership of stencil printing, reflow and incoming paste control.

## D2

**Problem description.** Hoshino Denso (fictional) raised complaint C-2026-024 on 2026-07-02, reporting tombstoning on 0402 chip resistors on ECU-PCB-7, lot L2389. Twelve of 500 boards showed one end of the resistor lifted off the pad at positions R23 and R47, found during the customer's incoming inspection.

## D3

**Containment.** The remaining boards in lot L2389 and the two adjacent lots were pulled and 100% re-inspected under magnification. Stock already shipped to Hoshino Denso (fictional) was sorted at incoming. Tombstoned boards were reworked where the resistor could be re-seated and re-reflowed by hand; boards with pad lift were scrapped.

## D4

**Root cause.** The solder paste pot used to print the affected boards had been out of refrigeration for roughly 26 hours before the last boards in the pot were printed, beyond the paste manufacturer's stated working-life window. The paste had begun to dry and lose tack, so one end of the 0402 resistor reflowed and wetted before the other; the imbalance in surface-tension pull lifted the lighter end off the pad. The root cause was paste age beyond its working window, not an operator action: the paste cart had no visible timer or hold tag, so there was no way for anyone on the line to see that the pot was already past its working life.

## D5

**Permanent corrective action.** A paste cart timer tag was introduced: every paste pot is tagged with the time it leaves refrigeration and a hard stop time by which it must be off the line. Paste is issued first-in-first-out from the fridge, and SPI is configured to flag a volume trend consistent with aging paste.

## D6

**Verification of effectiveness.** Tombstoning escapes on 0402 passives dropped from a running average of roughly 1 in 2,000 boards to zero over the four weeks following the timer-tag rollout, tracked against AOI tombstoning counts by week.

## D7

**Prevent recurrence.** PFMEA Row 2 (tombstoning) and Control plan Item 4 (paste storage and working-life control) were updated to reference the paste cart timer tag and the hard stop time as the prevention control.

## D8

**Closure.** Corrective actions verified effective and closed under CAPA-0098. The 8D was approved and sent to Hoshino Denso (fictional) against complaint C-2026-024.

*Synthetic document for demo purposes.*
