# Phase 2: Debug Visibility - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Add detection pipeline observability: detection funnel logs, stage timing breakdown, and annotated screenshots showing all detection boxes.
</domain>

<decisions>
## Implementation Decisions

### Debug Funnel Log Format
- **D-01:** Format: "YOLO:X → Template:Y → IconFilter:Z → Dedup:W → Final:V"
- **D-02:** Log after each scan cycle when DEBUG_MODE=True
- **D-03:** Stages in order: YOLO, Template, IconFilter, Dedup, Final

### Stage Timing Breakdown
- **D-04:** Stages timed: capture, YOLO, template, filter, dedup
- **D-05:** Format: "[耗时] capture=XXms, yolo=XXms, template=XXms, filter=XXms, dedup=XXms"
- **D-06:** Log when DEBUG_MODE=True

### Screenshot Annotation
- **D-07:** Draw ALL detection boxes (not just final candidates)
- **D-08:** Box color: green (BGR: 0, 255, 0)
- **D-09:** Label: white text with template name (Chinese OK)
- **D-10:** Use OpenCV cv2.putText for text
- **D-11:** Save to DEBUG_DIR with timestamp

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/REQUIREMENTS.md` — DEBUG-01, DEBUG-02, DEBUG-03 acceptance criteria
- `.planning/ROADMAP.md` §Phase 2 — Success criteria for this phase
- `.planning/phases/01-bug-fixes-debug-infrastructure/01-CONTEXT.md` — Phase 1 decisions (for continuity)

</canonical_refs>

<code_insights>
## Existing Code Insights

### Reusable Assets
- `utils/debug_visualizer.py` — Existing debug visualization utilities
- `config.DEBUG_DIR` — Debug image output directory
- `vision/hybrid_pipeline.py` — Where YOLO detection happens
- `vision/item_candidate_pipeline.py` — Where filtering happens

### Established Patterns
- Debug logging via `get_logger()` with category tags
- DEBUG_MODE flag controls detailed output
- Annotated screenshots saved to DEBUG_DIR

### Integration Points
- HybridPipeline.process() — add funnel counting
- ItemCandidatePipeline.process() — add funnel counting
- core/loop.py — add timing around each stage

</code_insights>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 02-debug-visibility*
*Context gathered: 2026-03-25*
