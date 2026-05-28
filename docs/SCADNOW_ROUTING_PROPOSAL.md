# SCADnow First-Year Spring Routing — Markup Proposal

Generated: 2026-05-06.

## Why this exists

NOW capture rate is 44.8% (vs SAV 81.7%). Diagnosis (see `MEMORY.md` Known Limitations #5): the seq map encodes only ~23% of the routing needed for NOW Spring 2026 — only ACCESSORY DESIGN, FURNITURE DESIGN, and SEQUENTIAL ART Group A currently route NOW students to upper-division First-Year FOUN courses (230/240/245). PZSMSCP actuals show 138 NOW students take FOUN 230/240/245 Spring 2026, but the model forecasts only ~34.

To hit ACT, the seq map needs more First-Year programs tagged with `Savannah | SCADnow` (or similar) AND routing to FOUN 230/240/245 in Spring. The ACT targets:

| Course | NOW ACT | Currently forecast | Need fraction | Need ~routes (numerator) |
|--|--:|--:|--:|--:|
| FOUN 230 | 37 | 11.6 | 0.246 | ~3 program-rows |
| FOUN 240 | 64 | 11.6 | 0.426 | ~5 program-rows |
| FOUN 245 | 37 | 12.7 | 0.246 | ~3 program-rows |

## Current First-Year NOW-eligible programs and their Spring routing

| # | Program | Campus tag | Current Spring target |
|---|---|---|---|
| 1 | ACCESSORY DESIGN | Savannah \| SCADnow | FOUN 230 ✓ |
| 2 | ADVERTISING AND BRANDING | General | (empty) |
| 3 | ADVERTISING AND BRANDING | Savannah \| Atlanta \| SCADnow | FOUN 113 |
| 4 | DRAMATIC WRITING | Savannah \| Atlanta \| SCADnow | FOUN 113 |
| 5 | FASHION MARKETING AND MANAGEMENT | Savannah \| Atlanta \| SCADnow | FOUN 113 |
| 6 | FURNITURE DESIGN | Savannah \| SCADnow | FOUN 240 + 245 ✓ |
| 7 | GAME DEVELOPMENT | General | FOUN 112 (no Spring 200-level target) |
| 8 | GRAPHIC DESIGN | General | FOUN 113 |
| 9 | GRAPHIC DESIGN | Savannah \| Atlanta \| SCADnow | FOUN 113 |
| 10 | PHOTOGRAPHY | Savannah \| Atlanta \| SCADnow | FOUN 112 (no Spring 200-level target) |
| 11 | PHOTOGRAPHY | General | FOUN 113 |
| 12 | SEQUENTIAL ART | General | FOUN 220 |
| 13 | SEQUENTIAL ART Group A | Savannah \| Atlanta \| SCADnow | FOUN 220 |
| 14 | SOCIAL STRATEGY AND MANAGEMENT | Savannah \| SCADnow | (empty) |
| 15 | SOCIAL STRATEGY AND MANAGEMENT | Major Course Sequencing Guide Sav... | FOUN 113 |

## Markup task — for each program, decide if Spring should also route to 230/240/245

Mark each program with what its **First-Year Spring** routing should be on SCADnow. Options:
- **K** = Keep current (no change)
- **+230** = Add FOUN 230 to Spring target
- **+240** = Add FOUN 240 to Spring target
- **+245** = Add FOUN 245 to Spring target
- **CHOICE: 230/240/245** = Spring target is CHOICE between these (split fraction)
- **?** = Unsure, ask registrar

Include reasoning if non-obvious.

```
[ ] K   ADVERTISING AND BRANDING (General)              currently empty
[ ] K   ADVERTISING AND BRANDING (SAV|ATL|NOW)          currently FOUN 113
[ ] K   DRAMATIC WRITING                                currently FOUN 113
[ ] K   FASHION MARKETING AND MANAGEMENT                currently FOUN 113
[ ] K   GAME DEVELOPMENT (General)                      currently FOUN 112
[ ] K   GRAPHIC DESIGN (General)                        currently FOUN 113
[ ] K   GRAPHIC DESIGN (SAV|ATL|NOW)                    currently FOUN 113
[ ] K   PHOTOGRAPHY (SAV|ATL|NOW)                       currently FOUN 112
[ ] K   PHOTOGRAPHY (General)                           currently FOUN 113
[ ] K   SOCIAL STRATEGY AND MANAGEMENT (SAV|NOW)        currently empty
```

## Programs missing from NOW entirely (worth checking)

These First-Year programs route to FOUN 230/240/245 in Spring on Savannah but are NOT tagged for SCADnow. If they actually run at SCADnow, they should be tagged:

```
[ ] ?   ILLUSTRATION Visual Development, Group B        SAV|ATL → FOUN 230  (does this run at NOW?)
[ ] ?   INDUSTRIAL DESIGN                               SAV|ATL → FOUN 245  (does this run at NOW?)
[ ] ?   INTERIOR DESIGN                                 SAV|ATL → FOUN 245  (does this run at NOW?)
[ ] ?   FIBERS                                          Savannah → FOUN 220+240  (does this run at NOW?)
```

If any of these run at NOW with First-Year cohorts, expanding their campus tag to include SCADnow is the cleanest fix.

## How to mark up

Edit this file inline and send back, or paste your annotations into chat. The dev team can then make the CSV edits for any program with a clear K/+230/+240/+245 mark, leaving any `?` marks for follow-up with registrar.

## Fallback option

If domain validation will take time, an interim fix is to use `set` adjustments calibrated to ACT in `Data/adjustments/spring_2026.json`:

```json
{
  "term": "Spring 2026",
  "adjustments": [
    {"course": "FOUN 230", "campus": "SCADnow", "operation": "set", "value": 37},
    {"course": "FOUN 240", "campus": "SCADnow", "operation": "set", "value": 64},
    {"course": "FOUN 245", "campus": "SCADnow", "operation": "set", "value": 37}
  ]
}
```

This is consistent with the existing adjustments policy (override against measured ACT, not projection) and is reversible once the seq map is corrected.
