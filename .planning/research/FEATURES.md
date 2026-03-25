# Feature Research

**Domain:** Game automation computer vision - debug visibility and detection stability
**Researched:** 2026-03-25
**Confidence:** MEDIUM

*Sources: Analysis of game bot ecosystems (GitHub topics: game-bot, automation), existing codebase patterns, RPA industry debugging practices (UiPath), template matching/OpenCV best practices*

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Annotated screenshot output** | When detection fails, users need to see WHY — what the bot saw, what it detected, what it missed | MEDIUM | Current codebase has `save_debug_frame()` generating 3 images per round (original, yolo, pipeline) — this is good foundation |
| **Detection bounding boxes on image** | Visual confirmation of WHAT was detected WHERE | LOW | Current: boxes with confidence scores. Should also show template name labels |
| **Confidence score display** | Users need to know HOW CONFIDENT the detection is to trust the output | LOW | Current: confidence shown as float (e.g., "0.85"). Consider categorical (HIGH/MED/LOW) for UX |
| **Structured log output** | Text logs for programmatic debugging and post-hoc analysis | LOW | Current: Logger exists with dual output (file + console). Could be enhanced with structured fields |
| **Stage timing metrics** | When cycle is slow, users need to know WHICH stage is bottleneck | MEDIUM | Current: Some timing in hybrid_pipeline. Missing: per-stage breakdown visible in debug output |
| **Detection count summary** | After each cycle: "Found X items, sold Y" — basic feedback loop | LOW | Partially exists in RoundSummary. Should be prominently logged |
| **Fail-fast on critical errors** | Bot should crash loudly on unrecoverable errors (not silently skip) | LOW | Current: exceptions logged but cycle continues. Consider log level CRITICAL for unrecoverable states |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable for reliability and user trust.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Pipeline stage visualization** | Show each filtering stage's effect: "YOLO found 12 → Icon filter removed 5 → Dedup removed 3 → Template match confirmed 4" | MEDIUM | Visualize the funnel. Current codebase has eliminated reason tracking but no visual output per stage |
| **Per-item detection certainty explainer** | For each detected item, show WHY it passed: "Item at (x,y) passed because template match 0.92 > threshold 0.8 AND icon filter score 0.7" | HIGH | Would require passing through intermediate decision data to debug output |
| **Live debug overlay (optional)** | Real-time annotated view while bot is running — see detections appear in real-time | MEDIUM | Could use cv2.imshow() in debug mode. Memory overhead, may affect performance |
| **Automatic threshold advisor** | After failed detections, suggest threshold adjustments based on confidence distribution | MEDIUM | Analyze confidence scores across runs, flag items that were "close to failing" |
| **Detection heatmap** | Aggregate visualization: "In last 100 runs, items in LEFT region fail 30% more often" | HIGH | Requires persistent metrics storage across runs |
| **Confidence histogram export** | Export confidence scores to CSV for threshold tuning | LOW | Simple addition to logging, high value for power users |
| **Silent failure detection** | Detect when bot is running but NOT detecting anything (false positive failure) | MEDIUM | Compare detection rate against historical baseline, alert if zero detections for N cycles |
| **Visual diff between runs** | Side-by-side comparison of detection results from run A vs run B | MEDIUM | Useful for regression testing after template updates |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time video recording of entire session** | User wants full playback of what bot did | Storage explosion (hours of video), performance overhead, rarely reviewed | Debug screenshot per cycle is sufficient; video only on-demand for specific bug reproduction |
| **GUI with live detection preview** | Seems helpful for debugging | Complex UI code, maintenance burden, often freezes under high-frequency updates | Keep CLI-based with screenshot output; offer optional cv2.imshow for manual testing |
| **Cloud metrics dashboard** | Enterprise-feeling observability | Over-engineering for single-user tool, privacy concerns, infrastructure cost | Local JSON/CSV metrics files that user can open in Excel |
| **Automatic threshold adjustment (auto-tune)** | Users don't want to manually tune | Unpredictable behavior, may make bot LESS reliable in edge cases | Provide clear manual threshold config with confidence histogram to guide adjustment |
| **Alert notifications (push/email)** | User wants remote monitoring | Adds notification infrastructure complexity, usually unnecessary for local tool | Console/log output is sufficient; add status file that external scripts can poll |
| **Support for multiple game windows** | "I want to run multiple accounts" | Session management complexity, detection cross-contamination, detection latency doubles | Keep single-window; document that multi-instance requires separate installations |

---

## Feature Dependencies

```
[Annotated Screenshots]
    └──requires──> [Detection Bounding Boxes]
                       └──requires──> [Confidence Scores]

[Pipeline Stage Visualization]
    └──requires──> [Stage Timing Metrics]
                       └──requires──> [Detection Summary Per Cycle]

[Per-item Detection Explainability]
    └──requires──> [Confidence Score Display]
                       └──requires──> [Pipeline Stage Visualization]

[Automatic Threshold Advisor]
    └──requires──> [Confidence Histogram Export]
                       └──requires──> [Silent Failure Detection]

[Detection Heatmap]
    └──requires──> [Persistent Metrics Storage]
```

---

## MVP Definition

### Launch With (v1)

Minimum viable debug visibility — what's needed to diagnose detection failures.

- [ ] **Enhanced annotated screenshots** — Add template name labels to all detection boxes, not just candidates. Show YOLO boxes in grayscale, template matches in color.
- [ ] **Pipeline stage timing breakdown** — Log time spent in: capture, YOLO detection, template matching, icon filtering, dedup, sorting. Display in debug output.
- [ ] **Detection funnel comment in logs** — Text summary: "YOLO:12 → Template:8 → IconFilter:6 → Dedup:5 → Final:3 candidates"
- [ ] **Confidence histogram on startup** — On first run (or with --calibrate), scan backpack and show confidence distribution to guide threshold setting
- [ ] **Fail-soft with detailed logging** — When detection finds nothing, log at WARN level: "WARNING: Zero detections in cycle 5. Last known good detection was cycle 3."

### Add After Validation (v1.x)

Features to add once core debug visibility is validated.

- [ ] **Silent failure detector** — Alert after N consecutive zero-detection cycles. Configurable threshold.
- [ ] **CSV metrics export** — Per-cycle: timestamp, items_found, items_sold, detection_confidence_avg, cycle_time_ms
- [ ] **Per-item explainability in debug images** — For each box, show WHY it passed: "template:0.92 > 0.8"

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Detection heatmap** — Persistent visualization of detection reliability by screen region
- [ ] **Visual diff between template versions** — Side-by-side detection results to validate template updates
- [ ] **Live debug overlay** — Optional cv2.imshow() window during manual testing

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Enhanced annotated screenshots (labels) | HIGH | LOW | P1 |
| Pipeline stage timing breakdown | HIGH | LOW | P1 |
| Detection funnel log summary | HIGH | LOW | P1 |
| Confidence histogram / threshold guidance | HIGH | MEDIUM | P1 |
| Silent failure detector | MEDIUM | LOW | P2 |
| CSV metrics export | MEDIUM | LOW | P2 |
| Per-item explainability in debug images | MEDIUM | MEDIUM | P2 |
| Live debug overlay | LOW | MEDIUM | P3 |
| Detection heatmap | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Game Bots (GitHub) | RPA Tools (UiPath) | Our Approach |
|---------|-------------------|-------------------|--------------|
| Annotated debug output | Basic — screenshot with boxes | Yes — full workflow visualization | Already implemented; enhance with labels |
| Stage timing | Rare | Yes — execution profiler | Add to debug output |
| Detection confidence | Sometimes shown | Yes — confidence scores | Already shown; add histogram |
| Pipeline visualization | Rare | Yes — activity breakdown | Add text-based funnel to logs |
| Silent failure detection | Almost never | Yes — exception handling | Add alert after N zero-detection cycles |
| Metrics export | Almost never | Yes — CSV/JSON export | Add CSV per-cycle metrics |

**Key insight:** Game bots typically have LESS debug tooling than enterprise RPA. This is an opportunity to differentiate on reliability and debuggability for power users who want to understand detection failures.

---

## Sources

- Game bot ecosystem analysis: GitHub topics/game-bot (327 repositories), including:
  - `paulonteri/play-game-with-computer-vision` (134 stars) — template matching basics
  - `Siterizer/new-world-fishing-bot` — configuration-based debugging with log levels
- RPA industry: UiPath debugging documentation patterns
- OpenCV template matching: `cv2.matchTemplate()` confidence-based detection
- Current codebase analysis: `utils/debug_visualizer.py`, `vision/recognizer.py`, `vision/hybrid_pipeline.py`

---

*Feature research for: Debug visibility and detection stability in game automation*
*Researched: 2026-03-25*
