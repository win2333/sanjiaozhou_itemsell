# External Integrations

**Analysis Date:** 2026-03-25

## Computer Vision & OCR

**Local OCR (Self-hosted):**
- EasyOCR 1.7.0+ - Price recognition from game screenshots
  - Implementation: `vision/price_reader.py`
  - GPU mode: Enabled by default (`gpu=True`)
  - Languages: Chinese (ch_sim), English

**YOLO Object Detection (Local):**
- Ultralytics YOLO - Item detection using trained model
  - Implementation: `vision/yolo_item_detector.py`
  - Model: `models/item_detector.pt`
  - Optional - only used when `ITEM_DETECTOR_MODE="yolo"` or `"hybrid"`

## Browser Automation

**Framework:**
- browser-use 0.12.2+ - AI-powered browser automation
  - Location: `browser-use-test/` sub-directory
  - Project: `pyproject.toml`
  - Purpose: Automating web browsing tasks (Bilibili interaction)

**AI Integration:**
- Anthropic Claude API - Powering browser automation agent
  - Implementation: `browser-use-test/bilibili_favorites.py`
  - Model: claude-sonnet-4-5
  - API Key: Uses environment variable / local proxy
  - Base URL: `http://127.0.0.1:5000` (local proxy)

**Browser:**
- Google Chrome - Browser automation target
  - User data directory: `C:\Users\Eureka\AppData\Local\Google\Chrome\User Data`
  - Profile: `Profile 3`
  - Uses existing Chrome profile for authentication

## Input Control APIs

**Mouse/Keyboard:**
- pydirectinput - Direct input simulation (game-compatible)
- pyautogui - General input control (fallback)
- keyboard - Global hotkey registration

**Windows API:**
- pywin32 - Cursor position, Windows-specific features
  - Used in `control/mouse.py` for `GetCursorPos()`

## Clipboard

**Price Input:**
- pyperclip - Clipboard operations
  - Used when `USE_CLIPBOARD_INPUT = True` in config

## No External Services

**Main Game Automation Project:**
- No cloud APIs
- No external databases
- No authentication services
- All processing is local

**Data Storage:**
- Local file system only
- Template images: `templates/` directory
- Debug output: `debug/` directory
- Logs: `logs/` directory
- YOLO model: `models/item_detector.pt`

## Web Access

**Proxy Configuration:**
- Local proxy for AI API calls: `http://127.0.0.1:5000`
  - Used in `browser-use-test/bilibili_favorites.py`

**Cookies:**
- Browser cookies imported from Chrome profile for web authentication

---

*Integration audit: 2026-03-25*
