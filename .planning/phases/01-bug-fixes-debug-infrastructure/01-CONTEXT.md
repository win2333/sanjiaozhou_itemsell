# Phase 1: Bug Fixes & Debug Infrastructure - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix CPU mode crash and consolidate threshold configuration. Bot must run without crashing in CPU mode with all thresholds configurable via config.py.
</domain>

<decisions>
## Implementation Decisions

### Configuration Style
- **D-01:** Use simple constants in config.py (not dataclass) — keep current style, just consolidate scattered thresholds

### Debug Output
- **D-02:** Print threshold configuration on startup — log current TEMPLATE_MATCH_THRESHOLD and COLOR_MATCH_THRESHOLD values on init

### Threshold Values
- **D-03:** TEMPLATE_MATCH_THRESHOLD = 0.95 (lowered from 0.98)
- **D-04:** COLOR_MATCH_THRESHOLD = 0.95 (lowered from 0.99 in hybrid mode)

### Code Fixes Required
- **D-05:** Fix recognizer.py lines 411-417 — replace undefined `w`/`h` with `tmpl_w`/`tmpl_h`
- **D-06:** Remove scattered threshold constants from modules — import from config.py only

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `config.py` — Main configuration file, target for consolidation
- `vision/recognizer.py` §lines 411-417 — CPU mode crash bug location
- `.planning/REQUIREMENTS.md` — DET-01 to DET-04 acceptance criteria
- `.planning/ROADMAP.md` §Phase 1 — Success criteria for this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.py` — Existing threshold constants (TEMPLATE_MATCH_THRESHOLD, etc.)

### Established Patterns
- Simple constant definitions in config.py (no dataclass)

### Integration Points
- `vision/recognizer.py` — imports thresholds from config
- `vision/hybrid_pipeline.py` — imports thresholds from config
- `vision/item_candidate_pipeline.py` — may need threshold imports

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 01-bug-fixes-debug-infrastructure*
*Context gathered: 2026-03-25*
