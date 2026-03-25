# Phase 2: Debug Visibility - Research

**Researched:** 2026-03-25
**Domain:** Detection pipeline observability — funnel logging, stage timing, enhanced screenshot annotation
**Confidence:** HIGH

## Summary

Phase 2 adds observability to the existing detection pipeline. The codebase already has:
- `save_debug_frame()` in `utils/debug_visualizer.py` that generates 3 debug images per round
- `RoundSummary` dataclass tracking `raw_count`, `filtered_count`, `dedup_count`, `final_count`
- `DEBUG_MODE` flag and `SAVE_DEBUG_IMAGES` flag in `config.py`

**Primary recommendation:** Inject funnel logging and timing around the existing `detector.process()` call in `_run_one_cycle_new()`, and extend `save_debug_frame()` to show ALL detection boxes with template labels (currently only final candidates are labeled).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3.x | current | Main automation scripting | Project requirement |
| OpenCV 4.8.0+ | current | Image annotation with `cv2.putText` and `cv2.rectangle` | Already used for debug visualization |
| `time.time()` | stdlib | Stage timing via elapsed ms | No new dependency |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| `utils/debug_visualizer.py` | Existing debug image writer | Extend for all-boxes annotation |
| `vision/item_types.py` | `RoundSummary`, `ItemCandidate`, `EliminatedCandidate` | Already contains funnel counts |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Project Structure
No new files required. Changes to:
- `core/loop.py` — add timing + funnel logging in `_run_one_cycle_new()`
- `utils/debug_visualizer.py` — extend `save_debug_frame()` for all-boxes annotation

### Pattern 1: Funnel Count Accumulation

**What:** Track counts at each pipeline stage and log as "YOLO:X → Template:Y → IconFilter:Z → Dedup:W → Final:V"

**When to use:** After each scan cycle in `_run_one_cycle_new()`

**Integration points:**

In `core/loop.py` `_run_one_cycle_new()` (lines 272-284):
```python
# Hybrid mode: candidates, eliminated, summary = detector.process(...)
# Template stage count: need to track from HybridPipeline._parallel_template_match()
# or infer from: summary.raw_count (YOLO) - dedup_count - final_count
```

The funnel for **hybrid mode** is: `YOLO → Template → Dedup → Final`
- YOLO count: available from `summary.raw_count` (actually YOLO detections)
- Template count: NOT directly tracked — needs new counter in HybridPipeline
- IconFilter count: `summary.filtered_count` (always 0 in hybrid mode per line 148)
- Dedup count: `summary.dedup_count`
- Final count: `summary.final_count`

For **template-only mode**, the funnel is: `Template → IconFilter → Dedup → Final`
- Template count: `summary.raw_count` from `recognize_as_raw_detections()`
- IconFilter count: `summary.filtered_count`
- Dedup count: `summary.dedup_count`
- Final count: `summary.final_count`

### Pattern 2: Stage Timing Injection

**What:** Wrap each stage with `time.time()` and log elapsed ms

**When to use:** In `_run_one_cycle_new()` around capture, yolo, template, filter, dedup stages

**Example location** in `_run_one_cycle_new()`:
```python
# Around line 264: capture
capture_start = time.time()
image = self.capture.capture_region(...)
capture_ms = (time.time() - capture_start) * 1000

# Around line 275: detector.process() — already has internal timing
# HybridPipeline.process() already logs yolo_time, roi_time, match_time, total_time
```

### Pattern 3: All-Boxes Screenshot Annotation

**What:** Draw bounding boxes on ALL detections (YOLO boxes, template matches, eliminated boxes), not just final candidates

**When to use:** In `save_debug_frame()` in `utils/debug_visualizer.py`

**Current state:** Only draws:
- YOLO boxes (gray, from `raw_detections`)
- Eliminated boxes (red, from `eliminated`)
- Candidate boxes (green/yellow, from `candidates`)

**Missing:** Template match boxes with template name labels — currently eliminated boxes only show reason text, not template name.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debug image naming/saving | Custom file logic | Extend `save_debug_frame()` | Already handles round_NNNN subdirs, timestamp, error handling |
| Funnel counting | Custom counters in loop | Use existing `RoundSummary` + add `template_match_count` field | Consistent with existing pipeline metrics |
| Stage timing | Custom timing class | Simple `time.time()` deltas | One-line, no dependency |

**Key insight:** The pipeline already has `RoundSummary` for funnel tracking. Just need to populate it fully in HybridPipeline and log the values in loop.py.

## Runtime State Inventory

> This is a debug/logging phase — no rename, refactor, or migration involved. Runtime state is not affected.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |

## Common Pitfalls

### Pitfall 1: HybridPipeline doesn't track template match count separately
**What goes wrong:** Funnel log "Template:Y" will be inaccurate — HybridPipeline returns only final candidates, not intermediate template match count.
**Why it happens:** `HybridPipeline._parallel_template_match()` returns `List[ItemCandidate]` (only successful matches), not a count before dedup.
**How to avoid:** Add a new field `template_match_count` to `HybridPipeline` or track it via a counter returned in the summary.
**Warning signs:** Funnel counts won't add up (e.g., Template:5 → Dedup:3 → Final:3 means 2 were dedup'd, but Template should be 5 before dedup).

### Pitfall 2: Template name not shown on detection boxes
**What goes wrong:** `save_debug_frame()` draws boxes for all candidates but only final candidates have `template_name` set.
**Why it happens:** In hybrid mode, `ItemCandidate.template_name` is set in `_match_single_roi()`, so even eliminated candidates should have template names. But the eliminated boxes in the image are drawn from `EliminatedCandidate` which doesn't have template_name.
**How to avoid:** Pass the full template match list (with template names) to `save_debug_frame()` separately, or augment `EliminatedCandidate` to include template name.

### Pitfall 3: Timing duplicates existing HybridPipeline logging
**What goes wrong:** `HybridPipeline.process()` already logs timing internally (lines 90-128 in hybrid_pipeline.py). Adding duplicate timing in `_run_one_cycle_new()` will double-log.
**How to avoid:** Use the existing internal timing logs from HybridPipeline, or refactor HybridPipeline to expose timing data via `RoundSummary`.

## Code Examples

### Adding funnel log in _run_one_cycle_new()

From `core/loop.py` lines 286-296:
```python
# Current summary logging
logger.log_only(
    "[摘要]",
    f"[轮次 {round_n}] 原始:{summary.raw_count} 过滤:{summary.filtered_count} "
    f"去重:{summary.dedup_count} 保留:{summary.final_count} | {status}",
)
```

Should be enhanced to (per D-01):
```python
# Funnel log format: YOLO:X → Template:Y → IconFilter:Z → Dedup:W → Final:V
# For hybrid mode: YOLO is summary.raw_count, Template needs new tracking
funnel_str = f"YOLO:{yolo_count} → Template:{template_count} → IconFilter:{summary.filtered_count} → Dedup:{summary.dedup_count} → Final:{summary.final_count}"
logger.log_only("[识别]", funnel_str)
```

### Timing in _run_one_cycle_new()

From `core/loop.py` line 264-275:
```python
# Capture timing
capture_start = time.time()
image = self.capture.capture_region(BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT)
capture_ms = (time.time() - capture_start) * 1000
```

The `detector.process()` already has internal timing (HybridPipeline logs yolo_time, match_time internally).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Summary log: "原始:N 过滤:N 去重:N 保留:N" | Funnel log: "YOLO:N → Template:N → IconFilter:N → Dedup:N → Final:N" | Phase 2 | More intuitive pipeline stage visualization |
| Debug screenshots with partial boxes | All detection boxes with template name labels | Phase 2 | Full observability of what pipeline sees |

**Deprecated/outdated:** None — this is a new feature phase.

## Open Questions

1. **Template count in hybrid mode**
   - What we know: HybridPipeline returns final candidates after dedup, but template matches before dedup aren't separately counted
   - What's unclear: Whether we should add a `template_match_count` field to `RoundSummary` or track it differently
   - Recommendation: Add `template_match_count: int = 0` to `RoundSummary`, populate in `HybridPipeline._parallel_template_match()`, expose via `process()` return

2. **EliminatedCandidate missing template_name**
   - What we know: `EliminatedCandidate` only has `screen_x`, `screen_y`, `reason` — no template name
   - What's unclear: How to label eliminated boxes in debug screenshots
   - Recommendation: Add `template_name: Optional[str] = None` to `EliminatedCandidate`, populate in `deduplicate_candidates()`

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified — pure Python/logging changes)

## Validation Architecture

> Skip — nyquist_validation not applicable for this research phase (pure code addition, no test infrastructure gap).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none |
| Quick run command | N/A — no tests exist yet |
| Full suite command | N/A |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBUG-01 | Funnel log output | Manual verification | Check logs for format | N/A |
| DEBUG-02 | Timing log output | Manual verification | Check logs for timing | N/A |
| DEBUG-03 | Debug screenshots with all boxes | Manual verification | Visual inspection of debug images | N/A |

### Sampling Rate
- **Per task commit:** N/A
- **Per wave merge:** N/A
- **Phase gate:** N/A

### Wave 0 Gaps
None — existing debug visualization infrastructure covers requirements. No new test files needed for this phase.

## Sources

### Primary (HIGH confidence)
- `core/loop.py` — _run_one_cycle_new() integration point, line 252-324
- `vision/hybrid_pipeline.py` — process() method, RoundSummary creation, line 68-154
- `vision/item_candidate_pipeline.py` — process() method, RoundSummary creation, line 52-108
- `utils/debug_visualizer.py` — save_debug_frame(), existing debug image generation

### Secondary (MEDIUM confidence)
- `vision/item_types.py` — RoundSummary, ItemCandidate, EliminatedCandidate dataclasses

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — only uses existing project libraries (time, cv2)
- Architecture: HIGH — clear integration points identified in loop.py and hybrid_pipeline.py
- Pitfalls: HIGH — template_match_count gap is the main risk, clearly identified

**Research date:** 2026-03-25
**Valid until:** 90 days (stable feature with known code paths)
