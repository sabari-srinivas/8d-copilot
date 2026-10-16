# PFMEA — SMT Reflow Line, ECU-PCB-7

Plant: Sree Electronics (fictional), Chennai

Process FMEA for the surface-mount reflow process (AIAG-VDA 2019 style). Twenty failure modes covering stencil printing, placement, reflow soldering, component storage and automated inspection.

## Row 1

| Field | Value |
|---|---|
| Process step | Stencil printing |
| Failure mode | Insufficient paste deposit |
| Effect | Starved solder joint; open circuit or weak fillet found at customer board-level vibration test |
| Severity | 6 |
| Cause | Stencil aperture partially blocked with dried solder paste residue |
| Occurrence | 4 |
| Prevention control | Scheduled under-stencil wipe every 10 boards and daily aperture inspection |
| Detection control | SPI 100% paste volume and area measurement |
| Detection | 3 |
| Action priority | Medium |

Mechanism: Insufficient paste deposit at Stencil printing is caused by Stencil aperture partially blocked with dried solder paste residue. Effect: Starved solder joint; open circuit or weak fillet found at customer board-level vibration test. Prevention control: Scheduled under-stencil wipe every 10 boards and daily aperture inspection. Detection control: SPI 100% paste volume and area measurement.

## Row 2

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Tombstoning |
| Effect | One end of a chip component lifts off the pad; open circuit at functional test |
| Severity | 6 |
| Cause | Paste age beyond its working window causing uneven wetting force between pad ends |
| Occurrence | 3 |
| Prevention control | Paste working-life timer tag on the cart; FIFO issue from refrigeration |
| Detection control | AOI 100% post-reflow inspection |
| Detection | 3 |
| Action priority | Medium |

Mechanism: Tombstoning at Reflow soldering is caused by Paste age beyond its working window causing uneven wetting force between pad ends. Effect: One end of a chip component lifts off the pad; open circuit at functional test. Prevention control: Paste working-life timer tag on the cart; FIFO issue from refrigeration. Detection control: AOI 100% post-reflow inspection.

## Row 3

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Voids under BGA/QFN thermal pad |
| Effect | Reduced thermal and electrical contact under the package; derating or field failure |
| Severity | 5 |
| Cause | Entrapped flux outgassing during reflow due to low nitrogen purity |
| Occurrence | 3 |
| Prevention control | Nitrogen purity monitoring with residual-oxygen alarm |
| Detection control | X-ray sampling of BGA/QFN lots per shift |
| Detection | 5 |
| Action priority | Medium |

Mechanism: Voids under BGA/QFN thermal pad at Reflow soldering is caused by Entrapped flux outgassing during reflow due to low nitrogen purity. Effect: Reduced thermal and electrical contact under the package; derating or field failure. Prevention control: Nitrogen purity monitoring with residual-oxygen alarm. Detection control: X-ray sampling of BGA/QFN lots per shift.

## Row 4

| Field | Value |
|---|---|
| Process step | Pick and place |
| Failure mode | Component misalignment |
| Effect | Component placed off-pad; solder bridge or open joint at an adjacent pad |
| Severity | 5 |
| Cause | Placement machine vision calibration drift |
| Occurrence | 3 |
| Prevention control | Daily placement accuracy verification against a gauge board |
| Detection control | AOI post-placement (pre-reflow) inspection |
| Detection | 3 |
| Action priority | Medium |

Mechanism: Component misalignment at Pick and place is caused by Placement machine vision calibration drift. Effect: Component placed off-pad; solder bridge or open joint at an adjacent pad. Prevention control: Daily placement accuracy verification against a gauge board. Detection control: AOI post-placement (pre-reflow) inspection.

## Row 5

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Cold solder joint |
| Effect | Dull, grainy joint with poor mechanical strength; intermittent open under vibration |
| Severity | 6 |
| Cause | Reflow peak temperature below profile minimum or insufficient time above liquidus |
| Occurrence | 2 |
| Prevention control | Profile verification after any oven maintenance; confirm minimum peak temperature and time above liquidus are met |
| Detection control | AOI 100% plus periodic cross-section audit |
| Detection | 4 |
| Action priority | Medium |

Mechanism: Cold solder joint at Reflow soldering is caused by Reflow peak temperature below profile minimum or insufficient time above liquidus. Effect: Dull, grainy joint with poor mechanical strength; intermittent open under vibration. Prevention control: Profile verification after any oven maintenance; confirm minimum peak temperature and time above liquidus are met. Detection control: AOI 100% plus periodic cross-section audit.

## Row 6

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Component shift during reflow |
| Effect | Component skewed or tombstoned after reflow; open or short at an adjacent pad |
| Severity | 5 |
| Cause | Conveyor vibration during the reflow cool-down zone |
| Occurrence | 3 |
| Prevention control | Conveyor speed and belt tension check per shift |
| Detection control | AOI 100% post-reflow inspection |
| Detection | 3 |
| Action priority | Medium |

Mechanism: Component shift during reflow at Reflow soldering is caused by Conveyor vibration during the reflow cool-down zone. Effect: Component skewed or tombstoned after reflow; open or short at an adjacent pad. Prevention control: Conveyor speed and belt tension check per shift. Detection control: AOI 100% post-reflow inspection.

## Row 7

| Field | Value |
|---|---|
| Process step | Incoming board handling |
| Failure mode | Warped board |
| Effect | Open joints at board-edge components from coplanarity loss during reflow |
| Severity | 6 |
| Cause | Incoming bare board exceeds the warpage specification |
| Occurrence | 2 |
| Prevention control | Incoming board warpage check per the receiving sample plan |
| Detection control | AOI 100% plus warpage gauge spot check |
| Detection | 4 |
| Action priority | Medium |

Mechanism: Warped board at Incoming board handling is caused by Incoming bare board exceeds the warpage specification. Effect: Open joints at board-edge components from coplanarity loss during reflow. Prevention control: Incoming board warpage check per the receiving sample plan. Detection control: AOI 100% plus warpage gauge spot check.

## Row 8

| Field | Value |
|---|---|
| Process step | Pick and place |
| Failure mode | Nozzle wear |
| Effect | Component drop or tilt during placement; missing or misaligned component |
| Severity | 5 |
| Cause | Pick-and-place nozzle wear beyond vacuum seal tolerance |
| Occurrence | 3 |
| Prevention control | Nozzle wear inspection and replacement schedule |
| Detection control | Placement vacuum sensor and AOI post-placement |
| Detection | 3 |
| Action priority | Medium |

Mechanism: Nozzle wear at Pick and place is caused by Pick-and-place nozzle wear beyond vacuum seal tolerance. Effect: Component drop or tilt during placement; missing or misaligned component. Prevention control: Nozzle wear inspection and replacement schedule. Detection control: Placement vacuum sensor and AOI post-placement.

## Row 9

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Insufficient reflow |
| Effect | Paste not fully reflowed; grainy, non-wetted joint with open-circuit risk |
| Severity | 6 |
| Cause | Reflow peak temperature or time above liquidus below profile minimum |
| Occurrence | 2 |
| Prevention control | Profile verification after any oven maintenance; confirm soak and ramp rates meet the paste datasheet |
| Detection control | AOI 100% + profile check per shift |
| Detection | 4 |
| Action priority | Medium |

Mechanism: Insufficient reflow at Reflow soldering is caused by Reflow peak temperature or time above liquidus below profile minimum. Effect: Paste not fully reflowed; grainy, non-wetted joint with open-circuit risk. Prevention control: Profile verification after any oven maintenance; confirm soak and ramp rates meet the paste datasheet. Detection control: AOI 100% + profile check per shift.

## Row 10

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Excess voiding under components |
| Effect | Thermal and electrical derating; risk of cracking under thermal cycling |
| Severity | 5 |
| Cause | Paste flux chemistry outgassing combined with a fast preheat ramp rate |
| Occurrence | 3 |
| Prevention control | Preheat ramp rate verification against the profile limits |
| Detection control | X-ray sampling per shift |
| Detection | 5 |
| Action priority | Medium |

Mechanism: Excess voiding under components at Reflow soldering is caused by Paste flux chemistry outgassing combined with a fast preheat ramp rate. Effect: Thermal and electrical derating; risk of cracking under thermal cycling. Prevention control: Preheat ramp rate verification against the profile limits. Detection control: X-ray sampling per shift.

## Row 11

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Head-in-pillow |
| Effect | BGA ball does not fully coalesce with the paste deposit; intermittent open under thermal cycling |
| Severity | 7 |
| Cause | BGA ball oxidation combined with board warpage at reflow peak |
| Occurrence | 2 |
| Prevention control | BGA ball co-planarity check and nitrogen-atmosphere reflow |
| Detection control | X-ray sampling of BGA lots per shift |
| Detection | 5 |
| Action priority | Medium |

Mechanism: Head-in-pillow at Reflow soldering is caused by BGA ball oxidation combined with board warpage at reflow peak. Effect: BGA ball does not fully coalesce with the paste deposit; intermittent open under thermal cycling. Prevention control: BGA ball co-planarity check and nitrogen-atmosphere reflow. Detection control: X-ray sampling of BGA lots per shift.

## Row 12

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Solder balls |
| Effect | Loose solder spheres between pads; risk of migration and short circuit |
| Severity | 6 |
| Cause | Excess paste volume or moisture in the paste causing spatter during reflow |
| Occurrence | 3 |
| Prevention control | SPI paste volume control and incoming paste moisture check |
| Detection control | AOI 100% post-reflow inspection |
| Detection | 3 |
| Action priority | Medium |

Mechanism: Solder balls at Reflow soldering is caused by Excess paste volume or moisture in the paste causing spatter during reflow. Effect: Loose solder spheres between pads; risk of migration and short circuit. Prevention control: SPI paste volume control and incoming paste moisture check. Detection control: AOI 100% post-reflow inspection.

## Row 13

| Field | Value |
|---|---|
| Process step | Stencil printing |
| Failure mode | Stencil blockage |
| Effect | Missing or insufficient paste deposit at the affected pads; open joint |
| Severity | 6 |
| Cause | Dried paste residue builds up in fine-pitch apertures between cleaning cycles |
| Occurrence | 3 |
| Prevention control | Increased under-stencil wipe frequency for fine-pitch stencils |
| Detection control | SPI 100% paste area measurement |
| Detection | 3 |
| Action priority | Medium |

Mechanism: Stencil blockage at Stencil printing is caused by Dried paste residue builds up in fine-pitch apertures between cleaning cycles. Effect: Missing or insufficient paste deposit at the affected pads; open joint. Prevention control: Increased under-stencil wipe frequency for fine-pitch stencils. Detection control: SPI 100% paste area measurement.

## Row 14

| Field | Value |
|---|---|
| Process step | Reflow soldering |
| Failure mode | Solder bridging |
| Effect | Short circuit between adjacent pins from excess solder flowing between adjacent fine-pitch pads; ECU functional failure at customer ICT |
| Severity | 8 |
| Cause | Reflow peak temperature above profile limit |
| Occurrence | 3 |
| Prevention control | Profile verification after any oven maintenance; confirm peak temperature does not exceed the upper profile limit |
| Detection control | AOI 100% + profile check per shift |
| Detection | 4 |
| Action priority | High |

Mechanism: Solder bridging at Reflow soldering is caused by Reflow peak temperature above profile limit. Effect: Short circuit between adjacent pins from excess solder flowing between adjacent fine-pitch pads; ECU functional failure at customer ICT. Prevention control: Profile verification after any oven maintenance; confirm peak temperature does not exceed the upper profile limit. Detection control: AOI 100% + profile check per shift.

## Row 15

| Field | Value |
|---|---|
| Process step | Board transport |
| Failure mode | Conveyor vibration |
| Effect | Component shift or tombstoning on boards passing through the vibration zone |
| Severity | 5 |
| Cause | Worn conveyor belt or a loose board-stop sensor mount |
| Occurrence | 2 |
| Prevention control | Conveyor preventive maintenance and belt tension check |
| Detection control | AOI 100% post-reflow inspection |
| Detection | 3 |
| Action priority | Medium |

Mechanism: Conveyor vibration at Board transport is caused by Worn conveyor belt or a loose board-stop sensor mount. Effect: Component shift or tombstoning on boards passing through the vibration zone. Prevention control: Conveyor preventive maintenance and belt tension check. Detection control: AOI 100% post-reflow inspection.

## Row 16

| Field | Value |
|---|---|
| Process step | Component storage |
| Failure mode | Oxidation |
| Effect | Poor wetting at component leads; open or weak joint |
| Severity | 5 |
| Cause | Components stored beyond shelf life outside the humidity-controlled cabinet |
| Occurrence | 2 |
| Prevention control | First-in-first-out component storage in humidity-controlled cabinets |
| Detection control | Incoming lead solderability sample test |
| Detection | 5 |
| Action priority | Medium |

Mechanism: Oxidation at Component storage is caused by Components stored beyond shelf life outside the humidity-controlled cabinet. Effect: Poor wetting at component leads; open or weak joint. Prevention control: First-in-first-out component storage in humidity-controlled cabinets. Detection control: Incoming lead solderability sample test.

## Row 17

| Field | Value |
|---|---|
| Process step | Component storage |
| Failure mode | Moisture sensitivity |
| Effect | Internal delamination or cracking of a moisture-sensitive package during reflow |
| Severity | 7 |
| Cause | Moisture-sensitive device exposed beyond its floor life before reflow |
| Occurrence | 2 |
| Prevention control | MSL floor-life tracking with bake-out when the floor life is exceeded |
| Detection control | Acoustic microscopy sampling of suspect lots |
| Detection | 6 |
| Action priority | Medium |

Mechanism: Moisture sensitivity at Component storage is caused by Moisture-sensitive device exposed beyond its floor life before reflow. Effect: Internal delamination or cracking of a moisture-sensitive package during reflow. Prevention control: MSL floor-life tracking with bake-out when the floor life is exceeded. Detection control: Acoustic microscopy sampling of suspect lots.

## Row 18

| Field | Value |
|---|---|
| Process step | Pick and place |
| Failure mode | Polarity reversal |
| Effect | Reversed diode or polarized capacitor; functional failure or damage at power-on test |
| Severity | 8 |
| Cause | Component reel loaded in the wrong orientation at feeder changeover |
| Occurrence | 2 |
| Prevention control | Feeder setup verification against the BOM polarity marking |
| Detection control | AOI polarity check 100% plus ICT functional test |
| Detection | 2 |
| Action priority | High |

Mechanism: Polarity reversal at Pick and place is caused by Component reel loaded in the wrong orientation at feeder changeover. Effect: Reversed diode or polarized capacitor; functional failure or damage at power-on test. Prevention control: Feeder setup verification against the BOM polarity marking. Detection control: AOI polarity check 100% plus ICT functional test.

## Row 19

| Field | Value |
|---|---|
| Process step | Pick and place |
| Failure mode | Missing component |
| Effect | Open circuit; functional failure at ICT |
| Severity | 7 |
| Cause | Feeder jam or an empty reel not detected before the placement cycle |
| Occurrence | 2 |
| Prevention control | Feeder low-count alarm and first-article inspection after changeover |
| Detection control | AOI 100% post-placement plus ICT |
| Detection | 2 |
| Action priority | Medium |

Mechanism: Missing component at Pick and place is caused by Feeder jam or an empty reel not detected before the placement cycle. Effect: Open circuit; functional failure at ICT. Prevention control: Feeder low-count alarm and first-article inspection after changeover. Detection control: AOI 100% post-placement plus ICT.

## Row 20

| Field | Value |
|---|---|
| Process step | AOI inspection |
| Failure mode | AOI false call |
| Effect | Defective board shipped as good, or a good board scrapped on a false reject |
| Severity | 6 |
| Cause | AOI algorithm threshold drift after a software or lighting change |
| Occurrence | 2 |
| Prevention control | AOI programming validation against known-good and known-defect reference boards |
| Detection control | Weekly AOI gauge R&R with a reference board set |
| Detection | 4 |
| Action priority | Medium |

Mechanism: AOI false call at AOI inspection is caused by AOI algorithm threshold drift after a software or lighting change. Effect: Defective board shipped as good, or a good board scrapped on a false reject. Prevention control: AOI programming validation against known-good and known-defect reference boards. Detection control: Weekly AOI gauge R&R with a reference board set.

*Synthetic document for demo purposes.*
