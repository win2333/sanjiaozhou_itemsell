# Codebase Concerns

**Analysis Date:** 2026-03-25

## Tech Debt

### Critical Bug: Undefined Variables in CPU Template Matching
- **Issue:** In `recognizer.py` lines 411-417, variables `w` and `h` are referenced but never defined in `_match_template()`. They should be `tmpl_w` and `tmpl_h` which are defined on lines 373-374.
- **Files:** `vision/recognizer.py` (lines 411-417)
- **Impact:** CPU template matching path crashes with `NameError` when attempting to match any template
- **Fix approach:** Replace `w` with `tmpl_w` and `h` with `tmpl_h` on lines 411-412, 414-415

### Hardcoded Screen Coordinates
- **Issue:** Multiple hardcoded coordinate values assume 1920x1080 resolution
- **Files:**
  - `config.py` (lines 66-88): UI coordinates (`UPLOAD1_X=1403`, `UPLOAD1_Y=700`, `BACKPACK_LEFT=1200`, etc.)
  - `core/loop.py` (line 499): Green button region `(1300, 670, 1500, 720)`
  - `core/loop.py` (lines 661-662): `REGION_HALF_WIDTH=150`, `REGION_HALF_HEIGHT=150`
  - `vision/recognizer.py` (line 197): Hardcoded 1150 pixel crop threshold
  - `vision/price_reader.py` (lines 52, 90-91): Price region `(440, 734, 1050, 770)`
- **Impact:** Game UI changes or different screen resolutions require code modifications
- **Fix approach:** Extract all coordinates to configuration with validation; implement dynamic UI detection

### Hardcoded Color Values
- **Issue:** Magic numbers used for empty slot detection: `RGB(26, 31, 34)` and tolerance of 5
- **Files:** `core/loop.py` (lines 622-650)
- **Impact:** Empty slot detection fails if game UI colors change
- **Fix approach:** Extract to config with comments explaining the values and their origin

### Inconsistent Thresholds Between Modules
- **Issue:** Threshold values duplicated and inconsistent across modules:
  - `hybrid_pipeline.py` hardcodes `_MATCH_THRESHOLD = 0.98` and `COLOR_THRESHOLD = 0.99`
  - `recognizer.py` uses `threshold` parameter and `COLOR_THRESHOLD = 0.85`
  - `config.py` has `TEMPLATE_MATCH_THRESHOLD = 0.98` and `ICON_FILTER_THRESHOLD = 0.8`
- **Files:** `vision/hybrid_pipeline.py`, `vision/recognizer.py`, `config.py`
- **Impact:** Hybrid mode and template mode behave differently; maintenance confusion
- **Fix approach:** Use config values consistently; pass thresholds through constructors

### YOLO Model Path Misconfiguration
- **Issue:** `config.py` specifies `YOLO_MODEL_PATH = "models/item_detector.pt"` but actual file exists at `models/item_detector.pt`. Relative path may fail if working directory differs from project root.
- **Files:** `config.py` (line 30)
- **Impact:** YOLO detection fails depending on how the application is launched
- **Fix approach:** Use `BASE_DIR / "models" / "item_detector.pt"` for absolute path

### Icon Filter Not Implemented in Hybrid Mode
- **Issue:** `HybridPipeline.process()` returns `filtered_count=0` as placeholder; icon filtering only works in template mode
- **Files:** `vision/hybrid_pipeline.py` (line 151)
- **Impact:** Items with "cannot sell" icon may be processed in hybrid mode
- **Fix approach:** Implement icon filter in hybrid pipeline or document this limitation clearly

### Duplicate Distance Definitions
- **Issue:** Deduplication distance defined in multiple places:
  - `config.py`: `DEDUP_DISTANCE = 30` (old flow)
  - `config.py`: `DEDUP_DISTANCE_PX = 20` (new pipeline)
  - `vision/candidate_utils.py`: `DEFAULT_DEDUP_DISTANCE_PX = 20`
- **Files:** `config.py`, `vision/candidate_utils.py`
- **Impact:** Inconsistent behavior between old and new code paths
- **Fix approach:** Consolidate to single source of truth in `config.py`

### Global Logger Pattern
- **Issue:** Singleton logger with global state complicates testing and multi-threaded scenarios
- **Files:** `utils/logger.py` (lines 152-161)
- **Impact:** Difficult to test logging behavior; potential race conditions with buffer flushing
- **Fix approach:** Consider dependency injection pattern or context managers

---

## Reliability Concerns

### Screen Recognition Failure Modes
- **Issue:** Template matching and YOLO detection can fail silently without clear error reporting
- **Files:** `vision/recognizer.py`, `vision/yolo_item_detector.py`, `vision/hybrid_pipeline.py`
- **Impact:** Items may be missed or incorrectly identified without user awareness
- **Current mitigation:** Verification via MSE comparison (threshold=500), but threshold is arbitrary
- **Fix approach:** Add confidence-based fallback, structured failure reporting, and adaptive thresholds

### No Game Window State Validation
- **Issue:** Code does not verify game is in foreground, focused, or visible before operations
- **Files:** `core/loop.py`, `vision/capture.py`
- **Impact:** Could capture wrong screen content or send input to wrong window
- **Fix approach:** Add window detection and validation before each operation cycle

### OCR Failure is Silent
- **Issue:** `PriceReader` returns empty list on OCR failure without logging meaningful error
- **Files:** `vision/price_reader.py` (lines 46-48)
- **Impact:** Price reading silently fails; fallback pricing used without user awareness
- **Fix approach:** Add proper error logging, retry logic, and user notification

### Green Button Detection Fragility
- **Issue:** HSV color range `H=35~85, S>40, V>40` with 5% threshold for green detection
- **Files:** `core/loop.py` (lines 593-600)
- **Impact:** Slight UI color changes from lighting, game updates, or theme changes will cause `upload1` detection to fail
- **Fix approach:** Use template matching for upload1 button instead of color detection, or implement threshold calibration

### Arbitrary MSE Verification Threshold
- **Issue:** `VERIFY_MSE_THRESHOLD = 500` is used but how this value was determined is undocumented
- **Files:** `core/loop.py` (line 52)
- **Impact:** Verification may incorrectly pass or fail based on arbitrary threshold
- **Fix approach:** Document reasoning, potentially implement adaptive threshold based on image characteristics

---

## Performance Considerations

### Thread Pool Sizing Not Adaptive
- **Issue:** `HYBRID_MAX_WORKERS = 8` and CPU template matching uses 16 threads hardcoded
- **Files:** `config.py` (line 35), `vision/recognizer.py` (line 349)
- **Impact:** May over/under-utilize CPU resources on different hardware
- **Fix approach:** Auto-detect CPU core count and adjust accordingly

### GPU Recognition Not Default Despite Availability
- **Issue:** `USE_GPU_TEMPLATE_RECOGNITION = False` in config despite PyTorch CUDA availability check
- **Files:** `config.py` (line 62)
- **Impact:** Template matching runs on CPU when GPU could be faster
- **Fix approach:** Auto-detect GPU availability and enable by default

### Unbounded Memory Growth
- **Issue:** `processed_positions` set in `SellState` grows indefinitely during runtime
- **Files:** `core/loop.py` (lines 79, 411-416)
- **Impact:** Memory leak over long-running sessions
- **Fix approach:** Use bounded cache, LRU eviction, or periodic reset

### Full Screen Capture Per Sell Item
- **Issue:** Multiple full-screen captures per sell cycle: once for initial detection, once per candidate for verification
- **Files:** `core/loop.py` (lines 262-266, 448-452, 640)
- **Impact:** Significant overhead, especially when processing many items
- **Fix approach:** Capture once per cycle and reuse image data for all verifications

### Debug Image Writing Overhead
- **Issue:** Debug visualization writes multiple images per cycle when enabled
- **Files:** `vision/debug_visualizer.py`, `core/loop.py`
- **Impact:** I/O overhead and disk space consumption
- **Fix approach:** Make conditional, use lower frequency, or async writes

---

## Maintainability Issues

### Duplicate Code Between Pipelines
- **Issue:** `HybridPipeline` and `ItemCandidatePipeline` both implement deduplication and sorting
- **Files:** `vision/hybrid_pipeline.py`, `vision/item_candidate_pipeline.py`, `vision/candidate_utils.py`
- **Impact:** Maintenance burden, potential for inconsistency in behavior
- **Fix approach:** Consolidate shared logic in `candidate_utils.py`; have both pipelines use it

### Confusing Configuration Structure
- **Issue:** Config mixes YOLO settings, template settings, UI coordinates, and behavior flags
- **Files:** `config.py`
- **Impact:** Hard to understand what each setting controls
- **Fix approach:** Group related settings into dataclasses or separate config files by concern

### Limited Test Coverage
- **Issue:** Integration tests only cover happy paths; many error paths untested
- **Files:** `py_test/test_loop_integration.py`
- **Coverage gaps:**
  - OCR failure scenarios
  - YOLO model loading failures
  - Template matching failures
  - Hotkey conflict scenarios
  - Multi-monitor setups
  - Price calculation edge cases
- **Fix approach:** Add parameterized tests for failure modes; increase path coverage

### Inconsistent Logging Patterns
- **Issue:** Mix of `print_only`, `log_only`, `step`, `stats`, etc. without clear convention
- **Files:** `utils/logger.py`
- **Impact:** Logs are hard to parse and maintain
- **Fix approach:** Simplify to standard log levels (DEBUG, INFO, WARNING, ERROR)

### Run Mode Not Fully Implemented
- **Issue:** `RUN_MODE = "observe"` exists but loop logic doesn't fully respect it
- **Files:** `config.py` (line 27), `core/loop.py`
- **Impact:** Observe mode may not work as documented
- **Fix approach:** Implement observe mode properly or remove if unused

---

## Known Limitations

### Single Monitor Support Only
- **Issue:** Screen capture uses `monitors[1]` assuming primary display
- **Files:** `vision/capture.py` (lines 31, 80)
- **Impact:** Does not work correctly with multiple monitors or windowed game mode
- **Workaround:** Close other monitors or run game in windowed mode on primary

### Windows-Only Input Control
- **Issue:** `win32api.GetCursorPos()` in `mouse.py` line 95 is Windows-specific
- **Files:** `control/mouse.py` (line 94-95)
- **Impact:** Code does not run on Linux/macOS
- **Workaround:** None - Windows only

### Fixed Price Input Method is Fragile
- **Issue:** Price input uses hardcoded coordinate `PRICE_DIRECT_CLICK_X = 860` as a workaround
- **Files:** `config.py` (line 84), `core/loop.py` (line 562)
- **Impact:** Only works with specific game UI layout; breaks if UI changes
- **Workaround:** May need to recalibrate coordinates if game updates

### No Recovery from Partial Sell Failures
- **Issue:** If sell operation fails mid-flow, game state may be inconsistent
- **Files:** `core/loop.py` (`_sell_item_with_log` method)
- **Impact:** Could leave game in bad state requiring manual intervention
- **Workaround:** Monitor and restart if behavior seems abnormal

---

## Security Considerations

### No Input Validation
- **Issue:** Mouse/keyboard operations send input directly without bounds checking
- **Files:** `control/mouse.py`, `control/keyboard.py`
- **Impact:** Unexpected behavior if coordinates are out of screen bounds
- **Current mitigation:** Random delays simulate human input speed
- **Fix approach:** Add coordinate bounds validation before operations

### Clipboard Interference
- **Issue:** `pyperclip` used for price input, overwrites user clipboard content
- **Files:** `control/keyboard.py` (lines 97-119)
- **Impact:** User clipboard data lost during automation
- **Current mitigation:** Only used when `USE_CLIPBOARD_INPUT` is enabled
- **Fix approach:** Save/restore clipboard content around operations

### Anti-Cheat Detection Risk
- **Issue:** Uses pydirectinput which sends input at fixed intervals
- **Files:** `control/mouse.py`, `control/keyboard.py`
- **Impact:** Game anti-cheat may detect automation patterns
- **Current mitigation:** Random delays between actions
- **Fix approach:** Add more randomization, longer delays between operations

### Screen Capture Permissions
- **Issue:** Uses mss library with no access control or window targeting
- **Files:** `vision/capture.py`
- **Impact:** Captures whatever is on screen - could capture sensitive information
- **Current mitigation:** Only captures configured region
- **Fix approach:** Add explicit window targeting

---

## Areas Needing Improvement

### Error Handling Consistency
- **Priority:** High
- **Problem:** Some functions return `None`, others return empty lists, others raise exceptions
- **Affected files:** Throughout `vision/` and `core/` modules
- **Recommendation:** Establish consistent error handling pattern; document expected return types

### Configuration Documentation
- **Priority:** Medium
- **Problem:** Many config values lack comments explaining purpose, valid ranges, and impact
- **Affected files:** `config.py`
- **Recommendation:** Add docstrings to all config values with examples

### Template Management
- **Priority:** Medium
- **Problem:** 322+ templates stored as individual PNG files; no versioning or organization
- **Affected files:** `templates/` directory
- **Recommendation:** Implement template grouping, validation, and update process

### Performance Monitoring
- **Priority:** Low
- **Problem:** No metrics collection for detection latency, sell duration, success rates
- **Affected files:** Throughout
- **Recommendation:** Add structured metrics for observability and debugging

---

## Dependencies at Risk

### EasyOCR
- **Risk:** Heavy dependency (~1GB), slow initialization (10+ seconds)
- **Impact:** Application startup delayed; high memory usage
- **Mitigation:** Lazy initialization; only loaded when price reading needed
- **Migration:** Consider lighter OCR solution or pre-processed templates

### pydirectinput/keyboard
- **Risk:** Not thread-safe; requires elevated permissions
- **Impact:** May conflict with other input automation tools
- **Migration:** Abstract input layer for future cross-platform support

### MSS
- **Risk:** Platform-specific (Windows/Linux)
- **Impact:** Cannot run on macOS without changes
- **Migration:** Abstract capture layer for multi-platform support

---

## Test Coverage Gaps

### Price Calculation Edge Cases
- **What's not tested:** `calculate_price()` with negative values, zero, None inputs
- **Files:** `config.py` (lines 92-118)
- **Risk:** Invalid price inputs could cause negative prices or exceptions
- **Priority:** Medium

### End-to-End Sell Loop
- **What's not tested:** Complete sell flow with actual game interaction
- **Files:** `core/loop.py`
- **Risk:** Undetected failures in mouse/keyboard sequences; timing issues
- **Priority:** High

### Template Recognition Accuracy
- **What's not tested:** Recognition under different lighting, resolutions, UI scales
- **Files:** `vision/recognizer.py`
- **Risk:** False positives/negatives in production
- **Priority:** High

### Icon Filter Edge Cases
- **What's not tested:** Missing/corrupted icon templates, partial icon matches
- **Files:** `vision/item_candidate_pipeline.py`
- **Risk:** Invalid items sold
- **Priority:** Medium

### YOLO Model Loading Failures
- **What's not tested:** Missing model file, corrupted model, GPU unavailable
- **Files:** `vision/yolo_item_detector.py`
- **Risk:** Unhandled exceptions during detection
- **Priority:** Medium

---

*Concerns audit: 2026-03-25*
