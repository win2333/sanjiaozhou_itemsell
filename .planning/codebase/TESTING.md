# Testing Patterns

**Analysis Date:** 2026-03-23

## Test Framework

**Primary:** pytest
- Used for most unit tests
- Supports fixtures and parametrize
- Installed via `requirements.txt`

**Secondary:** unittest (built-in)
- Used in `test_recognizer_backend.py`
- TestCase classes with setUp/tearDown

**No coverage tool configured:** No pytest-cov or coverage.py

**Test execution:**
```bash
python py_test/test_recognize.py              # Direct execution
python -m pytest py_test/test_loop_integration.py  # Via pytest
python -m unittest py_test/test_recognizer_backend.py  # Via unittest
```

## Test File Organization

**Location:** `py_test/` directory (at project root level)

**Naming pattern:**
- Unit tests: `test_*.py` (pytest style)
- Integration tests: `test_*_integration.py`
- Test modules: `test_item_candidate_pipeline.py`, `test_loop_integration.py`

**Structure:**
```
py_test/
├── test_recognize.py                  # Manual execution test
├── test_recognizer_backend.py          # unittest.TestCase
├── test_item_candidate_pipeline.py     # pytest class style
├── test_loop_integration.py           # pytest with mocking
├── test_price_method.py               # Manual workflow test
└── test_template_on_game_screenshot.py # Performance test
```

## Test Structure

**pytest Style - Class-based:**
```python
# test_item_candidate_pipeline.py
class TestItemCandidatePipeline:
    def setup_method(self):
        """Setup before each test method"""
        self.pipeline = ItemCandidatePipeline(...)

    def test_coordinate_conversion(self):
        """ROI local coordinates + origin -> screen coordinates"""
        dets = [make_det(10, 20, w=40, h=40)]
        candidates, _, summary = self.pipeline.process(dets, roi_origin_x=100, roi_origin_y=200)

        assert len(candidates) == 1
        assert candidates[0].screen_x == 110  # 10 + 100
```

**pytest Style - Direct functions:**
```python
# test_price_method.py
def test_price_input_flow():
    """Test price input workflow"""
    print("=" * 50)
    print("New price input method test")
    print("=" * 50)
    # Test implementation...
```

**unittest Style:**
```python
# test_recognizer_backend.py
class TestTemplateRecognizerBackend(unittest.TestCase):
    def test_explicit_cpu_mode_disables_gpu_even_when_cuda_available(self):
        fake_torch = SimpleNamespace(...)
        with patch.object(recognizer, 'TORCH_AVAILABLE', True):
            template_recognizer = recognizer.TemplateRecognizer(..., use_gpu=False)
        self.assertFalse(template_recognizer.use_gpu)
```

## Mocking Patterns

**Framework:** `unittest.mock` (built-in)

**MagicMock for dependencies:**
```python
# test_loop_integration.py
from unittest.mock import MagicMock, patch, PropertyMock

def _make_loop(run_mode: str = "observe", detector_mode: str = "template"):
    item_rec = MagicMock()
    item_rec.recognize_as_raw_detections.return_value = []
    ui_rec = MagicMock()
    capture = MagicMock()
    capture.capture_full_screen.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
    mouse = MagicMock()
    keyboard = MagicMock()
    price_reader = MagicMock()

    with patch('core.loop.ITEM_DETECTOR_MODE', detector_mode), \
         patch('core.loop.RUN_MODE', run_mode):
        loop = AutoSellLoop(...)

    return loop, mouse, capture, item_rec
```

**patch.object for methods:**
```python
# test_loop_integration.py
with patch.object(loop._candidate_pipeline, 'process', return_value=([first], [], summary)), \
     patch.object(loop, '_verify_candidate', return_value=True):
    loop._run_one_cycle_new()

mouse.click.assert_not_called()
```

**patch for module-level config:**
```python
# test_loop_integration.py
with patch('core.loop.ITEM_DETECTOR_MODE', 'template'), \
     patch('core.loop.RUN_MODE', 'observe'), \
     patch('core.loop.SAVE_DEBUG_IMAGES', False):
    loop._run_one_cycle_new()
```

## Fixtures and Test Data

**Factory functions:**
```python
# test_item_candidate_pipeline.py
def make_det(x: int, y: int, w: int = 50, h: int = 50, conf: float = 0.9, template_name: str = "测试物品") -> RawItemDetection:
    return RawItemDetection(x=x, y=y, w=w, h=h, confidence=conf, source="template", template_name=template_name)
```

**Test fixtures:**
```python
def setup_method(self):
    """Setup before each test"""
    self.pipeline = ItemCandidatePipeline(
        icon_filter_threshold=0.8,
        dedup_distance_px=20,
    )
```

**Numpy test images:**
```python
# test_item_candidate_pipeline.py
icon_tmpl = np.full((10, 10, 3), 200, dtype=np.uint8)
roi_img = np.zeros((100, 100, 3), dtype=np.uint8)
roi_img[0:10, 0:10] = 200  # Perfect match
```

## Assertion Patterns

**Standard assertions:**
```python
assert len(candidates) == 1
assert c.screen_x == 110
assert c.click_x == 130
```

**Float comparisons:**
```python
# test_item_candidate_pipeline.py
assert candidates[0].confidence == pytest.approx(0.95)
```

**Mock assertions:**
```python
mouse.click.assert_not_called()
mouse.click.assert_called_once_with(x, y)
```

**Exception testing:**
```python
# No explicit pattern found - likely manual testing for exceptions
```

## Test Types

**Unit Tests:**
- Focus on `ItemCandidatePipeline` processing logic
- Test coordinate conversion, icon filtering, deduplication
- Example: `test_item_candidate_pipeline.py`

**Integration Tests:**
- Test `AutoSellLoop` with mocked dependencies
- Test mode switching (observe/live, template/hybrid)
- Example: `test_loop_integration.py`

**Manual/Workflow Tests:**
- Interactive tests requiring game window
- Test price input flow, template recognition on real screenshots
- Example: `test_price_method.py`, `test_template_on_game_screenshot.py`

**Backend Tests:**
- Test hardware detection (GPU/CPU mode selection)
- Example: `test_recognizer_backend.py`

## Test Patterns

**Arrange-Act-Assert (AAA):**
```python
# test_item_candidate_pipeline.py
def test_icon_filter_removes_no_sell(self):
    # Arrange: Create pipeline with icon template
    pipeline = ItemCandidatePipeline(
        icon_filter_threshold=0.9,
        dedup_distance_px=20,
        icon_templates=[icon_tmpl],
    )

    # Act: Process detections
    candidates, eliminated, summary = pipeline.process(
        dets, roi_origin_x=0, roi_origin_y=0, roi_img=roi_img
    )

    # Assert: Verify filtering
    assert summary.filtered_count == 1
    assert len(eliminated) == 1
    assert eliminated[0].reason == "icon_filter"
```

**Setup-Teardown:**
```python
# test_item_candidate_pipeline.py
def setup_method(self):
    self.pipeline = ItemCandidatePipeline(...)

# setup_method runs before each test
# No explicit teardown needed
```

**Path setup:**
```python
# All test files include
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

## Coverage

**No coverage enforcement:**
- No pytest-cov installed
- No coverage target configured
- No CI/CD coverage gates

**Manual coverage:** Debug images saved to `debug/` directory

## Debugging & Diagnostics

**Test output:**
- Print statements for manual verification
- Debug images saved with timestamps
- Example from `test_recognize.py`:
  ```python
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  debug_path = f"debug_item_recognize_{timestamp}.png"
  pil_img.save(debug_path)
  ```

**Performance testing:**
```python
# test_template_on_game_screenshot.py
start = time.time()
results = recognizer.recognize(img)
elapsed = (time.time() - start) * 1000
print(f"Processed in {elapsed:.1f}ms")
```

## Common Testing Patterns

**Empty input handling:**
```python
def test_empty_input_returns_empty_summary(self):
    """Empty input doesn't error, summary final_count==0"""
    candidates, eliminated, summary = self.pipeline.process(
        [], roi_origin_x=0, roi_origin_y=0
    )

    assert len(candidates) == 0
    assert summary.final_count == 0
    assert summary.first_candidate is None
```

**Boundary conditions:**
```python
# test_item_candidate_pipeline.py
def test_sort_order(self):
    """Multiple candidates should be ordered by y asc, same row by x asc"""
    dets = [
        make_det(50, 100),  # rank 2
        make_det(10, 200),  # rank 3
        make_det(10, 50),   # rank 1
    ]
    candidates, _, _ = self.pipeline.process(
        dets, roi_origin_x=0, roi_origin_y=0
    )

    ys = [c.screen_y for c in candidates]
    assert ys == sorted(ys), "Should be ordered by y ascending"
```

**Deduplication logic:**
```python
def test_dedup_keeps_highest_confidence(self):
    """Two nearby boxes, keep highest confidence"""
    dets = [
        make_det(10, 10, conf=0.6),   # Low confidence
        make_det(12, 12, conf=0.95),  # High confidence, close to above
    ]
    candidates, eliminated, summary = self.pipeline.process(...)

    assert len(candidates) == 1
    assert candidates[0].confidence == pytest.approx(0.95)
    assert eliminated[0].reason == "dedup"
```

## Run Commands

**pytest (preferred):**
```bash
pytest py_test/test_item_candidate_pipeline.py
pytest py_test/test_loop_integration.py -v
```

**unittest:**
```bash
python -m unittest py_test/test_recognizer_backend.py
```

**Direct execution:**
```bash
python py_test/test_recognize.py
python py_test/test_price_method.py
```

---

*Testing analysis: 2026-03-23*
