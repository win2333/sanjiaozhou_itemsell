# OCR CPU Fallback Design

**Goal:** 当 EasyOCR 的 GPU 初始化失败时，自动回退到 CPU OCR，并向用户明确提示当前已回退到 CPU。

**Context:** 2026-03-16 的最近日志显示 `vision/price_reader.py` 在 `easyocr.Reader(..., gpu=True)` 初始化期间失败，错误为 `operator torchvision::nms does not exist`。模板 GPU 识别仍正常，故本次只修复 OCR 初始化链路。

## Chosen Approach

采用方案 A：在 `vision/price_reader.py` 中优先尝试 `gpu=True`，若失败则记录失败原因并自动重试 `gpu=False`。

## Why This Approach

- 改动最小，直接命中当前故障点
- 不影响 `vision/recognizer.py` 的 GPU 模板匹配路径
- 即使用户本机 CUDA / `torchvision` 环境短暂失配，也能继续使用 OCR

## Behavior

- GPU OCR 初始化成功：记录 `OCR 初始化成功 (GPU)`
- GPU OCR 初始化失败但 CPU 成功：记录 `GPU OCR 初始化失败` 与 `已回退到 CPU OCR`
- GPU/CPU 都失败：保留现有不可用行为，返回 `None`
- 启动提示展示当前 OCR 后端模式，避免用户误以为仍在 GPU 模式

## Files

- Modify: `vision/price_reader.py`
- Modify: `main.py`
- Modify: `requirements.txt`
- Add: `py_test/test_price_reader_fallback.py`

## Testing

- 使用标准库 `unittest` 编写回归测试，模拟：
  - GPU 初始化失败、CPU 初始化成功
  - GPU 初始化成功
  - GPU/CPU 都失败
- 运行单测验证回退逻辑
- 运行项目级初始化脚本确认当前环境下 OCR 可用且能报告正确后端

