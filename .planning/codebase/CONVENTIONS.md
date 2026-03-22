# Coding Conventions

**Analysis Date:** 2026-03-23

## Language & Type System

**Language:** Python 3

**Type Hints:**
- Used throughout codebase for function parameters and return types
- Pattern: `from typing import Optional, List, Dict, Tuple`
- Example in `config.py`:
  ```python
  def calculate_price(p1: int, p2: Optional[int] = None) -> int:
  ```

## Naming Conventions

**Files:**
- Python modules: snake_case (e.g., `recognizer.py`, `item_candidate_pipeline.py`)
- Test files: `test_*.py` pattern in `py_test/` directory

**Classes:**
- PascalCase: `TemplateRecognizer`, `AutoSellLoop`, `ScreenCapture`, `MouseController`
- Example in `vision/recognizer.py`:
  ```python
  class TemplateRecognizer:
      """Template recognizer (supports GPU acceleration)"""
  ```

**Functions/Methods:**
- snake_case: `recognize()`, `load_templates()`, `_run_one_cycle_new()`
- Private methods: Leading underscore `_random_delay()`, `_verify_candidate()`
- Example in `control/mouse.py`:
  ```python
  def _random_delay(self) -> None:
      """Random delay, anti-detection"""
  ```

**Constants:**
- UPPER_SNAKE_CASE: `TEMPLATE_MATCH_THRESHOLD`, `DEBUG_MODE`, `HYBRID_MAX_WORKERS`
- Example in `config.py`:
  ```python
  TEMPLATE_MATCH_THRESHOLD = 0.98
  DEBUG_MODE = False
  ```

**Variables:**
- snake_case: `item_recognizer`, `ui_recognizer`, `raw_detections`
- Example in `core/loop.py`:
  ```python
  candidates, eliminated, summary = self._candidate_pipeline.process(...)
  ```

## Code Style

**Formatting:**
- No automated formatting tools configured (no Black, autopep8, etc.)
- Manual formatting with 4-space indentation
- Chinese comments used for documentation

**Linting:**
- No linting tools configured (no flake8, pylint, mypy)
- No pre-commit hooks
- Python path manipulation via `sys.path.insert(0, ...)` in test files

**Documentation:**
- Chinese comments in module docstrings
- Google-style docstrings with Args/Returns sections
- Example in `vision/capture.py`:
  ```python
  def capture_region(self, left: int, top: int, width: int, height: int) -> np.ndarray:
      """Capture specified region

      Args:
          left: Left x coordinate
          top: Top y coordinate
          width: Region width
          height: Region height

      Returns:
          Image in numpy.ndarray format
      """
  ```

## Import Organization

**Order:**
1. Standard library imports
2. Third-party imports (mss, cv2, numpy, etc.)
3. Local project imports

**Pattern:**
```python
# Standard library
import time
import random
from pathlib import Path
from typing import List, Optional, Set, Dict, Tuple
from dataclasses import dataclass

# Third-party
import cv2
import numpy as np
import mss

# Local project
from vision.capture import ScreenCapture
from utils.logger import get_logger
from config import TEMPLATE_MATCH_THRESHOLD
```

**Path manipulation in tests:**
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

## Error Handling

**Approach:** Silent failures with optional logging

**Patterns observed:**
- Exception catching with logging
- Example in `vision/recognizer.py`:
  ```python
  try:
      icon_img = cv2.imread(icon_path, cv2.IMREAD_COLOR)
      if icon_img is not None:
          icon_templates.append(icon_img)
      else:
          get_logger().log_only("[初始化]", f"Cannot read icon template: {icon_path}")
  except Exception as e:
      get_logger().log_only("[初始化]", f"Failed to load icon template: {e}")
  ```

**No explicit exception types:** Often catches generic `Exception` without specific handling

## Logging

**Framework:** Custom `Logger` class in `utils/logger.py`

**Key methods:**
- `log(prefix, message)`: General logging
- `step(message)`: Step-by-step logging with microsecond timestamps
- `log_only(prefix, message)`: File-only logging
- `print_only(message)`: Console output only
- `system()`, `recognize()`, `verify()`, `operation()`: Domain-specific convenience methods

**Pattern:**
```python
logger = get_logger()
logger.log_only("[操作]", f"Preparing to process: {candidate.template_name}")
logger.print_only(f"Currently selling: {candidate.template_name}")
```

## Class Design

**Dataclasses:**
- Used for data containers with `@dataclass` decorator
- Example in `vision/recognizer.py`:
  ```python
  @dataclass
  class MatchResult:
      template_name: str
      x: int
      y: int
      width: int
      height: int
      confidence: float
      center_x: int
      center_y: int
  ```

**Singleton pattern:**
- Global logger instance via `get_logger()`
- Example in `utils/logger.py`:
  ```python
  _logger: Optional[Logger] = None

  def get_logger() -> Logger:
      global _logger
      if _logger is None:
          _logger = Logger()
      return _logger
  ```

## Module Design

**Single Responsibility:**
- `vision/recognizer.py`: Template matching logic
- `vision/capture.py`: Screen capture
- `vision/price_reader.py`: OCR price reading
- `control/mouse.py`: Mouse automation
- `control/keyboard.py`: Keyboard automation
- `core/loop.py`: Main automation loop

**Composition:**
- Components composed in main.py:
  ```python
  _loop = AutoSellLoop(
      item_recognizer=item_recognizer,
      ui_recognizer=ui_recognizer,
      capture=ScreenCapture(),
      mouse=MouseController(),
      keyboard=KeyboardController(),
      price_reader=price_reader,
  )
  ```

## Configuration

**Centralized config:**
- All constants in `config.py` as module-level variables
- Example:
  ```python
  TEMPLATE_MATCH_THRESHOLD = 0.98
  USE_FIXED_COORDINATES = True
  BACKPACK_LEFT = 1200
  ```

**No environment variables:** Direct constant usage
**No config files:** All settings in Python module

## Threading & Concurrency

**Pattern:** Threading via `threading.Thread` with daemon threads
- Example in `main.py`:
  ```python
  thread = threading.Thread(target=_run_loop, args=(loop, lambda: state == 'running'), daemon=True)
  thread.start()
  ```

**Thread-local storage:**
- Used in `vision/capture.py` for mss instances:
  ```python
  self._local = threading.local()

  def _get_sct(self):
      if not hasattr(self._local, 'sct') or self._local.sct is None:
          self._local.sct = mss.mss()
      return self._local.sct
  ```

## Code Complexity

**Large files:**
- `core/loop.py`: 740 lines - Main loop logic
- `vision/recognizer.py`: 614 lines - Template matching with GPU/CPU paths
- `vision/item_candidate_pipeline.py`: (seen in imports, likely complex)

**Functions should be split** - Long functions in loop.py could benefit from extraction

---

*Convention analysis: 2026-03-23*
