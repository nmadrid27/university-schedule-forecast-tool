# Adjustments Policy

Manual adjustments are for correcting model output against measured ground truth, not for matching another projection.

Use adjustments when:
- PZSMSCP ACT, MAX, or waitlist data shows a known anomaly.
- A course is new and the model has no usable history.
- A registrar-validated routing change is not yet encoded in the sequence map.

Do not use adjustments to:
- Force the model to match an older planning projection.
- Hide a known sequencing-map gap without documenting the reason.
- Replace source-data fixes that can be made in the sequencing map or Master Schedule import.

When adding an adjustment, include a short reason with the data source and date, for example: `Set FOUN 230 SCADnow to Spring 2026 ACT from PZSMSCP pulled 2026-05-05`.
