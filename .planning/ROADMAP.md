# Roadmap

## Phases

- [x] **Phase 1: Bug Fixes & Debug Infrastructure** — Fix CPU crash, consolidate thresholds, lower strict thresholds
- [x] **Phase 2: Debug Visibility** — Detection funnel log, stage timing, enhanced screenshots
- [ ] **Phase 3: Advanced Debug & Polish** — Confidence histogram, silent failure detector

## Phase Details

### Phase 1: Bug Fixes & Debug Infrastructure

**Goal**: Bot runs without crashing in CPU mode, with consolidated configuration

**Depends on**: Nothing (first phase)

**Requirements**: DET-01, DET-02, DET-03, DET-04

**Success Criteria** (what must be TRUE):
1. Bot runs in CPU mode without crashing on undefined variables `w`/`h`
2. All threshold constants consolidated to `config.py` as single source of truth
3. Template match threshold configurable via `config.py` (starting at 0.95)
4. Color verification threshold configurable via `config.py` (starting at 0.95)
5. Bot completes at least 5 consecutive scan cycles without crash or error

**Plans**: 1 plan

Plans:
- [x] 01-PLAN.md — Fix CPU crash, consolidate thresholds

---

### Phase 2: Debug Visibility

**Goal**: Detection pipeline decisions are observable at each stage

**Depends on**: Phase 1

**Requirements**: DEBUG-01, DEBUG-02, DEBUG-03

**Success Criteria** (what must be TRUE):
1. After each scan cycle, log shows detection funnel: "YOLO:X → Template:Y → IconFilter:Z → Dedup:W → Final:V"
2. After each scan cycle, log shows stage timing breakdown (capture, YOLO, template, filter, dedup)
3. Debug screenshots show ALL detection boxes with template name labels (not just candidates)
4. User can identify which pipeline stage eliminated valid items by reading logs and screenshots

**Plans**: 1 plan

Plans:
- [x] 02-PLAN.md — Debug visibility: funnel logging, timing, enhanced screenshots

---

### Phase 3: Advanced Debug & Polish

**Goal**: Historical detection patterns visible, silent failures detected and alerted

**Depends on**: Phase 2

**Requirements**: DEBUG-04, DEBUG-05

**Success Criteria** (what must be TRUE):
1. On startup, confidence histogram displays distribution from last N cycles
2. After N consecutive zero-detection cycles (configurable), warning is logged
3. User can tune thresholds based on confidence histogram feedback

**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Bug Fixes & Debug Infrastructure | 1/1 | Complete | 2026-03-25 |
| 2. Debug Visibility | 1/1 | Complete | 2026-03-25 |
| 3. Advanced Debug & Polish | 0/1 | Not started | - |

---

## Coverage

**All 9 v1 requirements mapped to phases:**

| Requirement | Phase | Description |
|-------------|-------|-------------|
| DET-01 | 1 | Fix CPU mode crash — undefined variables `w`/`h` |
| DET-02 | 1 | Consolidate threshold constants to `config.py` |
| DET-03 | 1 | Lower template match threshold to 0.95 |
| DET-04 | 1 | Lower color verification threshold to 0.95 |
| DEBUG-01 | 2 | Detection funnel text log |
| DEBUG-02 | 2 | Stage timing breakdown |
| DEBUG-03 | 2 | Enhanced annotated screenshots |
| DEBUG-04 | 3 | Confidence histogram on startup |
| DEBUG-05 | 3 | Silent failure detector |

**Coverage: 9/9 requirements mapped ✓**
**No orphaned requirements ✓**
