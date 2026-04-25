# 三角洲行动物品自动出售工具

通过屏幕视觉识别（YOLO 粗识别 + 模板匹配精识别 + OCR 价格读取）在游戏仓库中自动检测并出售物品。

---

## 功能特性

- **混合检测**：YOLO 快速定位候选 → ROI 裁剪 → 多线程模板配准，兼顾速度和精度
- **OCR 价格识别**：EasyOCR 读取交易行最低价 P1 和第二低价 P2
- **智能定价算法**：对称减法算法，自动计算最优挂单价
- **MSE 图像验证**：卖出前图像对比验证，防止误操作
- **4 步自动卖出**：点击物品 → 设置数量(×3) → 设置价格(退格+点击) → 上架确认
- **空闲阶梯延迟**：未识别到物品时渐进增加检测间隔（0.1s → 15s）
- **固定坐标加速**：UI 元素使用预校准坐标，跳过图像识别
- **F8 优雅停止**：按 F8 后当前物品卖完才退出，不中断进行中的操作
- **状态面板**：控制台实时显示状态、进度、识别结果、最近事件
- **双通道日志**：文件详细记录 + 控制台简洁状态面板

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.12+ |
| 操作系统 | Windows 10/11 |
| GPU | 可选（用于 GPU 加速模板匹配） |
| 游戏分辨率 | 1920×1080（其他分辨率需调整 config.py 坐标） |

---

## 安装

```bash
pip install -r requirements.txt
```

首次运行 OCR 会自动下载 EasyOCR 模型（约 200MB），需等待完成。

---

## 快速开始

1. 进入游戏，打开仓库/背包界面
2. 双击 `run.bat`（自动提权管理员），或 `python main.py`
3. 3 秒倒计时后自动开始识别并出售
4. 按 **F8** 优雅停止（当前物品卖完退出）

---

## 操作方式

| 操作 | 说明 |
|------|------|
| 直接运行 | `python main.py` 或双击 `run.bat` |
| 停止 | F8 — 当前物品卖完后退出 |
| 强制退出 | Ctrl+C |

---

---

## 项目结构

```
sanjiaozhouGame/
├── main.py                       # 主入口
├── config.py                     # 全局配置（坐标/阈值/模式）
├── run.bat                       # 启动脚本（自动提权）
├── requirements.txt              # 依赖
│
├── core/                         # 核心控制
│   └── loop.py                   # 主循环 + 卖出流程 + MSE 验证 + 控制台置顶
│
├── vision/                       # 视觉识别
│   ├── hybrid_pipeline.py        # YOLO+模板混合识别（_ROI_PADDING=10）
│   ├── yolo_item_detector.py     # YOLO 推理封装
│   ├── recognizer.py             # 模板匹配引擎（GPU/CPU 双路径，中文文件名）
│   ├── item_candidate_pipeline.py# 候选过滤/去重/排序流水线
│   ├── candidate_utils.py        # 去重排序工具函数
│   ├── item_types.py             # 数据类型定义
│   ├── capture.py                # 屏幕截图（mss）
│   └── price_reader.py           # OCR 价格识别（EasyOCR）
│
├── control/                      # 输入控制
│   ├── mouse.py                  # 鼠标 + focus_window() 游戏激活
│   └── keyboard.py               # 键盘控制
│
├── utils/                        # 工具模块
│   ├── logger.py                 # 双通道日志
│   ├── status_panel.py           # 实时状态面板
│   └── debug_visualizer.py       # 调试标注图
│
├── py_test/                      # 测试工具
│   ├── step_by_step_debug.py     # 逐步调试（推荐：截图→YOLO→ROI→模板匹配）
│   ├── test_item_candidate_pipeline.py  # Pipeline 单元测试
│   ├── test_loop_integration.py         # 主循环集成测试
│   ├── test_recognizer_backend.py       # GPU/CPU 后端测试
│   ├── test_price_method.py             # 价格输入测试
│   ├── debug_detection_steps.py         # 检测流水线调试
│   ├── debug_coords.py                  # 坐标偏移校准
│   ├── debug_markers.py                 # UI 坐标标记
│   └── find_coords.py                   # 鼠标坐标查找
│
├── templates/                    # 963 个物品模板 PNG
└── models/
    └── item_detector.pt          # YOLO 模型
```

---

## 关键配置

修改 `config.py` 中的参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TEMPLATE_MATCH_THRESHOLD` | **0.70** | 模板匹配阈值 |
| `COLOR_MATCH_THRESHOLD` | **0.85** | 九宫格颜色验证阈值 |
| `DEDUP_DISTANCE_PX` | 20 | 空间去重距离 |
| `DEBUG_MODE` | `False` | 控制台详细日志 |
| `SAVE_DEBUG_IMAGES` | `False` | 保存每轮调试截图 |
| `USE_GPU_TEMPLATE_RECOGNITION` | `False` | GPU 加速（需 CUDA） |
| `USE_FIXED_COORDINATES` | `True` | 预校准坐标 |
| `HYBRID_MAX_WORKERS` | 8 | 模板匹配线程数 |

坐标参数（1920×1080）：

| 参数 | 值 |
|------|-----|
| 背包区域 | (1200,100) → (1850,1000) |
| 上架按钮 (upload1) | (1403, 700) |
| 确认按钮 (upload2) | (1311, 749) |
| 价格框偏移 | (+1, -104) |
| 数量按钮偏移 | (+139, -189) |

---

## 价格算法：对称减法

```
步长 = P2 - P1           （图表上一格代表多少钱）
分界线 = P1 - 步长        （低于此价显示在左侧空白区）
安全下沉 = 分界线 - 10
最终价格 = 取整到10的倍数

异常（仅有 P1）：回退到 P1 × 0.95
```

---

## 调试

```bash
# 逐步调试（推荐）：截图→YOLO→ROI→模板匹配，每步输出TOP-5
python py_test/step_by_step_debug.py

# Pipeline 单元测试（需 pip install pytest）
python -m pytest py_test/test_item_candidate_pipeline.py

# 主循环集成测试（需 pip install pytest）
python -m pytest py_test/test_loop_integration.py

# 其他
python py_test/debug_detection_steps.py    # 检测流程分步调试
python py_test/test_price_method.py        # 价格输入测试
python py_test/debug_coords.py             # 坐标偏移校准
python py_test/find_coords.py              # 鼠标坐标查找
```

### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 识别不到物品 | 游戏窗口位置变化 | 调整 `BACKPACK_*` 坐标 |
| 点击偏移 | 非 1920×1080 分辨率 | 重新校准坐标 |
| OCR 失败 | 价格区域截图不对 | 检查 `PRICE_OFFSET_*` |
| 模板匹配失败（0匹配） | ROI 太小/阈值过高 | 用 `step_by_step_debug.py` 排查，看 TOP-5 分数 |
| GPU 报错 | 未安装 CUDA | 关闭 `USE_GPU_TEMPLATE_RECOGNITION` |

---

## 依赖

```
mss>=9.0.1
opencv-python>=4.8.0
pydirectinput>=1.0.4
keyboard>=0.13.5
numpy>=1.24.0
Pillow>=10.0.0
easyocr>=1.7.0
pywin32>=306
torch>=2.0.0          # 可选（GPU 加速）
```
