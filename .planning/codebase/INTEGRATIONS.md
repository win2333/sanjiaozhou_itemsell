# External Integrations

**Analysis Date:** 2026-03-23

## APIs & External Services

**No External APIs Detected:**
- Standalone desktop automation
- No cloud services
- No third-party web APIs
- No network requests

## Data Storage

**Databases:**
- None - In-memory processing only
- No persistent data storage

**File Storage:**
- Local filesystem only
  - `templates/` - PNG images for template matching
  - `logs/` - Text log files (selling logs)
  - `debug/` - Debug output images
  - `models/` - Optional YOLO model files

**Caching:**
- None - No external cache services

## Input/Output Hardware

**Screen Capture:**
- mss library - Direct screen capture
- No game API integration
- No memory reading

**Input Control:**
- pydirectinput - DirectInput game controller simulation
- pyautogui - Fallback GUI automation
- pywin32 - Windows SendInput API
- keyboard - Global hotkey registration
- No game memory modification

**OCR:**
- EasyOCR - Local text recognition (no cloud API)
  - Languages: Chinese (simplified), English
  - Models: Downloaded on first use

## Authentication & Identity

**Auth Provider:**
- None - No authentication required
- Single-user desktop automation tool

## Monitoring & Observability

**Error Tracking:**
- None - No external error tracking
- Local logging to `logs/` directory

**Logs:**
- Text files: `logs/selling_YYYYMMDD_HHMMSS.txt`
- Custom Logger class in `utils/logger.py`
- Buffered file writing with timestamp prefixes

**Debug Output:**
- Debug images: `debug/debug_*.png`
- Controlled via `config.py` (SAVE_DEBUG_IMAGES flag)

## CI/CD & Deployment

**Hosting:**
- None - Desktop application only
- Manual execution via `main.py` or `run.bat`

**CI Pipeline:**
- None - No automated testing pipeline

## Environment Configuration

**Required env vars:**
- None detected

**Secrets location:**
- No secrets required
- No credential storage

## Webhooks & Callbacks

**Incoming:**
- None - No HTTP endpoints

**Outgoing:**
- None - No network requests

## Optional Model Files

**YOLO Object Detection (experimental):**
- Model file: `models/item_detector.pt`
- Loaded if `ITEM_DETECTOR_MODE = "yolo"` or `"hybrid"`
- Falls back to template matching if unavailable

## Platform-Specific Features

**Windows APIs:**
- pywin32 (SendInput) - Mouse/keyboard simulation
- threading.local - Thread-safe screen capture
- signal.SIGINT - Graceful shutdown handler

**Chinese Font Support:**
- System fonts: Microsoft YaHei, SimHei, FangSong, SimSun
- Used for debug image annotations

---

*Integration audit: 2026-03-23*
