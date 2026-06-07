# Spring 2026 Calibration Worklist

- **Date:** 2026-06-07
- **Ground truth:** final Spring 2026 section export (`export.csv`, CLSS), aggregated to actual enrollment per FOUN course per campus (Active sections only).
- **Compared against:** the raw sequence model (`POST /api/forecast`, Spring 2026, **adjustments disabled**) so the numbers reflect the model, not manual overrides.
- **Method:** instrumented the real pipeline to capture each feeder route's weight and `source_totals`, decomposed every target into its feeder and admits contributions, and compared to actuals.

## Root cause (established)

The forecast is off because the **sequencing map is mis-calibrated and incomplete**, not because of a code bug. Proof: disabling the `source_totals` dilution (the mechanism that produces the under-count) makes Savannah overshoot to 235% (FOUN 112 SAV → 2276 vs 641 actual). The dilution is load-bearing; the inputs to it (route weights and coverage) are wrong.

Raw model vs actual: **SAV capture 92% but MAPE 64%; NOW capture 54%, MAPE 59%; combined 85%.** The decent total hides large offsetting per-course errors. The model is miscalibrated in both directions, not uniformly low.

Note on the 10% buffer: a well-calibrated forecast sits ~10% above actual enrollment by design (section headroom). Targets below aim for model demand ≈ actual, so the buffered output lands just above actual.

## Calibration table (raw model, adjustments off)

| Campus | Course | Actual | Forecast | Δ | Dominant feeder (effective share) | Action |
|--------|--------|-------:|---------:|----:|-----------------------------------|--------|
| SAV | FOUN 220 | 255 | 510 | +255 | FOUN 112 [Winter] 21% | **Cut** (×0.55) |
| SAV | FOUN 113 | 1020 | 805 | -215 | FOUN 112 [Winter] 45% | **Raise** (×1.39, ~63%) |
| NOW | FOUN 113 | 230 | 72 | -158 | FOUN 112 [Winter] 46% | **Raise hard** (×3.5) |
| SAV | FOUN 112 | 641 | 510 | -131 | FOUN 111 [Winter] 54% | Raise (×1.38) |
| SAV | FOUN 260 | 52 | 164 | +112 | FOUN 250 [Winter] 67% | **Cut hard** (×0.35) |
| SAV | FOUN 240 | 208 | 107 | -101 | FOUN 112 [Winter] 6% | **Raise** (×2.1) |
| SAV | FOUN 250 | 121 | 39 | -82 | FOUN 220 [Fall] 13% | Raise (×3.4) |
| NOW | FOUN 250 | 56 | 0 | -56 | **NO ROUTE** | **Add route** |
| NOW | FOUN 112 | 102 | 55 | -47 | FOUN 111 [Winter] 67% | Raise (×2.0) |
| NOW | FOUN 260 | 0 | 43 | +43 | FOUN 250 [Winter] 100% | **Remove** (NOW has no 260) |
| NOW | FOUN 240 | 55 | 12 | -43 | FOUN 112 [Winter] 8% | Raise hard (×5.2) |
| SAV | FOUN 230 | 182 | 146 | -36 | FOUN 112 [Winter] 6% | Raise (×1.4) |
| NOW | FOUN 111 | 51 | 20 | -31 | admits (18) | Admits undercount (×2.8) |
| SAV | FOUN 110 | 60 | 33 | -27 | admits (30) | Admits undercount (×2.0) |
| SAV | FOUN 245 | 241 | 268 | +27 | FOUN 112 [Winter] 9% | ~OK (slightly over) |
| NOW | FOUN 230 | 36 | 12 | -24 | FOUN 112 [Winter] 8% | Raise (×3.4) |
| NOW | FOUN 220 | 39 | 63 | +24 | FOUN 251 [Winter] 50% | Cut (×0.68) |
| NOW | FOUN 245 | 35 | 13 | -22 | FOUN 112 [Winter] 8% | Raise (×3.0) |
| SAV | FOUN 222 | 21 | 0 | -21 | **NO ROUTE** | Add or accept out-of-scope |
| SAV | FOUN 331 | 16 | 0 | -16 | **NO ROUTE** | Add or accept out-of-scope |
| NOW | FOUN 110 | 29 | 19 | -10 | admits (17) | Admits undercount (×1.7) |
| SAV | FOUN 251 | 151 | 142 | -9 | FOUN 240 [Winter] 19% | OK |
| SAV | FOUN 330 | 6 | 0 | -6 | **NO ROUTE** | Add or accept out-of-scope |
| NOW | FOUN 251 | 58 | 63 | +5 | FOUN 240 [Winter] 100% | OK |
| SAV | FOUN 111 | 116 | 112 | -4 | FOUN 110 [Fall] 4% | OK |
| SAV | FOUN 360 | 4 | 0 | -4 | **NO ROUTE** | Add or accept out-of-scope |

## Prioritized fixes

### A. Remove stale manual adjustments — DONE
`Data/adjustments/spring_2026.json` had three `set` overrides (110→60, 220→187, 245→159) calibrated to an old SCAD **projection**, against the "calibrate only to measured ACT" policy. Against actuals they were a wash-to-harmful (245→159 was worse than the raw 268 vs actual 241). Removed; file is now an empty template.

### B. Re-weight the FOUN 112 feeder split — highest leverage
FOUN 112 (Winter) is the dominant feeder for 113, 230, 240, 245 and contributes to 220. Its weight budget is misallocated: too much to **220** (and via 250 to **260**), too little to **113 / 230 / 240 / 245**, on both campuses. Shifting weight off 220/260 and onto 113/230/240/245 corrects the largest deltas at once. These routes are coupled through 112's `source_totals`, so they must be re-weighted together. **Requires your domain judgment on which program rows carry the shift.**

### C. Cut the over-routes (high confidence)
- FOUN 260 SAV 164→52: the FOUN 250→260 route is over-weighted.
- FOUN 260 NOW 43→0: remove entirely; SCADnow does not run FOUN 260.
- FOUN 220 SAV 510→255 and 220 NOW 63→39: trim the over-routing.

### D. SCADnow coverage gaps (high confidence, structural)
- FOUN 250 NOW has **no route** (actual 56). Add one.
- NOW two-terms-back ("farther") feeders contribute **0** across the board; NOW relies entirely on Winter routes. Add farther routes for NOW programs.
- NOW 230/240/245 route at ~8% where actuals need 3-5×.

### E. Admits undercount (separate lever, not the seq map)
FOUN 110/111 on both campuses come from the admits file (PZSAAPF-SL31) and run ~half of actual (110 SAV 30 vs 60; 111 NOW 18 vs 51). Investigate `load_admits_foun_demand` and the admits→FOUN mapping coverage. This is independent of the sequencing map.

### F. Missing courses
FOUN 222 SAV (21), 330 (6), 331 (16), 360 (4) have no map entries. Mostly low-volume upper-year; decide whether to add minimal routes or accept as out-of-model.

### G. Atlanta scope
The model emits Atlanta rows (e.g., FOUN 251 ATL = 74) that have no counterpart in this Savannah+SCADnow export. Confirm whether Atlanta FOUN is in scope; if not, the map over-routes ATL.

## Caveats

- **Single-term calibration.** This is one term (Spring 2026). The **structural** fixes (C remove-phantom, D coverage, E admits, F missing) generalize; **fine per-course re-weighting** (B tuning, and small near-OK rows) risks over-fitting to one term. Validate against a second term's actuals before trusting fine tweaks.
- **Course-level direction, program-level edits.** The table gives the magnitude and direction per course; the map is program × year × campus. You decide which program rows carry each re-weighting.
- **Highest-confidence first:** A (done), C (over-routes), D (NOW coverage), E (admits). B is high-leverage but coupled; treat its fine values as directional.
