# 项目 CLAUDE.md

## 语言设置
默认回复简体中文（Simplified Chinese）

## /workflow3 - 三阶段工作流
您正在处理当前项目。遵循用户的三阶段工作流规则，从【分析问题】阶段开始。

### 【分析问题】
**必须做的事**：
1. **需求澄清**（如果用户提出了需求）：
   - 理解表层需求：用户说要什么
   - 追问本质："为什么需要？""想解决什么问题？""有没有其他方式？"
   - 收集信息：Who/When/Where/How
   - 识别边界：例外情况、异常流程、限制条件
   - 输出结构化需求文档
2. **代码分析**：
   - 理解用户意图，有歧义时提问
   - 搜索所有相关代码
   - 识别问题根因
   - 主动发现：重复代码、不合理命名、多余代码、过时设计、复杂调用、不一致类型

**绝对禁止**：
- ❌ 修改任何代码
- ❌ 急于给出解决方案
- ❌ 跳过搜索和理解
- ❌ 不分析就推荐方案

**阶段转换**：向用户提问，如果存在多个无法抉择的方案要问用户。

### 【制定方案】
**前置条件**：用户明确回答了关键技术决策。

**必须做的事**：
- 列出变更文件清单（新增、修改、删除）
- 消除重复逻辑（DRY原则）
- 确保符合良好架构设计

**阶段转换**：继续向用户收集关键决策，直到没有不明确的问题。

### 【执行方案】
**必须做的事**：
- 严格按照选定方案实现
- 修改后运行类型检查

**绝对禁止**：
- ❌ 提交代码（除非用户明确要求）
- ❌ 启动开发服务器

**阶段声明**：用【分析问题】【制定方案】【执行方案】标记当前阶段。

使用示例: `/workflow3`

---

## 项目结构

```
sanjiaozhouGame/
+-- main.py                    # 主入口程序
+-- config.py                  # 全局配置
+-- core/                      # 核心模块
|   +-- loop.py               # 主循环
|   +-- hotkey.py             # 热键管理
|   +-- menu.py               # 菜单系统
+-- vision/                    # 视觉识别
|   +-- capture.py            # 屏幕截图
|   +-- recognizer.py         # 模板识别
|   +-- price_reader.py       # 价格识别(OCR)
+-- control/                   # 输入控制
|   +-- mouse.py              # 鼠标控制
|   +-- keyboard.py           # 键盘控制
+-- utils/                     # 工具模块
|   +-- logger.py             # 日志系统
+-- templates/                 # 模板图片目录
|   +-- ui/                   # UI元素模板
|   +-- [322个物品模板]       # 物品截图
+-- debug/                     # debug输出图片
+-- logs/                      # 日志文件
+-- py_test/                   # 测试工具
|   +-- test_screenshot.py    # 截图测试
|   +-- test_recognize.py     # 识别测试
|   +-- debug_markers.py      # UI坐标标记
|   +-- debug_coords.py       # 坐标调试
|   +-- crop_templates.py     # 模板裁剪
|   +-- find_coords.py        # 坐标查找
|   +-- nul                   # 空文件
```

<!-- GSD:project-start source:PROJECT.md -->
## Project

**游戏装备自动出售工具**

游戏装备自动出售工具，通过屏幕视觉识别（模板匹配 + OCR）自动在游戏背包中检测并出售物品。运行在Windows平台，使用热键（F8）控制开始/暂停。当前代码已完成基础功能，但存在检测不稳定和debug可观测性不足的问题。

**Core Value:** **可靠的物品检测** — 每次扫描都能准确识别所有可售物品，不漏识别；同时具备完整的检测过程可观测性，debug模式能看到详细的中间结果。

### Constraints

- **性能模式**：CPU-only — 不使用 GPU 加速
- **平台**：Windows — 游戏自动化依赖 pydirectinput/win32
- **游戏分辨率**：固定坐标（BACKPACK_LEFT/TOP/WIDTH/HEIGHT）— 假设游戏窗口位置固定
- **Python版本**：Python 3.x — 依赖 pydirectinput、mss、cv2 等
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12+ - Main game automation scripting
- None significant
## Runtime
- Windows (Desktop game automation)
- Python 3.12+ (based on `browser-use-test/pyproject.toml` requires-python >=3.12)
- pip (requirements.txt)
- uv (for browser-use-test sub-project)
## Frameworks
- Custom game automation framework
- Template matching (OpenCV-based)
- YOLO object detection (optional, via ultralytics)
- OpenCV 4.8.0+ - Image processing, template matching
- PyTorch (optional) - GPU acceleration for template matching
- Ultralytics YOLO (optional) - Deep learning object detection
- pydirectinput - Mouse/keyboard control (primary)
- pyautogui - Input control (fallback)
- keyboard - Global hotkey handling
- pywin32 - Windows API access
- EasyOCR 1.7.0+ - Local OCR for price recognition (GPU-accelerated)
- mss 9.0.1+ - Fast cross-platform screen capture
## Key Dependencies
- `opencv-python>=4.8.0` - Template matching, image processing
- `numpy>=1.24.0` - Numerical operations for image arrays
- `mss>=9.0.1` - Screen capture
- `pydirectinput>=1.0.4` - Mouse/keyboard simulation
- `keyboard>=0.13.5` - Hotkey registration and listening
- `torch` - GPU acceleration (auto-detected if CUDA available)
- `ultralytics` - YOLO item detection model
- `easyocr>=1.7.0` - OCR for price reading
- `Pillow>=10.0.0` - Image format conversion, Chinese font rendering
- `pyperclip>=1.8.0` - Clipboard operations for price input
- `pywin32>=306` - Windows API bindings
- `browser-use>=0.12.2` - AI-powered browser automation (browser-use-test/)
## Configuration
- `config.py` - Main configuration file
- Hardcoded game window coordinates (pixel-based)
- Environment-specific paths for templates
- `requirements.txt` - Main project dependencies
- `browser-use-test/pyproject.toml` - Browser automation sub-project
## Platform Requirements
- Windows OS (game automation for desktop game)
- Python 3.12+
- Screen resolution awareness (coordinates hardcoded for 1920x1080)
- Windows with game client running
- 1920x1080 or compatible resolution
- Game window must be visible at configured coordinates
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Python modules: `snake_case.py` (e.g., `item_candidate_pipeline.py`, `price_reader.py`)
- Test files: `test_*.py` prefix (e.g., `test_recognize.py`, `test_loop_integration.py`)
- Debug/util scripts: `debug_*.py`, `crop_*.py`, `find_*.py`
- `snake_case` for functions and methods
- Prefix with underscore for "private" internal methods: `_run_one_cycle_new()`, `_verify_candidate()`
- Action verbs for methods: `capture_region()`, `recognize()`, `move_to()`, `click()`
- `snake_case` for local variables: `raw_detections`, `click_x`, `price_offset_x`
- CamelCase for dataclass names: `MatchResult`, `ItemCandidate`, `SellState`, `RawItemDetection`
- ALL_CAPS for constants: `TEMPLATE_MATCH_THRESHOLD`, `USE_GPU_TEMPLATE_RECOGNITION`, `DEDUP_DISTANCE`
- PascalCase for class names: `TemplateRecognizer`, `ScreenCapture`, `MouseController`, `AutoSellLoop`
- PascalCase for dataclasses: `ItemRecord`, `RoundSummary`, `EliminatedCandidate`
- snake_case for module-level type aliases
## Code Style
- No explicit formatter configured (no `black`, `ruff`, `prettierrc`)
- 4-space indentation
- Maximum line length not enforced
- Standard library first, then third-party, then local
- `sys.path.insert(0, '.')` pattern used in test files to enable imports
- Absolute imports from package: `from vision.capture import ScreenCapture`
- Used in function signatures: `def recognize(self, image: np.ndarray, draw_debug: bool = False) -> List[MatchResult]:`
- `Optional[]` for nullable parameters: `price_reader: Optional[PriceReader] = None`
- `from typing import List, Tuple, Optional, Set, Dict` used throughout
## Error Handling
## Logging
- `DEBUG_MODE = True`: All logs output to console + file
- `DEBUG_MODE = False`: Logs write to file only, console shows minimal info
- `[操作]` - Mouse/keyboard operations
- `[识别]` - Vision recognition
- `[验证]` - Candidate verification
- `[统计]` - Statistics
- `[初始化]` - Initialization messages
- `[扫描]` - YOLO/scanning phase
- `[步骤]` - Detailed step logging
- `[控制台]` - Console-only output
## Recognition Patterns
- Uses OpenCV `cv2.matchTemplate()` with `TM_CCOEFF_NORMED`
- Two backends: GPU (PyTorch CUDA) and CPU (ThreadPoolExecutor)
- Color verification after template match (cosine similarity of average BGR colors)
- Deduplication by distance: keeps highest confidence within `DEDUP_DISTANCE` pixels
- Groups templates by (height, width)
- Precomputes normalized templates: `(T - mean_T) / std_T`
- Uses `conv2d` for batch template matching
- Implements TM_CCOEFF_NORMED manually for GPU efficiency
- ThreadPoolExecutor with 16 workers
- Each template matched independently
- Color verification after template match
## Control Patterns
- Uses `pydirectinput` for mouse operations
- Random delays between actions: `random.uniform(min_delay, max_delay)`
- Methods: `move_to(x, y)`, `click(x, y)`, `double_click()`, `right_click()`, `drag()`
- Uses `pydirectinput` for key operations
- `combo(keys)` for key combinations with proper key-down/key-up ordering
- `type_text()` filters non-digit characters for price input
- Optional clipboard support via `pyperclip`
- Uses `mss` for cross-platform screen capture
- Thread-local mss instances for thread safety
- Methods: `capture_region()`, `capture_full_screen()`, `capture_center_region()`
## Data Flow
- `SellState` dataclass tracks: `processed_positions`, `total_sold`, `is_running`, `consecutive_empty`, `idle_delay`
- `ItemRecord` for verification: stores name, coordinates, snapshot
## Key Abstractions
- Loads templates from directory (supports Chinese filenames via binary read + decode)
- `recognize()` returns `List[MatchResult]` with coordinates and confidence
- `recognize_as_raw_detections()` returns `List[RawItemDetection]` for pipeline
- Stateless processor: `process(raw_detections, roi_origin_x, roi_origin_y, roi_img)`
- Returns tuple: `(candidates, eliminated, summary)`
- `MatchResult`: Template recognition output (coordinates in matched region)
- `RawItemDetection`: Pipeline input (ROI local coords, source="template"|"yolo")
- `ItemCandidate`: Pipeline output (screen coords, ranked, filtered)
## Comments
- Complex algorithms: "对称减法算法 - 计算最优价格" (price calculation)
- Non-obvious behavior: "9 个格子颜色是否一致（相互间容差小）"
- Debug code explanation: "拍当前画面与 snapshot 做 MSE 对比"
- Args/Returns format used in public methods
- Chinese comments for Chinese developers (project uses Chinese documentation)
## Module Design
- No explicit `__all__` defined
- Classes imported directly: `from vision.capture import ScreenCapture`
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Game automation for FPS inventory selling
- Three-tier detection: YOLO (fast) → Template (precise) → Pipeline (filter/dedup)
- Hotkey-controlled state machine (idle → running ↔ menu)
- Threaded architecture for non-blocking UI responsiveness
- Lazy initialization for heavy components (YOLO)
## Layers
- Purpose: Application bootstrap and state orchestration
- Location: `main.py`
- Contains: Global component initialization, hotkey registration, main state machine
- Depends on: All modules
- Used by: OS runtime (`python main.py`)
- Purpose: Centralized constants and coordinate definitions
- Location: `config.py`
- Contains: Thresholds, screen coordinates, timing parameters, feature flags
- Depends on: None
- Used by: All modules
- Purpose: Main automation logic - detect items, verify, sell
- Location: `core/loop.py` (764 lines)
- Contains: `AutoSellLoop` class with `_run_one_cycle_new()` and `_sell_item_with_log()`
- Depends on: vision, control, config, utils.logger
- Used by: `main.py`
- Purpose: Screen capture, template matching, item detection, price OCR
- Location: `vision/capture.py`, `vision/recognizer.py`, `vision/price_reader.py`
- Contains:
- Depends on: mss, cv2, numpy, torch (optional), easyocr (optional)
- Used by: `core/loop.py`
- Purpose: Input simulation (mouse/keyboard)
- Location: `control/mouse.py`, `control/keyboard.py`
- Contains:
- Depends on: pydirectinput, pyperclip (optional)
- Used by: `core/loop.py`
- Purpose: Hotkey management and menu display
- Location: `core/hotkey.py`, `core/menu.py`
- Contains:
- Depends on: keyboard (library)
- Used by: `main.py`
- Purpose: Dual-output logging (file always, console conditional)
- Location: `utils/logger.py`
- Contains: `Logger` class with buffered file writes
- Depends on: config (DEBUG_MODE)
- Used by: All modules via `get_logger()`
## Data Flow
```
```
## Key Abstractions
- Purpose: Multi-template matching with GPU acceleration
- Examples: `vision/recognizer.py` (618 lines)
- Pattern: Lazy-load templates on init, GPU path (PyTorch conv2d) vs CPU path (ThreadPoolExecutor + cv2.matchTemplate)
- Interface: `recognize()`, `recognize_as_raw_detections()`, `load_templates()`
- Purpose: Filter/dedup/sort detected items
- Examples: `vision/item_candidate_pipeline.py` (238 lines)
- Pattern: Fixed 5-stage pipeline (convert → icon_filter → dedup → sort → rank)
- Purpose: YOLO rough detection + template precise recognition
- Examples: `vision/hybrid_pipeline.py` (372 lines)
- Pattern: YOLO → ROI extraction → parallel template match → merge results
- Interface: `process(full_screen, roi_origin_x, roi_origin_y)`
- Purpose: Per-session state tracking
- Examples: `core/loop.py` lines 76-92
- Contains: processed_positions, total_sold, is_running, consecutive_empty, idle_delay, menu_visible
- Purpose: Type-safe data containers for pipeline stages
- Examples: `vision/item_types.py`
## Entry Points
- Location: `main.py`
- Triggers: `python main.py` from command line
- Responsibilities:
- Location: `config.py`
- Triggers: Imported by all modules
- Responsibilities:
## Error Handling
- GPU unavailable → fallback to CPU template matching (`TemplateRecognizer.__init__`)
- OCR initialization fails → `PriceReader` returns empty results
- Template match fails → ESC to dismiss dialog, skip item
- Green button check fails → skip item without selling
- Empty slot detected → skip without selling
- Icon filter failure → continues with all candidates
## Cross-Cutting Concerns
- `USE_FIXED_COORDINATES=True` skips UI template matching
- `USE_CLIPBOARD_INPUT=True` for faster price entry
- `USE_GPU_TEMPLATE_RECOGNITION=False` (CPU mode)
- Thread-local mss instances for screen capture (`ScreenCapture._init_thread_local()`)
- Idle escalation delays through `IDLE_DELAYS` list
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
