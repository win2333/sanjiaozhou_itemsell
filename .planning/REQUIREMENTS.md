# Requirements

## v1 Requirements

### Detection Bug Fixes

- [ ] **DET-01**: Fix CPU mode crash — undefined variables `w`/`h` → `tmpl_w`/`tmpl_h` in `recognizer.py` lines 411-417
- [ ] **DET-02**: Consolidate all threshold constants to `config.py` as single source of truth (remove scattered thresholds from modules)
- [ ] **DET-03**: Lower template match threshold from 0.98 to 0.95 as starting point (configurable)
- [ ] **DET-04**: Lower color verification threshold from 0.99 to 0.95 in hybrid mode

### Debug Visibility

- [ ] **DEBUG-01**: Detection funnel text log — output "YOLO:12 → Template:8 → IconFilter:6 → Dedup:5 → Final:3" after each scan cycle
- [ ] **DEBUG-02**: Stage timing breakdown — log time spent in each pipeline stage (capture, YOLO, template, filter, dedup)
- [ ] **DEBUG-03**: Enhanced annotated screenshots — label ALL detection boxes with template name
- [ ] **DEBUG-04**: Confidence histogram on startup — show confidence distribution from last N cycles to guide threshold tuning
- [ ] **DEBUG-05**: Silent failure detector — warn after N consecutive zero-detection cycles

### Out of Scope

- Multi-scale template matching — deferred to future phase
- Cluster-based deduplication — deferred to future phase
- Adaptive per-template thresholds — requires historical data collection
- YOLO model retraining — only use existing model

## v2 Requirements (Deferred)

- [ ] Multi-scale template matching (0.8x-1.2x scales)
- [ ] Cluster-based deduplication with elimination trace
- [ ] Adaptive thresholds based on historical match quality
- [ ] Cross-run metrics persistence for heatmap analysis

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DET-01 | 1 | — |
| DET-02 | 1 | — |
| DET-03 | 1 | — |
| DET-04 | 1 | — |
| DEBUG-01 | 2 | — |
| DEBUG-02 | 2 | — |
| DEBUG-03 | 2 | — |
| DEBUG-04 | 3 | — |
| DEBUG-05 | 3 | — |
