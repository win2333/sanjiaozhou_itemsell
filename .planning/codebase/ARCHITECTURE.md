# Architecture

**Analysis Date:** 2026-03-23

## Pattern Overview

**Overall:** Hybrid Detection Pipeline Architecture

**Key Characteristics:**
- **Detection Pipeline Pattern**: Multi-stage detection with Template/YOLO backend selection
- **Coordinator Pattern**: `AutoSellLoop` orchestrates vision, control, and state
- **Lazy Initialization**: Heavy components (YOLO detector) initialized on first use
- **Configurable Backends**: Three detection modes: "template", "yolo", "hybrid"
- **Fixed Coordinates Mode**: Optional optimization bypassing UI template recognition

## Layers

**Application Layer:**
- Purpose: Entry point and state machine management
- Location: `main.py`
- Contains: Component initialization, hotkey registration, state transitions (idle/running/menu)
- Depends on: All other layers
- Used by: Runtime (F8/F9 hotkeys)

**Core Control Layer:**
- Purpose: Main loop orchestration and state management
- Location: `core/loop.py`
- Contains: `AutoSellLoop`, `SellState`, `ItemRecord` dataclasses
- Depends on: Vision (detection), Control (input), Utils (logging)
- Used by: `main.py`

**Vision Layer:**
- Purpose: Screen capture, template/YOLO detection, item candidate processing
- Location: `vision/`
- Contains:
  - `capture.py`: ScreenCapture (thread-safe mss wrapper)
  - `recognizer.py`: TemplateRecognizer (CPU/GPU template matching)
  - `yolo_item_detector.py`: YoloItemDetector (YOLO inference)
  - `hybrid_pipeline.py`: HybridPipeline (YOLO + template combination)
  - `item_candidate_pipeline.py`: ItemCandidatePipeline (filter/dedup/sort)
  - `item_types.py`: RawItemDetection, ItemCandidate, EliminatedCandidate, RoundSummary
  - `candidate_utils.py`: Deduplication and sorting utilities
- Depends on: numpy, opencv-python, torch (optional), mss
- Used by: `core/loop.py`

**Control Layer:**
- Purpose: Low-level input simulation (mouse/keyboard)
- Location: `control/`
- Contains:
  - `mouse.py`: MouseController (pydirectinput wrapper)
  - `keyboard.py`: KeyboardController (pydirectinput + pyperclip)
- Depends on: pydirectinput, pyperclip
- Used by: `core/loop.py`

**Utility Layer:**
- Purpose: Logging and debugging visualization
- Location: `utils/`
- Contains:
  - `logger.py`: Logger (file + console with DEBUG_MODE toggle)
  - `debug_visualizer.py`: Debug frame visualization
- Depends on: Standard library
- Used by: All layers

## Data Flow

**Detection Flow (Per Round):**

1. **Screenshot**: `ScreenCapture.capture_region()` captures backpack area (1200,0 to 1920,1080)
2. **Detection**: Selected detector processes image:
   - Template mode: `TemplateRecognizer.recognize_as_raw_detections()`
   - YOLO mode: `YoloItemDetector.detect()`
   - Hybrid mode: `HybridPipeline.process()` (YOLO coarse + template fine)
3. **Candidate Pipeline**:
   - Coordinate conversion (ROI local → screen absolute)
   - Icon filter (exclude unsellable items)
   - Deduplication (center distance < threshold)
   - Sorting (y-ascending, x-ascending)
   - Summary generation (RoundSummary with counts)
4. **Verification**: MSE comparison against snapshot (anti-duplicate)
5. **Sell Operation**: Mouse move → Alt+D → Upload1 → Upload2 → Price input → Quantity
6. **Logging**: Stats update and file output

**State Flow:**

```
idle → (F8/auto) → running → (F8) → menu → (restart) → running
                 → (exit) → terminated
```

## Key Abstractions

**TemplateRecognizer:**
- Purpose: Generic template matching engine (CPU/GPU)
- Examples: `vision/recognizer.py`
- Pattern: Strategy pattern with CPU/GPU implementations
- Interface: `recognize()`, `recognize_as_raw_detections()`, `load_templates()`

**ItemCandidate:**
- Purpose: Processed detection result with business metadata
- Location: `vision/item_types.py`
- Contains: Screen coordinates, click point, confidence, rank, filter status

**RoundSummary:**
- Purpose: Per-cycle statistics container
- Location: `vision/item_types.py`
- Contains: raw_count, filtered_count, dedup_count, final_count, first_candidate

**HybridPipeline:**
- Purpose: Combine YOLO speed + template accuracy
- Location: `vision/hybrid_pipeline.py`
- Interface: `process(full_screen, roi_origin_x, roi_origin_y) -> (candidates, eliminated, summary)`

**ItemCandidatePipeline:**
- Purpose: Filter/dedup/sort raw detections
- Location: `vision/item_candidate_pipeline.py`
- Interface: `process(raw_detections, roi_origin_x, roi_origin_y, roi_img) -> (candidates, eliminated, summary)`

## Entry Points

**main.py:**
- Location: `main.py`
- Triggers: Python interpreter execution (`python main.py`)
- Responsibilities:
  - Component initialization (once)
  - Hotkey registration (F8: start/stop, F9: exit)
  - State machine loop (idle → running → menu)
  - Thread management for AutoSellLoop

**AutoSellLoop.start():**
- Location: `core/loop.py:163`
- Triggers: `main.py` state transitions
- Responsibilities:
  - Run one detection + sell cycle
  - Return "continue", "restart", "exit"

## Error Handling

**Strategy:** Graceful degradation with fallback modes

**Patterns:**
- **YOLO unavailable**: Falls back to template-only mode
- **GPU unavailable**: Falls back to CPU template matching
- **Icon filter failure**: Skips filter, continues with all candidates
- **Green button detection**: Falls back to fixed coordinates if green not found
- **Empty slot detection**: Skips selling, logs warning
- **Verification failure**: Skips candidate, records to prevent retries

## Cross-Cutting Concerns

**Logging:** `utils/logger.py`
- Approach: Dual-output (file + conditional console)
- Format: `[timestamp] [prefix] message`
- Modes: DEBUG_MODE controls console visibility
- Buffers: 2-second flush interval to prevent I/O bottleneck

**Validation:** Per-candidate verification
- Approach: MSE image comparison against snapshot
- Threshold: 500 (tunable via VERIFY_MSE_THRESHOLD)
- Purpose: Prevent duplicate sells of same item

**Authentication:** Not applicable (game automation, not web app)

---

*Architecture analysis: 2026-03-23*
