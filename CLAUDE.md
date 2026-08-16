# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**三角洲行动装备自动出售工具** — 通过屏幕视觉识别（YOLO 粗识别 + 模板匹配精识别）在游戏背包中自动检测并出售物品。

- 平台：Windows；分辨率：1920×1080（坐标硬编码）
- Python 3.12+
- GSD 工作流：`/gsd:quick` `/gsd:debug` `/gsd:execute-phase`

## 常用命令

```bash
# 运行主程序
python main.py

# 类型检查
python -m mypy main.py config.py core/ vision/ control/ utils/

# 测试工具
python py_test/step_by_step_debug.py      # 逐步调试：截图→YOLO→ROI→模板匹配（推荐）
python py_test/debug_detection_steps.py   # 检测流水线分步调试
python py_test/test_price_method.py       # 价格算法测试
python py_test/debug_coords.py            # 坐标偏移校准
python py_test/find_coords.py             # 鼠标坐标查找
python -m pytest py_test/test_item_candidate_pipeline.py  # Pipeline 单元测试（需 pytest）
python -m pytest py_test/test_loop_integration.py   # 主循环集成测试（需 pytest）
python py_test/test_recognizer_backend.py # GPU/CPU 后端对比测试
```

## 架构

```
main.py — F8热键 → loop.start()
    │
    ├── AutoSellLoop — 主循环（core/loop.py）
    │       │
    │       ├── ScreenCapture (mss 截图, 线程安全)
    │       ├── HybridPipeline — YOLO粗筛 → ROI提取 → 模板精识别 → 合并去重
    │       │       ├── YoloItemDetector (需 models/item_detector.pt)
    │       │       ├── TemplateRecognizer (GPU PyTorch conv2d / CPU ThreadPoolExecutor)
    │       │       └── ItemCandidatePipeline (坐标换算 → 去重 → 排序)
    │       ├── PriceReader (EasyOCR 读价格柱 P1/P2，上架界面动态定价，失败回退固定坐标)
    │       ├── MouseController (pydirectinput 点击/移动)
    │       └── KeyboardController (退格键)
    └── keyboard.add_hotkey("f8") — 全局热键（仅设标志位，主线程处理）
```

**关键数据流（每轮循环）：**
1. `ScreenCapture.capture_region()` 截图背包区域（1200,100 → 1850,1000）
2. HybridPipeline: YOLO 检测 → ROI 裁剪（+10px padding）→ 多线程模板匹配 → 去重排序
3. `_sell_item_with_log()` 4步卖出流程（点击物品 → 设置数量×3 → 设置价格(退格+坐标点击) → 上架确认）
4. `RoundSummary` 本轮统计摘要（各阶段数量 + 第一名 + YOLO 原始框）

**三段数据类型：**
- `RawItemDetection` — 第一段输出，检测器的原始结果（ROI 局部坐标 + 置信度 + 来源）
- `ItemCandidate` — 第二段输出，pipeline 整理后（全屏坐标 + 排序 + 去重，含模板名）
- `RoundSummary` — 每轮统计摘要（各阶段数量 + 第一名 + raw_yolo_detections）

**4步卖出流程：** 点击物品 → 设置数量×3 → 设置价格(OCR 动态定价，失败回退退格+坐标点击) → 点击上架确认 → 结果验证(格子清空或内容变化，最多重试3次)

## 核心目录/文件

| 文件 | 职责 |
|------|------|
| `config.py` | 所有阈值/坐标/模式开关，单一真相来源 |
| `vision/hybrid_pipeline.py` | YOLO + 模板混合识别主逻辑（_ROI_PADDING=10） |
| `vision/item_candidate_pipeline.py` | 候选过滤/去重/排序流水线 |
| `vision/candidate_utils.py` | 去重/排序共享工具函数 |
| `vision/recognizer.py` | 模板匹配引擎（GPU PyTorch conv2d / CPU ThreadPoolExecutor，支持中文文件名） |
| `vision/item_types.py` | 所有 dataclass 类型定义 |
| `vision/capture.py` | mss 截图封装（线程安全，每线程独立 mss 实例） |
| `vision/price_reader.py` | EasyOCR 价格柱识别，延迟初始化单例 |
| `vision/yolo_item_detector.py` | YOLO 推理封装（需 models/item_detector.pt） |
| `core/loop.py` | AutoSellLoop — 主循环 + 卖出流程 + 背包锚点校验 + 控制台置顶 |
| `control/mouse.py` | pydirectinput 鼠标控制 + focus_window() 游戏窗口激活 |
| `control/keyboard.py` | 键盘控制（pydirectinput press） |
| `utils/logger.py` | 双通道日志（文件始终写入，控制台仅 DEBUG_MODE 时输出） |
| `utils/debug_visualizer.py` | 调试标注图生成（3张/轮：原图 → YOLO框 → 候选+淘汰+物品名） |
| `utils/status_panel.py` | 实时状态面板（无边框分组布局，_row() 格式） |

## HybridPipeline（唯一检测模式）

检测流程固定为 **YOLO 粗筛 → ROI 裁剪(+10px padding) → 模板精识别 → 去重排序**。
不再支持纯 `template` 或纯 `yolo` 模式。

空闲延迟阶梯：连续 N 次未识别到物品时递增延迟，`LOOP_DELAY → 0.5 → 1.0 → 3.0 → 5.0 → 10.0 → 15.0` 秒（最后一级常驻）。

## 关键配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TEMPLATE_MATCH_THRESHOLD` | **0.70** | 模板匹配阈值（调低以适应 YOLO 裁剪后的 ROI 小图） |
| `COLOR_MATCH_THRESHOLD` | **0.85** | 九宫格颜色验证阈值 |
| `DEDUP_DISTANCE_PX` | 20 | 空间去重距离（像素） |
| `USE_FIXED_COORDINATES` | `True` | 跳过 UI 识别，用预校准坐标 |
| `USE_GPU_TEMPLATE_RECOGNITION` | `False` | GPU 加速（需 NVIDIA CUDA + torch） |
| `DEBUG_MODE` | `False` | `True`=详细日志到控制台+文件；`False`=仅写文件，控制台只显示摘要 |
| `VERIFY_SELL_RESULT` | `True` | 确认点击后验证格子清空/内容变化+背包UI，失败不计入卖出数 |
| `SELL_VERIFY_WAIT_S` | `0.5` | 每次验证等待秒数（最多重试 3 次） |
| `USE_OCR_PRICE` | `True` | 上架时 OCR 读价格柱动态定价，失败/拆读/异常价回退固定坐标点击 |
| `ROI_SOLID_COLOR_STD` | `4.0` | 纯色 ROI（空格）灰度 std 低于此值直接跳过模板匹配 |
| `PRICE_REGION_LEFT/TOP/RIGHT/BOTTOM` | `400/734/1050/770` | 价格柱 OCR 区域（全屏坐标） |
| `SAVE_DEBUG_IMAGES` | `False` | debug 图片输出开关（生成到 debug/round_NNNN/） |
| `LOOP_DELAY` | 0.1 | 主循环间隔秒数 |
| `HYBRID_MAX_WORKERS` | 8 | Hybrid 模式模板匹配线程数 |

## 命名约定

- 模块/函数/变量：`snake_case`
- 类：`PascalCase`
- 常量：`ALL_CAPS`
- 私有方法：前导 `_` 下划线
- dataclass：`PascalCase`（如 `ItemCandidate`、`RoundSummary`）

## 注意事项

### HybridPipeline 模板匹配要点
- YOLO 检测框 ~59x60px，ROI 加 10px padding（`_ROI_PADDING`）后约 **79x81px**
- 模板匹配跑在**裁剪后的 ROI 小图**上，不是全图。`_match_single_roi()` 对每个 ROI 独立遍历所有模板
- 模板尺寸大于 ROI 会被**跳过**（`if tmpl_h > roi_h or tmpl_w > roi_w: continue`）。955 个模板中约 634 个大于 79x81px
- 阈值 0.70 + 0.85 九宫格颜色验证已通过实测验证
- 中文文件名加载需用 `cv2.imdecode(np.frombuffer(open(path, "rb").read(), ...))`，不能用 `cv2.imread`（不识别中文路径）
- 逐步调试脚本 `py_test/step_by_step_debug.py` 可逐段查看 YOLO→ROI→模板匹配过程，每个 ROI 显示 TOP-5 最佳匹配及分数

### F8 优雅停止机制
- F8 回调运行在 keyboard 库的 hook 线程中，**只设标志位**（`stop_requested=True`），不调 `loop.stop()`
- 主线程在 `_run_one_cycle_new()` 入口检测 `stop_requested`，自然退出
- Logger 只在 `main.py` 的 `finally` 中关闭，避免 hook 线程提前关 logger 导致日志分裂

### 控制台窗口置顶
- `main.py` 启动时调用 `SetWindowPos(HWND_TOPMOST)` 置顶控制台
- `_run_one_cycle_new()` 批处理前调用 `focus_window("三角洲行动")` 激活游戏；激活失败会跳过本轮点击
- `run()` 每轮循环末尾调用 `_keep_console_topmost()` 恢复控制台置顶

### 其他
- 模板文件支持中文文件名，放在 `templates/` 目录（963 个物品模板）
- `vision/recognizer.py` 启动时加载所有模板到内存，按 (h, w) 分组加速匹配
- `_is_empty_slot` 通过 3x3 共 9 像素判断格子 RGB(26,31,34) 是否一致，用于跳过空白格；在卖出流程中被调用两次：点击前判断格内有无物品、确认上架后判断格子是否清空
- `save_debug_frame` 每轮可生成 3 张标注截图（00_original / 01_yolo / 02_pipeline），按 round_NNNN/ 分目录
- `RoundSummary.raw_yolo_detections` 存储 YOLO 原始检测框列表，供调试绘图使用

## 当前 Roadmap

- Phase 1 ✓：Bug Fixes — 修复 CPU 崩溃，阈值统一到 config
- Phase 2 ✓：Debug Visibility — 检测漏斗日志、阶段耗时、标注截图、YOLO原始框
- Phase 3 ✓：Reliability — 卖出结果验证（格子清空/变化）、OCR 动态定价（拆读检测回退）、纯色 ROI 跳过、模板尺寸分组、29 个单元测试
- Phase 4 ○：游戏内实测校准 — OCR 左截断假设验证、验证阈值实测调整（待用户实测数据）


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:7510c1e2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->


<!-- project-agent-tools:start -->
## 本项目 Agent 工具链规则

- 本项目查代码优先使用 Semble 做语义定位。
- 不要先全仓库 grep / glob / Read；先返回最少需要读取的文件列表。
- logs、outputs、ecordings、memory、env、.venv、
ode_modules、dist、uild、__pycache__ 默认不读。
- 任务、依赖和进度用 Beads 管理；本项目的 Beads 数据在 .beads/。
- git、test、pytest、npm、grep、find、diff、日志输出优先用 RTK 压缩；RTK 不会自动压缩内置 Read / Grep / Glob。
- 稳定结论写入全局 llmwiki 对应项目页：$wikiPage。
- llmwiki 不复制大段源码，只记录稳定结论、踩坑、配置和架构决策。
- 修改代码前先说明涉及文件和影响范围。
<!-- project-agent-tools:end -->

## Agent skills

### Issue tracker

Issues are tracked with beads (`bd`): a local Dolt DB synced to the git remote via `bd dolt push`/`bd dolt pull`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles use their default label strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
