# 三州宙物品卖出助手

FPS 游戏自动卖货助手 — 自动识别仓库物品，读取市场价格，计算最优定价，一键上架交易行。

> 使用 Claude Code（Anthropic Claude Sonnet 4 模型）辅助开发

---

## 功能特性

- **自动识别物品**：模板匹配（GPU/CPU 多线程加速）+ 可选 YOLO 检测，957 个物品模板
- **OCR 价格识别**：EasyOCR 读取交易行最低价 P1 和第二低价 P2
- **智能定价算法**：对称减法算法，自动计算最优挂单价
- **MSE 图像验证**：卖出前图像对比验证，防止误操作
- **9 步自动卖出**：Alt+D 打开菜单 → 点击 → 定价 → 确认
- **空闲阶梯延迟**：未识别到物品时渐进增加检测间隔（0.1s → 15s）
- **固定坐标加速**：UI 元素使用预校准坐标，跳过图像识别
- **热键控制**：F8 开始/停止，F9/Ctrl+C 退出
- **双通道日志**：控制台简洁输出 + 文件详细记录
- **卖出统计**：每轮/总计成功卖出数量、跳过数量、耗时

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.10+ |
| 操作系统 | Windows 10/11 |
| GPU | NVIDIA（可选，用于 GPU 加速模板匹配） |
| 游戏分辨率 | 1920×1080（其他分辨率需调整 config.py 坐标） |

---

## 安装

```bash
pip install -r requirements.txt
```

**首次运行 OCR 会自动下载 EasyOCR 模型（约 200MB），需等待完成。**

---

## 快速开始

1. 进入游戏，打开仓库/背包界面
2. 运行 `python main.py`
3. 按 **F8** 开始自动卖货
4. 再次按 **F8** 暂停，显示统计菜单
5. 菜单中按 **F8** 重新开始，**F9** 或 **Ctrl+C** 退出

---

## 操作热键

| 按键 | 功能 |
|------|------|
| F8 | 开始运行 / 暂停显示菜单 |
| F9 | 强制退出 |
| Ctrl+C | 强制退出（SIGINT） |

---

## 项目结构

```
sanjiaozhouGame/
+-- main.py                           # 主入口，状态机初始化
+-- config.py                         # 全局配置（坐标/阈值/模式）
+-- requirements.txt                  # 依赖列表
+-- README.md                          # 本文档
+-- CLAUDE.md                          # AI 开发上下文
|
+-- core/                             # 核心控制模块
|   +-- loop.py                       # 主循环 AutoSellLoop（约710行）
|   |       - start() / stop()        # 启停控制
|   |       - _run_one_cycle_new()    # Hybrid 一轮处理
|   |       - _sell_item_with_log()   # 9步卖出流程
|   |       - _verify_candidate()      # MSE 图像验证
|   |       - _has_green_button()      # 检测绿色上架按钮
|   +-- hotkey.py                     # 热键监听 HotkeyManager
|   +-- menu.py                       # 暂停菜单 SimpleMenu
|
+-- vision/                           # 视觉识别模块
|   +-- capture.py                    # 屏幕截图 ScreenCapture（mss）
|   +-- recognizer.py                 # 模板识别 TemplateRecognizer
|   |       - load_templates()         # 加载模板（支持中文文件名）
|   |       - recognize()              # GPU/多线程批量匹配
|   |       - deduplicate()            # 空间去重（像素距离）
|   |       - deduplicate_by_name()     # 名称去重（同物品保留最高置信度）
|   +-- price_reader.py               # OCR 价格识别 PriceReader
|   |       - read_prices()            # 读取所有价格柱
|   |       - get_p1_p2()              # 获取 P1/P2 最低两价
|   +-- item_types.py                 # 数据类型定义（dataclass）
|   |       - RawItemDetection         # 原始检测结果
|   |       - ItemCandidate            # 整理后候选物品
|   |       - EliminatedCandidate      # 淘汰物品及原因
|   |       - RoundSummary             # 每轮统计摘要
|   +-- item_candidate_pipeline.py    # 候选整理流水线
|   |       1. 坐标换算（ROI → 全屏）
|   |       2. Icon 过滤（不能卖物品）
|   |       3. 去重（贪心算法）
|   |       4. 排序（y升序/同行x升序）
|   |       5. 生成摘要
|   +-- candidate_utils.py            # 候选处理工具函数
|
+-- control/                          # 输入控制模块
|   +-- mouse.py                      # 鼠标 MouseController
|   |       - move_to() / click()      # 移动和点击
|   |       - right_click()            # 右键
|   |       - double_click()           # 双击
|   +-- keyboard.py                   # 键盘 KeyboardController
|           - press() / combo()       # 按键和组合键
|           - alt_d()                  # Alt+D 打开卖出菜单
|           - copy_to_clipboard()      # 剪贴板输入价格
|
+-- utils/                            # 工具模块
|   +-- logger.py                     # 日志 Logger
|   |       - step() / log()           # 步骤/通用日志
|   |       - print_only()             # 仅控制台
|   +-- debug_visualizer.py           # 调试可视化
|           - save_debug_frame()       # 保存标注图像
|
+-- templates/                        # 模板图片目录（957个文件）
|   +-- icon_01.png                   # 不能卖物品的过滤图标
|   +-- [物品名称].png                 # 物品截图模板
|       支持中文文件名，建议四边各留 2px 空白
|
+-- py_test/                          # 测试工具
|   +-- test_screenshot.py            # 截图测试
|   +-- test_recognize.py             # 识别测试
|   +-- test_recognizer_backend.py   # GPU/CPU 后端测试
|   +-- test_template_on_game_screenshot.py  # 模板游戏截图测试
|   +-- test_item_candidate_pipeline.py      # Pipeline 测试
|   +-- test_loop_integration.py      # 主循环集成测试
|   +-- test_price_method.py          # 价格方法测试
|   +-- debug_markers.py              # UI 坐标标记
|   +-- debug_coords.py               # 坐标调试
|   +-- crop_templates.py             # 模板裁剪工具
|   +-- find_coords.py                # 坐标查找工具
|
+-- models/                           # YOLO 模型目录
+-- datasets/                         # YOLO 数据集
+-- backgrounds/                      # 背景图片
+-- debug/                            # 调试输出图片
+-- logs/                             # 日志文件
|       selling_YYYYMMDD_HHMMSS.txt
```

---

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│                      main.py                        │
│            状态机: idle → running → menu            │
└────────────────────────┬────────────────────────────┘
                         │
         ┌───────────────┼───────────────────┐
         ▼               ▼                   ▼
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │HotkeyManager│  │AutoSellLoop │  │ SimpleMenu  │
  └─────────────┘  └──────┬──────┘  └─────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │ScreenCapture│  │TemplateRecog│  │ PriceReader │
  └─────────────┘  └──────┬──────┘  └─────────────┘
                           │                 │
          ┌────────────────┘                 │
          ▼                                  ▼
  ┌─────────────┐                    ┌─────────────┐
  │ ItemCandidate│                   │ EasyOCR     │
  │  Pipeline    │                   │ (GPU/CPU)   │
  └──────┬──────┘                    └─────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────┐
  │        _sell_item_with_log() — 9步流程       │
  │   MouseController + KeyboardController       │
  └─────────────────────────────────────────────┘
```

---

## 卖出流程（9步）

```
1. 鼠标移动到物品坐标 (x, y)
2. Alt+D 打开卖出菜单
3. 点击上架按钮 upload1（固定坐标）
4. 点击确认按钮 upload2（固定坐标）
5. 点击数量按钮 3 次（全数量）
6. 点击价格输入框
7. 退格键清除原价格
8. 粘贴计算后的售价
9. 点击 upload2 确认卖出
```

---

## 价格算法：对称减法

```
目标：在交易行图表上选择一个价格，使得自己的物品排在最低价左侧，
      买家按默认排序时会优先看到更贵的物品，从而更容易卖出。

计算逻辑：
  步长 = P2 - P1          （图表上一格代表多少钱）
  分界线 = P1 - 步长       （低于这个价格会显示在左侧空白区间）
  安全下沉 = 分界线 - 10
  最终价格 = 取整到10的倍数

异常情况（P2 <= P1 或只有一个价格柱）：
  回退到 P1 × 0.95
```

---

## 配置参数

修改 `config.py` 中的以下参数：

### 物品识别

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TEMPLATE_MATCH_THRESHOLD` | 0.98 | 物品模板匹配阈值，越高越严格 |
| `UI_TEMPLATE_THRESHOLD` | 0.75 | UI 元素匹配阈值 |
| `DEDUP_DISTANCE` | 30 | 像素级空间去重距离 |
| `ITEM_DETECTOR_MODE` | `"hybrid"` | 检测模式：`template` / `yolo` / `hybrid` |
| `HYBRID_MAX_WORKERS` | 8 | 模板匹配线程数 |
| `ICON_FILTER_THRESHOLD` | 0.8 | Icon 过滤图标匹配阈值 |

### 运行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEBUG_MODE` | `True` | True=控制台详细日志，False=仅简洁输出 |
| `LOOP_DELAY` | 0.1 | 主循环基础间隔（秒） |
| `IDLE_DELAYS` | [0.1, 0.5, 1.0, 3.0, 5.0, 10.0, 15.0] | 空闲延迟阶梯 |
| `RUN_MODE` | `"live"` | `live`=实际卖出，`observe`=仅观察不操作 |

### 性能优化

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `USE_FIXED_COORDINATES` | `True` | 使用预校准坐标，跳过 UI 识别 |
| `USE_CLIPBOARD_INPUT` | `True` | 使用剪贴板输入价格 |
| `USE_GPU_TEMPLATE_RECOGNITION` | `False` | 启用 GPU 加速（需 NVIDIA GPU） |
| `USE_NEW_PRICE_METHOD` | `True` | 退格+直接点击输入价格 |

### 固定坐标（1920×1080）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `BACKPACK_LEFT` / `BACKPACK_TOP` | 1200 / 0 | 背包截图区域左上角 |
| `BACKPACK_WIDTH` / `BACKPACK_HEIGHT` | 720 / 1080 | 背包截图区域宽高 |
| `UPLOAD1_X` / `UPLOAD1_Y` | 1403 / 700 | 上架按钮坐标 |
| `UPLOAD2_X` / `UPLOAD2_Y` | 1311 / 749 | 确认按钮坐标 |
| `PRICE_OFFSET_X` / `PRICE_OFFSET_Y` | 1 / -104 | 价格输入框相对偏移 |
| `QUANTITY_OFFSET_X` / `QUANTITY_OFFSET_Y` | 139 / -189 | 数量按钮相对偏移 |

---

## 添加新物品模板

1. 在游戏中截取物品图标（四边各留 2px 空白效果最佳）
2. 保存为 PNG 格式，放入 `templates/` 目录
3. 文件名即为物品名称（如 `AKM强化战术枪托.png`）
4. 支持中文文件名
5. 可选：放入子目录分类管理（如 `templates/枪械/`）
6. 重新运行程序自动加载

> 模板数量越多，识别覆盖率越高。建议优先添加价值高、出现频率高的物品模板。

---

## 调试与排查

### 开启调试模式
```python
DEBUG_MODE = True  # config.py
SAVE_DEBUG_IMAGES = True  # config.py
```
调试图片输出到 `debug/` 目录：
- **蓝色框**：原始检测结果
- **红色框**：被过滤/淘汰的候选
- **绿色框**：最终候选物品
- **黄色框**：当前卖出目标（第一名）

### 测试工具

```bash
# 截图测试
python py_test/test_screenshot.py

# 模板识别测试
python py_test/test_recognize.py

# GPU/CPU 后端性能测试
python py_test/test_recognizer_backend.py

# 候选 Pipeline 流程测试
python py_test/test_item_candidate_pipeline.py

# 价格算法测试
python py_test/test_price_method.py
```

### 常见问题

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 识别不到物品 | 游戏窗口位置变化 | 调整 `config.py` 中的 `BACKPACK_*` 坐标 |
| 点击位置偏移 | 分辨率不是 1920×1080 | 重新校准所有坐标参数 |
| OCR 读取失败 | 字体颜色浅/截图区域不对 | 检查 `PRICE_*` 坐标偏移是否正确 |
| 物品卖出失败 | 绿色按钮检测不到 | 降低 `UI_TEMPLATE_THRESHOLD` 或开启 `USE_FIXED_COORDINATES` |
| GPU 加速报错 | 未安装 CUDA/PyTorch | 关闭 `USE_GPU_TEMPLATE_RECOGNITION`，使用 CPU 模式 |

---

## 依赖说明

```
mss>=9.0.1              # 高性能屏幕截图（比 Pillow 快）
opencv-python>=4.8.0   # 图像处理和模板匹配
pydirectinput>=1.0.4   # 鼠标键盘控制
keyboard>=0.13.5        # 热键监听
numpy>=1.24.0          # 数值计算
Pillow>=10.0.0         # 图像处理
easyocr>=1.7.0         # OCR 文字识别
pyperclip>=1.8.0       # 剪贴板操作
pyautogui>=0.9.53      # GUI 自动化（备选）
pywin32>=306           # Windows API
torch>=2.0.0           # GPU 加速（可选，安装后自动启用 CUDA）
```

---

## 工作流程图

```
启动 main.py
    │
    ▼
初始化组件（一次性）
  - 加载 957 个物品模板
  - 加载 UI 模板（绿色按钮等）
  - 初始化 OCR 引擎
  - 注册热键（F8/F9）
    │
    ▼
等待 F8 按下
    │
    ▼ ── F8 按下 ──► 启动后台线程
                         │
                         ▼
                    主循环 running
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    ▼                    ▼                    ▼
截图背包区域        候选整理Pipeline      空闲阶梯延迟
（BACKPACK_*）      → 过滤 → 去重 → 排序    ↑
    │                    │                    │
    ▼                    ▼                    │
模板识别              候选列表         未识别到物品
(GPU/多线程)          │                   │
    │                  ▼                   │
    ▼            遍历每个候选                │
空间+名称去重         │                    │
    │          ┌─────┴─────┐                │
    ▼          │           │                │
候选列表         ▼           ▼                │
            MSE验证    MSE验证失败           │
              │         → 跳过               │
              ▼                            │
          9步卖出流程                        │
            │                              │
            ▼                              │
       成功计数 ◄────────────────────────────┘
            │
            ▼
       再次 F8 ──► 显示菜单（统计/重启/退出）
```
