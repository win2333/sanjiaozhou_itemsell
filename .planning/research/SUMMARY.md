# Project Research Summary

**Project:** sanjiaozhouGame (Game Automation Bot)
**Domain:** Game automation computer vision - template matching reliability and debug visualization
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a game automation bot using computer vision (template matching + YOLO hybrid) to detect and sell items in a game called "三角州" (Sanjiaozhou/Zhou). The core problem is **false negatives in template matching** — items that should be detected are being silently discarded, causing revenue loss. Research across stack, features, architecture, and pitfalls reveals a pipeline with good foundation but missing debug instrumentation and several reliability issues that prevent confident operation.

Experts in this domain solve false negatives through **multi-scale template matching** with adaptive thresholds, stage-based debug hooks for observability, and cluster-based deduplication instead of pairwise distance. The recommended approach is to build a stage-based detection pipeline with lazy-evaluated debug hooks, implement per-template adaptive thresholds, and add comprehensive debug output so detection failures can be diagnosed rather than silently ignored.

Key risks: A blocking bug (undefined variables in CPU template matching), threshold inconsistency across modules, and overly strict color verification. These must be addressed before the bot can run reliably in production.

## Key Findings

### Recommended Stack

The existing stack (OpenCV, numpy, Pillow) is sufficient. Key improvements needed in how technologies are used:

**Core technologies:**
- **OpenCV matchTemplate (TM_CCOEFF_NORMED)** — Use instead of TM_SQDIFF_NORMED for lighting robustness; already in stack but used incorrectly
- **Multi-scale matching (cv2.resize + pyramid)** — Handle size variations without adding dependencies; 5 scales [0.8-1.2]
- **Bilateral filter (cv2.bilateralFilter)** — Edge-preserving denoising; better than Gaussian for template matching
- **CLAHE preprocessing (cv2.createCLAHE)** — Adaptive histogram equalization for lighting variation compensation
- **matplotlib** — Debug heatmaps and visualization; add as dependency for debug mode

**What NOT to use:**
- TM_SQDIFF_NORMED (sensitive to brightness differences)
- TM_CCORR_NORMED (less reliable than CCOEFF)
- Single-scale template matching (causes false negatives on size variations)
- Fixed 0.98 threshold without tuning (too strict for some items)

### Expected Features

**Must have (table stakes):**
- **Enhanced annotated screenshots** — Template name labels on all detection boxes, not just candidates
- **Detection bounding boxes with confidence** — Visual confirmation of what was detected where
- **Structured log output** — Text logs for programmatic debugging
- **Stage timing metrics** — Which pipeline stage is bottleneck when cycle is slow
- **Detection funnel comment** — "YOLO:12 → Template:8 → IconFilter:6 → Dedup:5 → Final:3"
- **Fail-soft with detailed logging** — Warn on zero detections, don't silently skip

**Should have (competitive differentiators):**
- **Pipeline stage visualization** — Show each filtering stage's effect on detection counts
- **Per-item detection certainty explainer** — For each box, show "template:0.92 > 0.8"
- **Confidence histogram export** — CSV for threshold tuning by power users
- **Silent failure detector** — Alert after N consecutive zero-detection cycles

**Defer (v2+):**
- Detection heatmap (persistent visualization by screen region)
- Visual diff between template versions
- Live debug overlay (cv2.imshow)

### Architecture Approach

The recommended architecture uses a **stage-based detection pipeline with lazy-evaluated debug hooks**. Each pipeline stage (Capture, Preprocess, YOLO, ROI Extract, Multi-Scale Template Match, Threshold, Deduplication, Ranking) has conditional debug hooks that only capture data when enabled, avoiding performance overhead in production.

**Major components:**
1. **RobustDetectionPipeline** — Main orchestrator, manages stage execution order
2. **DebugContext** — Accumulates debug artifacts across stages, lazy evaluation
3. **MultiScaleMatcher** — Multi-scale template matching with consistency check across scales
4. **AdaptiveThreshold** — Per-template confidence thresholds based on historical match quality
5. **SpatialDeduplicator** — Cluster-based deduplication (DBSCAN) preserving elimination trace
6. **StageHook** — Conditional debug hook with lazy evaluation for zero-overhead when disabled

Key architectural patterns: Stage Hook with Lazy Evaluation (zero overhead when disabled), Adaptive Threshold (reduces false negatives for "easy" templates), Cluster-Based Deduplication (preserves items pairwise comparison would merge), Multi-Scale Consistency Check (catches false positives from scale mismatch).

### Critical Pitfalls

1. **Undefined Variables Bug (CPU mode crash)** — `w` and `h` undefined in `recognizer.py` lines 411-417; should be `tmpl_w`/`tmpl_h`. CPU template matching crashes silently. **Fix in Phase 1.**

2. **Threshold Inconsistency Across Modules** — `config.py` has TEMPLATE_MATCH_THRESHOLD=0.98, `hybrid_pipeline.py` has hardcoded _MATCH_THRESHOLD=0.98 and COLOR_THRESHOLD=0.99, `recognizer.py` has threshold parameter and COLOR_THRESHOLD=0.85. No single source of truth. **Consolidate in Phase 2.**

3. **Overly Strict Color Verification** — Color similarity uses cosine similarity on average color. Gaming UI lighting changes cause valid items to be rejected. Line 402 in `recognizer.py`: `color_sim < self.color_threshold` rejects matches even when template IS present. **Make adaptive in Phase 2.**

4. **Aggressive Deduplication (DEDUP_DISTANCE_PX=20)** — Items closer than 20px center-to-center considered duplicates. Adjacent legitimate items incorrectly eliminated. **Add debug logging to understand behavior in Phase 2.**

5. **Icon Filter False Positives** — Valid sellable items incorrectly eliminated by icon filter. `ICON_SEARCH_MARGIN = 10` pixels may not be enough. Silent failure. **Add debug logging when filter triggers, Phase 2.**

## Implications for Roadmap

### Phase 1: Debug Infrastructure & Bug Fixes
**Rationale:** The undefined variable bug (Pitfall 1) is a blocking issue — CPU mode crashes on every match. Before any reliability work, the bot must not crash. This phase establishes the debug infrastructure needed to validate subsequent phases.

**Delivers:**
- Fix undefined `w`/`h` bug in `recognizer.py` (CPU mode functionality)
- Create `DebugContext` dataclass with stage hooks
- Implement `StageHook` with lazy evaluation
- Add `DEBUG_LEVEL` config flag (OFF/ESSENTIAL/DETAILED/FULL)
- Create debug output directory structure

**Addresses:** Basic annotated screenshots, fail-fast on errors

**Avoids:** CPU mode crash, debug logging in hot loops

---

### Phase 2: Reliability Hardening
**Rationale:** With debug infrastructure in place, now tackle the five reliability pitfalls that cause false negatives. This phase makes the bot trustworthy by adding visibility into detection decisions and fixing threshold/color/dedup issues.

**Delivers:**
- Consolidate all thresholds to config.py as single source of truth
- Implement per-template adaptive thresholds based on historical match quality
- Lower or make color threshold adaptive (use histogram matching)
- Add debug logging to deduplication showing what was eliminated
- Implement icon filter in hybrid mode or document limitation
- Log near-miss counts (confidence within 5% of threshold)
- CSV metrics export per cycle

**Uses:** MultiScaleMatcher pattern, AdaptiveThreshold pattern, BilateralFilter/CLAHE preprocessing

**Implements:** DebugContext accumulation, stage timing per phase

**Avoids:** Pitfalls 2, 3, 4, 5, 7, 9 from PITFALLS.md

---

### Phase 3: Advanced Detection & Polish
**Rationale:** Once reliability is established, add features that differentiate for power users and address long-term maintenance issues.

**Delivers:**
- Cluster-based deduplication (DBSCAN) preserving elimination trace
- Multi-scale consistency check across [0.8-1.2] scales
- Per-item detection certainty explainer on debug images
- Detection heatmap (persistent visualization by screen region)
- Template versioning process for game updates
- Visual diff between template versions

**Uses:** SpatialDeduplicator, MultiScaleMatcher components

**Avoids:** Pitfalls 6, 8, 10 from PITFALLS.md

---

### Phase Ordering Rationale

1. **Phase 1 before Phase 2**: Can't validate reliability fixes without debug infrastructure
2. **Phase 2 before Phase 3**: Cluster dedup and multi-scale are improvements, not blockers
3. **Bug fix first**: The undefined variable bug is a crash, not a reliability issue — must be first
4. **Observability before tuning**: Can't tune thresholds without debug output showing current behavior
5. **Group by risk**: Phase 2 has the most unknowns (threshold behavior, color verification) — more research may be needed

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Reliability Hardening):** Adaptive threshold implementation details — how much historical data needed? What's the adaptation algorithm?
- **Phase 2 (Color Verification):** Histogram matching vs cosine similarity on average color — empirical testing needed to determine which works better for this game's UI

Phases with standard patterns (skip research-phase):
- **Phase 1 (Debug Infrastructure):** Stage hook pattern well-documented in ARCHITECTURE.md
- **Phase 3 (Cluster Dedup):** DBSCAN is standard sklearn, implementation straightforward

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | OpenCV patterns well-established; some version numbers need PyPI verification |
| Features | MEDIUM | Game bot ecosystem sparse on debug tooling; RPA patterns partially applicable |
| Architecture | HIGH | Detailed pipeline design with working code patterns from codebase analysis |
| Pitfalls | MEDIUM-HIGH | Code analysis confirms issues; some runtime behavior requires validation |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Adaptive threshold calibration**: Research suggests adaptive thresholds but doesn't provide specific parameters. Need to collect confidence score distributions from real runs before settling on adaptation algorithm.
- **Color verification accuracy**: Whether histogram matching is significantly better than average color cosine similarity needs empirical comparison.
- **Dedup distance calibration**: 20px based on intuition; actual item grid size in game UI should be measured.
- **YOLO model version**: No research on which YOLO version is in use or if upgrades would help.

## Sources

### Primary (HIGH confidence)
- Codebase analysis of `vision/recognizer.py`, `vision/hybrid_pipeline.py`, `vision/item_candidate_pipeline.py` — architecture and bug identification
- OpenCV matchTemplate documentation patterns — verified via training data

### Secondary (MEDIUM confidence)
- PyImageSearch multi-scale template matching article — implementation patterns
- UiPath RPA debugging documentation — feature expectations
- Game bot ecosystem (GitHub: game-bot topic) — feature landscape
- sklearn DBSCAN documentation — clustering pattern

### Tertiary (LOW confidence)
- Computer vision Stack Exchange pattern discussions — needs verification
- Template matching confidence thresholds (0.98 industry common practice) — should be validated against actual game UI

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
