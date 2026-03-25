# State

## Project Reference

**Project:** sanjiaozhouGame (游戏装备自动出售工具)
**Core Value:** 可靠的物品检测 — 每次扫描都能准确识别所有可售物品，不漏识别；同时具备完整的检测过程可观测性
**Current Focus:** Phase 1: Bug Fixes & Debug Infrastructure

## Current Position

**Phase:** 1 — Bug Fixes & Debug Infrastructure
**Plan:** Not started
**Status:** Not started
**Progress:** [=---------] 0%

## Phase Dependencies

```
Phase 1 (Bug Fixes & Debug Infra)
    ↓
Phase 2 (Debug Visibility)
    ↓
Phase 3 (Advanced Debug & Polish)
```

## Accumulated Context

### Key Decisions
- CPU-only mode (no GPU acceleration)
- Template matching as primary detection method
- Fixed coordinate mode for game window

### Technical Notes
- Tech stack: Python 3 + OpenCV + EasyOCR + pydirectinput + mss
- Architecture: HybridPipeline (YOLO粗检 + 模板精检) + ItemCandidatePipeline (5级过滤)
- Known issues: Template recognition occasional misses, debug output insufficient

### Requirements Coverage
- v1 requirements: 9 total
- Phase 1: 4 (DET-01 to DET-04)
- Phase 2: 3 (DEBUG-01 to DEBUG-03)
- Phase 3: 2 (DEBUG-04 to DEBUG-05)

## Session Continuity

- Last session: Research completed, requirements gathered
- Next action: Plan Phase 1 with `/gsd-plan-phase 1`
