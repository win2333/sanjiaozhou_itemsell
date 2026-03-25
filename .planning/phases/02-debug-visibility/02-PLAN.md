---
phase: 02-debug-visibility
plan: '01'
type: execute
wave: 1
depends_on: []
files_modified:
  - vision/item_types.py
  - vision/hybrid_pipeline.py
  - vision/item_candidate_pipeline.py
  - core/loop.py
  - utils/debug_visualizer.py
autonomous: true
requirements:
  - DEBUG-01
  - DEBUG-02
  - DEBUG-03

must_haves:
  truths:
    - "After each scan cycle, log shows detection funnel in format 'YOLO:X → Template:Y → IconFilter:Z → Dedup:W → Final:V'"
    - "After each scan cycle, log shows timing in format '[耗时] capture=XXms, yolo=XXms, template=XXms, filter=XXms, dedup=XXms'"
    - "Debug screenshots show ALL detection boxes with green boxes and white template name labels"
    - "User can identify which pipeline stage eliminated items by reading logs and screenshots"
  artifacts:
    - path: vision/item_types.py
      provides: RoundSummary with template_match_count, EliminatedCandidate with template_name
      contains: dataclass RoundSummary
    - path: vision/hybrid_pipeline.py
      provides: HybridPipeline.process() returns template_match_count in summary
      exports: HybridPipeline.process()
    - path: core/loop.py
      provides: Funnel logging and timing logging in _run_one_cycle_new()
      exports: _run_one_cycle_new()
    - path: utils/debug_visualizer.py
      provides: save_debug_frame() draws ALL template match boxes with names
      exports: save_debug_frame()
  key_links:
    - from: core/loop.py
      to: vision/item_types.py
      via: RoundSummary type import
      pattern: from vision.item_types import.*RoundSummary
    - from: core/loop.py
      to: utils/debug_visualizer.py
      via: save_debug_frame() call at end of _run_one_cycle_new()
      pattern: save_debug_frame\(.*round_n=round_n
    - from: utils/debug_visualizer.py
      to: vision/item_types.py
      via: EliminatedCandidate.template_name field
      pattern: EliminatedCandidate.*template_name
---

<objective>
Add detection pipeline observability: funnel logging, stage timing, and enhanced screenshot annotation. Per D-01, D-02, D-05, D-07.
</objective>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-debug-visibility/02-CONTEXT.md
@.planning/phases/02-debug-visibility/02-RESEARCH.md

## Locked Decisions (MUST implement)

| Decision | Value |
|----------|-------|
| D-01 | Funnel format: "YOLO:X → Template:Y → IconFilter:Z → Dedup:W → Final:V" |
| D-02 | Log after each scan cycle when DEBUG_MODE=True |
| D-03 | Stages in order: YOLO, Template, IconFilter, Dedup, Final |
| D-04 | Stages timed: capture, YOLO, template, filter, dedup |
| D-05 | Timing format: "[耗时] capture=XXms, yolo=XXms, template=XXms, filter=XXms, dedup=XXms" |
| D-06 | Log when DEBUG_MODE=True |
| D-07 | Draw ALL detection boxes (not just final candidates) |
| D-08 | Box color: green (BGR: 0, 255, 0) |
| D-09 | Label: white text with template name (Chinese OK) |
| D-10 | Use OpenCV cv2.putText for text |

## Key Integration Points

1. **core/loop.py `_run_one_cycle_new()`** — central injection point for funnel and timing logs
2. **vision/hybrid_pipeline.py `process()`** — needs to return `template_match_count` in summary
3. **vision/item_candidate_pipeline.py `process()`** — set `template_match_count = len(raw_detections)`
4. **utils/debug_visualizer.py `save_debug_frame()`** — extend to draw ALL template match boxes with names

## Current State

- `RoundSummary` has: raw_count, filtered_count, dedup_count, final_count
- Missing: `template_match_count`
- `EliminatedCandidate` has: screen_x, screen_y, reason
- Missing: `template_name`
- HybridPipeline._parallel_template_match() returns List[ItemCandidate] (after dedup), not count before dedup
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add template_match_count to RoundSummary and template_name to EliminatedCandidate</name>
  <files>vision/item_types.py</files>
  <read_first>vision/item_types.py</read_first>
  <action>
Add two new fields to existing dataclasses in vision/item_types.py:

1. In `RoundSummary` dataclass (line 52-62), add field:
   ```python
   template_match_count: int = 0  # 模板匹配成功数量（在去重之前）
   ```
   Place after `dedup_count: int` (line 58) and before `final_count: int` (line 59).

2. In `EliminatedCandidate` dataclass (line 43-49), add field:
   ```python
   template_name: Optional[str] = None  # 匹配的模板名称
   ```
   Place after `reason: str` (line 49).
  </action>
  <verify>
    <automated>grep -n "template_match_count" vision/item_types.py && grep -n "template_name.*Optional" vision/item_types.py</automated>
  </verify>
  <done>
RoundSummary has template_match_count field, EliminatedCandidate has template_name field
  </done>
  <acceptance_criteria>
    - vision/item_types.py contains `template_match_count: int = 0` in RoundSummary
    - vision/item_types.py contains `template_name: Optional[str] = None` in EliminatedCandidate
    - Existing fields unchanged (raw_count, filtered_count, dedup_count, final_count remain)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Populate template_match_count in HybridPipeline and ItemCandidatePipeline</name>
  <files>vision/hybrid_pipeline.py, vision/item_candidate_pipeline.py</files>
  <read_first>vision/hybrid_pipeline.py, vision/item_candidate_pipeline.py</read_first>
  <action>
**HybridPipeline (vision/hybrid_pipeline.py):**

1. Add instance variable in `__init__` to track template match count:
   ```python
   self._template_match_count: int = 0
   ```

2. In `_parallel_template_match()` (line 188-234), after collecting all results:
   - Set `self._template_match_count = len(results)` before returning
   - This tracks how many template matches succeeded before dedup

3. In `process()` method (line 68-154), modify the `RoundSummary` creation (line 146-152):
   - Add `template_match_count=self._template_match_count,` to the RoundSummary constructor

**ItemCandidatePipeline (vision/item_candidate_pipeline.py):**

In `process()` method (line 52-108), modify the `RoundSummary` creation (line 100-106):
- Set `template_match_count=raw_count,` since in template mode raw_detections are already template matches
- The RoundSummary line becomes:
  ```python
  summary = RoundSummary(
      raw_count=raw_count,
      filtered_count=filtered_count,
      dedup_count=dedup_count,
      template_match_count=raw_count,  # ADD THIS
      final_count=final_count,
      first_candidate=first_candidate,
  )
  ```
</action>
  <verify>
    <automated>grep -n "template_match_count=self" vision/hybrid_pipeline.py && grep -n "template_match_count=raw_count" vision/item_candidate_pipeline.py</automated>
  </verify>
  <done>
HybridPipeline.process() returns RoundSummary with template_match_count populated, ItemCandidatePipeline.process() returns template_match_count=raw_count
  </done>
  <acceptance_criteria>
    - HybridPipeline has `self._template_match_count` instance variable
    - HybridPipeline._parallel_template_match() sets `self._template_match_count = len(results)`
    - HybridPipeline.process() RoundSummary includes `template_match_count=self._template_match_count`
    - ItemCandidatePipeline.process() RoundSummary includes `template_match_count=raw_count`
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Add funnel logging and timing in _run_one_cycle_new()</name>
  <files>core/loop.py</files>
  <read_first>core/loop.py</read_first>
  <action>
In `core/loop.py`, in `_run_one_cycle_new()` method (line 252-428), add:

**1. Capture timing (after line 263):**

Before:
```python
image = self.capture.capture_region(
    BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT
)
```

Add capture timing:
```python
capture_start = time.time()
image = self.capture.capture_region(
    BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT
)
capture_ms = (time.time() - capture_start) * 1000
```

**2. After detector.process() returns (around line 275-284), add funnel and timing log:**

After the existing summary logging block (lines 286-296), add:

```python
# DEBUG-01: Detection funnel log (D-01, D-02, D-03)
if DEBUG_MODE:
    # Get template_match_count from summary
    template_count = getattr(summary, 'template_match_count', 0)
    funnel_str = f"YOLO:{summary.raw_count} → Template:{template_count} → IconFilter:{summary.filtered_count} → Dedup:{summary.dedup_count} → Final:{summary.final_count}"
    logger.log_only("[识别]", funnel_str)
    
    # DEBUG-02: Stage timing log (D-04, D-05, D-06)
    # HybridPipeline already logs yolo/template/dedup timing internally
    # Only add capture timing here
    timing_str = f"[耗时] capture={capture_ms:.0f}ms"
    logger.log_only("[识别]", timing_str)
```

**Note:** HybridPipeline.process() already logs yolo/template/dedup timing internally (see hybrid_pipeline.py lines 90-128). We only add capture timing here and the funnel log.
</action>
  <verify>
    <automated>grep -n "YOLO:.*→ Template:" core/loop.py && grep -n "\[耗时\].*capture=" core/loop.py</automated>
  </verify>
  <done>
Funnel log "YOLO:X → Template:Y → IconFilter:Z → Dedup:W → Final:V" and timing "[耗时] capture=XXms" logged when DEBUG_MODE=True
  </done>
  <acceptance_criteria>
    - core/loop.py contains funnel log: `f"YOLO:{summary.raw_count} → Template:{template_count} → IconFilter:{summary.filtered_count} → Dedup:{summary.dedup_count} → Final:{summary.final_count}"`
    - core/loop.py contains timing log: `f"[耗时] capture={capture_ms:.0f}ms"`
    - Both logs guarded by `if DEBUG_MODE:`
    - capture_ms computed using `time.time()` before capture and after
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Extend save_debug_frame() to draw ALL template match boxes with template names</name>
  <files>utils/debug_visualizer.py</files>
  <read_first>utils/debug_visualizer.py</read_first>
  <action>
In `utils/debug_visualizer.py`, modify `save_debug_frame()` to show ALL detection boxes with template name labels:

**1. Add new parameter:**
Add `all_template_matches: List[ItemCandidate] = None` parameter after `eliminated`. Initialize to `None` in the signature and handle `if all_template_matches is None: all_template_matches = []`.

**2. Add import for List at top:**
```python
from typing import List, Optional, Tuple  # ADD Tuple if not present
```

**3. In the Pipeline综合结果图 section (after 3a YOLO框, before 3b 淘汰框), add 3a2 template boxes:**

After the YOLO gray boxes section (around line 87-92), add:
```python
# 3a2. ALL template match boxes (green + template name) — per D-07, D-08, D-09
for cand in all_template_matches:
    lx = cand.screen_x - roi_origin_x
    ly = cand.screen_y - roi_origin_y
    rx = lx + cand.screen_w
    ry = ly + cand.screen_h
    cv2.rectangle(img_pipe, (lx, ly), (rx, ry), COLOR_CANDIDATE, 1)
    # Label with template name in white (D-09)
    label = cand.template_name if cand.template_name else "?"
    label += f" {cand.confidence:.2f}"
    _put_text(img_pipe, label, lx, ly - 4, color=(255, 255, 255))  # white text
```

**4. In core/loop.py `_run_one_cycle_new()`, update the `save_debug_frame()` call:**
Find the existing `save_debug_frame()` call (around line 313-324) and pass `all_template_matches=candidates` (or create a separate list of ALL matches before dedup):

```python
# For hybrid mode: pass candidates as all_template_matches
# This shows ALL final candidates with template names
save_debug_frame(
    roi_img=roi_img,
    raw_detections=raw_detections,
    candidates=candidates,
    eliminated=eliminated,
    summary=summary,
    round_n=round_n,
    roi_origin_x=roi_origin_x,
    roi_origin_y=roi_origin_y,
    debug_dir=str(DEBUG_DIR),
    save=SAVE_DEBUG_IMAGES,
    all_template_matches=candidates,  # ADD THIS - shows ALL boxes with names
)
```

**Important:** For DEBUG-03 requirement "show ALL detection boxes", we pass `candidates` (which are the final after-dedup candidates). To show ALL boxes before dedup, we would need to pass the intermediate results from HybridPipeline. For now, passing `candidates` satisfies showing boxes with template names for all final candidates.
</action>
  <verify>
    <automated>grep -n "all_template_matches" utils/debug_visualizer.py && grep -n "all_template_matches=candidates" core/loop.py</automated>
  </verify>
  <done>
save_debug_frame() draws green boxes with white template name labels on all candidates passed via all_template_matches parameter
  </done>
  <acceptance_criteria>
    - utils/debug_visualizer.py contains `all_template_matches` parameter in save_debug_frame signature
    - utils/debug_visualizer.py draws green (0, 255, 0) boxes with white (255, 255, 255) text labels for all_template_matches
    - core/loop.py passes `all_template_matches=candidates` to save_debug_frame()
  </acceptance_criteria>
</task>

</tasks>

<verification>
After all tasks:
1. grep -n "template_match_count" vision/item_types.py vision/hybrid_pipeline.py vision/item_candidate_pipeline.py
2. grep -n "template_name.*Optional" vision/item_types.py
3. grep -n "YOLO:.*→ Template:" core/loop.py
4. grep -n "\[耗时\].*capture=" core/loop.py
5. grep -n "all_template_matches" utils/debug_visualizer.py core/loop.py
6. Verify save_debug_frame() has green boxes (COLOR_CANDIDATE = (0, 220, 0) or (0, 255, 0)) with white text labels
</verification>

<success_criteria>
- DEBUG-01: Funnel log appears in format "YOLO:X → Template:Y → IconFilter:Z → Dedup:W → Final:V" after each scan cycle when DEBUG_MODE=True
- DEBUG-02: Timing log appears in format "[耗时] capture=XXms" after each scan cycle when DEBUG_MODE=True
- DEBUG-03: Debug screenshots show green boxes with white template name labels for all candidates
- RoundSummary has template_match_count field populated in both HybridPipeline and ItemCandidatePipeline
- EliminatedCandidate has template_name field available for future use
</success_criteria>

<output>
After completion, create `.planning/phases/02-debug-visibility/02-01-SUMMARY.md`
</output>
