# Domain Pitfalls: Template Matching False Negatives in Game Automation

**Domain:** Game automation - visual item detection using template matching
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH (based on code analysis + general CV knowledge)

---

## Critical Pitfalls

### Pitfall 1: Undefined Variables Crash in CPU Template Matching

**What goes wrong:** CPU template matching crashes with `NameError` when building MatchResult objects.

**Root cause:** In `recognizer.py` lines 411-417, variables `w` and `h` are referenced but never defined in `_match_template()`. They should be `tmpl_w` and `tmpl_h` which are defined on lines 373-374.

```python
# Bug at lines 411-417:
results.append(
    MatchResult(
        template_name=template_name,
        x=int(x),
        y=int(y),
        width=int(w),      # BUG: w is undefined
        height=int(h),     # BUG: h is undefined
        confidence=float(confidence),
        center_x=int(x + w // 2),   # BUG: w undefined
        center_y=int(y + h // 2),  # BUG: h undefined
    )
)
```

**Consequences:**
- CPU mode crashes on every match attempt
- All template detection silently fails in CPU mode
- Error goes unnoticed until explicit testing

**Prevention:**
- Static analysis tools (pylint, mypy)
- Unit tests for both CPU and GPU code paths
- Code review focusing on variable scope

**Detection:**
- Run in CPU mode with test screenshots
- Check logs for `NameError` exceptions
- Add assertions on MatchResult fields

**Phase:** Must fix in Phase 1 (core functionality) — this is a blocking bug.

---

### Pitfall 2: Threshold Inconsistency Between Modules

**What goes wrong:** Different threshold values used across modules cause unpredictable detection behavior.

**Root cause:** Thresholds defined in multiple places with different values:
- `config.py`: `TEMPLATE_MATCH_THRESHOLD = 0.98`
- `hybrid_pipeline.py`: `_MATCH_THRESHOLD = 0.98` (hardcoded), `COLOR_THRESHOLD = 0.99` (hardcoded)
- `recognizer.py`: `threshold` parameter, `COLOR_THRESHOLD = 0.85`
- `config.py`: `ICON_FILTER_THRESHOLD = 0.8`

**Why it happens:** No single source of truth; values evolved independently.

**Consequences:**
- Hybrid mode uses 0.99 color threshold (very strict) vs template mode 0.85
- Icon filter at 0.8 may have different behavior than expected
- Debugging becomes difficult when thresholds aren't traceable

**Prevention:**
- Use config values consistently everywhere
- Pass thresholds through constructors, not globals
- Document what each threshold controls

**Phase:** Phase 2 (reliability hardening) — consolidate thresholds.

---

### Pitfall 3: Overly Strict Color Verification

**What goes wrong:** Valid items rejected because their average color differs slightly from template.

**Root cause:** Color similarity uses simple cosine similarity on average color. Gaming UI lighting changes, item aging effects, or partial occlusion cause color deviation.

**Specific issue:** In `recognizer.py` line 402, `color_sim < self.color_threshold` rejects matches even when the template IS present, just with slightly different lighting.

**Consequences:**
- False negatives for items that ARE present but under different lighting
- No detection for aged items (darker/lighter than fresh template)
- Detection fails when game UI has dynamic lighting effects

**Prevention:**
- Lower color threshold OR make it adaptive based on image variance
- Use histogram matching instead of average color
- Consider making color verification optional for stable templates

**Phase:** Phase 2 (reliability hardening).

---

### Pitfall 4: Aggressive Deduplication

**What goes wrong:** Legitimate items eliminated as "duplicates" due to small dedup distance.

**Root cause:** `DEDUP_DISTANCE_PX = 20` (20 pixels center-to-center) may be too small for items that naturally appear close together.

**Consequences:**
- Adjacent items incorrectly deduplicated
- Multi-item stacks detected as single item
- Some items never get sold

**Prevention:**
- Calibrate dedup distance based on actual item grid size
- Consider grid-based deduplication (items snap to grid)
- Log when deduplication eliminates items (currently not tracked well)

**Phase:** Phase 2 — add debug output to understand dedup behavior.

---

### Pitfall 5: Icon Filter False Positives

**What goes wrong:** Valid sellable items incorrectly eliminated by icon filter.

**Root cause:** `ItemCandidatePipeline._has_no_sell_icon()` searches the candidate region + margin for "cannot sell" icons. Small search margin or icon template mismatch causes false positives.

**Specific issue:** `ICON_SEARCH_MARGIN = 10` pixels may not be enough to avoid edge detection of adjacent icons.

**Consequences:**
- Items that CAN be sold are filtered out
- Revenue loss (items not sold)
- Silent failure — no indication items were filtered

**Prevention:**
- Increase search margin carefully
- Verify icon templates are accurate
- Add debug logging when icon filter triggers

**Phase:** Phase 2.

---

## Moderate Pitfalls

### Pitfall 6: Template Degradation

**What goes wrong:** Templates become outdated as game UI updates.

**Root cause:** 322+ templates stored as static PNG files. Game updates may change:
- Item icons (new items, redesigned icons)
- UI element appearance (color, shape)
- Font rendering in UI elements

**Prevention:**
- Version templates with game version
-定期重新采集关键模板
- Store templates with metadata (capture date, game version)

**Phase:** Phase 3 (polish) — establish template update process.

---

### Pitfall 7: Gray Zone Matches Silently Discarded

**What goes wrong:** Matches with confidence between 0.85-0.98 are found by OpenCV but then rejected by threshold.

**Root cause:** `cv2.matchTemplate()` finds all locations, but `np.where(res >= threshold)` discards sub-threshold matches. No visibility into how many matches were "close but not enough."

**Prevention:**
- Log counts of near-misses (confidence within 5% of threshold)
- Consider adaptive thresholding for borderline cases
- Save debug images showing failed match locations

**Phase:** Phase 2 — add visibility into gray zone.

---

### Pitfall 8: Image Preprocessing Differences

**What goes wrong:** Screenshots captured differently than templates (color space, resolution, compression).

**Root cause:** 
- Game renders at different resolution than template capture
- Screenshot includes UI elements not in template
- Color depth differences between capture and template

**Prevention:**
- Verify template capture uses exact same settings as runtime
- Normalize images before matching (resize, color correction)
- Log screenshot dimensions vs expected template dimensions

**Phase:** Phase 2.

---

### Pitfall 9: Hybrid Pipeline Icon Filter Not Implemented

**What goes wrong:** `HybridPipeline.process()` returns `filtered_count=0` as placeholder — icon filtering only works in template-only mode.

**Root cause:** Line 151 in `hybrid_pipeline.py` returns placeholder, icon filter never actually runs in hybrid mode.

**Consequences:**
- "Cannot sell" items may be processed in hybrid mode
- Inconsistent behavior between modes

**Prevention:**
- Implement icon filter in hybrid pipeline OR document limitation clearly
- Add mode-specific test coverage

**Phase:** Phase 2 — implement or document.

---

### Pitfall 10: Multi-Channel Image Handling Bug

**What goes wrong:** Images with 4 channels (BGRA) handled inconsistently.

**Root cause:** In `item_candidate_pipeline.py` line 174-175, BGRA→BGR conversion is done, but `recognizer.py` line 116-117 does similar conversion. If one path misses conversion, templates won't match.

**Prevention:**
- Centralize image normalization
- Add asserts checking channel count at pipeline entry
- Test with both 3-channel and 4-channel inputs

**Phase:** Phase 2.

---

## Debug Practices for False Negatives

### Debug Practice 1: Visual Diff of Failed Matches

**What:** When detection fails, save debug image showing:
- Original screenshot with detection overlays
- What templates were searched
- What matches were found (before threshold)
- Why matches were rejected (color similarity scores)

**How to implement:**
```python
# In _match_template, save debug info for near-misses
for y, x in zip(*locations):
    confidence = res[y, x]
    if confidence > self.threshold * 0.9:  # Near threshold
        log.debug(f"Near-miss: {template_name} at ({x},{y}) conf={confidence:.3f}")
```

**Phase:** Phase 2 — this is the primary observability improvement needed.

---

### Debug Practice 2: Pipeline Stage Counting

**What:** Track item counts at each pipeline stage to identify where items are lost.

**Current state:** `RoundSummary` tracks counts, but `filtered_count=0` in hybrid mode is a placeholder.

**Improvement needed:**
- Ensure all stages report accurate counts
- Log eliminated candidates with reasons
- Compare counts between template and hybrid modes

**Phase:** Phase 2.

---

### Debug Practice 3: Threshold Sensitivity Testing

**What:** Test detection rate across a range of thresholds (0.7-1.0) on known-positive images.

**How:**
1. Capture screenshot with known items
2. Run detection at each threshold
3. Plot detection count vs threshold
4. Identify the "cliff" where items drop off

**Phase:** Phase 2 — use to calibrate optimal thresholds.

---

### Debug Practice 4: Color Histogram Comparison

**What:** Instead of average color, compare full color histograms.

**Implementation:**
```python
def color_similarity_histogram(template: np.ndarray, roi: np.ndarray) -> float:
    template_hist = cv2.calcHist([template], [0, 1, 2], None, [32, 32, 32], [0, 256, 0, 256, 0, 256])
    roi_hist = cv2.calcHist([roi], [0, 1, 2], None, [32, 32, 32], [0, 256, 0, 256, 0, 256])
    return cv2.compareHist(template_hist, roi_hist, cv2.HISTCMP_CORREL)
```

**Phase:** Phase 3 — more robust color matching.

---

## Phase-Specific Warnings

| Phase | Topic | Pitfall | Mitigation |
|-------|-------|---------|------------|
| Phase 1 | Core functionality | **Pitfall 1** (undefined variables) | Fix the `w`/`h` bug before anything else |
| Phase 2 | Reliability | **Pitfall 2** (threshold inconsistency) | Consolidate all thresholds to config |
| Phase 2 | Reliability | **Pitfall 3** (color verification) | Lower or make adaptive |
| Phase 2 | Reliability | **Pitfall 4** (deduplication) | Add debug logging to see dedup in action |
| Phase 2 | Debug visibility | **Pitfall 7** (gray zone) | Log near-miss counts |
| Phase 2 | Hybrid mode | **Pitfall 9** (icon filter missing) | Implement or document limitation |
| Phase 3 | Polish | **Pitfall 6** (template degradation) | Establish template versioning |

---

## Quick Reference: Detection Failure Checklist

When items are missed, check in order:

1. [ ] **Bug in recognizer.py** — `w`/`h` undefined (CPU mode crashes)
2. [ ] **Threshold too high** — Check if items detected at lower thresholds
3. [ ] **Color verification failing** — Check `color_sim` scores in debug log
4. [ ] **Icon filter false positive** — Check if "cannot sell" icon template matches wrong element
5. [ ] **Deduplication too aggressive** — Check if adjacent items merged
6. [ ] **Template doesn't match** — Verify template capture vs current game UI
7. [ ] **Coordinate conversion bug** — Verify ROI→screen coordinate math
8. [ ] **Image format mismatch** — Check if screenshot is BGRA vs template BGR

---

## Sources

- OpenCV `matchTemplate` documentation — threshold behavior
- Code analysis of `vision/recognizer.py`, `vision/item_candidate_pipeline.py`, `vision/hybrid_pipeline.py`
- CONCERNS.md audit (2026-03-25) — existing known issues
