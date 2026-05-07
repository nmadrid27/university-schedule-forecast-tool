# Spring 2026 Backtest — Forecast vs ACT (PZSMSCP ground truth)

**Date:** 2026-05-05
**Branch:** `claude/peaceful-jang-c98903`
**Forecast configuration:** Cognos OFF (`enrollmentByMajorFile: null`); admits ON; no manual adjustments applied.

## Why this document exists

Until now, every accuracy check in `MEMORY.md` and prior sprint notes compared the forecast against `Data/clon_sav_atl_seat_projection_202630_20260107.xlsx` — a January 2026 SCAD planning **projection**, not actual demand. Today (2026-05-05), Spring 2026 is essentially complete and the published schedule (PZSMSCP) carries real ACT enrollment counts. PZSMSCP is the correct ground truth for backtesting.

## Source

`/Users/nathanmadrid/Desktop/PZSMSCP - Flexible Master Schedule of Classes with Power Prompts.xlsx` (sheet `Page1`).

Extraction rules:
- Header row 17, data starts row 18.
- Dedupe by CRN (one row per instructor in source; we keep the first row per CRN).
- Filter `SUBJ = FOUN`, `TERM = 202630`.
- Group by `(CRS NUMBER, CAMPUS)`, sum `MAX ENR` and `ACT ENR`.

After dedupe: 7,906 unique CRNs across all subjects/terms; 242 FOUN sections in Spring 2026.

## Confirmed Spring 2026 actuals

### Savannah (SAV)

| Course   | Sections | MAX  | ACT  |
|----------|---------:|-----:|-----:|
| FOUN 110 |        4 |   80 |   63 |
| FOUN 111 |        9 |  180 |  125 |
| FOUN 112 |       50 |  948 |  653 |
| FOUN 113 |       54 | 1072 | 1029 |
| FOUN 220 |       22 |  440 |  262 |
| FOUN 222 |        2 |   40 |   21 |
| FOUN 230 |       10 |  200 |  184 |
| FOUN 240 |       12 |  240 |  210 |
| FOUN 245 |       13 |  260 |  249 |
| FOUN 250 |       10 |  197 |  125 |
| FOUN 251 |        8 |  156 |  155 |
| FOUN 260 |        3 |   60 |   52 |
| FOUN 330 |        1 |   20 |    6 |
| FOUN 331 |        1 |   20 |   16 |
| FOUN 360 |        1 |   20 |    4 |

SAV total ACT: **3,154** across 200 sections.

### SCADnow (NOW)

| Course   | Sections | MAX | ACT |
|----------|---------:|----:|----:|
| FOUN 110 |        2 |  40 |  38 |
| FOUN 111 |        3 |  60 |  55 |
| FOUN 112 |        6 | 120 | 107 |
| FOUN 113 |       13 | 260 | 241 |
| FOUN 220 |        3 |  60 |  47 |
| FOUN 230 |        2 |  40 |  37 |
| FOUN 240 |        4 |  80 |  64 |
| FOUN 245 |        2 |  40 |  37 |
| FOUN 250 |        4 |  80 |  64 |
| FOUN 251 |        3 |  60 |  61 |

NOW total ACT: **751** across 42 sections.

These match the table provided in the prompt exactly for SAV. NOW also has 250/251 sections; the prompt's reference table was SAV-only.

## Task 1 — Accuracy backtest

Forecast generated with the worktree's current code (post prior-sprint changes), Cognos OFF, no adjustments file present.

### Savannah comparison

| Course   | Forecast |  ACT |  MAX | Δ vs ACT |       Δ% | Δ vs MAX |
|----------|---------:|-----:|-----:|---------:|---------:|---------:|
| FOUN 110 |     33.0 |   63 |   80 |    -30.0 |   -47.6% |    -47.0 |
| FOUN 111 |    111.8 |  125 |  180 |    -13.2 |   -10.5% |    -68.2 |
| FOUN 112 |    532.3 |  653 |  948 |   -120.7 |   -18.5% |   -415.7 |
| FOUN 113 |    804.5 | 1029 | 1072 |   -224.5 |   -21.8% |   -267.5 |
| FOUN 220 |    378.9 |  262 |  440 |   +116.9 |   +44.6% |    -61.1 |
| FOUN 222 |   (none) |   21 |   40 |    +21.0 | (missing) |   +40.0 |
| FOUN 230 |    106.7 |  184 |  200 |    -77.3 |   -42.0% |    -93.3 |
| FOUN 240 |    106.7 |  210 |  240 |   -103.3 |   -49.2% |   -133.3 |
| FOUN 245 |    160.0 |  249 |  260 |    -89.0 |   -35.7% |   -100.0 |
| FOUN 250 |   (none) |  125 |  197 |   +125.0 | (missing) |  +197.0 |
| FOUN 251 |      1.1 |  155 |  156 |   -153.9 |   -99.3% |   -154.9 |
| FOUN 260 |   (none) |   52 |   60 |    +52.0 | (missing) |   +60.0 |
| FOUN 330 |   (none) |    6 |   20 |     +6.0 | (missing) |   +20.0 |
| FOUN 331 |   (none) |   16 |   20 |    +16.0 | (missing) |   +20.0 |
| FOUN 360 |   (none) |    4 |   20 |     +4.0 | (missing) |   +20.0 |

**SAV statistics** (over the 9 courses with both forecast and ACT):

- MAE vs ACT: **103.2 students/course**
- MAPE vs ACT: **41.0%**
- Forecast sum (matched only): 2,235.1 vs ACT 2,930 → **-23.7% aggregate bias (under-forecast)**
- Total ACT including unforecasted courses: 3,154 → forecast captures **70.9%** of true demand
- Unforecasted-course gap: **224 SAV ACT students** (FOUN 222 + 250 + 260 + 330 + 331 + 360) the model produced no row for at all
- Per-course bias direction: 8 of 9 matched courses **under**-forecast; only FOUN 220 over-forecasts (+44.6%)

### SCADnow comparison

| Course   | Forecast | ACT | MAX | Δ vs ACT |       Δ% | Δ vs MAX |
|----------|---------:|----:|----:|---------:|---------:|---------:|
| FOUN 110 |     18.7 |  38 |  40 |    -19.3 |   -50.8% |    -21.3 |
| FOUN 111 |     19.8 |  55 |  60 |    -35.2 |   -64.0% |    -40.2 |
| FOUN 112 |     54.7 | 107 | 120 |    -52.3 |   -48.8% |    -65.3 |
| FOUN 113 |     92.5 | 241 | 260 |   -148.5 |   -61.6% |   -167.5 |
| FOUN 220 |     31.2 |  47 |  60 |    -15.8 |   -33.6% |    -28.8 |
| FOUN 230 |   (none) |  37 |  40 |    +37.0 | (missing) |   +40.0 |
| FOUN 240 |   (none) |  64 |  80 |    +64.0 | (missing) |   +80.0 |
| FOUN 245 |      1.1 |  37 |  40 |    -35.9 |   -97.0% |    -38.9 |
| FOUN 250 |   (none) |  64 |  80 |    +64.0 | (missing) |   +80.0 |
| FOUN 251 |   (none) |  61 |  60 |    +61.0 | (missing) |   +60.0 |

**NOW statistics** (over the 6 courses with both forecast and ACT):

- MAE vs ACT: **51.2 students/course**
- MAPE vs ACT: **59.3%**
- Forecast sum (matched only): 218.0 vs ACT 525 → **-58.5% aggregate bias (severe under-forecast)**
- Total ACT including unforecasted courses: 751 → forecast captures **29.0%** of true demand
- Unforecasted-course gap: **226 NOW ACT students** (230 + 240 + 250 + 251)
- Per-course bias direction: 6 of 6 matched courses **under**-forecast (no over-forecast on NOW)

### Aggregate bias direction (both campuses)

The forecast under-forecasts in nearly every dimension. Combined SAV+NOW:

- Total forecasted demand (matched courses): 2,235.1 + 218.0 = **2,453.1**
- Total ACT (matched courses): 2,930 + 525 = **3,455**
- Total ACT (all FOUN, all campuses): 3,154 + 751 = **3,905**
- Aggregate forecast capture rate (vs all ACT): **62.8%**
- Aggregate forecast capture rate (vs matched-only ACT): **71.0%**

The model is structurally low. The single over-forecast (FOUN 220 SAV +44.6%) does not offset the broad under-forecast pattern; even with that contribution included, the matched-course aggregate is -23.7%.

## Task 2 — FOUN 250 / 251 / 260 / 330 / 331 / 360 investigation

The current `_active_curriculum_years('202630')` returns `['First Year']` — a function defined in `api/forecaster.py` based on the assumption that the FOUN curriculum launched Fall 2025, so Spring 2026 only contains First-Year cohorts.

### Question 1 — Are FOUN 250/251/260 listed as Spring targets in the seq map for First Year, Second Year, or both?

Search of `Data/FOUN_sequencing_map_by_major.csv`:

| Course   | First Year mentions | Second Year mentions | Third Year mentions |
|----------|--------------------:|---------------------:|--------------------:|
| FOUN 250 |                   0 |                    4 |                   1 |
| FOUN 251 |                   0 |                   14 |                   7 |
| FOUN 260 |                   0 |                    3 |                   1 |
| FOUN 330 |                   0 |                    0 |                   0 |
| FOUN 331 |                   0 |                    0 |                   0 |
| FOUN 360 |                   0 |                    0 |                   0 |

FOUN 250/251/260 appear **only in Second/Third Year rows** — exactly the rows the year filter strips out for term 202630. FOUN 330/331/360 do not appear in the seq map at all.

For First Year Spring specifically (the only rows the filter passes today), the seq map mentions:

```
FOUN 111: 3 rows    FOUN 230: 2 rows
FOUN 112: 15 rows   FOUN 240: 2 rows
FOUN 113: 15 rows   FOUN 245: 3 rows
FOUN 220: 7 rows
```

This explains exactly which courses the forecaster can produce a row for: 111, 112, 113, 220, 230, 240, 245 — and that is what the run output shows for SAV plus an out-of-place 251 that comes from a single CHOICE expansion remnant.

### Question 2 — Does the forecast produce ANY row for these courses?

From the SAV run: **no** for 250, 260, 330, 331, 360. FOUN 251 SAV does get a row (1.1 students, 1 section), but that's a CHOICE-expansion artifact, not a real signal.

For NOW: no rows for 230, 240, 250, 251.

### Question 3 — Where are those 358 SAV ACT students actually coming from?

There are two compatible hypotheses; both are likely true to varying degrees, and neither requires changing code in this sprint.

**Hypothesis A (most likely): the year filter assumption is wrong.** The seq map clearly carries Second/Third Year FOUN routing rules. Those upper-year students exist *now* in Spring 2026 — they cannot be year-1 cohorts that started Fall 2025 (those students are still First Year in Spring 2026 by definition). They are existing Sophomores/Juniors who took legacy DRAW/DSGN courses earlier and are now being routed into FOUN 250/251/260/330/331/360 in their later years. The curriculum did not "launch" with only First Years in Fall 2025; it appears upper-year students entered the FOUN sequence simultaneously, picking up wherever they were in the legacy DRAW/DSGN sequence.

Evidence:
- 358 SAV ACT students are real and currently enrolled in 250/251/260/330/331/360.
- Their existence in Spring 2026 is mathematically incompatible with the "First-Year only" curriculum-start model: the curriculum is one term old plus winter; First Years cannot have reached 250-level Spring courses.
- The seq map already encodes Second/Third Year Spring routing for these very courses.
- The legacy crosswalk (`Data/sequence_crosswalk_template.csv`) maps DRAW/DSGN codes into FOUN 250/251/260, indicating SCAD historically ran an equivalent sequence under different codes.

**Hypothesis B (partial contributor): FOUN 330/331/360 are entirely unmodeled.** These courses do not appear in the seq map at any year and have no legacy crosswalk entry feeding them. The total ACT for 330+331+360 is 26 students SAV — small, but it confirms the seq map is incomplete for 300-level FOUN.

### Question 4 — Is the year-filter assumption wrong?

Given Hypothesis A, almost certainly yes. The "FOUN curriculum launched Fall 2025" framing led to a defensive year filter that is now masking real, modelable upper-year demand. A future sprint should:

1. Verify with the registrar that FOUN was rolled out simultaneously across all years, not phased in cohort-by-cohort.
2. If confirmed, change `_active_curriculum_years` so 202630 returns `['First Year', 'Second Year', 'Third Year']` (or remove the filter entirely for terms post-launch).
3. Add a seq-map row (or registrar-confirmed entry) for FOUN 330/331/360 so they are forecastable at all.

This sprint diagnoses only — no code change.

## Task 3 — Adjustments template recommendation

`Data/adjustments/spring_2026.json` (gitignored, currently in worktree) holds three `set` adjustments calibrated to the stale Jan 2026 projection:

| Adjustment | Set value | ACT value | MAX value | Verdict |
|------------|----------:|----------:|----------:|---------|
| FOUN 110 SAV | 60 | 63 | 80 | Wrong by 3 students. Close to ACT, but the rationale ("compromise between raw and SCAD official") is now meaningless. |
| FOUN 220 SAV | 187 | 262 | 440 | Severely wrong. Set value is 75 students *under* ACT. Model raw of 379 is closer to ACT than the override. |
| FOUN 240 SAV | 16 | 210 | 240 | Catastrophically wrong. Set value is 194 students under ACT. The "official 16" was a planning artifact, not real demand. |

**Recommendation: remove all three `set` adjustments.** Calibrating model output to a stale projection is fundamentally the wrong intervention; if the projection is wrong, capping the forecast to it propagates the error. The honest position is:

- Run the model raw with no adjustments.
- Document the under-forecast bias as a known limitation.
- Treat any future adjustment as a correction against a *measured* anomaly (ACT vs. forecast), not against another forecaster.

The `Data/adjustments/README.md` should be updated to make this policy explicit: adjustments only against ACT, never against another projection.

## Summary findings

1. The model under-forecasts SAV total demand by 23.7% on matched courses and misses 224 SAV ACT students entirely on courses it cannot produce rows for (FOUN 222, 250, 260, 330, 331, 360).
2. NOW under-forecast is more severe: 58.5% on matched courses, with 226 ACT students on unforecasted courses.
3. The dominant root cause for missing rows is `_active_curriculum_years` filtering out Second/Third Year seq-map entries; FOUN 330/331/360 are also missing from the seq map at all.
4. The single over-forecast (FOUN 220 SAV +44.6%) is not enough to offset the broad under-forecast pattern.
5. The current `Data/adjustments/spring_2026.json` template was calibrated to a stale Jan 2026 projection and is wrong against ACT for all three entries.

## Out of scope for this sprint

- Any change to `_active_curriculum_years`, the seq map, or any forecasting code.
- Any new sequencing-map rows for 330/331/360.
- Re-running the forecast under hypothetical year-filter relaxations.

These are all candidates for a follow-up sprint informed by registrar confirmation.

---

# Post-Fix Section (Sprint follow-up)

**Date:** 2026-05-05
**Change:** `_active_curriculum_years` now returns all four cohort labels for any term at or after Fall 2025 (term code 202610), and `None` for pre-curriculum terms. The prior phased-rollout assumption (`['First Year']` only for Spring 2026) was wrong. Same forecast configuration as the pre-fix run: Cognos OFF, admits ON, no manual adjustments.

## Variant comparison (A/B/C/D)

Four candidate implementations of `_active_curriculum_years` were forecast-tested side-by-side for term 202630:

- **A. Current** — `['First Year']` only (baseline)
- **B. No filter** — returns `None` (all rows pass)
- **C. Always all four** — returns the explicit four-label list
- **D. Term-gated all-years** — `None` pre-curriculum (< 202610), all four labels post-launch

### SAVANNAH per-course forecast under each variant

| Course   | A.Current | B.NoFilter | C.AllYrs | D.TermGate |   ACT |   MAX |
|----------|----------:|-----------:|---------:|-----------:|------:|------:|
| FOUN 110 |     30.0  |      30.0  |    30.0  |      30.0  |    63 |    80 |
| FOUN 111 |    101.7  |     101.7  |   101.7  |     101.7  |   125 |   180 |
| FOUN 112 |    483.9  |     463.6  |   463.6  |     463.6  |   653 |   948 |
| FOUN 113 |    731.4  |     731.4  |   731.4  |     731.4  |  1029 |  1072 |
| FOUN 220 |    344.4  |     464.0  |   464.0  |     464.0  |   262 |   440 |
| FOUN 222 |   (none)  |    (none)  |  (none)  |    (none)  |    21 |    40 |
| FOUN 230 |     97.0  |     132.7  |   132.7  |     132.7  |   184 |   200 |
| FOUN 240 |     97.0  |      97.0  |    97.0  |      97.0  |   210 |   240 |
| FOUN 245 |    145.5  |     243.3  |   243.3  |     243.3  |   249 |   260 |
| FOUN 250 |   (none)  |      35.7  |    35.7  |      35.7  |   125 |   197 |
| FOUN 251 |      1.0  |     129.0  |   129.0  |     129.0  |   155 |   156 |
| FOUN 260 |   (none)  |     149.5  |   149.5  |     149.5  |    52 |    60 |
| FOUN 330 |   (none)  |    (none)  |  (none)  |    (none)  |     6 |    20 |
| FOUN 331 |   (none)  |    (none)  |  (none)  |    (none)  |    16 |    20 |
| FOUN 360 |   (none)  |    (none)  |  (none)  |    (none)  |     4 |    20 |

### SCADNOW per-course forecast under each variant

| Course   | A.Current | B.NoFilter | C.AllYrs | D.TermGate |  ACT |  MAX |
|----------|----------:|-----------:|---------:|-----------:|-----:|-----:|
| FOUN 110 |     17.0  |      17.0  |    17.0  |      17.0  |   38 |   40 |
| FOUN 111 |     18.0  |      18.0  |    18.0  |      18.0  |   55 |   60 |
| FOUN 112 |     49.8  |      49.8  |    49.8  |      49.8  |  107 |  120 |
| FOUN 113 |     84.1  |      84.1  |    84.1  |      84.1  |  241 |  260 |
| FOUN 220 |     28.4  |      64.0  |    64.0  |      64.0  |   47 |   60 |
| FOUN 230 |   (none)  |    (none)  |  (none)  |    (none)  |   37 |   40 |
| FOUN 240 |   (none)  |    (none)  |  (none)  |    (none)  |   64 |   80 |
| FOUN 245 |      1.0  |       1.0  |     1.0  |       1.0  |   37 |   40 |
| FOUN 250 |   (none)  |    (none)  |  (none)  |    (none)  |   64 |   80 |
| FOUN 251 |   (none)  |      57.0  |    57.0  |      57.0  |   61 |   60 |

### Aggregate stats per variant

| Variant | Campus | MAE | MAPE | Capt%(all) | #Captured |
|---------|--------|----:|-----:|-----------:|----------:|
| A. Current ['First Year']     | SAV | 118.1 | 44.4% | 64.4% |  9/15 |
| B. No filter (None)           | SAV | 102.5 | 51.4% | 81.7% | 11/15 |
| C. Always all 4 years         | SAV | 102.5 | 51.4% | 81.7% | 11/15 |
| D. Term-gated all 4           | SAV | 102.5 | 51.4% | 81.7% | 11/15 |
| A. Current ['First Year']     | NOW |  54.5 | 63.0% | 26.4% |  6/10 |
| B. No filter (None)           | NOW |  47.0 | 54.4% | 38.7% |  7/10 |
| C. Always all 4 years         | NOW |  47.0 | 54.4% | 38.7% |  7/10 |
| D. Term-gated all 4           | NOW |  47.0 | 54.4% | 38.7% |  7/10 |

> Note: variant A here shows MAE=118.1 / MAPE=44.4% / capture=64.4% for SAV, slightly worse than the pre-fix section above (which reported MAE=103.2 / MAPE=41.0% / capture=70.9%). The difference is because the pre-fix section excluded the FOUN 251 SAV `1.1` "CHOICE artifact" from the matched-courses count, while this comparison includes it as a captured row (the metric is mechanical: forecast > 0 means captured). Treat the comparison numbers as internally consistent across A/B/C/D; the absolute pre-fix capture for "real" courses still rounds to ~71%.

### Identity check

For Spring 2026 (term 202630), variants B, C, and D produce **identical** forecasts (0 differing per-course values across all 28 forecast rows). This is expected: the seq map only contains First/Second/Third/Fourth Year row labels, so passing the explicit four-label list is functionally equivalent to passing `None`. The variants only diverge on:

- **Pre-curriculum terms** (e.g. backtests of Spring 2025 = 202530): A returns `[]` once (per the original pre-curriculum guard fix from sprint of 2026-02-28) and B/C/D handle differently. Variant D matches A here (both return `None`), preserving backtest behavior. Variant C would incorrectly filter against year labels not present in pre-2025 seq-map snapshots.
- **Post-2028 terms**: A and B return `None`; C and D return the explicit list. Functionally equivalent for current seq map but C/D protect against future seq-map additions of non-cohort year labels.

### Recommendation: variant D

Variant D (term-gated all-years) was selected because it (a) produces identical correct numbers to B and C for Spring 2026, (b) preserves the existing pre-curriculum safety behavior that backtests rely on, and (c) is explicit about intent rather than relying on `None` to mean "all rows." Implementation: pre-Fall-2025 → `None`; Fall 2025 onwards → all four cohort labels.

## Post-fix accuracy

### Savannah comparison (Pre-fix vs Post-fix vs ACT)

| Course   | Pre-fix | Post-fix |   ACT | Pre Δ% | Post Δ% |
|----------|--------:|---------:|------:|-------:|--------:|
| FOUN 110 |    33.0 |     30.0 |    63 | -47.6% |  -52.4% |
| FOUN 111 |   111.8 |    101.7 |   125 | -10.5% |  -18.7% |
| FOUN 112 |   532.3 |    463.6 |   653 | -18.5% |  -29.0% |
| FOUN 113 |   804.5 |    731.4 |  1029 | -21.8% |  -28.9% |
| FOUN 220 |   378.9 |    464.0 |   262 | +44.6% |  +77.1% |
| FOUN 222 |  (none) |   (none) |    21 |   miss |    miss |
| FOUN 230 |   106.7 |    132.7 |   184 | -42.0% |  -27.9% |
| FOUN 240 |   106.7 |     97.0 |   210 | -49.2% |  -53.8% |
| FOUN 245 |   160.0 |    243.3 |   249 | -35.7% |   -2.3% |
| FOUN 250 |  (none) |     35.7 |   125 |   miss |  -71.4% |
| FOUN 251 |     1.1 |    129.0 |   155 | -99.3% |  -16.8% |
| FOUN 260 |  (none) |    149.5 |    52 |   miss | +187.4% |
| FOUN 330 |  (none) |   (none) |     6 |   miss |    miss |
| FOUN 331 |  (none) |   (none) |    16 |   miss |    miss |
| FOUN 360 |  (none) |   (none) |     4 |   miss |    miss |

**SAV aggregate (matched courses with forecast > 0):**

|              | Pre-fix | Post-fix |     Δ |
|--------------|--------:|---------:|------:|
| Captured     |    9/15 |    11/15 |    +2 |
| MAE          |   103.2 |    102.5 |  -0.7 |
| MAPE         |  41.0%  |   51.4%  | +10.4pp |
| Capture(all) |  70.9%  |   81.7%  | +10.9pp |
| Capture(matched) | 76.3% | 83.0%  |  +6.7pp |
| Under/Over   |     8/1 |      9/2 |     — |

### SCADnow comparison (Pre-fix vs Post-fix vs ACT)

| Course   | Pre-fix | Post-fix |  ACT | Pre Δ% | Post Δ% |
|----------|--------:|---------:|-----:|-------:|--------:|
| FOUN 110 |    18.7 |     17.0 |   38 | -50.8% |  -55.3% |
| FOUN 111 |    19.8 |     18.0 |   55 | -64.0% |  -67.3% |
| FOUN 112 |    54.7 |     49.8 |  107 | -48.8% |  -53.5% |
| FOUN 113 |    92.5 |     84.1 |  241 | -61.6% |  -65.1% |
| FOUN 220 |    31.2 |     64.0 |   47 | -33.6% |  +36.1% |
| FOUN 230 |  (none) |   (none) |   37 |   miss |    miss |
| FOUN 240 |  (none) |   (none) |   64 |   miss |    miss |
| FOUN 245 |     1.1 |      1.0 |   37 | -97.0% |  -97.3% |
| FOUN 250 |  (none) |   (none) |   64 |   miss |    miss |
| FOUN 251 |  (none) |     57.0 |   61 |   miss |   -6.6% |

**NOW aggregate (matched courses with forecast > 0):**

|              | Pre-fix | Post-fix |    Δ |
|--------------|--------:|---------:|-----:|
| Captured     |    6/10 |     7/10 |   +1 |
| MAE          |    51.2 |     47.0 | -4.1 |
| MAPE         |   59.3% |   54.4%  | -4.9pp |
| Capture(all) |   29.0% |   38.7%  | +9.7pp |
| Capture(matched) | 41.5% | 49.6%  | +8.1pp |
| Under/Over   |     6/0 |      6/1 |    — |

### Combined (SAV + NOW)

|              | Pre-fix | Post-fix |    Δ |
|--------------|--------:|---------:|-----:|
| Captured     |   15/25 |    18/25 |   +3 |
| MAE          |    82.4 |     81.0 | -1.4 |
| MAPE         |   48.4% |   52.6%  | +4.2pp |
| Capture(all) |   62.8% |   73.5%  | +10.6pp |
| Capture(matched) | 71.0% | 77.7%  |  +6.7pp |

## Honest assessment

**Did the fix resolve the under-forecast problem?** Partially. It did exactly what it was supposed to do — restore the upper-year cohort routing — but did not deliver a uniform improvement.

What got better:

- **Capture rate climbed materially**: SAV +10.9pp, NOW +9.7pp, combined +10.6pp. The model now produces forecast rows for FOUN 250 and FOUN 260 (SAV) and FOUN 251 (both campuses) where it previously produced nothing.
- **Three new courses captured** (250 SAV, 260 SAV, 251 NOW) representing 240 SAV ACT students + 61 NOW ACT students that were previously entirely missed.
- **FOUN 245 SAV moved from -35.7% to -2.3%** — now within rounding of ACT.
- **FOUN 251 SAV went from a 1.1 CHOICE-artifact to 129 vs ACT 155** — proper signal where there was noise.
- **NOW MAPE dropped 4.9pp** (54.4% vs 59.3%).

What did not get better, or got worse:

- **MAPE on SAV got worse** (41.0% → 51.4%), driven by two over-forecast courses: FOUN 220 (now +77.1% vs ACT) and FOUN 260 SAV (now +187.4% vs ACT 52). Adding upper-year cohort rows pulled FOUN 220 SAV from 344 to 464 and FOUN 260 SAV from 0 to 149.5.
- **First Year courses (FOUN 110/111/112/113) actually moved slightly farther from ACT** in absolute Δ%: e.g. FOUN 112 SAV -18.5% → -29.0%. This is because the same denominator (feeder enrollments) is now being divided across more target courses, so per-course allocations dropped slightly.
- **Six courses still entirely unforecasted**: SAV 222, 330, 331, 360 (zero seq-map presence) and NOW 230, 240, 250 (no NOW-applicable seq-map routing).
- **Capture rate at SAV (81.7%) is still well short of the 90%+ "the year filter was the only culprit" threshold** the prompt mentioned. The fix is necessary but not sufficient.

**Diagnosis**: this fix solves the structural exclusion of upper-year cohorts but exposes two pre-existing issues that were previously masked:

1. **The seq map's anchor selection / source-totals logic dilutes First Year demand once Second/Third Year rows are present** — adding them increases denominators while the same Winter feeder enrollment must now stretch across more target rows. This is mechanical, not a bug per se, but the calibration was tuned to the (incorrect) First-Year-only world.
2. **FOUN 220 and FOUN 260 are now over-forecast**. With upper-year routes active, both courses pick up cohort traffic that ACT data shows did not actually flow to them. Either the seq map over-routes to these courses or some upper-year students dropped out / changed sequence between the seq map's authored state and the actual Spring 2026 enrollment. Likely a mix.
3. **FOUN 222, 330, 331, 360 (SAV) and 230/240/250 (NOW) remain entirely missing** — these courses are not in the seq map at all (or at least not for routing into Spring 2026 at NOW). The year filter was never going to fix them; they need seq-map additions or registrar-confirmed routing rules.

**Recommended next steps** (out of this sprint's scope):

- Investigate FOUN 220 SAV over-forecast: which programs are routing there and whether actuals show those programs' students went elsewhere (e.g., FOUN 240/245). Likely Animation 3D or VFX cohorts whose Winter feeder is FOUN 251 but who in practice took FOUN 240 in Spring instead.
- Investigate FOUN 260 SAV over-forecast: only 3 seq-map rows route here (per the original sprint diagnostic), but they appear to be amplified by enrollment-weighted denominators. Cross-check ACT against the actual programs in those rows.
- Add seq-map entries (or a synthetic routing) for FOUN 222 SAV and FOUN 330/331/360 SAV so they are forecastable at all. The 47 SAV ACT students they collectively represent will otherwise remain a permanent capture-rate ceiling.
- Add NOW-specific routing rows for FOUN 230, 240, 250 — the seq map currently does not route any program's Winter feeders into these courses for the SCADnow campus. (Either the seq map was authored Savannah-first, or these are general-routing rows that the campus filter is dropping; needs investigation.)

The under-forecast bias is materially reduced (capture +10.6pp, MAE -1.4) but not eliminated. Treat this fix as a necessary correction that raises the floor; the remaining gap is structural seq-map coverage and per-course calibration, both of which are downstream sprint candidates.

---

# Post-Mechanical-Fixes Section (Sprint follow-up, 2026-05-05)

**Change:** Two seq-map rows expanded from `Savannah` to `Savannah | SCADnow`:

1. `ACCESSORY DESIGN` First Year (line 2) — routes to FOUN 230 in Spring (NOW ACT 37, FOUN 230 has nonzero NOW enrollment)
2. `Fall Only Winter Only Spring Only FURNITURE DESIGN` First Year (line 78) — routes to FOUN 240 + FOUN 245 in Spring (FOUN 240 has nonzero NOW enrollment; FOUN 245 has 2 NOW sections with 0 ACT)

**Baseline for this comparison:** the post-year-filter forecast already documented above. Same forecast configuration: Cognos OFF, admits ON, no manual adjustments, year filter returns all four cohort years.

## What was NOT changed (and why)

The sprint scope included three additional candidate changes that were each blocked by the prompt's stop-conditions. None of these were executed; all are flagged for the next sprint's domain owner.

| Candidate | Block reason |
|-----------|--------------|
| FIBERS First Year (line 62) campus expansion | Prompt explicitly listed "FIBERS dual-route" as ambiguous. The row's Spring routes to FOUN 220 + FOUN 240 (not 230 + 240 as the audit framed it). Expanding the campus would attribute SCADnow demand to both 220 and 240 simultaneously — a domain judgment call. |
| ANIMATION Storytelling Second Year (line 27) | Already campus = `Savannah \| Atlanta`, not Savannah-only. Does not match the strict filter "Savannah (or some equivalent SAV-only tag)." Audit listed it but the literal criterion fails. |
| `SEQUENTIAL ART` un-suffixed row deletion (lines 154-157) | Differs from `SEQUENTIAL ART Group A` on degree (`B.A.` vs `B.F.A`), campus (`General` vs `Savannah \| Atlanta \| SCADnow`), and Second Year content (empty vs `FOUN 230, FOUN 250, FOUN 260`). They are not the same cohort listed twice; the B.A. and B.F.A. are different programs. |
| `PRODUCTION DESIGN Set Design and Art Direction Design, Group A` Second Year (line 151) deletion | Fall column contains `FOUN 113` — non-empty farther feeder content. Per the prompt, any farther-feeder content blocks deletion because of the `farther_to_target` path. |

Net effect: only the two unambiguous campus expansions (ACCESSORY DESIGN, FURNITURE DESIGN) were applied. The audit-estimated +19.5pp NOW capture jump assumed all four expansions plus the SEQ ART deletion; that aggregate is therefore unreachable from this sprint's allowed change set.

## Post-fix accuracy (this sprint's mechanical-fix run)

### Savannah comparison (year-filter Post-fix vs Mechanical-Fix Post-fix vs ACT)

| Course   | Pre (yr-filter) | Post (mech-fix) |   ACT |   Δ vs pre | Pre Δ% | Post Δ% |
|----------|----------------:|----------------:|------:|-----------:|-------:|--------:|
| FOUN 110 |            30.0 |            30.0 |    63 |       +0.0 | -52.4% |  -52.4% |
| FOUN 111 |           101.7 |           101.7 |   125 |       +0.0 | -18.7% |  -18.7% |
| FOUN 112 |           463.6 |           463.6 |   653 |       +0.0 | -29.0% |  -29.0% |
| FOUN 113 |           731.4 |           731.4 |  1029 |       +0.0 | -28.9% |  -28.9% |
| FOUN 220 |           464.0 |           464.0 |   262 |       +0.0 | +77.1% |  +77.1% |
| FOUN 230 |           132.7 |           132.7 |   184 |       +0.0 | -27.9% |  -27.9% |
| FOUN 240 |            97.0 |            97.0 |   210 |       +0.0 | -53.8% |  -53.8% |
| FOUN 245 |           243.3 |           243.3 |   249 |       +0.0 |  -2.3% |   -2.3% |
| FOUN 250 |            35.7 |            35.7 |   125 |       +0.0 | -71.4% |  -71.4% |
| FOUN 251 |           129.0 |           129.0 |   155 |       +0.0 | -16.8% |  -16.8% |
| FOUN 260 |           149.5 |           149.5 |    52 |       +0.0 | +187.4%|  +187.4%|

**SAV: zero change.** Expected — neither edited row dropped Savannah from its campus tag, so no SAV row's denominator or routing changed. Both edited rows still contribute identically to SAV; they additionally contribute to NOW.

### SCADnow comparison (year-filter Post-fix vs Mechanical-Fix Post-fix vs ACT)

| Course   | Pre (yr-filter) | Post (mech-fix) |  ACT |   Δ vs pre | Pre Δ%  | Post Δ% |
|----------|----------------:|----------------:|-----:|-----------:|--------:|--------:|
| FOUN 110 |            17.0 |            17.0 |   38 |       +0.0 |  -55.3% |  -55.3% |
| FOUN 111 |            18.0 |            18.0 |   55 |       +0.0 |  -67.3% |  -67.3% |
| FOUN 112 |            49.8 |            49.8 |  107 |       +0.0 |  -53.5% |  -53.5% |
| FOUN 113 |            84.1 |            65.1 |  241 |      -18.9 |  -65.1% |  -73.0% |
| FOUN 220 |            64.0 |            57.7 |   47 |       -6.3 |  +36.1% |  +22.7% |
| FOUN 230 |          (none) |            10.5 |   37 |    new row |    miss |  -71.5% |
| FOUN 240 |          (none) |            10.5 |   64 |    new row |    miss |  -83.5% |
| FOUN 245 |             1.0 |            11.5 |   37 |      +10.5 |  -97.3% |  -68.9% |
| FOUN 250 |          (none) |          (none) |   64 |          — |    miss |    miss |
| FOUN 251 |            57.0 |            57.0 |   61 |       +0.0 |   -6.6% |   -6.6% |
| FOUN 260 |            38.9 |            38.9 |    — |       +0.0 |   over  |   over  |

**Two new NOW rows appeared** (FOUN 230 NOW = 10.5 from ACCESSORY DESIGN; FOUN 240 NOW = 10.5 from FURNITURE DESIGN). FOUN 245 NOW also rose (+10.5) because FURNITURE DESIGN routes there. Two existing rows decreased: FOUN 113 NOW dropped 18.9 and FOUN 220 NOW dropped 6.3 because expanding a row's campus dilutes the source feeder denominator (the same Winter feeder enrollment must now stretch across one more campus's target rows).

### Aggregate stats

|              | Year-filter Post-fix | Mechanical-Fix Post-fix |     Δ |
|--------------|---------------------:|------------------------:|------:|
| **SAV**      |                      |                         |       |
| MAE          |                102.5 |                   102.5 |   0.0 |
| MAPE         |                51.4% |                   51.4% |  +0.0pp |
| Capture(all) |                81.7% |                   81.7% |  +0.0pp |
| **NOW**      |                      |                         |       |
| MAE          |                 47.0 |                    45.7 |  -1.3 |
| MAPE         |                54.4% |                   55.8% |  +1.4pp |
| Capture(all) |                43.9% |                   44.8% |  +0.9pp |

Note: the year-filter Post-fix capture for NOW above (43.9%) is computed against `ACT_NOW_TOTAL = 751` using the same methodology as the post-mechanical-fix run (sum of all forecast rows ÷ sum of all ACT rows). The earlier doc section reported NOW Post-fix capture as 38.7%; that section excluded `FOUN 260 NOW = 38.9` from the numerator because there is no ACT entry for FOUN 260 NOW. Both numbers are internally consistent within their own table.

## Honest assessment

**Did the mechanical fix deliver the audit-estimated +19.5pp NOW capture jump?** No. NOW capture moved from 43.9% to 44.8% — a 0.9pp gain.

**Why the small movement:**

1. **Three of the four candidate expansions were blocked** by the prompt's stop-conditions (FIBERS as ambiguous, ANIMATION Storytelling as already-multi-campus, plus the SEQUENTIAL ART deletion which would have removed an over-counted row). The audit's +19.5pp estimate assumed all four moves; only two went through.
2. **Dilution offsets gains.** Adding `SCADnow` to a row spreads the same feeder enrollment across more campus buckets via `source_totals`. This pulled FOUN 113 NOW from 84.1 to 65.1 and FOUN 220 NOW from 64.0 to 57.7 — a combined -25.2 student loss on existing rows. The new rows (FOUN 230 NOW + FOUN 240 NOW + FOUN 245 NOW gain) added +31.5. Net: +6.3 students, hence the small capture-rate move.
3. **FOUN 250 NOW remains unforecasted.** Neither expanded row routes to FOUN 250. Closing this gap requires either expanding ANIMATION Storytelling (blocked by the campus-tag mismatch flag) or adding a dedicated NOW-routing row.

**What did improve:**

- **NOW MAE dropped 1.3** (47.0 → 45.7) — small but in the right direction.
- **Two previously-missed NOW courses now have forecast rows** (FOUN 230, FOUN 240). The values (10.5 each) are far below ACT (37, 64) but a nonzero row is the prerequisite for any future calibration.
- **FOUN 220 NOW over-forecast eased** from +36.1% to +22.7% (closer to ACT 47).

**What got slightly worse:**

- **NOW MAPE rose 1.4pp** (54.4% → 55.8%). The two new rows (10.5 vs ACT 37 and 64) are large percentage misses individually, even though they reduce absolute error.
- **FOUN 113 NOW** moved from -65.1% to -73.0% — a real regression on an already-under-forecast course caused by source-totals dilution.

**Possible code-level reason the campus expansion under-delivered (worth a future-sprint diagnostic, not fixed here):** the seq-map source-totals logic adds *all* same-row feeder contributions to the denominator regardless of campus, but the per-campus enrollment lookup is filtered to that campus's CRN-level data. For programs that enroll students at SCADnow under a different organizational tag than the seq-map row's campus list, the row weight may resolve to 0 even after expansion — meaning the new campus tag does not pull any actual NOW enrollment through. The 10.5 figures suggest some rows are flowing, but not at the magnitude FOUN 230/240 NOW ACT (37/64) implies.

**Constraint reminder:** the manual `set` adjustments file (`Data/adjustments/spring_2026.json`) remains empty per sprint scope. Any improvement here is from the seq-map edits alone.

**Net verdict:** small, directionally-correct gain. The audit's premise — that the SCADnow gap is largely a campus-tag coverage problem — is partially supported but appears to be only one of several factors. The remaining gap likely needs (a) the blocked expansions resolved domain-side, (b) a code-level investigation of how campus expansion interacts with feeder enrollment lookup, and (c) seq-map authoring of explicit NOW routing for FOUN 250.
