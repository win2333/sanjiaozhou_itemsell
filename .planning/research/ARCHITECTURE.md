# Architecture Research

**Domain:** Game automation detection pipeline (template matching + hybrid detection)
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

This architecture addresses two interconnected problems in the existing detection pipeline: **false negatives in template matching** and **debug instrumentation overhead**. The core insight is that these are not separate concerns—the same pipeline stages that create false negatives (thresholds, filtering, deduplication) are exactly where debug hooks need to be added.

The proposed architecture uses a **stage-based debug hook system** with lazy evaluation and conditional capture, enabling detailed diagnostics without impacting production performance.

---

## Current Architecture Analysis

### Existing Pipeline Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HybridPipeline                                │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐    ┌─────────┐    ┌─────────────────┐    ┌───────────┐ │
│  │  YOLO   │───▶│ Extract │───▶│ Template Match  │───▶│ Deduplica-│ │
│  │ (coarse)│    │  ROI    │    │  (parallel, 8)  │    │   tion    │ │
│  └─────────┘    └─────────┘    └─────────────────┘    └─────┬─────┘ │
└───────────────────────────────────────────────────────────────┼─────┘
                                                                │
                        ItemCandidatePipeline ◀──────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│  ┌─────────────┐    ┌────────────┐    ┌───────────┐    ┌────────┐ │
│  │  Coordinate │───▶│    Icon    │───▶│ Deduplica-│───▶│ Sort + │ │
│  │ Conversion  │    │   Filter   │    │   tion    │    │  Rank  │ │
│  └─────────────┘    └────────────┘    └───────────┘    └────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Problem Diagnosis

**False Negative Sources (identified from codebase):**

1. **Template Match Threshold** (`_MATCH_THRESHOLD = 0.98`): Very high strict threshold
   - Line 280 in `hybrid_pipeline.py`: `if max_val >= _MATCH_THRESHOLD`
   - Any match below 0.98 confidence is discarded

2. **Deduplication** (`dedup_distance_px = 20`): Aggressive center-distance based deduplication
   - Line 41 in `candidate_utils.py`: `if dist < dedup_distance_px`
   - Items closer than 20px center-to-center are considered duplicates

3. **Icon Filter**: False positives from "cannot sell" icon detection
   - `_apply_icon_filter()` may incorrectly eliminate valid items

4. **ROI Padding** (`_ROI_PADDING = 10`): Affects coordinate calculation
   - Line 326-327: `screen_x = roi_origin_x + detection.x - _ROI_PADDING + best_match["x"]`

---

## Recommended Architecture

### Stage-Based Detection Pipeline with Debug Hooks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RobustDetectionPipeline                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Capture Stage                                   │   │
│  │   Input: raw screenshot                                               │   │
│  │   Output: captured image + debug_artifact (lazy)                       │   │
│  │   Hook: DEBUG_CAPTURE.enabled → store raw frame                        │   │
│  └────────────────────────────────┬───────────────────────────────────────┘   │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    Preprocessing Stage                                  │ │
│  │   Input: captured image                                                │ │
│  │   Output: normalized image + debug_artifact                             │ │
│  │   Ops: grayscale convert, edge detection, pyramid build                │ │
│  │   Hook: DEBUG_PREPROCESS.enabled → store intermediate                   │ │
│  └────────────────────────────────┬───────────────────────────────────────┘   │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    Coarse Detection Stage                              │ │
│  │   Input: preprocessed image                                            │ │
│  │   Output: region proposals + debug_artifact                             │ │
│  │   Ops: YOLO inference, confidence filtering                             │ │
│  │   Hook: DEBUG_YOLO.enabled → annotate YOLO boxes on copy               │ │
│  └────────────────────────────────┬───────────────────────────────────────┘   │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    ROI Extraction Stage                                 │ │
│  │   Input: regions, original image                                       │ │
│  │   Output: cropped ROIs + debug_artifact                                 │ │
│  │   Ops: extract with padding                                             │ │
│  │   Hook: DEBUG_ROI.enabled → save cropped regions                        │ │
│  └────────────────────────────────┬───────────────────────────────────────┘   │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    Multi-Scale Template Match Stage                     │ │
│  │   Input: ROIs, templates                                                │ │
│  │   Output: matches + debug_artifact                                      │ │
│  │   Ops:                                                                  │ │
│  │     1. Build image pyramid (scale 0.5 - 1.0, 5 levels)                   │ │
│  │     2. For each ROI:                                                   │ │
│  │        a. Try template matching at each scale                           │ │
│  │        b. Track best match across scales                               │ │
│  │        c. Apply adaptive threshold (0.85 base, per-template)             │ │
│  │        d. Color verification (9-point grid)                            │ │
│  │   Hook: DEBUG_TEMPLATE.enabled → save match visualization               │ │
│  └────────────────────────────────┬───────────────────────────────────────┘   │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    Confidence Threshold Stage                            │ │
│  │   Input: raw matches                                                    │ │
│  │   Output: filtered matches + elimination reasons                        │ │
│  │   Ops:                                                                  │ │
│  │     1. Primary filter: confidence >= adaptive_threshold                  │ │
│  │     2. Secondary filter: multi-scale consistency check                   │ │
│  │     3. Log all eliminations with reason                                 │ │
│  │   Hook: DEBUG_THRESHOLD.enabled → log each decision                     │ │
│  └────────────────────────────────┬───────────────────────────────────────┘   │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    Deduplication Stage                                  │ │
│  │   Input: filtered matches                                                │ │
│  │   Output: unique items + duplicates list                                │ │
│  │   Ops:                                                                  │ │
│  │     1. Spatial clustering (DBSCAN or hierarchical)                       │ │
│  │     2. Keep highest confidence per cluster                             │ │
│  │     3. Preserve elimination trace for debug                            │ │
│  │   Hook: DEBUG_DEDUP.enabled → visualize clusters                        │ │
│  └────────────────────────────────┬───────────────────────────────────────┘   │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    Ranking Stage                                        │ │
│  │   Input: unique items                                                   │ │
│  │   Output: ranked items + RoundSummary                                   │ │
│  │   Hook: DEBUG_SUMMARY.enabled → full pipeline trace                     │ │
│  └────────────────────────────────┬───────────────────────────────────────┘   │
│                                   │                                          │
│                        Final Output                                        │
│            (candidates, eliminated, summary, debug_context)                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `RobustDetectionPipeline` | Main orchestrator, manages stage execution | `vision/robust_pipeline.py` |
| `DebugContext` | Accumulates debug artifacts across stages | `vision/debug_context.py` |
| `MultiScaleMatcher` | Multi-scale template matching with adaptive threshold | `vision/multi_scale_matcher.py` |
| `AdaptiveThreshold` | Per-template confidence thresholds based on historical performance | `vision/adaptive_threshold.py` |
| `SpatialDeduplicator` | Cluster-based deduplication preserving elimination trace | `vision/spatial_dedup.py` |
| `StageHook` | Conditional debug hook with lazy evaluation | `vision/stage_hook.py` |

---

## Key Architectural Patterns

### Pattern 1: Stage Hook with Lazy Evaluation

**What:** Debug hooks that only capture data when explicitly enabled, with lazy evaluation to avoid overhead.

**When to use:** Performance-critical pipelines where debug capability is needed but debug mode is rarely active.

**Trade-offs:**
- Pro: Zero overhead when disabled
- Pro: Captured data is structured and queryable
- Con: Slight complexity in hook implementation
- Con: Debug artifacts consume memory until flushed

**Example:**
```python
class StageHook:
    """Conditional debug hook with lazy evaluation."""
    
    def __init__(self, stage_name: str, enabled: bool = False):
        self.stage_name = stage_name
        self.enabled = enabled
        self._artifact = None
        self._lazy_factory = None
    
    def capture(self, lazy_factory: Callable[[], Any]):
        """Register lazy factory - only called if enabled."""
        if self.enabled:
            self._lazy_factory = lazy_factory
            self._artifact = lazy_factory()  # Evaluate now
        else:
            self._lazy_factory = None  # Discard reference
    
    def get_artifact(self) -> Any:
        return self._artifact
    
    def flush(self):
        """Release memory."""
        self._artifact = None
        self._lazy_factory = None
```

### Pattern 2: Adaptive Threshold

**What:** Per-template confidence thresholds adjusted based on historical match quality.

**When to use:** When different templates have inherently different match quality distributions.

**Trade-offs:**
- Pro: Reduces false negatives for "easy" templates
- Pro: Maintains precision for "noisy" templates
- Con: Requires historical data collection
- Con: Threshold adaptation adds startup latency

**Example:**
```python
class AdaptiveThreshold:
    """Per-template adaptive threshold based on historical match scores."""
    
    def __init__(self, base_threshold: float = 0.85, min_threshold: float = 0.70):
        self.base_threshold = base_threshold
        self.min_threshold = min_threshold
        self._template_stats: Dict[str, TemplateStats] = {}
    
    def get_threshold(self, template_name: str) -> float:
        """Get threshold for specific template."""
        stats = self._template_stats.get(template_name)
        if stats is None:
            return self.base_threshold
        
        # If template historically has many misses (low precision), lower threshold
        if stats.miss_rate > 0.3:
            return max(self.min_threshold, self.base_threshold - 0.10)
        return self.base_threshold
    
    def record_match(self, template_name: str, confidence: float, was_correct: bool):
        """Update statistics after verification."""
        stats = self._template_stats.setdefault(
            template_name, TemplateStats()
        )
        stats.update(confidence, was_correct)
```

### Pattern 3: Cluster-Based Deduplication

**What:** Spatial clustering instead of pairwise distance comparison for deduplication.

**When to use:** When items can overlap in complex ways and pairwise deduplication is too aggressive.

**Trade-offs:**
- Pro: Preserves items that pairwise comparison would incorrectly merge
- Pro: Provides cluster membership data for debug visualization
- Con: More computational overhead than simple distance check
- Con: Requires cluster parameter tuning

**Example:**
```python
def cluster_deduplicate(
    candidates: List[ItemCandidate],
    eps: float = 25.0,  # Cluster radius
    min_samples: int = 1
) -> Tuple[List[ItemCandidate], List[EliminatedCandidate], List[ClusterDebug]]:
    """DBSCAN-style clustering with debug trace."""
    # Build feature matrix for clustering
    coords = np.array([(c.click_x, c.click_y) for c in candidates])
    
    # DBSCAN clustering
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    labels = db.labels_
    
    kept = []
    eliminated = []
    cluster_debug = []
    
    for cluster_id in set(labels):
        if cluster_id == -1:  # Noise points
            continue
        
        cluster_indices = np.where(labels == cluster_id)[0]
        cluster_candidates = [candidates[i] for i in cluster_indices]
        
        # Keep highest confidence
        best = max(cluster_candidates, key=lambda c: c.confidence)
        kept.append(best)
        
        # Track eliminated
        for c in cluster_candidates:
            if c is not best:
                eliminated.append(create_eliminated(c, "cluster_dedup", best))
        
        cluster_debug.append(ClusterDebug(
            cluster_id=cluster_id,
            center=coords[cluster_indices[0]],
            members=len(cluster_indices),
            kept=best
        ))
    
    return kept, eliminated, cluster_debug
```

### Pattern 4: Multi-Scale Consistency Check

**What:** Verify match consistency across image scales to reduce false positives from noise.

**When to use:** When template size can vary in the input image due to resolution changes or UI scaling.

**Trade-offs:**
- Pro: Catches false positives from scale mismatch
- Pro: Improves robustness to UI scaling
- Con: 5x template matching cost (one per scale level)
- Con: Threshold tuning needed per template

**Example:**
```python
def multi_scale_consistency_check(
    roi: np.ndarray,
    template: np.ndarray,
    scales: List[float] = [0.8, 0.9, 1.0, 1.1, 1.2],
    threshold: float = 0.90
) -> Tuple[bool, float, Dict]:
    """Check if match is consistent across multiple scales.
    
    Returns:
        (is_consistent, best_confidence, scale_results)
    """
    results = {}
    best_confidence = 0.0
    best_scale = 1.0
    
    for scale in scales:
        scaled_roi = cv2.resize(roi, None, fx=scale, fy=scale)
        
        if scaled_roi.shape[0] < template.shape[0] or \
           scaled_roi.shape[1] < template.shape[1]:
            continue
        
        result = cv2.matchTemplate(scaled_roi, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        results[scale] = {"confidence": max_val, "location": max_loc}
        
        if max_val > best_confidence:
            best_confidence = max_val
            best_scale = scale
    
    # Consistency: at least 3 scales should have confidence > threshold
    consistent_scales = sum(1 for r in results.values() 
                          if r["confidence"] >= threshold * best_confidence)
    
    is_consistent = consistent_scales >= 3
    
    return is_consistent, best_confidence, {
        "scale_results": results,
        "best_scale": best_scale,
        "consistent_scales": consistent_scales
    }
```

---

## Debug Instrumentation Design

### Debug Levels

| Level | Enabled | Performance Impact | Output |
|-------|---------|-------------------|--------|
| OFF | - | Zero | None |
| ESSENTIAL | `DEBUG=essential` | ~1% | Stage counts, final summary |
| DETAILED | `DEBUG=detailed` | ~5% | Stage inputs/outputs, eliminations |
| FULL | `DEBUG=full` | ~15% | Annotated images, all intermediates |

### DebugContext Structure

```python
@dataclass
class DebugContext:
    """Accumulates debug information across pipeline stages."""
    
    round_id: int
    level: DebugLevel
    timestamp: float
    
    # Stage artifacts (populated lazily)
    capture: Optional[np.ndarray] = None           # Raw screenshot
    preprocessed: Optional[np.ndarray] = None     # After preprocessing
    yolo_annotated: Optional[np.ndarray] = None   # YOLO boxes drawn
    roi_crops: List[np.ndarray] = field(default_factory=list)  # Cropped ROIs
    template_matches: List[TemplateMatchDebug] = field(default_factory=list)
    threshold_decisions: List[ThresholdDecision] = field(default_factory=list)
    dedup_clusters: List[ClusterDebug] = field(default_factory=list)
    eliminated_trace: List[EliminationTrace] = field(default_factory=list)
    
    # Metadata
    stage_timings: Dict[str, float] = field(default_factory=dict)
    total_time_ms: float = 0.0
    
    def should_capture(self, stage: str) -> bool:
        """Check if debug capture is enabled for this stage."""
        return self.level >= STAGE_DEBUG_LEVELS.get(stage, DebugLevel.OFF)
```

### Stage Timing Hook

```python
@contextmanager
def timed_stage(stage_name: str, debug_ctx: Optional[DebugContext]):
    """Context manager for timing pipeline stages."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        if debug_ctx:
            debug_ctx.stage_timings[stage_name] = elapsed
```

---

## Data Flow

### Detection Flow (Production)

```
Screenshot
    ↓
[Capture Stage] → DebugContext.capture (if enabled)
    ↓
[Preprocess Stage] → DebugContext.preprocessed (if enabled)
    ↓
[YOLO Stage] → DebugContext.yolo_annotated (if enabled)
    ↓
[ROI Extract] → DebugContext.roi_crops (if enabled)
    ↓
[Multi-Scale Template Match]
    ├─→ Try scales [0.8, 0.9, 1.0, 1.1, 1.2]
    ├─→ Adaptive threshold per template
    └─→ Color verification (9-point grid)
    ↓
[Threshold Stage] → DebugContext.threshold_decisions
    ↓
[Cluster Dedup] → DebugContext.dedup_clusters + DebugContext.eliminated_trace
    ↓
[Rank + Summary] → DebugContext.stage_timings
    ↓
(candidates, eliminated, summary, debug_ctx)
```

### Debug Flow (When Enabled)

```
After each cycle:
    if debug_ctx.level >= DEBUG_BASIC:
        log_summary(debug_ctx)
    
    if debug_ctx.level >= DEBUG_DETAILED:
        save_stage_artifacts(debug_ctx)
    
    if debug_ctx.level >= DEBUG_FULL:
        save_annotated_images(debug_ctx)
    
    debug_ctx.flush()  # Release memory
```

---

## Scaling Considerations

| Scale | Bottleneck | Solution |
|-------|------------|----------|
| 1-10 items/cycle | Template matching CPU | Multi-scale is acceptable |
| 10-30 items/cycle | ThreadPool contention | Reduce max_workers, use ProcessPool |
| 30+ items/cycle | YOLO inference | Batch inference, model quantization |

### Performance Optimization Priorities

1. **First:** Multi-scale matching adds 5x cost → Use early exit when high confidence at default scale
2. **Second:** Debug capture overhead → Lazy evaluation + async disk write
3. **Third:** Memory pressure from debug artifacts → Flush after each cycle

---

## Anti-Patterns

### Anti-Pattern 1: Global Threshold Tuning

**What people do:** Adjust `_MATCH_THRESHOLD` up/down globally to fix false negatives.
**Why it's wrong:** A threshold that fixes misses on one template causes false positives on another.
**Do this instead:** Per-template adaptive thresholds based on historical match quality.

### Anti-Pattern 2: Deduplication Before Filtering

**What people do:** Run deduplication immediately after template matching, before any filtering.
**Why it's wrong:** Two distinct items at similar positions (e.g., stacked) will incorrectly deduplicate.
**Do this instead:** Filter first (threshold, icon filter), then deduplicate only remaining candidates.

### Anti-Pattern 3: Debug Logging Inside Hot Loop

**What people do:** `logger.debug(f"Match confidence: {val}")` inside tight template matching loop.
**Why it's wrong:** String formatting + logger call overhead in hot path, even when debug disabled.
**Do this instead:** Use lazy-evaluated StageHook, accumulate in memory, write only if enabled.

### Anti-Pattern 4: Single-Scale Template Matching

**What people do:** Match template at exactly one scale, reject if no good match.
**Why it's wrong:** Game UI can render items at slightly different sizes due to DPI, scaling, or anti-aliasing.
**Do this instead:** Multi-scale matching across [0.8, 1.2] range with consistent confidence.

---

## Integration Points

### With Existing Codebase

| Component | Integration Approach |
|-----------|---------------------|
| `HybridPipeline` | Refactor into stages, keep interface compatibility |
| `ItemCandidatePipeline` | Replace with unified pipeline, reuse dedup logic |
| `TemplateRecognizer` | Extract multi-scale logic into `MultiScaleMatcher` |
| `config.py` | Add `DEBUG_LEVEL`, `ADAPTIVE_THRESHOLD_ENABLED` flags |

### Debug Output Compatibility

| Existing Output | Migration |
|-----------------|-----------|
| `RoundSummary` | Extend with `debug_ctx` field |
| `EliminatedCandidate` | Already structured, extend with `cluster_info` |
| Logger output | Redirect to `DebugContext` when structured debug enabled |

---

## Build Order

### Phase 1: Debug Infrastructure
1. Create `DebugContext` dataclass with stage hooks
2. Implement `StageHook` with lazy evaluation
3. Add `DEBUG_LEVEL` config flag
4. Create debug output directory structure

**Files:** `vision/debug_context.py`, `vision/stage_hook.py`, update `config.py`

### Phase 2: Multi-Scale Template Matching
1. Extract template matching from `HybridPipeline` into `MultiScaleMatcher`
2. Implement pyramid building
3. Add consistency check across scales
4. Add per-template adaptive threshold

**Files:** `vision/multi_scale_matcher.py`, update `hybrid_pipeline.py`

### Phase 3: Cluster-Based Deduplication
1. Implement `SpatialDeduplicator` with DBSCAN
2. Preserve elimination trace
3. Add debug visualization of clusters

**Files:** `vision/spatial_dedup.py`, update `candidate_utils.py`

### Phase 4: Pipeline Integration
1. Refactor `HybridPipeline` to use new stages
2. Wire up debug hooks at each stage
3. Add async artifact saving
4. Performance testing

**Files:** Update `vision/hybrid_pipeline.py`, add `vision/robust_pipeline.py`

---

## Sources

- Multi-scale template matching: PyImageSearch (2015) — https://pyimagesearch.com/2015/01/26/multi-scale-template-matching-using-python-opencv/
- OpenCV template matching: cv2.matchTemplate documentation
- DBSCAN clustering: scikit-learn implementation
- Debug instrumentation patterns: Google Crashpad logging design

---

*Architecture research for: Hybrid detection pipeline improvements*
*Researched: 2026-03-25*
