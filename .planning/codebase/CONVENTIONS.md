# Coding Conventions

**Analysis Date:** 2026-03-25

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `item_candidate_pipeline.py`, `price_reader.py`)
- Test files: `test_*.py` prefix (e.g., `test_recognize.py`, `test_loop_integration.py`)
- Debug/util scripts: `debug_*.py`, `crop_*.py`, `find_*.py`

**Functions/Methods:**
- `snake_case` for functions and methods
- Prefix with underscore for "private" internal methods: `_run_one_cycle_new()`, `_verify_candidate()`
- Action verbs for methods: `capture_region()`, `recognize()`, `move_to()`, `click()`

**Variables:**
- `snake_case` for local variables: `raw_detections`, `click_x`, `price_offset_x`
- CamelCase for dataclass names: `MatchResult`, `ItemCandidate`, `SellState`, `RawItemDetection`
- ALL_CAPS for constants: `TEMPLATE_MATCH_THRESHOLD`, `USE_GPU_TEMPLATE_RECOGNITION`, `DEDUP_DISTANCE`

**Types/Classes:**
- PascalCase for class names: `TemplateRecognizer`, `ScreenCapture`, `MouseController`, `AutoSellLoop`
- PascalCase for dataclasses: `ItemRecord`, `RoundSummary`, `EliminatedCandidate`
- snake_case for module-level type aliases

## Code Style

**Formatting:**
- No explicit formatter configured (no `black`, `ruff`, `prettierrc`)
- 4-space indentation
- Maximum line length not enforced

**Imports:**
- Standard library first, then third-party, then local
- `sys.path.insert(0, '.')` pattern used in test files to enable imports
- Absolute imports from package: `from vision.capture import ScreenCapture`

**Type Annotations:**
- Used in function signatures: `def recognize(self, image: np.ndarray, draw_debug: bool = False) -> List[MatchResult]:`
- `Optional[]` for nullable parameters: `price_reader: Optional[PriceReader] = None`
- `from typing import List, Tuple, Optional, Set, Dict` used throughout

## Error Handling

**Pattern: Silent failures with logging**
```python
# Graceful degradation when optional resources missing
icon_templates: List[np.ndarray] = []
if icon_path:
    try:
        icon_img = cv2.imread(icon_path, cv2.IMREAD_COLOR)
        if icon_img is not None:
            icon_templates.append(icon_img)
    except Exception as e:
        get_logger().log_only("[初始化]", f"加载 icon 模板失败: {e}")
```

**Pattern: Validation with early returns**
```python
def _verify_candidate(self, candidate, snapshot):
    if snapshot is None:
        return True  # Skip verification if no snapshot
    # ... validation logic
    if mse >= VERIFY_MSE_THRESHOLD:
        return False
    return True
```

**Pattern: Skip with reason logging**
```python
def _skip(reason: str) -> None:
    skipped_names.add(item_name)
    logger.log_only("[操作]", f"[{item_name}] {reason}，跳过")
    logger.print_only(f"跳过: {item_name} ({reason})")
```

## Logging

**Framework:** Custom `Logger` class in `utils/logger.py`

**Output modes:**
- `DEBUG_MODE = True`: All logs output to console + file
- `DEBUG_MODE = False`: Logs write to file only, console shows minimal info

**Key methods:**
```python
logger.log_only("[前缀]", "消息")      # File only, no console
logger.print_only("消息")             # Console + file
logger.step("消息")                   # Timestamped step (file + console in DEBUG)
logger.stats("消息")                  # Statistics
```

**Prefix conventions:**
- `[操作]` - Mouse/keyboard operations
- `[识别]` - Vision recognition
- `[验证]` - Candidate verification
- `[统计]` - Statistics
- `[初始化]` - Initialization messages
- `[扫描]` - YOLO/scanning phase
- `[步骤]` - Detailed step logging
- `[控制台]` - Console-only output

## Recognition Patterns

**Template Matching:**
- Uses OpenCV `cv2.matchTemplate()` with `TM_CCOEFF_NORMED`
- Two backends: GPU (PyTorch CUDA) and CPU (ThreadPoolExecutor)
- Color verification after template match (cosine similarity of average BGR colors)
- Deduplication by distance: keeps highest confidence within `DEDUP_DISTANCE` pixels

**Architecture: Hybrid Pipeline**
1. Raw detection (YOLO or template matching) → `RawItemDetection`
2. Coordinate conversion (ROI local → screen)
3. Icon filter (filters "cannot sell" icons)
4. Deduplication
5. Sorting (y ascending, then x ascending)
6. Output: `(candidates, eliminated, summary)`

**GPU Recognition (`_recognize_gpu`):**
- Groups templates by (height, width)
- Precomputes normalized templates: `(T - mean_T) / std_T`
- Uses `conv2d` for batch template matching
- Implements TM_CCOEFF_NORMED manually for GPU efficiency

**CPU Recognition (`_recognize_cpu`):**
- ThreadPoolExecutor with 16 workers
- Each template matched independently
- Color verification after template match

## Control Patterns

**Mouse Control (`control/mouse.py`):**
- Uses `pydirectinput` for mouse operations
- Random delays between actions: `random.uniform(min_delay, max_delay)`
- Methods: `move_to(x, y)`, `click(x, y)`, `double_click()`, `right_click()`, `drag()`

**Keyboard Control (`control/keyboard.py`):**
- Uses `pydirectinput` for key operations
- `combo(keys)` for key combinations with proper key-down/key-up ordering
- `type_text()` filters non-digit characters for price input
- Optional clipboard support via `pyperclip`

**Screen Capture (`vision/capture.py`):**
- Uses `mss` for cross-platform screen capture
- Thread-local mss instances for thread safety
- Methods: `capture_region()`, `capture_full_screen()`, `capture_center_region()`

## Data Flow

**Main Loop (`core/loop.py`):**
1. Capture backpack region screenshot
2. Detect items via detector (YOLO/template/hybrid)
3. Run candidate pipeline (filter, dedup, sort)
4. For each candidate:
   - Capture verification snapshot
   - Verify candidate still present (MSE comparison)
   - Execute sell flow if verified
5. Sleep with idle delay if no candidates

**State Management:**
- `SellState` dataclass tracks: `processed_positions`, `total_sold`, `is_running`, `consecutive_empty`, `idle_delay`
- `ItemRecord` for verification: stores name, coordinates, snapshot

## Key Abstractions

**TemplateRecognizer:**
- Loads templates from directory (supports Chinese filenames via binary read + decode)
- `recognize()` returns `List[MatchResult]` with coordinates and confidence
- `recognize_as_raw_detections()` returns `List[RawItemDetection]` for pipeline

**ItemCandidatePipeline:**
- Stateless processor: `process(raw_detections, roi_origin_x, roi_origin_y, roi_img)`
- Returns tuple: `(candidates, eliminated, summary)`

**MatchResult vs RawItemDetection vs ItemCandidate:**
- `MatchResult`: Template recognition output (coordinates in matched region)
- `RawItemDetection`: Pipeline input (ROI local coords, source="template"|"yolo")
- `ItemCandidate`: Pipeline output (screen coords, ranked, filtered)

## Comments

**When to Comment:**
- Complex algorithms: "对称减法算法 - 计算最优价格" (price calculation)
- Non-obvious behavior: "9 个格子颜色是否一致（相互间容差小）"
- Debug code explanation: "拍当前画面与 snapshot 做 MSE 对比"

**Docstrings:**
- Args/Returns format used in public methods
- Chinese comments for Chinese developers (project uses Chinese documentation)

## Module Design

**Exports:**
- No explicit `__all__` defined
- Classes imported directly: `from vision.capture import ScreenCapture`

**Package Structure:**
```
sanjiaozhouGame/
├── main.py                    # Entry point, initializes components
├── config.py                  # All configuration constants
├── core/                      # Business logic
│   ├── loop.py               # AutoSellLoop, SellState, ItemRecord
│   ├── hotkey.py             # HotkeyManager
│   └── menu.py               # SimpleMenu
├── vision/                    # Image processing
│   ├── capture.py            # ScreenCapture
│   ├── recognizer.py         # TemplateRecognizer, MatchResult
│   ├── price_reader.py       # PriceReader (OCR)
│   ├── item_types.py         # Dataclasses
│   ├── item_candidate_pipeline.py  # ItemCandidatePipeline
│   └── ...
├── control/                   # Input control
│   ├── mouse.py              # MouseController
│   └── keyboard.py           # KeyboardController
├── utils/                     # Utilities
│   └── logger.py             # Logger
└── py_test/                   # Tests and debug tools
```

---

*Convention analysis: 2026-03-25*
