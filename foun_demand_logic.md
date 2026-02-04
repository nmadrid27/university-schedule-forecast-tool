# FOUN Course Demand Forecasting Logic

## Overview

This document describes the methodology for forecasting Foundation (FOUN) course demand by term and campus (SAV, ATL, SCADnow).

---

## 1. Regular Term Forecasting (Fall, Winter, Spring)

### Formula

$$
\text{Total Demand} = \text{New Student Demand} + \text{Continuing Student Demand (Sequence Progression)}
$$

### 1.1 New Student Demand

Calculated from Admissions Report (`PZSAAPF-SL31`):

#### Incoming Freshmen (FR)

- **Source**: Tabs containing term code (e.g., `202620` for Winter 26) and `FR`
- **Logic**: Use **First Interest** (Column R) × **Location**
- **Mapping**: Match to `Masterlist` First Year sequence guides
- **Calculation**: `Count of Students by Major/Location × Required FOUN Courses`

#### Incoming Transfers (TR)

- **Source**: Tabs containing term code and `TR`
- **Logic**: Use **Major** (Column AF) × **Location**
- **Mapping**: Match to `Masterlist` First Year sequence guides

### 1.2 Continuing Student Demand (Sequence Progression)

Students progress through the FOUN sequence each quarter:

| Previous Course | Next Course(s) | Distribution |
|-----------------|----------------|--------------|
| FOUN 110 | FOUN 112 | 100% |
| FOUN 111 | FOUN 113 | 100% |
| FOUN 112 | FOUN 220, 230, 240 | 50%, 30%, 20% (by major) |
| FOUN 113 | FOUN 220, 245 | 60%, 40% |
| FOUN 220 | FOUN 230, 240, 250 | 30%, 30%, 40% |
| FOUN 230 | FOUN 250, 260 | 70%, 30% |
| FOUN 240 | FOUN 250 | 100% |
| FOUN 245 | FOUN 251 | 100% |
| FOUN 250 | FOUN 260 | 15% (most complete) |

**Progression Rate**: 99% of students progress (1% retake same course)

---

## 2. Summer Term Forecasting

Summer enrollment is significantly lower than regular terms. Use these specific rates:

### 2.1 Summer Base Demand Rates

Calculate Summer demand from **Spring enrollment** using these progression rates:

| Summer Course | Source | Rate | Notes |
|---------------|--------|------|-------|
| FOUN 112 | Spring FOUN 110 | **35%** SAV, **4%** SCADnow | Primary summer progression |
| FOUN 113 | Spring FOUN 111 | **30%** SAV, **34%** SCADnow | High summer demand |
| FOUN 220 | Spring FOUN 112 + 113 | **6%** from 112, **8%** from 113 | Combined sources |
| FOUN 245 | Spring FOUN 113 | **6%** | |
| FOUN 230 | Spring FOUN 112 | **2%** | |
| FOUN 240 | Spring FOUN 112 | **1.6%** | |
| FOUN 251 | Spring FOUN 245 | **24%** | |
| FOUN 260 | Spring FOUN 250 | **15%** SAV, **16%** SCADnow | |
| FOUN 250 | Spring FOUN 240 | **3%** | |
| FOUN 111 | New admits | ~10 SAV | Minimal summer new admits |
| FOUN 110 | New admits | ~0 | Very few summer starts |

### 2.2 Summer Retake Calculations

Add failure/drop retakes to base demand:

| Scenario | Rate | Calculation |
|----------|------|-------------|
| **1% Retake** | 0.01 | Spring enrollment × 1% |
| **2% Retake** | 0.02 | Spring enrollment × 2% |

Apply retakes primarily to intro courses: FOUN 110, 111, 112, 113

### 2.3 Summer Section Calculation

- **Section Size**: 18 students
- **Formula**: `ceil(demand / 18)` with minimum of 1 section if demand > 0

### 2.4 Expected Summer Totals (Reference)

| Campus | Base Sections | With 1% Retakes | With 2% Retakes |
|--------|---------------|-----------------|-----------------|
| **Savannah** | 34-36 | 39-40 | 41-42 |
| **SCADnow** | 5 | 5 | 5 |
| **Total** | 39-41 | 44-45 | 46-47 |

---

## 3. Validation Against External Data

### Seat Projection Files

When available, compare forecasts against seat projection files (e.g., `clon_sav_atl_seat_projection_*.xlsx`):

> **Important**: Seat projection files often represent specific populations only:
>
> - FY (First Year) students
> - ESL-exempt students
> - Currently enrolled in previous term
>
> Your forecast should be **higher** than these projections since it includes ALL populations.

**Expected Ratios**:

- Forecast should be ~2-3x the FY-only projection
- Ratios >5x may indicate over-forecasting
- Forecast < Projection indicates missing demand

---

## 4. Data Sources

| File | Purpose |
|------|---------|
| `PZSAAPF-SL31 - Accepted Applicants...xlsx` | New student admissions data |
| `Masterlist.md` | FOUN course requirements by major |
| `FAll25.csv`, `Winter26.csv`, etc. | Historical enrollment by term |
| `Spring_2026_FOUN_Combined_Forecast.csv` | Source for Summer projections |
| `clon_sav_atl_seat_projection_*.xlsx` | FY ESL-exempt projections (validation) |

---

## 5. Output Files

| File | Contents |
|------|----------|
| `*_FOUN_Forecast.csv` | Demand totals by course |
| `*_FOUN_Forecast_By_Campus.csv` | Demand split by SAV/ATL/SCADnow |
| `*_FOUN_Forecast_With_Retakes.csv` | Includes retake scenarios |

---

## 6. Implementation

### Python Environment

```bash
source .venv/bin/activate
```

### Required Libraries

- `pandas`
- `openpyxl`

### Key Scripts

- `calculate_foun_demand.py` - Main forecasting script
- `prophet_forecast/` - Prophet-based forecasting module

---

## 7. Quick Reference: Section Size

| Course Type | Section Size |
|-------------|--------------|
| Standard FOUN | 18 students |
| Studio FOUN | 18 students |

**Formula**: `sections = ceil(demand / 18)` or `max(1, (demand + 17) // 18)`

---

*Last Updated: January 20, 2026*
