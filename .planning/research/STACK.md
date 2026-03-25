# Stack Research

**Domain:** Computer Vision Debug Visualization & Template Matching Reliability
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

*Note: Context7/OpenCV docs unavailable for verification. Findings based on established OpenCV patterns and best practices from computer vision community. Some version numbers should be verified against current PyPI releases.*

## Recommended Stack

### Core Debug Visualization

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| OpenCV drawing | Built-in | Annotate frames with boxes, labels, circles | Already in stack — zero extra dependencies |
| matplotlib | 3.8+ | Save intermediate pipeline results to files | Mature, handles numpy arrays directly, good for batch export |
| Pillow | 10.0+ | Chinese text annotation, image format conversion | Already in stack — use for text rendering with Chinese fonts |
| numpy | 1.24+ | Save debug arrays as images, heatmap generation | Already in stack — essential for numerical debugging |

### Template Matching Reliability

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| OpenCV matchTemplate | 4.8.0+ | Core template matching with multi-scale support | Already in stack — use properly instead of adding libraries |
| cv2.resize + pyramid | Built-in | Multi-scale matching to handle size variations | No extra deps — scales templates to multiple sizes |
| cv2.addWeighted / cv2.subtract | Built-in | Image alignment normalization | Reduce lighting variation impact |
| cv2.bilateralFilter | Built-in | Edge-preserving denoising | Better than Gaussian for template matching |

### Image Preprocessing

| Technology | Version | Purpose | When to Use |
|------------|---------|---------|-------------|
| cv2.cvtColor | Built-in | Grayscale/HSV/LAB color space conversion | When templates and screenshots differ in color encoding |
| cv2.equalizeHist | Built-in | Histogram equalization | Improve contrast for consistent lighting |
| cv2.createCLAHE | Built-in | Adaptive histogram equalization | Local lighting variation compensation |
| cv2. morphologyEx | Built-in | Open/close operations | Remove noise while preserving edges |

## Installation

```bash
# All required libraries are already in requirements.txt
# opencv-python>=4.8.0
# numpy>=1.24.0
# Pillow>=10.0.0

# Optional for enhanced visualization
# matplotlib>=3.8.0  # For plotting heatmaps and saving debug grids
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| OpenCV native drawing | imutils library | imutils adds convenience functions but adds dependency for minimal gain |
| Multi-scale matchTemplate | skimage template matching | skimage has SSIM-based matching but slower; OpenCV sufficient |
| Bilateral filter denoising | Non-local means (fastNlMeansDenoising) | NLM slower but better for extreme noise; bilateral is sufficient for game screens |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `TM_SQDIFF_NORMED` | Sensitive to template/screenshot brightness differences; returns low values for good matches | `TM_CCOEFF_NORMED` — more robust to lighting variation |
| `TM_CCORR_NORMED` | Generally less reliable than CCOEFF for template matching | `TM_CCOEFF_NORMED` |
| Single-scale template matching | Game UI may render items at slightly different sizes | Multi-scale matching (try 0.9x, 1.0x, 1.1x scales) |
| Fixed confidence threshold without tuning | 0.98 may be too strict for some items, too loose for others | Analyze ROC curve per-item, or use adaptive threshold |
| Grayscale-only matching when color matters | Some items differ primarily in color | Try both grayscale and color matching, pick better result |
| Ignoring template quality | Blurry/low-res templates cause false negatives | Re-capture templates at native game resolution |

## Debug Visualization Patterns

### Pattern 1: Pipeline Stage Saving

```python
# Save annotated screenshot at each pipeline stage
def debug_save_stage(name, image, bboxes=None, labels=None):
    """Save debug image with annotations."""
    vis = image.copy()
    if bboxes:
        for i, (x, y, w, h) in enumerate(bboxes):
            color = (0, 255, 0)  # Green for detections
            cv2.rectangle(vis, (x, y), (x+w, y+h), color, 2)
            if labels:
                cv2.putText(vis, labels[i], (x, y-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    # Save to debug/ folder with timestamp
    from datetime import datetime
    ts = datetime.now().strftime("%H%M%S_%f")
    cv2.imwrite(f"debug/{name}_{ts}.png", vis)
```

### Pattern 2: Template Match Heatmap

```python
# Visualize match confidence across entire screen
def debug_match_heatmap(screenshot, template, result):
    """Save heatmap of match confidence."""
    import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 8))
    plt.imshow(result, cmap='jet')
    plt.colorbar(label='Match Confidence')
    plt.title('Template Match Confidence Map')
    # Mark best match
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    plt.plot(max_loc[0], max_loc[1], 'rx', markersize=15)
    plt.savefig(f"debug/heatmap_{cv2.getTickCount()}.png")
    plt.close()
```

### Pattern 3: Multi-Scale Debug Output

```python
# Debug multi-scale matching
def debug_multiscale(template, scales=[0.9, 0.95, 1.0, 1.05, 1.1]):
    """Visualize which scale found the best match."""
    results = []
    for scale in scales:
        resized = cv2.resize(template, None, fx=scale, fy=scale)
        # ... matching logic ...
        results.append((scale, max_confidence))
    
    # Plot scale vs confidence
    import matplotlib.pyplot as plt
    scales_list, confs = zip(*results)
    plt.plot(scales_list, confs, 'b-o')
    plt.xlabel('Scale Factor')
    plt.ylabel('Match Confidence')
    plt.title('Multi-Scale Match Analysis')
    plt.savefig(f"debug/scale_analysis_{cv2.getTickCount()}.png")
```

## Template Matching Reliability Checklist

### Pre-Matching

- [ ] **Template quality**: Capture templates at native game resolution, no compression
- [ ] **Color space**: Match template and screenshot color encoding (RGB vs BGR)
- [ ] **Lighting normalization**: Apply CLAHE or bilateral filter to reduce lighting variation
- [ ] **Multi-scale**: Try 3-5 scales around 1.0 (e.g., 0.9, 0.95, 1.0, 1.05, 1.1)

### Match Method Selection

- [ ] **Prefer `TM_CCOEFF_NORMED`**: More robust to brightness differences than SQDIFF
- [ ] **Avoid `TM_SQDIFF` variants**: Unless you specifically need squared difference minimization
- [ ] **Threshold tuning**: Don't hardcode 0.98 — analyze false positive/negative tradeoff

### Post-Matching

- [ ] **Validation**: If match found, verify with secondary check (e.g., check nearby region)
- [ ] **Non-maximum suppression**: Prevent overlapping duplicate detections
- [ ] **Logging**: Always log match location, scale, and confidence for debugging

## Stack Patterns by Variant

**If detection is too strict (false negatives):**
- Lower threshold from 0.98 to 0.95 for `TM_CCOEFF_NORMED`
- Enable multi-scale matching
- Add CLAHE preprocessing to both template and screenshot

**If detection is too loose (false positives):**
- Raise threshold to 0.99
- Add secondary validation (check pixel color at match center)
- Use bilateral filter to reduce noise-induced matches

**If items render at varying sizes:**
- Implement full multi-scale pyramid (e.g., 0.8x to 1.2x in 0.05 increments)
- Use largest consistent template size (benefits from more features)

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| opencv-python 4.8.0+ | numpy 1.24+, Python 3.8+ | Current stable recommended |
| matplotlib 3.8+ | numpy 1.24+, Python 3.9+ | For debug visualization |
| Pillow 10.0+ | Python 3.8+ | Already in stack for Chinese font support |

## Sources

- OpenCV matchTemplate documentation — verified via training data, not current docs (LOW confidence on latest API)
- PyImageSearch articles on template matching optimization — community best practices (MEDIUM confidence)
- Computer vision Stack Exchange pattern discussions — established patterns (MEDIUM confidence)

---

*Stack research: Template matching reliability and debug visualization*
*Researched: 2026-03-25*
