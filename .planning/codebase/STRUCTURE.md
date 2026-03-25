# Codebase Structure

**Analysis Date:** 2026-03-25

## Directory Layout

```
sanjiaozhouGame/
├── main.py                    # Main entry point
├── config.py                  # Global configuration
├── core/                      # Core automation logic
│   ├── __init__.py
│   ├── loop.py               # AutoSellLoop (main cycle, 764 lines)
│   ├── hotkey.py             # HotkeyManager
│   └── menu.py               # SimpleMenu
├── vision/                    # Visual recognition
│   ├── __init__.py
│   ├── capture.py            # ScreenCapture
│   ├── recognizer.py         # TemplateRecognizer (CPU/GPU, 618 lines)
│   ├── price_reader.py       # PriceReader (EasyOCR)
│   ├── item_types.py         # Dataclasses (ItemCandidate, etc.)
│   ├── item_candidate_pipeline.py  # Filter/dedup pipeline (238 lines)
│   ├── candidate_utils.py    # Shared dedup/sort functions
│   ├── yolo_item_detector.py # YoloItemDetector
│   └── hybrid_pipeline.py    # HybridPipeline (YOLO+template, 372 lines)
├── control/                   # Input control
│   ├── __init__.py
│   ├── mouse.py              # MouseController
│   └── keyboard.py           # KeyboardController
├── utils/                     # Utilities
│   ├── logger.py             # Logger (dual-output)
│   └── debug_visualizer.py   # Debug frame annotation
├── templates/                 # Template images
│   ├── ui/                   # UI element templates
│   └── [322+ item templates] # Item screenshots
├── debug/                     # Debug output images
│   └── round_NNNN/           # Per-round debug frames
├── logs/                      # Log files
│   └── selling_YYYYMMDD_HHMMSS.txt
├── py_test/                   # Test utilities
│   ├── test_screenshot.py
│   ├── test_recognize.py
│   ├── test_item_candidate_pipeline.py
│   ├── test_loop_integration.py
│   ├── test_recognizer_backend.py
│   ├── test_price_method.py
│   ├── test_template_on_game_screenshot.py
│   ├── crop_templates.py
│   ├── debug_markers.py
│   ├── debug_coords.py
│   ├── find_coords.py
│   └── nul
├── browser-use-test/          # Browser automation tests (unrelated)
│   ├── bilibili_favorites.py
│   ├── test_proxy.py
│   ├── test_browser_use.py
│   └── src/
├── models/                    # YOLO model weights
├── tools/                     # Standalone tools
│   └── verify_backgrounds.py
└── .planning/                 # GSD planning docs
    └── codebase/
        ├── ARCHITECTURE.md
        └── STRUCTURE.md
```

## Directory Purposes

**Root (`main.py`, `config.py`):**
- Purpose: Application bootstrap and global configuration
- Contains: Entry point, feature flags, screen coordinates, price algorithm

**`core/`:**
- Purpose: Core automation orchestration
- Contains: Main loop, hotkey handling, menu system
- Key files: `loop.py` (764 lines - largest file)

**`vision/`:**
- Purpose: All visual recognition capabilities
- Contains: Screen capture, template matching, OCR, YOLO, hybrid pipelines
- Key files: `recognizer.py` (618 lines), `hybrid_pipeline.py` (372 lines)

**`control/`:**
- Purpose: Input simulation
- Contains: Mouse and keyboard controllers using pydirectinput

**`utils/`:**
- Purpose: Shared utilities
- Contains: Logger with buffered file output

**`templates/`:**
- Purpose: Reference images for template matching
- Contains: 322+ item templates + UI element templates

**`py_test/`:**
- Purpose: Test and debugging utilities
- Contains: Screenshot tests, coordinate finders, template cropping

**`browser-use-test/`:**
- Purpose: Unrelated browser automation project
- Note: Gitignored, separate from main project

## Key File Locations

**Entry Points:**
- `main.py`: Application entry, state machine, component initialization
- `config.py`: Configuration constants (imported by all modules)

**Configuration:**
- `config.py`: Thresholds, coordinates, timeouts, feature flags

**Core Logic:**
- `core/loop.py`: Main selling loop (AutoSellLoop class)
- `core/hotkey.py`: HotkeyManager (keyboard event handling)
- `core/menu.py`: SimpleMenu (stats display)

**Vision:**
- `vision/capture.py`: ScreenCapture (mss-based)
- `vision/recognizer.py`: TemplateRecognizer (CPU/GPU template matching)
- `vision/price_reader.py`: PriceReader (EasyOCR price reading)
- `vision/item_types.py`: Data classes for pipeline
- `vision/item_candidate_pipeline.py`: Filter/dedup pipeline
- `vision/hybrid_pipeline.py`: YOLO + template hybrid
- `vision/yolo_item_detector.py`: YOLO wrapper
- `vision/candidate_utils.py`: Shared dedup/sort utilities
- `vision/debug_visualizer.py`: Debug frame annotation

**Control:**
- `control/mouse.py`: MouseController (pydirectinput)
- `control/keyboard.py`: KeyboardController (pydirectinput + pyperclip)

**Utilities:**
- `utils/logger.py`: Logger (dual-output: file always, console conditional)
- `utils/debug_visualizer.py`: Debug frame annotation (NOT in vision/)

## Naming Conventions

**Files:**
- `snake_case.py`: All Python files use snake_case
- `lower_snake_case`: Modules and utilities

**Functions:**
- `snake_case`: All functions and methods
- `_prefixed_with_underscore`: "Private" internal functions (e.g., `_run_one_cycle_new`, `_sell_item_with_log`)

**Classes:**
- `PascalCase`: All classes (e.g., `AutoSellLoop`, `TemplateRecognizer`, `ScreenCapture`)

**Variables:**
- `snake_case`: All variables (e.g., `item_recognizer`, `consecutive_empty`)
- `UPPER_SNAKE_CASE`: Constants in `config.py` (e.g., `TEMPLATE_MATCH_THRESHOLD`, `IDLE_DELAYS`)

**Dataclasses:**
- `PascalCase` with `@dataclass` decorator (e.g., `SellState`, `ItemCandidate`, `MatchResult`)

## Where to Add New Code

**New Feature (detection/selling logic):**
- Primary code: `core/loop.py` (add method to `AutoSellLoop` or modify `_sell_item_with_log`)
- Tests: `py_test/test_loop_integration.py`

**New Vision Module:**
- Implementation: `vision/` (create new file or extend existing)
- If adding new detector type: Consider `HybridPipeline` integration in `_get_detector()`

**New Control Action:**
- Implementation: `control/mouse.py` or `control/keyboard.py`
- Usage: `core/loop.py`

**Configuration Changes:**
- `config.py`: Add new constants (UPPER_SNAKE_CASE)
- Consider adding feature flag for gradual rollout

**Testing:**
- Test utilities: `py_test/`
- Run individual tests: `python py_test/test_xxx.py`

## Special Directories

**`templates/`:**
- Purpose: Reference images for item recognition
- Contains: 322+ PNG files named with item names (Chinese supported)
- Generated: No (manually curated screenshots)
- Committed: Yes (version controlled)

**`debug/`:**
- Purpose: Debug output images
- Structure: `debug/round_NNNN/` with per-round frames (00_original.png, 01_yolo.png, 02_pipeline.png)
- Generated: Yes (runtime, controlled by `SAVE_DEBUG_IMAGES`)
- Committed: No (gitignored)

**`logs/`:**
- Purpose: Runtime logs
- Format: `selling_YYYYMMDD_HHMMSS.txt`
- Generated: Yes (runtime)
- Committed: No (gitignored)

**`models/`:**
- Purpose: YOLO model weights
- Contains: `item_detector.pt`
- Generated: No (trained separately)
- Committed: Yes

**`py_test/`:**
- Purpose: Test and debugging utilities
- Contains: 12 standalone test scripts
- Pattern: Each tests one component independently
- Note: No pytest/unittest framework - standalone scripts only

---

*Structure analysis: 2026-03-25*
