# 混合识别架构实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 YOLO粗识别 + 模板精确识别的混合架构，提升物品识别速度

**Architecture:** YOLO快速全图扫描定位候选区域 → ROI裁剪 → 多线程模板匹配精识别 → 合并去重输出

**Tech Stack:** ultralytics(YOLO), opencv-python, numpy, torch, threading

---

## 任务概览

| 任务 | 文件 | 描述 |
|------|------|------|
| 1 | `vision/yolo_detector.py` | YOLO检测器封装 |
| 2 | `vision/hybrid_pipeline.py` | 混合识别Pipeline |
| 3 | `config.py` | 添加hybrid配置 |
| 4 | `utils/logger.py` | 添加progress日志级别 |
| 5 | `core/loop.py` | 集成HybridPipeline |
| 6 | 测试验证 | 功能测试 |

---

## Task 1: 创建 YoloItemDetector 类

**Files:**
- Create: `vision/yolo_detector.py`
- Test: `py_test/test_yolo_detector.py`

**Step 1: 创建测试文件**

```python
# py_test/test_yolo_detector.py
import numpy as np
import sys
sys.path.insert(0, 'C:/Users/Eureka/Desktop/python_tools/sanjiaozhouGame')

from vision.yolo_detector import YoloItemDetector

def test_yolo_detector_init():
    """测试YOLO检测器初始化"""
    detector = YoloItemDetector()
    assert detector is not None
    assert hasattr(detector, 'detect')

def test_yolo_detector_detect():
    """测试YOLO检测功能"""
    # 创建测试图像 (模拟 screenshot)
    test_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    detector = YoloItemDetector()
    results = detector.detect(test_image)
    
    # 返回类型应该是 List
    assert isinstance(results, list)

if __name__ == '__main__':
    test_yolo_detector_init()
    print("✅ test_yolo_detector_init passed")
    test_yolo_detector_detect()
    print("✅ test_yolo_detector_detect passed")
```

**Step 2: 运行测试验证失败**

```bash
cd C:/Users/Eureka/Desktop/python_tools/sanjiaozhouGame
python py_test/test_yolo_detector.py
```
Expected: `ModuleNotFoundError: No module named 'vision.yolo_detector'`

**Step 3: 创建 YoloItemDetector 实现**

```python
# vision/yolo_detector.py
from typing import List, Tuple, Optional
import numpy as np
from dataclasses import dataclass

try:
    from ultralytics import YOLO
    import torch
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    YOLO = None
    torch = None

@dataclass
class RawDetection:
    """YOLO原始检测结果"""
    x: int  # bbox左上x
    y: int  # bbox左上y
    w: int  # bbox宽度
    h: int  # bbox高度
    class_id: int  # 类别ID
    confidence: float  # 置信度

class YoloItemDetector:
    """YOLO物品检测器"""
    
    def __init__(
        self,
        model_path: str = "models/item_detector.pt",
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.4
    ):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self._model = None
    
    def _load_model(self):
        """延迟加载模型"""
        if self._model is None:
            if not ULTRALYTICS_AVAILABLE:
                raise RuntimeError("ultralytics not installed. Run: pip install ultralytics")
            self._model = YOLO(self.model_path)
            # 尝试移动到GPU如果可用
            if torch.cuda.is_available():
                self._model.to('cuda')
    
    def detect(self, image: np.ndarray) -> List[RawDetection]:
        """
        检测物品
        
        Args:
            image: BGR格式图像 (numpy array)
            
        Returns:
            List[RawDetection]: 检测结果列表
        """
        self._load_model()
        
        # YOLO expects RGB
        rgb_image = image[..., ::-1]  # BGR -> RGB
        
        # 执行推理
        results = self._model(
            rgb_image,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
            device='cuda' if torch.cuda.is_available() else 'cpu'
        )
        
        detections = []
        if results and len(results) > 0:
            result = results[0]
            if result.boxes is not None:
                boxes = result.boxes.cpu().numpy()
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    
                    detections.append(RawDetection(
                        x=int(x1),
                        y=int(y1),
                        w=int(x2 - x1),
                        h=int(y2 - y1),
                        class_id=cls_id,
                        confidence=conf
                    ))
        
        return detections
    
    def detect_as_raw_detections(self, image: np.ndarray) -> List[RawDetection]:
        """兼容旧接口"""
        return self.detect(image)
```

**Step 4: 运行测试验证通过**

```bash
python py_test/test_yolo_detector.py
```
Expected: `✅ test_yolo_detector_init passed` 和 `✅ test_yolo_detector_detect passed`

---

## Task 2: 创建 HybridPipeline 类

**Files:**
- Create: `vision/hybrid_pipeline.py`
- Test: `py_test/test_hybrid_pipeline.py`

**Step 1: 创建测试文件**

```python
# py_test/test_hybrid_pipeline.py
import numpy as np
import sys
sys.path.insert(0, 'C:/Users/Eureka/Desktop/python_tools/sanjiaozhouGame')

from vision.hybrid_pipeline import HybridPipeline
from vision.yolo_detector import YoloItemDetector
from vision.recognizer import TemplateRecognizer

def test_hybrid_pipeline_init():
    """测试HybridPipeline初始化"""
    yolo = YoloItemDetector()
    template = TemplateRecognizer("templates")
    
    pipeline = HybridPipeline(yolo_detector=yolo, template_recognizer=template)
    
    assert pipeline is not None
    assert hasattr(pipeline, 'process')

def test_extract_roi():
    """测试ROI提取功能"""
    # 创建测试图像
    test_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    yolo = YoloItemDetector()
    template = TemplateRecognizer("templates")
    pipeline = HybridPipeline(yolo_detector=yolo, template_recognizer=template)
    
    # 模拟YOLO检测结果
    from vision.yolo_detector import RawDetection
    mock_detections = [
        RawDetection(x=100, y=200, w=50, h=50, class_id=0, confidence=0.9),
        RawDetection(x=300, y=400, w=60, h=60, class_id=1, confidence=0.85),
    ]
    
    # 测试ROI提取
    rois = pipeline._extract_rois(test_image, mock_detections)
    
    assert len(rois) == 2
    assert rois[0].shape[2] == 3  # BGR image

if __name__ == '__main__':
    test_hybrid_pipeline_init()
    print("✅ test_hybrid_pipeline_init passed")
```

**Step 2: 运行测试验证失败**

```bash
python py_test/test_hybrid_pipeline.py
```
Expected: `ModuleNotFoundError: No module named 'vision.hybrid_pipeline'`

**Step 3: 创建 HybridPipeline 实现**

```python
# vision/hybrid_pipeline.py
from typing import List, Optional, Tuple
import numpy as np
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time

from vision.yolo_detector import YoloItemDetector, RawDetection
from vision.recognizer import TemplateRecognizer, MatchResult
from utils.logger import get_logger

logger = get_logger()


@dataclass
class ItemRecord:
    """物品记录"""
    name: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    snapshot: Optional[np.ndarray] = None


class HybridPipeline:
    """
    混合识别Pipeline: YOLO粗识别 + 模板精确识别
    
    工作流程:
    1. YOLO快速扫描全图，定位候选区域
    2. 裁剪ROI小图
    3. 多线程模板匹配精识别
    4. 合并去重，输出ItemRecord列表
    """
    
    def __init__(
        self,
        yolo_detector: YoloItemDetector,
        template_recognizer: TemplateRecognizer,
        max_workers: int = 8
    ):
        self.yolo = yolo_detector
        self.template = template_recognizer
        self.max_workers = max_workers
    
    def process(self, full_screen: np.ndarray) -> List[ItemRecord]:
        """
        处理完整屏幕截图
        
        Args:
            full_screen: BGR格式全屏截图
            
        Returns:
            List[ItemRecord]: 识别到的物品列表
        """
        start_time = time.time()
        
        # Step 1: YOLO粗识别
        logger.scan(f"YOLO扫描中... (0ms)")
        yolo_start = time.time()
        yolo_detections = self.yolo.detect(full_screen)
        yolo_time = (time.time() - yolo_start) * 1000
        
        if not yolo_detections:
            logger.scan(f"YOLO完成: 0个候选区域 ({yolo_time:.0f}ms)")
            return []
        
        logger.scan(f"YOLO完成: {len(yolo_detections)}个候选区域 ({yolo_time:.0f}ms)")
        
        # Step 2: 提取ROI
        roi_start = time.time()
        rois = self._extract_rois(full_screen, yolo_detections)
        roi_time = (time.time() - roi_start) * 1000
        logger.scan(f"ROI提取完成: {len(rois)}个ROI ({roi_time:.0f}ms)")
        
        # Step 3: 多线程模板匹配
        match_start = time.time()
        template_results = self._parallel_template_match(rois, yolo_detections)
        match_time = (time.time() - match_start) * 1000
        logger.scan(f"模板匹配完成: {len(template_results)}个有效物品 ({match_time:.0f}ms)")
        
        total_time = (time.time() - start_time) * 1000
        logger.scan(f"混合识别总耗时: {total_time:.0f}ms")
        
        return template_results
    
    def _extract_rois(
        self,
        image: np.ndarray,
        detections: List[RawDetection]
    ) -> List[Tuple[np.ndarray, RawDetection]]:
        """
        从全图中提取ROI区域
        
        Args:
            image: 全图
            detections: YOLO检测结果
            
        Returns:
            List[(ROI图像, detection元数据)]
        """
        rois = []
        for det in detections:
            x1 = max(0, det.x)
            y1 = max(0, det.y)
            x2 = min(image.shape[1], det.x + det.w)
            y2 = min(image.shape[0], det.y + det.h)
            
            roi = image[y1:y2, x1:x2]
            
            # 边框扩展一些像素用于模板匹配
            padding = 5
            x1_pad = max(0, x1 - padding)
            y1_pad = max(0, y1 - padding)
            x2_pad = min(image.shape[1], x2 + padding)
            y2_pad = min(image.shape[0], y2 + padding)
            
            roi_padded = image[y1_pad:y2_pad, x1_pad:x2_pad]
            
            rois.append((roi_padded, det))
        
        return rois
    
    def _parallel_template_match(
        self,
        rois: List[Tuple[np.ndarray, RawDetection]],
        detections: List[RawDetection]
    ) -> List[ItemRecord]:
        """
        多线程模板匹配
        
        Args:
            rois: ROI图像列表
            detections: 对应的检测元数据
            
        Returns:
            List[ItemRecord]: 匹配成功的物品
        """
        results: List[ItemRecord] = []
        
        if not rois:
            return results
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, (roi, det) in enumerate(rois):
                future = executor.submit(
                    self._match_single_roi,
                    roi, det, i, len(rois)
                )
                futures[future] = (det, i)
            
            for future in as_completed(futures):
                det, idx = futures[future]
                try:
                    item = future.result()
                    if item is not None:
                        results.append(item)
                except Exception as e:
                    logger.warning(f"ROI[{idx}] 匹配失败: {e}")
        
        return results
    
    def _match_single_roi(
        self,
        roi: np.ndarray,
        detection: RawDetection,
        index: int,
        total: int
    ) -> Optional[ItemRecord]:
        """
        单个ROI的模板匹配
        
        Args:
            roi: ROI图像
            detection: YOLO检测元数据
            index: 当前索引
            total: 总数
            
        Returns:
            ItemRecord或None
        """
        logger.progress(f"模板精识别: [{index+1}/{total}] ... (0ms)")
        
        # 在ROI上执行模板匹配
        matches = self.template.recognize(roi, draw_debug=False)
        
        if not matches:
            return None
        
        # 取最高置信度匹配
        best_match = max(matches, key=lambda m: m.confidence)
        
        # 构建ItemRecord，使用ROI内的相对坐标
        item = ItemRecord(
            name=best_match.template_name,
            x=detection.x + best_match.x,  # 转换为全图坐标
            y=detection.y + best_match.y,
            width=best_match.width,
            height=best_match.height,
            confidence=best_match.confidence,
            snapshot=roi
        )
        
        return item
    
    def process_as_raw_detections(self, full_screen: np.ndarray) -> List[ItemRecord]:
        """兼容旧接口"""
        return self.process(full_screen)
```

**Step 4: 运行测试验证通过**

```bash
python py_test/test_hybrid_pipeline.py
```
Expected: `✅ test_hybrid_pipeline_init passed`

---

## Task 3: 修改 config.py 添加 hybrid 配置

**Files:**
- Modify: `config.py`

**Step 1: 添加hybrid模式配置**

在 `config.py` 中找到 `ITEM_DETECTOR_MODE` 配置，添加 `"hybrid"` 选项：

```python
# config.py 添加
ITEM_DETECTOR_MODE = "hybrid"  # "template" | "yolo" | "hybrid"
YOLO_MODEL_PATH = "models/item_detector.pt"
YOLO_CONF_THRESHOLD = 0.5
YOLO_IOU_THRESHOLD = 0.4
HYBRID_MAX_WORKERS = 8  # 模板匹配线程数
```

---

## Task 4: 修改 utils/logger.py 添加 progress 日志级别

**Files:**
- Modify: `utils/logger.py`

**Step 1: 添加 progress 日志级别**

在 `Logger` 类中添加 `progress` 方法：

```python
def progress(self, msg: str):
    """进度日志 - 仅控制台输出，不写文件"""
    self._buffer.append(("progress", msg))
    print(f"[{self._timestamp()}] {msg}")
```

---

## Task 5: 修改 core/loop.py 集成 HybridPipeline

**Files:**
- Modify: `core/loop.py:270-290` (大约位置)

**Step 1: 集成HybridPipeline到主循环**

找到 `_get_detector` 方法，添加 hybrid 模式分支：

```python
def _get_detector(self):
    """获取检测器实例（延迟初始化）"""
    if self._detector is None:
        mode = ITEM_DETECTOR_MODE
        if mode == "template":
            self._detector = self.item_recognizer
        elif mode == "yolo":
            self._detector = YoloItemDetector(
                model_path=YOLO_MODEL_PATH,
                conf_threshold=YOLO_CONF_THRESHOLD,
                iou_threshold=YOLO_IOU_THRESHOLD
            )
        elif mode == "hybrid":
            self._detector = HybridPipeline(
                yolo_detector=YoloItemDetector(
                    model_path=YOLO_MODEL_PATH,
                    conf_threshold=YOLO_CONF_THRESHOLD,
                    iou_threshold=YOLO_IOU_THRESHOLD
                ),
                template_recognizer=self.item_recognizer,
                max_workers=HYBRID_MAX_WORKERS
            )
        else:
            raise ValueError(f"Unknown ITEM_DETECTOR_MODE: {mode}")
    return self._detector
```

**Step 2: 确保导入新类**

在 `core/loop.py` 顶部添加：

```python
from vision.yolo_detector import YoloItemDetector
from vision.hybrid_pipeline import HybridPipeline
```

---

## Task 6: 集成测试验证

**Files:**
- Run: `py_test/test_hybrid_pipeline.py`

**Step 1: 运行完整测试**

```bash
cd C:/Users/Eureka/Desktop/python_tools/sanjiaozhouGame
python py_test/test_hybrid_pipeline.py
```

**Step 2: 手动验证日志输出**

启动程序，观察控制台是否有：
```
[时间] 🔍 YOLO扫描中... (0ms)
[时间] ✅ YOLO完成: X个候选区域 (XXXms)
[时间] 🔎 模板精识别: [1/X] ...
[时间] ✅ 精识别完成: X个有效物品 (XXXms)
```

**Step 3: 验证性能**

对比 hybrid 模式 vs template 模式的单轮识别时间。

---

## 实施检查清单

- [ ] Task 1: YoloItemDetector 创建并测试通过
- [ ] Task 2: HybridPipeline 创建并测试通过
- [ ] Task 3: config.py 更新，包含hybrid配置
- [ ] Task 4: logger.py 更新，包含progress级别
- [ ] Task 5: loop.py 更新，集成hybrid pipeline
- [ ] Task 6: 集成测试通过
- [ ] 控制台实时日志正常输出
- [ ] 性能对比: hybrid vs template

---

**Plan Version:** 1.0  
**Created:** 2026-03-20
