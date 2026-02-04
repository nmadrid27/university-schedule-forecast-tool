# Forecast Tool Runbook

## Purpose
Forecast Spring 2026 FOUN sections for Savannah and SCADnow using the sequencing guide and Fall/Winter enrollments.

## Standard workflow
1) Update `forecast_config.json` with the correct input file paths and parameters.
2) Run:
   `python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json`
3) Use the output CSV defined in the config.

## Inputs
- Sequencing guide: `Data/FOUN_sequencing_map_by_major.csv`
- Fall/Winter enrollment (default): `Data/FAll25.csv` and `Data/Winter26.csv`
- Alternative: `Data/Master Schedule of Classes.csv` with term codes set in `forecast_config.json`

## Logic and assumptions
- Sequencing guide drives which Fall/Winter courses map into Spring courses.
- "CHOICE" course lists split demand evenly across the listed FOUN courses.
- Progression rate is applied per term (Fall -> Spring = 2 transitions, Winter -> Spring = 1).
- Campus filtering uses the `campus` column in the sequencing guide. "General" applies to all.
- SCADnow enrollments are detected by room `OLNOW` or section starting with `N`.
  - When using the Master Schedule file, campus comes from the `CAMPUS` column (`SAV` or `NOW`).

## Output
- CSV with course, campus, projected seats, and sections.
- Default output path: `Data/Spring_2026_FOUN_Forecast_SAV_SCADnow_From_Sequence_Guides.csv`

## Change guidance
- If the term files change names, update `forecast_config.json`.
- If capacity or progression rate changes, update `forecast_config.json`.
- If SCADnow detection rules change, update `load_term_enrollments` in `forecast_spring26_from_sequence_guides.py`.
