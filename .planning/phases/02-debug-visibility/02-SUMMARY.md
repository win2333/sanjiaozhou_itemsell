# Phase 2: Debug Visibility - Summary

**Plan:** 01
**Wave:** 1
**Completed:** 2026-03-25

## Tasks Completed

| Task | Status | Details |
|------|--------|---------|
| Task 1 | ✓ | Added `template_match_count` to RoundSummary, `template_name` to EliminatedCandidate |
| Task 2 | ✓ | HybridPipeline and ItemCandidatePipeline populate template_match_count |
| Task 3 | ✓ | Added funnel log + timing log in _run_one_cycle_new() |
| Task 4 | ✓ | Extended save_debug_frame() with all_template_matches parameter |

## Requirements Coverage

| Requirement | Status | Details |
|------------|--------|---------|
| DEBUG-01 | ✓ | Funnel log "YOLO:X → Template:Y → IconFilter:Z → Dedup:W → Final:V" |
| DEBUG-02 | ✓ | Timing log "[耗时] capture=XXms" |
| DEBUG-03 | ✓ | Annotated screenshots with green boxes + white template name labels |

## Files Modified

- `vision/item_types.py` — RoundSummary.template_match_count, EliminatedCandidate.template_name
- `vision/hybrid_pipeline.py` — Track and populate template_match_count
- `vision/item_candidate_pipeline.py` — Populate template_match_count=raw_count
- `core/loop.py` — Funnel log and timing log in _run_one_cycle_new()
- `utils/debug_visualizer.py` — all_template_matches parameter with green boxes + white labels

## Commit

`9182299` feat(phase2): debug visibility - funnel log, timing, annotated screenshots
