# OCR CPU Fallback Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 OCR 初始化增加 GPU 失败后的 CPU 自动回退，并把兼容依赖固定到当前可用组合。

**Architecture:** `vision/price_reader.py` 负责 OCR 单例初始化和后端状态记录；`main.py` 只消费初始化状态并输出用户可见提示；`requirements.txt` 固定已验证的 `torch/torchvision/numpy` 兼容组合。

**Tech Stack:** Python 3.12, EasyOCR, PyTorch, torchvision, unittest.

---

### Task 1: Add fallback regression tests

**Files:**
- Create: `py_test/test_price_reader_fallback.py`
- Modify: `vision/price_reader.py`

**Step 1: Write the failing test**

写一个测试：模拟 `easyocr.Reader(gpu=True)` 抛异常，而 `easyocr.Reader(gpu=False)` 成功；断言 `get_ocr_reader()` 返回可用 reader，且后端状态为 CPU。

**Step 2: Run test to verify it fails**

Run: `python -m unittest py_test.test_price_reader_fallback -v`
Expected: FAIL because current code does not retry with `gpu=False`.

**Step 3: Write minimal implementation**

在 `vision/price_reader.py` 中增加双阶段初始化和后端状态记录。

**Step 4: Run test to verify it passes**

Run: `python -m unittest py_test.test_price_reader_fallback -v`
Expected: PASS.

### Task 2: Surface backend mode to users

**Files:**
- Modify: `main.py`

**Step 1: Write the failing test**

如无合适现有测试入口，则通过项目级验证脚本替代，检查启动初始化输出能区分 GPU 与 CPU。

**Step 2: Implement minimal output change**

在主程序初始化后输出 `GPU` / `CPU（回退）` 状态。

**Step 3: Verify behavior**

运行初始化脚本，确认状态输出与后端一致。

### Task 3: Pin compatible dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Update versions**

固定当前已验证组合，避免下次安装拿到不兼容的 `torchvision`。

**Step 2: Verify imports**

运行导入检查，确认 `torch` / `torchvision` / `easyocr` / `cv2` 可同时导入。

