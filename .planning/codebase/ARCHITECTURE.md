# Architecture

**Analysis Date:** 2026-03-25

## Pattern Overview

**Overall:** Event-driven automation with hybrid detection pipeline

**Key Characteristics:**
- Game automation for FPS inventory selling
- Three-tier detection: YOLO (fast) → Template (precise) → Pipeline (filter/dedup)
- Hotkey-controlled state machine (idle → running ↔ menu)
- Threaded architecture for non-blocking UI responsiveness
- Lazy initialization for heavy components (YOLO)

## Layers

**Main Entry (`main.py`):**
- Purpose: Application bootstrap and state orchestration
- Location: `main.py`
- Contains: Global component initialization, hotkey registration, main state machine
- Depends on: All modules
- Used by: OS runtime (`python main.py`)

**Configuration (`config.py`):**
- Purpose: Centralized constants and coordinate definitions
- Location: `config.py`
- Contains: Thresholds, screen coordinates, timing parameters, feature flags
- Depends on: None
- Used by: All modules

**Core Loop (`core/loop.py`):**
- Purpose: Main automation logic - detect items, verify, sell
- Location: `core/loop.py` (764 lines)
- Contains: `AutoSellLoop` class with `_run_one_cycle_new()` and `_sell_item_with_log()`
- Depends on: vision, control, config, utils.logger
- Used by: `main.py`

**Vision Layer (`vision/`):**
- Purpose: Screen capture, template matching, item detection, price OCR
- Location: `vision/capture.py`, `vision/recognizer.py`, `vision/price_reader.py`
- Contains:
  - `ScreenCapture` - mss-based screen capture with thread-local instances
  - `TemplateRecognizer` - CPU (ThreadPoolExecutor) or GPU (PyTorch conv2d) template matching
  - `PriceReader` - EasyOCR-based price reading
- Depends on: mss, cv2, numpy, torch (optional), easyocr (optional)
- Used by: `core/loop.py`

**Control Layer (`control/`):**
- Purpose: Input simulation (mouse/keyboard)
- Location: `control/mouse.py`, `control/keyboard.py`
- Contains:
  - `MouseController` - pydirectinput move/click/drag
  - `KeyboardController` - pydirectinput key presses, Alt+D combo, clipboard
- Depends on: pydirectinput, pyperclip (optional)
- Used by: `core/loop.py`

**Core Utilities (`core/`):**
- Purpose: Hotkey management and menu display
- Location: `core/hotkey.py`, `core/menu.py`
- Contains:
  - `HotkeyManager` - keyboard event listener with start/stop toggle
  - `SimpleMenu` - statistics display with F8/F9 actions
- Depends on: keyboard (library)
- Used by: `main.py`

**Logging (`utils/logger.py`):**
- Purpose: Dual-output logging (file always, console conditional)
- Location: `utils/logger.py`
- Contains: `Logger` class with buffered file writes
- Depends on: config (DEBUG_MODE)
- Used by: All modules via `get_logger()`

## Data Flow

**Main Loop Cycle (`_run_one_cycle_new`):**

1. **Screenshot** → `capture.capture_region(BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT)`
2. **Detection** → `_get_detector()` returns `HybridPipeline` or `TemplateRecognizer`
3. **Pipeline Processing** → `ItemCandidatePipeline.process()` or `HybridPipeline.process()`:
   - Coordinate conversion (ROI → screen)
   - Icon filter (reject "cannot sell" icons)
   - Deduplication (center distance < threshold)
   - Sorting (y ascending, then x ascending)
4. **Summary Logging** → raw/filtered/dedup/final counts
5. **Verification** → MSE comparison against snapshot before sell
6. **Sell** → `_sell_item_with_log()`:
   - Mouse move to item
   - Alt+D to list
   - Click upload1 (fixed coords or template match)
   - Click quantity button (x3)
   - Enter price (backspace + click fixed coordinate)
   - Click upload2 to confirm
7. **Idle Escalation** → If no items found, escalate delay through `IDLE_DELAYS` list

**State Machine (main.py):**

```
idle → (F8 or countdown) → running
running → (F8) → menu
menu → (F8) → running
menu → (F9) → exit
```

## Key Abstractions

**TemplateRecognizer:**
- Purpose: Multi-template matching with GPU acceleration
- Examples: `vision/recognizer.py` (618 lines)
- Pattern: Lazy-load templates on init, GPU path (PyTorch conv2d) vs CPU path (ThreadPoolExecutor + cv2.matchTemplate)
- Interface: `recognize()`, `recognize_as_raw_detections()`, `load_templates()`

**ItemCandidatePipeline:**
- Purpose: Filter/dedup/sort detected items
- Examples: `vision/item_candidate_pipeline.py` (238 lines)
- Pattern: Fixed 5-stage pipeline (convert → icon_filter → dedup → sort → rank)

**HybridPipeline:**
- Purpose: YOLO rough detection + template precise recognition
- Examples: `vision/hybrid_pipeline.py` (372 lines)
- Pattern: YOLO → ROI extraction → parallel template match → merge results
- Interface: `process(full_screen, roi_origin_x, roi_origin_y)`

**SellState (dataclass):**
- Purpose: Per-session state tracking
- Examples: `core/loop.py` lines 76-92
- Contains: processed_positions, total_sold, is_running, consecutive_empty, idle_delay, menu_visible

**ItemCandidate, RawItemDetection, RoundSummary (dataclasses):**
- Purpose: Type-safe data containers for pipeline stages
- Examples: `vision/item_types.py`

## Entry Points

**main.py:**
- Location: `main.py`
- Triggers: `python main.py` from command line
- Responsibilities:
  1. Register signal handler (SIGINT)
  2. Call `init_components()` → creates `AutoSellLoop`, `SimpleMenu`, `HotkeyManager`
  3. Start main loop in `threading.Thread`
  4. Run F8 toggle hotkey listener

**config.py:**
- Location: `config.py`
- Triggers: Imported by all modules
- Responsibilities:
  - Define all tunable parameters (thresholds, coordinates, delays)
  - `calculate_price()` function for symmetric subtraction pricing algorithm

## Error Handling

**Strategy:** Graceful degradation with fallback mechanisms

**Patterns:**
- GPU unavailable → fallback to CPU template matching (`TemplateRecognizer.__init__`)
- OCR initialization fails → `PriceReader` returns empty results
- Template match fails → ESC to dismiss dialog, skip item
- Green button check fails → skip item without selling
- Empty slot detected → skip without selling
- Icon filter failure → continues with all candidates

## Cross-Cutting Concerns

**Logging:** Dual-mode Logger (file always, console only if DEBUG_MODE)

**Validation:** MSE-based verification before selling (`compare_images_mse()` in `core/loop.py`)

**Authentication:** N/A - game automation without authentication

**Performance Optimization:**
- `USE_FIXED_COORDINATES=True` skips UI template matching
- `USE_CLIPBOARD_INPUT=True` for faster price entry
- `USE_GPU_TEMPLATE_RECOGNITION=False` (CPU mode)
- Thread-local mss instances for screen capture (`ScreenCapture._init_thread_local()`)
- Idle escalation delays through `IDLE_DELAYS` list

---

*Architecture analysis: 2026-03-25*
