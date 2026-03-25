# 混合识别架构设计文档

**日期**: 2026-03-20  
**项目**: 三角洲游戏自动化 - 物品识别重构  
**目标**: YOLO粗识别 + 模板精确识别混合架构，提升识别速度

---

## 1. 架构概览

```
ScreenCapture
       │
       ▼
┌──────────────────┐
│  YOLO Detector    │  ← 粗识别，全图扫描，快速定位候选区域
│  (models/item_    │     输出: [(x,y,w,h,class_id,conf), ...]
│   detector.pt)   │
└────────┬─────────┘
         │ 候选区域列表
         ▼
┌──────────────────┐
│  ROI 提取器       │  ← 按bbox裁剪小图，送给下游精识别
│  (小区域)         │     输入: (x,y,w,h)  输出: ROI图像
└────────┬─────────┘
         │ ROI列表
         ▼
┌──────────────────┐
│  TemplateMatch    │  ← 精识别，模板匹配，精确到具体物品
│  (322物品+UI模板) │     对每个ROI匹配所有模板
└────────┬─────────┘
         │ 精确结果
         ▼
   ItemRecord 列表
```

---

## 2. 组件设计

### 2.1 YoloItemDetector (新增)

**文件**: `vision/yolo_detector.py`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model_path` | str | `models/item_detector.pt` | YOLO模型路径 |
| `conf_threshold` | float | 0.5 | 置信度阈值 |
| `iou_threshold` | float | 0.4 | NMS IOU阈值 |

**接口**:
```python
class YoloItemDetector:
    def detect(self, image: np.ndarray) -> List[RawDetection]:
        """
        RawDetection = (x, y, w, h, class_id, confidence)
        返回: List[RawDetection]
        """
```

### 2.2 HybridPipeline (核心编排器)

**文件**: `vision/hybrid_pipeline.py`

```python
class HybridPipeline:
    def __init__(self, yolo_detector, template_recognizer):
        self.yolo = yolo_detector
        self.template = template_recognizer
    
    def process(self, full_screen: np.ndarray) -> List[ItemRecord]:
        """
        1. YOLO粗识别
        2. ROI提取
        3. 模板精识别 (并行)
        4. 合并去重
        5. 返回ItemRecord列表
        """
```

### 2.3 可插拔架构

```python
ITEM_DETECTOR_MODE:
├── "template"  → 纯模板识别 (现有逻辑，保持不变)
├── "yolo"      → 纯YOLO识别 (预留，后续开发)
└── "hybrid"    → YOLO粗筛 + 模板精识 (本次重构目标)
```

---

## 3. 日志/进度输出设计

### 3.1 分层日志级别

| 级别 | 输出位置 | 场景 |
|------|----------|------|
| `system` | 控制台 + 文件 | 程序启停、异常、统计 |
| `scan` | 控制台 + 文件 | YOLO识别进度 |
| `match` | 控制台 + 文件 | 模板匹配进度 |
| `sell` | 控制台 + 文件 | 卖出操作结果 |
| `progress` | 仅控制台 | 实时进度条/百分比 |

### 3.2 控制台输出示例

```
[14:23:01] 🔍 YOLO扫描中... (0ms)
[14:23:01] ✅ YOLO完成: 12个候选区域 (156ms)
[14:23:01] 🔎 模板精识别: [1/12] 物品A... (0ms)
[14:23:02] 🔎 模板精识别: [3/12] 物品C... (456ms)
[14:23:02] ✅ 精识别完成: 8个有效物品 (1234ms)
[14:23:03] 📦 卖出物品A @ (1200,450)...
[14:23:05] ✅ 卖出成功: 14190金 (P1=15000)
[14:23:10] 📊 本轮: 5个卖出, 累计: 42个, 耗时: 9.2s
```

### 3.3 日志文件

| 文件 | 内容 |
|------|------|
| `logs/YYYY-MM-DD.log` | 完整日志 (含时间戳) |
| `logs/error.log` | 仅错误和异常 |

---

## 4. 数据流设计

```
full_screen (1920x1080)
       │
       ▼
┌─────────────────┐
│  YOLO detect()  │  ← 原始检测
└────────┬────────┘
         │ List[RawDetection]
         ▼
┌─────────────────┐
│  NMS + Filter   │  ← 按置信度过滤 + 非极大值抑制
└────────┬────────┘
         │ List[FilteredDetection]
         ▼
┌─────────────────┐
│  extract_ROIs() │  ← 裁剪小图
└────────┬────────┘
         │ List[ROI]
         ▼
┌─────────────────┐
│  parallel match │  ← 多线程模板匹配
│  (per ROI)      │
└────────┬────────┘
         │ List[TemplateMatchResult]
         ▼
┌─────────────────┐
│  merge + dedup  │  ← YOLO去重 + 模板去重
└────────┬────────┘
         │ List[ItemRecord]
         ▼
     卖给主循环
```

---

## 5. 关键设计决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| **并行策略** | 多线程并行处理ROI模板匹配 | 充分利用CPU，IO-bound |
| **YOLO降级** | YOLO失败时日志警告，不影响继续 | 部分场景YOLO可能不工作 |
| **模板降级** | 模板匹配失败时跳过该ROI | 单个物品失败不影响整体 |
| **显存优化** | YOLO batch_size=1 | 避免显存溢出 |

---

## 6. 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| **新增** | `vision/yolo_detector.py` | YOLO检测器封装 |
| **新增** | `vision/hybrid_pipeline.py` | 混合识别Pipeline |
| **改造** | `vision/recognizer.py` | 添加YOLO模式支持 |
| **改造** | `core/loop.py` | 集成HybridPipeline |
| **改造** | `config.py` | 添加 `ITEM_DETECTOR_MODE = "hybrid"` |
| **改造** | `utils/logger.py` | 添加progress级别日志 |

---

## 7. 测试验证计划

| 测试 | 方法 | 合格标准 |
|------|------|----------|
| YOLO检测 | 截图测试 | 输出候选区域数量合理 |
| ROI提取 | 可视化ROI图 | 裁剪区域正确 |
| 混合识别 | 实际运行 | 10秒内完成一轮 |
| 日志输出 | 观察控制台 | 每阶段有输出 |
| 模式切换 | 切回template模式 | 功能正常 |

---

## 8. 依赖项

```txt
ultralytics  # YOLO框架
torch        # GPU加速 (可选)
numpy
opencv-python
```

---

**文档版本**: v1.0  
**确认状态**: ✅ 用户已确认
