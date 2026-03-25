# Background Screenshots for YOLO Training

This directory should contain **empty backpack screenshots** for generating synthetic training data.

## How to Capture Backgrounds

1. Open the game and enter the backpack/inventory screen
2. Make sure the backpack is **empty** (no items visible) — or nearly empty
3. Use **Win+Shift+S** (Windows Snip & Sketch) or any screenshot tool to capture the **entire game window**
4. Save each screenshot to this directory with names like `bg_001.png`, `bg_002.png`, ...
5. Capture **30~50 images** total, covering different scenarios:
   - Near-empty backpack (1~5 items)
   - Half-full backpack (5~15 items)
   - Near-full backpack (15+ items)
   - Different game locations/scenes
6. **IMPORTANT**: Keep the game window position **exactly the same** throughout the capture process

## Naming Convention

```
bg_001.png
bg_002.png
...
bg_050.png
```

## Requirements

- Format: PNG (lossless)
- Resolution: Match your game window resolution
- No items should be visible in the screenshots
- After capturing, run the verification script:

```bash
python tools/verify_backgrounds.py
```

## Notes

- These backgrounds serve as the "canvas" for pasting item templates
- Having diverse backgrounds (different lighting, item densities) improves model generalization
- The verification script will check each background for item leakage
