# Codebase Concerns

**Analysis Date:** 2026-03-23

## Tech Debt

### Hardcoded Configuration Values
- **Issue:** Extensive hardcoded coordinate values scattered across code
- **Files:**
  - `config.py` (lines 66-88): UI coordinates (UPLOAD1_X=1403, UPLOAD1_Y=700, BACKPACK_LEFT=1200, etc.)
  - `core/loop.py` (line 499): Hardcoded green button region (1300, 670, 1500, 720)
  - `core/loop.py` (lines 636-637): REGION_HALF_WIDTH=150, REGION_HALF_HEIGHT=150
  - `vision/recognizer.py` (line 197): Hardcoded 1150 pixel crop threshold
  - `vision/price_reader.py` (lines 52, 90-91): Hardcoded price region coordinates (440, 734, 1050, 770)
- **Impact:** Game UI changes require code modifications; fragile across screen resolutions
- **Fix approach:** Extract all coordinates to configuration with validation; implement UI element detection fallback

### Duplicate Duplicate Distance Definitions
- **Issue:** Deduplication distance defined in multiple places
- **Files:**
  - `config.py`: DEDUP_DISTANCE = 30 (for old flow)
  - `config.py`: DEDUP_DISTANCE_PX = 20 (for new pipeline)
  - `vision/candidate_utils.py`: DEFAULT_DEDUP_DISTANCE_PX = 20
  - `config.py`: ICON_FILTER_THRESHOLD = 0.8
- **Impact:** Inconsistent behavior between old and new code paths
- **Fix approach:** Consolidate to single source of truth in config.py

### Global Logger Pattern
- **Issue:** Singleton logger with global state complicates testing and multi-threaded scenarios
- **Files:** `utils/logger.py`
- **Impact:** Difficult to test logging behavior; potential race conditions with buffer flushing
- **Fix approach:** Consider dependency injection pattern for logger

## Known Bugs

### Template Image Alignment in New Price Method
- **Issue:** New price method uses PRICE_DIRECT_CLICK_X=860 but this may not align with price input field
- **Files:** `config.py` (line 84)
- **Symptoms:** Price input may fail to clear old value properly; could input to wrong field
- **Trigger:** Using USE_NEW_PRICE_METHOD=True mode
- **Workaround:** Set USE_NEW_PRICE_METHOD=False to use Ctrl+A method

### Icon Filter Template Loading Failure Silent
- **Issue:** If icon template fails to load, code only logs warning but continues
- **Files:** `core/loop.py` (lines 140-153)
- **Symptoms:** Items with "cannot sell" icon may still be processed
- **Trigger:** Missing or corrupted icon_01.png template file
- **Workaround:** Ensure templates/icon_01.png exists and is valid

### OCR Reader Initialization Failure Handling
- **Issue:** OCR reader initialized once, but failures not retried
- **Files:** `vision/price_reader.py` (lines 16-27)
- **Symptoms:** Price reading silently fails if EasyOCR initialization fails
- **Trigger:** GPU not available or EasyOCR package corrupted

## Security Considerations

### Screen Capture Permissions
- **Risk:** Uses mss library for screen capture with no access control
- **Files:** `vision/capture.py`
- **Current mitigation:** None - runs with user permissions
- **Recommendations:** Add explicit window targeting instead of full screen capture

### Input Control Libraries
- **Risk:** Uses pydirectinput and keyboard libraries for automation
- **Files:**
  - `control/mouse.py`
  - `control/keyboard.py`
- **Current mitigation:** None
- **Recommendations:** Document that this requires exclusive input control; warn about anti-cheat detection

### No Credential Storage
- **Risk:** No credentials or API keys used currently, but architecture supports none
- **Impact:** Cannot extend to cloud services without security architecture
- **Recommendations:** Design secrets management before adding external integrations

## Performance Bottlenecks

### ThreadPoolExecutor Workers
- **Problem:** Template recognition uses 16 threads by default
- **Files:** `vision/recognizer.py` (line 349)
- **Cause:** High thread count may cause context switching overhead
- **Improvement path:** Reduce to 4-8 workers; batch templates for GPU processing

### Full Screen Capture in Loop
- **Problem:** Multiple full-screen captures per sell cycle
- **Files:** `core/loop.py` (lines 262-266, 448-452, 640)
- **Cause:** Each sell item triggers new full-screen capture for verification
- **Improvement path:** Capture once per cycle, reuse image data

### Green Button HSV Detection
- **Problem:** Color-based detection with fixed HSV thresholds
- **Files:** `core/loop.py` (lines 593-600)
- **Cause:** Environment lighting changes affect green detection accuracy
- **Improvement path:** Use template matching for upload1 button instead of color

## Fragile Areas

### Hardcoded 1150 Pixel Crop Threshold
- **Files:** `vision/recognizer.py` (lines 196-198, 232-235, 575-589)
- **Why fragile:** Assumes backpack always at x>=1150; breaks on different screen layouts
- **Safe modification:** Replace with config-based BACKPACK_LEFT coordinate
- **Test coverage:** Only tested on 1920x1080 resolution

### Price Region Coordinates
- **Files:** `vision/price_reader.py` (lines 52, 90-91)
- **Why fragile:** Fixed to specific game UI layout; cannot adapt to UI scaling
- **Safe modification:** Detect price region dynamically using template matching
- **Test coverage:** None - manual testing only

### MSE Threshold for Verification
- **Files:** `core/loop.py` (line 52: VERIFY_MSE_THRESHOLD = 500)
- **Why fragile:** Arbitrary threshold; may fail with different lighting or game states
- **Safe modification:** Implement adaptive threshold or multi-pass verification
- **Test coverage:** Minimal - hard to reproduce verification failures

## Scaling Limits

### Template-Based Recognition
- **Current capacity:** 322+ templates loaded in memory
- **Limit:** Memory usage increases linearly with template count; matching time O(n) per template
- **Scaling path:** Switch to YOLO/ML-based detection for better scalability

### Single Monitor Assumption
- **Current capacity:** Hardcoded to monitors[1] for main display
- **Limit:** Does not support multi-monitor or windowed game mode
- **Scaling path:** Add explicit window/game area targeting

## Dependencies at Risk

### EasyOCR
- **Risk:** Heavy dependency (~1GB), slow initialization
- **Impact:** Application startup delayed 10+ seconds; memory intensive
- **Migration plan:** Consider lighter OCR solution or cached pre-processing

### pydirectinput/keyboard
- **Risk:** Not thread-safe; requires elevated permissions
- **Impact:** May conflict with other input automation tools
- **Migration plan:** Abstract input layer for future cross-platform support

### MSS
- **Risk:** Platform-specific (Windows/Linux)
- **Impact:** Cannot run on macOS without changes
- **Migration plan:** Abstract capture layer for multi-platform support

## Test Coverage Gaps

### Unit Tests for Price Calculation
- **What's not tested:** calculate_price() function edge cases
- **Files:** `config.py` (lines 92-118)
- **Risk:** Invalid price inputs could cause negative prices or exceptions
- **Priority:** Medium

### Integration Tests for Sell Flow
- **What's not tested:** End-to-end sell loop with actual game
- **Files:** `core/loop.py`
- **Risk:** Undetected failures in mouse/keyboard sequences
- **Priority:** High

### Template Recognition Accuracy
- **What's not tested:** Recognition under different lighting, resolutions
- **Files:** `vision/recognizer.py`
- **Risk:** False positives/negatives in production
- **Priority:** High

### Icon Filter Validation
- **What's not tested:** Edge cases with missing/corrupted icon templates
- **Files:** `vision/item_candidate_pipeline.py`
- **Risk:** Invalid items sold; account penalties
- **Priority:** Medium

---

*Concerns audit: 2026-03-23*
