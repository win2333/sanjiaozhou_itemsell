# Technology Stack

**Analysis Date:** 2026-03-25

## Languages

**Primary:**
- Python 3.12+ - Main game automation scripting

**Secondary:**
- None significant

## Runtime

**Environment:**
- Windows (Desktop game automation)
- Python 3.12+ (based on `browser-use-test/pyproject.toml` requires-python >=3.12)

**Package Manager:**
- pip (requirements.txt)
- uv (for browser-use-test sub-project)

## Frameworks

**Core Game Automation:**
- Custom game automation framework
- Template matching (OpenCV-based)
- YOLO object detection (optional, via ultralytics)

**Computer Vision:**
- OpenCV 4.8.0+ - Image processing, template matching
- PyTorch (optional) - GPU acceleration for template matching
- Ultralytics YOLO (optional) - Deep learning object detection

**Input Control:**
- pydirectinput - Mouse/keyboard control (primary)
- pyautogui - Input control (fallback)
- keyboard - Global hotkey handling
- pywin32 - Windows API access

**OCR:**
- EasyOCR 1.7.0+ - Local OCR for price recognition (GPU-accelerated)

**Screen Capture:**
- mss 9.0.1+ - Fast cross-platform screen capture

## Key Dependencies

**Critical:**
- `opencv-python>=4.8.0` - Template matching, image processing
- `numpy>=1.24.0` - Numerical operations for image arrays
- `mss>=9.0.1` - Screen capture
- `pydirectinput>=1.0.4` - Mouse/keyboard simulation
- `keyboard>=0.13.5` - Hotkey registration and listening

**Vision/ML (Optional):**
- `torch` - GPU acceleration (auto-detected if CUDA available)
- `ultralytics` - YOLO item detection model
- `easyocr>=1.7.0` - OCR for price reading

**Utilities:**
- `Pillow>=10.0.0` - Image format conversion, Chinese font rendering
- `pyperclip>=1.8.0` - Clipboard operations for price input
- `pywin32>=306` - Windows API bindings

**Browser Automation (Separate sub-project):**
- `browser-use>=0.12.2` - AI-powered browser automation (browser-use-test/)

## Configuration

**Environment:**
- `config.py` - Main configuration file
- Hardcoded game window coordinates (pixel-based)
- Environment-specific paths for templates

**Key configs in `config.py`:**
```python
ITEM_DETECTOR_MODE = "hybrid"  # "template" | "yolo" | "hybrid"
USE_FIXED_COORDINATES = True   # Use fixed coordinates instead of UI recognition
USE_GPU_TEMPLATE_RECOGNITION = False
YOLO_MODEL_PATH = "models/item_detector.pt"
TEMPLATE_MATCH_THRESHOLD = 0.98
```

**Build:**
- `requirements.txt` - Main project dependencies
- `browser-use-test/pyproject.toml` - Browser automation sub-project

## Platform Requirements

**Development:**
- Windows OS (game automation for desktop game)
- Python 3.12+
- Screen resolution awareness (coordinates hardcoded for 1920x1080)

**Production:**
- Windows with game client running
- 1920x1080 or compatible resolution
- Game window must be visible at configured coordinates

---

*Stack analysis: 2026-03-25*
