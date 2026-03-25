# Testing Patterns

**Analysis Date:** 2026-03-25

## Test Framework

**Test Runner:**
- `pytest` - Primary test framework for unit/integration tests
- `unittest` - Standard library, used alongside pytest

**Test Files Location:** `py_test/` directory

**Run Commands:**
```bash
python -m pytest py_test/                    # Run all tests
python -m pytest py_test/test_loop_integration.py  # Run specific file
python py_test/test_recognize.py            # Run standalone test script
```

## Test File Organization

**Location:** All test files in `py_test/` directory (flat structure, not mirrored)

**Naming:**
- Unit tests: `test_*.py` prefix
- Integration tests: `test_*_integration.py`
- Debug/util scripts: `debug_*.py`, `crop_*.py`, `find_*.py`

**Example files:**
- `test_recognize.py` - Template recognition verification
- `test_screenshot.py` - Screen capture verification
- `test_recognizer_backend.py` - Backend selection unit test
- `test_loop_integration.py` - AutoSellLoop integration tests
- `test_item_candidate_pipeline.py` - Pipeline unit tests
- `test_price_method.py` - Price input flow test
- `test_template_on_game_screenshot.py` - End-to-end template matching test

## Test Structure

**Pattern: Standalone test scripts (most common)**
```python
"""物品识别测试 - 支持中文标签显示，自动执行"""

import sys
sys.path.insert(0, '.')  # Enable imports from project root

# ... imports ...

def main():
    print("=" * 50)
    print("      物品识别测试 v2.0")
    print("=" * 50)
    # Test logic...

if __name__ == "__main__":
    main()
```

**Pattern: pytest class-based tests**
```python
class TestItemCandidatePipeline:
    def setup_method(self):
        self.pipeline = ItemCandidatePipeline(...)

    def test_coordinate_conversion(self):
        """ROI 局部坐标 + origin → 全屏坐标"""
        dets = [make_det(10, 20, w=40, h=40)]
        candidates, _, summary = self.pipeline.process(dets, roi_origin_x=100, roi_origin_y=200)
        assert len(candidates) == 1
        # ... assertions ...
```

**Pattern: unittest class-based tests**
```python
class TestTemplateRecognizerBackend(unittest.TestCase):
    def test_explicit_cpu_mode_disables_gpu_even_when_cuda_available(self):
        # ... test logic ...
        self.assertFalse(template_recognizer.use_gpu)
```

## Mocking

**Framework:** `unittest.mock` (MagicMock, patch, PropertyMock)

**Patterns:**
```python
from unittest.mock import MagicMock, patch

# Mock dependencies
item_rec = MagicMock()
item_rec.recognize_as_raw_detections.return_value = []

# Patch config values
with patch('core.loop.ITEM_DETECTOR_MODE', 'template'), \
     patch('core.loop.RUN_MODE', 'observe'), \
     patch('core.loop.SAVE_DEBUG_IMAGES', False):
    loop = AutoSellLoop(...)

# Mock pipeline return
with patch.object(loop._candidate_pipeline, 'process', return_value=([first], [], summary)):
    loop._run_one_cycle_new()

# Mock method return value
with patch.object(loop, '_verify_candidate', return_value=True):
    loop._run_one_cycle_new()
```

**What to Mock:**
- External dependencies: `capture`, `mouse`, `keyboard`, `price_reader`
- Config values: `ITEM_DETECTOR_MODE`, `RUN_MODE`, `SAVE_DEBUG_IMAGES`
- Methods that interact with game: `_verify_candidate`, `_has_gold_button`

## Fixtures and Factories

**Factory helper pattern:**
```python
def make_det(x: int, y: int, w: int = 50, h: int = 50, 
             conf: float = 0.9, template_name: str = "测试物品") -> RawItemDetection:
    return RawItemDetection(x=x, y=y, w=w, h=h, confidence=conf, 
                           source="template", template_name=template_name)
```

**Test image fixtures:**
- Uses `np.zeros((1080, 1920, 3), dtype=np.uint8)` for mock screenshots
- Reads actual screenshots from `debug/000[1-9].png` in integration tests

## Debug Utilities

**`py_test/debug_markers.py`:**
- Captures screenshot and marks UI element positions
- User presses Enter to capture, elements defined in code
- Outputs marked image to `debug/debug_markers.png`

**`py_test/debug_coords.py`:**
- Interactive coordinate finder
- Captures screenshot, recognizes UI templates
- User clicks to select point, calculates offset from template center

**`py_test/find_coords.py`:**
- Real-time mouse position display
- Simple `pyautogui.position()` polling loop
- Used to find correct coordinates for UI elements

**`py_test/crop_templates.py`:**
- Batch crops template images (2px border removal)
- Supports Chinese filenames via custom `imread`/`imwrite`

## Test Categories

**Unit Tests:**
- `test_recognizer_backend.py` - Backend selection logic
- `test_item_candidate_pipeline.py` - Pipeline processing logic
- Tests individual classes/methods in isolation with mocks

**Integration Tests:**
- `test_loop_integration.py` - AutoSellLoop with mocked dependencies
- `test_template_on_game_screenshot.py` - Real template matching on actual screenshots
- Tests component interactions

**End-to-End/Manual Tests:**
- `test_recognize.py` - Full recognition flow with screenshot + display
- `test_screenshot.py` - Screen capture verification
- `test_price_method.py` - Manual testing of price input flow
- Require manual verification or game running

## Common Patterns

**Async/Threading Tests:**
```python
# Using threading for non-blocking hotkey listener
thread = threading.Thread(target=_run_loop, args=(loop, lambda: state == 'running'), daemon=True)
thread.start()
```

**Image Comparison:**
```python
def compare_images_mse(img1: np.ndarray, img2: np.ndarray) -> float:
    """计算两张图片的 MSE（均方误差）"""
    if img1.shape != img2.shape:
        h = min(img1.shape[0], img2.shape[0])
        w = min(img1.shape[1], img2.shape[1])
        img1 = cv2.resize(img1, (w, h))
        img2 = cv2.resize(img2, (w, h))
    return np.mean((img1.astype(float) - img2.astype(float)) ** 2)
```

**Image loading for Chinese paths:**
```python
def imread(path):
    """支持中文路径的图片读取"""
    with open(path, 'rb') as f:
        data = np.frombuffer(f.read(), np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)
```

## Test Configuration

**Config used in tests:**
- `TEMPLATE_MATCH_THRESHOLD` - Recognition threshold
- `TEMPLATES_DIR` - Template image directory
- `DEBUG_DIR` - Debug output directory
- `UI_TEMPLATES_DIR`, `UI_TEMPLATE_THRESHOLD` - UI element recognition

**Mocked config values in integration tests:**
- `ITEM_DETECTOR_MODE` - "template" | "yolo" | "hybrid"
- `RUN_MODE` - "observe" | "live"
- `SAVE_DEBUG_IMAGES` - Debug image output flag

## CI/Testing Automation

**No CI detected** - No `.github/workflows/`, `Jenkinsfile`, or similar CI configuration found.

**Test execution:** Manual via `python -m pytest` or direct script execution.

---

*Testing analysis: 2026-03-25*
