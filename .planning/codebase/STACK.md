# Technology Stack

**Analysis Date:** 2026-03-23

## Languages

**Primary:**
- Python 3.x - Core language for automation scripts

**Secondary:**
- None detected

## Runtime

**Environment:**
- Python 3 (Windows native)
- Platform: Windows 11

**Package Manager:**
- pip (requirements.txt)
- No lockfile present

## Frameworks

**Core:**
- None (standalone Python automation)

**Vision/Image Processing:**
- opencv-python >= 4.8.0 - Template matching, image processing
- mss >= 9.0.1 - Screen capture (cross-platform)
- numpy >= 1.24.0 - Numerical operations
- Pillow >= 10.0.0 - Image format support

**Input Automation:**
- pydirectinput >= 1.0.4 - Direct input simulation (keyboard/mouse)
- pyautogui >= 0.9.53 - High-level GUI automation
- keyboard >= 0.13.5 - Keyboard event handling
- pywin32 >= 306 - Windows API access

**OCR:**
- easyocr >= 1.7.0 - Chinese and English text recognition

**Clipboard:**
- pyperclip >= 1.8.0 - System clipboard operations

**Optional GPU Acceleration:**
- torch (PyTorch) - CUDA-accelerated template matching (optional, auto-detected)

**Configuration:**
- Python native (config.py module)

## Key Dependencies

**Critical:**
- opencv-python - Template matching algorithm (TM_CCOEFF_NORMED)
- mss - Screen capture functionality
- pydirectinput - Game input simulation
- easyocr - Price text recognition

**Infrastructure:**
- numpy - Array operations for image processing
- Pillow - Image format handling
- pywin32 - Windows-specific input control

**Optional:**
- torch - GPU acceleration for template matching

## Configuration

**Environment:**
- No environment variables or .env files detected
- Configuration via `config.py` (Python constants)
- Hardcoded paths and thresholds

**Key Config Files:**
- `config.py` - Main configuration (thresholds, coordinates, modes)

**Build/Dev:**
- No build tools required (pure Python)
- `run.bat` - Windows batch launcher

## Platform Requirements

**Development:**
- Python 3.8+
- Windows 10/11
- Optional: NVIDIA GPU with CUDA for acceleration

**Production:**
- Windows 11 Home (current environment)
- Game window positioned at fixed coordinates (1920x1080 screen assumed)
- Screen resolution: 1920x1080
- Game window region: 1200x0 to 1920x1080

---

*Stack analysis: 2026-03-23*
