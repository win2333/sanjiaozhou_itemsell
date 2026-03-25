# YOLO Item Detection Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current item template matching pipeline with a single-class YOLO detector that finds sellable item boxes quickly, while keeping the existing UI recognition, price OCR, and sell flow unchanged.

**Architecture:** Introduce a new item-detection backend that outputs item boxes in the same shape expected by `core/loop.py`, and keep the rest of the app stable. Use synthetic training data built from real inventory/background screenshots plus existing template assets, then add a post-detection icon filter that excludes non-sellable items by matching a fixed small icon in the lower-left corner of each detected crop.

**Tech Stack:** Python 3.12, Ultralytics YOLO, OpenCV, NumPy, MSS, existing project control/loop modules, optional PyTorch GPU inference.

---

## Scope And Decisions

- Replace only **item recognition**.
- Keep **UI recognition** in `vision/recognizer.py` for `templates/ui` unchanged.
- Keep **price OCR** in `vision/price_reader.py` unchanged.
- Use **single-class detection** (`item`) instead of hundreds of fine-grained item classes.
- Use a **fixed icon template filter** to reject non-sellable items after YOLO detection.
- Prefer **real background synthetic data** over black-background-only synthetic data.
- Treat horizontal/vertical variants and multi-slot items as the same detection target type.
- Run YOLO only on the **right-side item region**, not on the full screen.
- Use about **10 pixels of crop padding** so the lower-left icon remains inside the icon-filter crop.
- If YOLO model loading fails, **stop startup with a clear error** instead of silently falling back.

## Success Criteria

- Item detection is meaningfully faster than the current template matching pass on the target machine.
- Detected boxes are stable enough for the existing mouse click flow.
- Non-sellable items with the fixed lower-left icon are filtered out reliably.
- Existing UI detection and OCR behavior remain unchanged.
- The system can be toggled between template matching and YOLO during rollout.

## Risks To Manage

- YOLO may detect boxes well but produce unstable centers for thin or long attachments.
- Synthetic-only data may underperform on real screenshots if layout statistics are unrealistic.
- The fixed icon filter may fail if the crop margins are too tight or if confidence thresholds are wrong.
- Replacing name-based deduplication with spatial deduplication may change sell order behavior.

## Files Expected To Change

- Create: `vision/yolo_item_detector.py`
- Create: `vision/icon_filter.py`
- Create: `tools/generate_yolo_dataset.py`
- Create: `tools/train_yolo_item_detector.py`
- Create: `py_test/test_icon_filter.py`
- Create: `py_test/test_yolo_item_detector_adapter.py`
- Create: `docs/plans/2026-03-17-yolo-item-detection.md`
- Modify: `main.py`
- Modify: `core/loop.py`
- Modify: `config.py`
- Modify: `requirements.txt`
- Modify: `README.md`

---

### Task 1: Freeze the integration target and performance baseline

**Files:**
- Modify: `core/loop.py`
- Modify: `vision/recognizer.py`
- Create: `py_test/test_yolo_item_detector_adapter.py`

**Step 1: Document the current result contract**

Write down the fields from `vision/recognizer.py` and `core/loop.py` that the new detector must preserve:
- `x`
- `y`
- `width`
- `height`
- `center_x`
- `center_y`
- `confidence`
- a placeholder name such as `item`

**Step 2: Add a regression test for loop compatibility**

Write a test that feeds fake detection results into the current `AutoSellLoop` item-processing path and verifies the loop only depends on box geometry and confidence, not on a real template class name.

Run: `python -m unittest py_test.test_yolo_item_detector_adapter -v`

Expected: FAIL if the loop still assumes template-name semantics.

**Step 3: Make minimal loop adjustments**

Update `core/loop.py` so the item-processing path accepts generic item detections and does not require `deduplicate_by_name()` for YOLO mode.

**Step 4: Re-run the compatibility test**

Run: `python -m unittest py_test.test_yolo_item_detector_adapter -v`

Expected: PASS.

**Step 5: Record a timing baseline**

Run the current template path once on the target machine and note:
- full-screen capture time
- item recognition time
- deduplication time
- total cycle time

Save the measured numbers in the implementation notes before replacing the backend.

---

### Task 2: Add configuration and backend switch for item detection

**Files:**
- Modify: `config.py`
- Modify: `main.py`
- Modify: `README.md`

**Step 1: Add explicit detector-mode config**

Add config values for:
- `ITEM_DETECTOR_MODE = "template" | "yolo"`
- `YOLO_MODEL_PATH`
- `YOLO_CONFIDENCE_THRESHOLD`
- `YOLO_IOU_THRESHOLD`
- `YOLO_IMAGE_SIZE`
- `ICON_FILTER_ENABLED`
- `ICON_TEMPLATE_PATH`
- `ICON_MATCH_THRESHOLD`
- `ICON_FILTER_PADDING = 10`

**Step 2: Update startup wiring**

Modify `main.py` so only the item recognizer backend changes. UI recognizer creation remains on the existing template recognizer path.

**Step 3: Expose the active mode at startup**

Print a clear startup line such as:
- `Item detector backend: TEMPLATE`
- `Item detector backend: YOLO`

**Step 4: Update README usage notes**

Document the new detector switch and the fact that YOLO replaces only item recognition.

---

### Task 3: Build the synthetic YOLO dataset generator

**Files:**
- Create: `tools/generate_yolo_dataset.py`
- Modify: `config.py`
- Modify: `README.md`

**Step 1: Define generator inputs and outputs**

Generator inputs:
- item templates from `templates/` excluding `templates/ui/`
- clean real background images from a dedicated folder such as `dataset/backgrounds/`

Generator outputs:
- `dataset/yolo_item/images/train/`
- `dataset/yolo_item/images/val/`
- `dataset/yolo_item/labels/train/`
- `dataset/yolo_item/labels/val/`
- `dataset/yolo_item/data.yaml`

**Step 2: Define placement rules**

Implement generation rules that match the real game scene:
- use real clean backgrounds, not black-only backgrounds
- place items only in realistic right-side inventory/list regions
- allow different object sizes naturally from the source PNG sizes
- avoid unrealistic heavy overlap
- allow light adjacency similar to the live UI
- keep all labels as class `0: item`

**Step 3: Add light augmentation only**

Allow only small, realistic variation:
- light scale jitter if the live capture can vary slightly
- light blur or sharpen if needed
- optional mild noise

Do not add strong rotation, color jitter, or arbitrary perspective warps unless later evidence proves they help.

**Step 4: Add manifest logging**

For every generated sample, log:
- background file used
- templates placed
- boxes generated
- split assignment

This makes debugging generator mistakes possible.

**Step 5: Smoke-test the generator**

Run: `python tools/generate_yolo_dataset.py --count 50`

Expected:
- images and label files are created
- every image has a matching label file
- bounding boxes align visually with objects

---

### Task 4: Validate the fixed icon filter in isolation

**Files:**
- Create: `vision/icon_filter.py`
- Create: `py_test/test_icon_filter.py`

**Step 1: Write the failing tests**

Add tests that cover:
- icon present in lower-left crop -> returns blocked
- icon absent -> returns sellable
- crop too small -> returns safe fallback without crashing

Run: `python -m unittest py_test.test_icon_filter -v`

Expected: FAIL because the filter module does not exist yet.

**Step 2: Implement minimal icon filter**

Implement a helper that:
- accepts the original screenshot and one detection box
- extracts the lower-left region using configurable padding (default about 10 pixels)
- runs a single small template match against the fixed icon
- returns `True/False` for blocked state and the match score

**Step 3: Re-run the icon tests**

Run: `python -m unittest py_test.test_icon_filter -v`

Expected: PASS.

**Step 4: Save debug crops for threshold tuning**

Add an optional debug mode that writes the inspected lower-left crop and match score to a debug folder.

---

### Task 5: Add the YOLO detector adapter

**Files:**
- Create: `vision/yolo_item_detector.py`
- Create: `py_test/test_yolo_item_detector_adapter.py`
- Modify: `requirements.txt`

**Step 1: Write the failing adapter test**

Add a test that mocks the Ultralytics model output and verifies the adapter returns loop-compatible results with:
- pixel coordinates in the current screen coordinate system
- center points
- width and height
- confidence
- placeholder name `item`

Run: `python -m unittest py_test.test_yolo_item_detector_adapter -v`

Expected: FAIL because the adapter module does not exist yet.

**Step 2: Implement the adapter**

Implement a detector wrapper that:
- loads one YOLO model once
- runs inference only on the configured right-side item region
- converts model outputs into the existing result shape expected by `core/loop.py`
- applies confidence thresholding and spatial deduplication/NMS if needed

**Step 3: Re-run the adapter test**

Run: `python -m unittest py_test.test_yolo_item_detector_adapter -v`

Expected: PASS.

**Step 4: Pin the new dependency**

Add the minimum required package versions for the YOLO inference stack in `requirements.txt` and verify the project still imports correctly.

---

### Task 6: Integrate YOLO plus icon filter into the sell loop

**Files:**
- Modify: `core/loop.py`
- Modify: `main.py`
- Modify: `config.py`

**Step 1: Replace name-based post-processing in YOLO mode**

When `ITEM_DETECTOR_MODE == "yolo"`:
- skip `deduplicate_by_name()`
- keep spatial deduplication only
- sort detections in a stable order suitable for clicking

**Step 2: Insert the icon filter before selling**

Before `_verify_item()` or immediately after detection normalization, filter out detections whose lower-left icon match indicates non-sellable items.

**Step 3: Preserve current verification behavior**

Keep `_verify_item()` as a second safety check so the loop still confirms the object is present before acting.

**Step 4: Add structured logging**

Log at least:
- YOLO inference time
- number of raw detections
- number of detections rejected by icon filter
- number of final sell candidates

**Step 5: Run the loop-level tests**

Run the targeted unit tests for loop integration and icon filtering.

Expected: PASS.

---

### Task 7: Train and evaluate the first detector

**Files:**
- Create: `tools/train_yolo_item_detector.py`
- Modify: `README.md`

**Step 1: Add a reproducible training command**

Document and script a training command that points to `dataset/yolo_item/data.yaml` and writes outputs to a predictable run directory.

Suggested command shape:

```bash
python tools/train_yolo_item_detector.py --data dataset/yolo_item/data.yaml --imgsz 960 --epochs 50
```

**Step 2: Define the first evaluation gate**

Evaluate on a small real-image validation set and record:
- box recall
- obvious false positives
- icon-filter failure cases
- average inference latency on the target machine

**Step 3: Compare against template baseline**

Use the same scene samples to compare:
- detection latency
- number of usable candidates
- number of incorrect clicks avoided by icon filter

**Step 4: Pick a provisional deployment model**

Select the best weights file and copy or link it to the configured `YOLO_MODEL_PATH`.

---

### Task 8: Add rollout safety and fallback behavior

**Files:**
- Modify: `main.py`
- Modify: `config.py`
- Modify: `README.md`

**Step 1: Keep template fallback available**

If YOLO model load fails or inference throws, either:
- fail fast with a clear message, or
- optionally fall back to template mode if configured

Chosen behavior: fail fast with a clear startup error. Do not auto-fallback.

**Step 2: Add a safe debugging mode**

Add a dry-run or debug-only detection mode that logs detections and icon filtering results without clicking, so thresholds can be tuned safely.

**Step 3: Document the rollback path**

Explain how to switch back to template mode immediately via `config.py`.

---

### Task 9: Verify on the real workflow before claiming completion

**Files:**
- Modify: `README.md`

**Step 1: Run targeted automated tests**

Run:
- `python -m unittest py_test.test_icon_filter -v`
- `python -m unittest py_test.test_yolo_item_detector_adapter -v`

Expected: PASS.

**Step 2: Run a non-click real-screen dry run**

Execute the detector in debug mode on the live game screen and verify:
- item boxes align with visible items
- non-sellable icon items are filtered out
- no obvious missed detections appear in common cases

**Step 3: Run a limited live sell session**

Test with a small controlled inventory and confirm:
- correct click centers
- no blocked items sold
- stable throughput

**Step 4: Update final docs**

Document:
- how to generate the dataset
- how to train the model
- how to switch detector mode
- how to tune icon filter thresholds

---

## Recommended Rollout Order

1. Stabilize loop contract for generic detections.
2. Build generator and icon filter.
3. Add YOLO adapter behind a config switch.
4. Train a first model from synthetic data.
5. Validate on real screenshots without clicks.
6. Run limited live selling.
7. Keep template mode available until YOLO proves stable.

## Open Questions To Resolve During Execution

- Is a small real-image validation set enough, or will a second pass of synthetic generation be needed?

## Out Of Scope For This Plan

- Replacing UI template recognition with YOLO
- Replacing price OCR with YOLO or another model
- Fine-grained item class prediction
- Multi-model pipelines for per-item classification after detection
