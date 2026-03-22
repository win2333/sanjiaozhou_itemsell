# Codebase Structure

**Analysis Date:** 2026-03-23

## Directory Layout

```
sanjiaozhouGame/
├── main.py                    # Application entry point
├── config.py                  # Global configuration and constants
├── core/                      # Core orchestration layer
│   ├── loop.py               # Main auto-sell loop
│   ├── hotkey.py             # Keyboard hotkey manager
│   └── menu.py               # Interactive menu system
├── vision/                    # Computer vision layer
│   ├── capture.py            # Screen capture (mss wrapper)
│   ├── recognizer.py         # Template matching engine
│   ├── price_reader.py       # OCR for price recognition
│   ├── item_types.py         # Data classes (ItemCandidate, etc.)
│   ├── item_candidate_pipeline.py  # Filter/dedup/sort pipeline
│   ├── candidate_utils.py    # Deduplication and sorting
│   ├── yolo_item_detector.py # YOLO inference wrapper
│   ├── hybrid_pipeline.py    # YOLO + template hybrid
│   └── __init__.py
├── control/                   # Input control layer
│   ├── mouse.py              # Mouse controller (pydirectinput)
│   ├── keyboard.py           # Keyboard controller
│   └── __init__.py
├── utils/                     # Utility layer
│   ├── logger.py             # Logging system
│   ├── debug_visualizer.py   # Debug frame visualization
│   └── __init__.py
├── templates/                 # Template images (322+ items + UI)
│   ├── ui/                   # UI element templates (upload1, upload2, etc.)
│   ├── 物品名称.png          # Item template images
│   └── icon_01.png           # Unsellable item icon
├── py_test/                   # Test and debugging tools
│   ├── test_screenshot.py    # Screen capture test
│   ├── test_recognize.py     # Template recognition test
│   ├── test_recognizer_backend.py  # GPU/CPU backend test
│   ├── test_item_candidate_pipeline.py  # Pipeline test
│   ├── test_loop_integration.py  # Loop integration test
│   ├── test_price_method.py   # Price input method test
│   ├── test_template_on_game_screenshot.py  # E2E recognition test
│   ├── crop_templates.py     # Template cropping utility
│   ├── debug_markers.py      # UI coordinate markers
│   ├── debug_coords.py       # Coordinate debugging
│   ├── find_coords.py        # Coordinate finder
│   └── nul                   # Placeholder
├── debug/                     # Debug output directory
├── logs/                      # Log files (auto-generated)
├── models/                    # ML models (YOLO weights)
├── backgrounds/               # Background images for testing
├── datasets/                  # Training data
├── runs/                      # YOLO training runs
├── tools/                     # Standalone tools
├── docs/                      # Documentation
├── browser-use-test/          # Separate project (git ignored)
├── .worktrees/                # Git worktrees (experiments)
└── .planning/                 # GSD planning docs
```

## Directory Purposes

**Core:**
- Purpose: Orchestrate detection and selling workflow
- Contains: Main loop, hotkey management, menu system
- Key files: `core/loop.py` (AutoSellLoop class)

**Vision:**
- Purpose: All computer vision operations
- Contains: Capture, detection, candidate processing
- Key files: `vision/recognizer.py` (template matching), `vision/hybrid_pipeline.py` (detection strategy)

**Control:**
- Purpose: Low-level input simulation
- Contains: Mouse and keyboard controllers
- Key files: `control/mouse.py`, `control/keyboard.py`

**Utils:**
- Purpose: Shared utilities (logging, visualization)
- Key files: `utils/logger.py`

**Templates:**
- Purpose: Reference images for recognition
- Contains: 322+ item templates, UI element templates
- Format: PNG files with Chinese names

**Py_test:**
- Purpose: Testing and debugging utilities
- Contains: Standalone test scripts, coordinate tools
- Pattern: Each file tests specific component

## Key File Locations

**Entry Points:**
- `main.py`: Application startup and state machine
- `core/loop.py:AutoSellLoop.start()`: Main execution method

**Configuration:**
- `config.py`: All configuration constants and parameters
  - Detection thresholds (TEMPLATE_MATCH_THRESHOLD, YOLO_CONFIDENCE_THRESHOLD)
  - Coordinates (BACKPACK_*, UPLOAD1_*, UPLOAD2_*)
  - Mode switches (USE_FIXED_COORDINATES, ITEM_DETECTOR_MODE)
  - Price calculation (calculate_price function)

**Core Logic:**
- `core/loop.py`:
  - `AutoSellLoop` class (lines 107-738)
  - `_run_one_cycle_new()`: One detection + sell cycle (lines 252-428)
  - `_sell_item_with_log()`: Single item sell operation (lines 462-577)
  - `_verify_candidate()`: MSE verification (lines 430-459)

**Vision Processing:**
- `vision/recognizer.py:TemplateRecognizer`:
  - `recognize()`: Full detection with GPU/CPU selection (line 176)
  - `_recognize_gpu()`: GPU accelerated matching (line 239)
  - `_recognize_cpu()`: CPU multi-threaded matching (line 344)
- `vision/hybrid_pipeline.py:HybridPipeline`:
  - `process()`: YOLO + template combination (line 71)
- `vision/item_candidate_pipeline.py:ItemCandidatePipeline`:
  - `process()`: Filter/dedup/sort pipeline (line 52)

**Data Types:**
- `vision/item_types.py`:
  - `RawItemDetection`: Raw detector output
  - `ItemCandidate`: Processed candidate with screen coordinates
  - `EliminatedCandidate`: Filtered-out candidate with reason
  - `RoundSummary`: Per-cycle statistics

**Control:**
- `control/mouse.py:MouseController`:
  - `move_to()`, `click()`, `double_click()`, `drag()`, `get_position()`
- `control/keyboard.py:KeyboardController`:
  - `press()`, `combo()`, `type_text()`, `alt_d()`, `copy_to_clipboard()`

**Logging:**
- `utils/logger.py:Logger`:
  - Methods: `log()`, `step()`, `log_only()`, `print_only()`, `stats()`
  - Buffer: 2-second flush interval
  - File: `logs/selling_YYYYMMDD_HHMMSS.txt`

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `item_candidate_pipeline.py`)
- Template images: `物品名称.png` (Chinese, with optional color suffix)
- Data files: Lowercase with underscores

**Directories:**
- All directories: `kebab-case` or `lowercase` (mixed usage)
- Resource dirs: `templates/`, `models/`, `datasets/`, `backgrounds/`
- Output dirs: `debug/`, `logs/`, `runs/`

**Classes:**
- PascalCase: `TemplateRecognizer`, `AutoSellLoop`, `ItemCandidatePipeline`
- Data classes: PascalCase: `ItemCandidate`, `RoundSummary`, `RawItemDetection`

**Functions/Methods:**
- snake_case: `recognize()`, `deduplicate()`, `sort_candidates()`
- Private methods: `_underscore_prefix()`

**Variables:**
- snake_case: `item_recognizer`, `raw_detections`, `click_x`
- Constants: `UPPER_SNAKE_CASE`: `TEMPLATE_MATCH_THRESHOLD`, `BACKPACK_LEFT`
- Dataclass fields: snake_case: `screen_x`, `screen_y`, `passed_icon_filter`

## Where to Add New Code

**New Detection Backend:**
- Primary: Create new file in `vision/`
- Example: `vision/new_detector.py`
- Register in `core/loop.py:_get_detector()` (line 221)

**New Filter Stage:**
- Primary: Add method to `vision/item_candidate_pipeline.py`
- Example: `_apply_quality_filter()`
- Modify `process()` to call new stage (line 52)

**New Control Action:**
- Primary: `control/mouse.py` or `control/keyboard.py`
- Example: Add `scroll()` to `MouseController`

**New Utility:**
- Primary: `utils/`
- Example: `utils/image_utils.py` for shared image operations

**New Test:**
- Primary: `py_test/`
- Pattern: Standalone script, e.g., `py_test/test_new_feature.py`

**New Template:**
- Location: `templates/`
- Naming: `物品名称.png` or `物品名称(颜色).png`
- Format: PNG with transparency support

## Special Directories

**Templates:**
- Purpose: Reference images for item and UI recognition
- Contains: 322+ item templates, UI templates, icon template
- Generated: No (manually created/captured)
- Committed: Yes (in git)

**Debug:**
- Purpose: Debug output images and visualizations
- Generated: Yes (runtime)
- Committed: No (.gitignore)

**Logs:**
- Purpose: Runtime log files
- Generated: Yes (runtime, auto-named by timestamp)
- Committed: No (.gitignore)

**Models:**
- Purpose: ML model weights (YOLO)
- Contains: `item_detector.pt`
- Generated: No (trained separately)
- Committed: Yes

**Py_test:**
- Purpose: Standalone testing scripts
- Contains: 12+ test/debug scripts
- Pattern: Each tests one component independently
- No pytest/unittest framework, just standalone scripts

**Docs:**
- Purpose: Project documentation
- Contains: AI context files, architecture docs
- Note: GSD planning docs go in `.planning/codebase/`

---

*Structure analysis: 2026-03-23*
