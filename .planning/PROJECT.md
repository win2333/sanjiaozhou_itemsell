# 游戏装备自动出售工具

## What This Is

游戏装备自动出售工具，通过屏幕视觉识别（模板匹配 + OCR）自动在游戏背包中检测并出售物品。运行在Windows平台，使用热键（F8）控制开始/暂停。当前代码已完成基础功能，但存在检测不稳定和debug可观测性不足的问题。

## Core Value

**可靠的物品检测** — 每次扫描都能准确识别所有可售物品，不漏识别；同时具备完整的检测过程可观测性，debug模式能看到详细的中间结果。

## Requirements

### Validated

- ✓ 基础框架 — main.py + 热键状态机（idle ↔ running ↔ menu）
- ✓ 屏幕截图 — mss 多线程截图
- ✓ 模板识别 — CPU/GPU 双模式 TemplateRecognizer
- ✓ 混合检测管线 — HybridPipeline（YOLO粗检 + 模板精检）
- ✓ 物品过滤管线 — ItemCandidatePipeline（坐标转换 → 图标过滤 → 去重 → 排序）
- ✓ 价格OCR — EasyOCR 读取价格
- ✓ 输入控制 — pydirectinput 鼠标键盘模拟
- ✓ Debug日志 — Logger 双输出（文件 + 控制台）

### Active

- [ ] 修复模板识别漏识别 — 排查 ItemCandidatePipeline 去重/过滤逻辑
- [ ] 增强 debug 可视性 — 检测过程的中间结果可视化（截图标注、阶段耗时等）

### Out of Scope

- GPU加速模式 — 明确使用 CPU 模式
- 添加YOLO模型训练 — 仅使用现有模型
- 多账号支持 — 单账号使用场景

## Context

**技术栈：** Python 3 + OpenCV + EasyOCR + pydirectinput + mss

**当前架构：**
- `core/loop.py` — AutoSellLoop 主循环，_run_one_cycle_new() + _sell_item_with_log()
- `vision/` — capture.py（截图）、recognizer.py（模板识别）、price_reader.py（OCR）
- `vision/hybrid_pipeline.py` — YOLO粗检 + 模板精检
- `vision/item_candidate_pipeline.py` — 5级过滤管线

**已知问题：**
- 模板识别偶尔漏识别物品（怀疑：去重阈值、图标过滤、或排序逻辑）
- Debug模式输出信息不足，难以定位问题根因
- 现有架构文档较完整（ARCHITECTURE.md 180行）

**用户环境：**
- Windows 系统
- CPU模式（GPU不可用或不希望使用）
- 单显示器游戏窗口

## Constraints

- **性能模式**：CPU-only — 不使用 GPU 加速
- **平台**：Windows — 游戏自动化依赖 pydirectinput/win32
- **游戏分辨率**：固定坐标（BACKPACK_LEFT/TOP/WIDTH/HEIGHT）— 假设游戏窗口位置固定
- **Python版本**：Python 3.x — 依赖 pydirectinput、mss、cv2 等

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CPU模式 | 用户明确不需要GPU加速，现有CPU性能已足够 | ✓ Good |
| 模板识别为主 | 游戏物品图标固定，模板匹配比YOLO更精确 | ✓ Good |
| 固定坐标模式 | 游戏窗口位置固定，固定坐标比模板匹配更快 | ✓ Good |

---

*Last updated: 2026-03-25 after initial requirements gathering*
