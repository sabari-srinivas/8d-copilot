# Past 8D — Voids Under QFN Thermal Pad (CAPA-0111)

Plant: Sree Electronics (fictional), Chennai

Product: ECU-PCB-7 | Lot: L2457 | Discovered via internal X-ray audit

## D1

**Team.** SMT process engineer (lead), quality engineer, reflow equipment technician, and the facilities technician responsible for the nitrogen generation and distribution system.

## D2

**Problem description.** A routine X-ray audit on ECU-PCB-7 lot L2457 found void area under the QFN thermal pad exceeding the acceptance limit on 9 of 30 sampled boards, flagged before the lot shipped.

## D3

**Containment.** Lot L2457 and the three lots produced on the same reflow oven since the last verified nitrogen purity check were held. Each held lot was 100% X-rayed under the QFN thermal pad; boards exceeding the void area limit were scrapped, boards within limit were released.

## D4

**Root cause.** The reflow oven's nitrogen supply regulator had drifted out of calibration, allowing residual oxygen in the reflow zones to rise above the 500 ppm specification. The resulting increase in oxidation of the paste flux and the QFN thermal pad surface slowed and delayed flux outgassing during reflow, trapping more gas under the thermal pad as the solder solidified and producing void area beyond the acceptance limit. The root cause was nitrogen supply regulator drift, not an operator action: the regulator had no alarm, so the drift was invisible until the X-ray audit caught it.

## D5

**Permanent corrective action.** An inline oxygen analyzer with a low-purity alarm was installed on the nitrogen feed to the reflow oven, interlocked to stop the conveyor if residual oxygen rises above 500 ppm. A preventive calibration schedule for the nitrogen regulator was added to the maintenance plan.

## D6

**Verification of effectiveness.** Void area under QFN thermal pads on weekly X-ray sampling returned to the historical baseline within two weeks of the analyzer and alarm going live, with no exceedances in the eight weeks tracked afterward.

## D7

**Prevent recurrence.** PFMEA Row 3 (voids under BGA/QFN thermal pad) and Control plan Item 5 (nitrogen purity monitoring) were updated to reference the inline oxygen analyzer and low-purity alarm as the detection and prevention controls.

## D8

**Closure.** Corrective actions verified effective and closed under CAPA-0111.

*Synthetic document for demo purposes.*
