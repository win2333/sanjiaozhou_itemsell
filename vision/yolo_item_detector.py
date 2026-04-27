"""YOLO 物品检测器"""

import cv2
from pathlib import Path
from typing import List

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from vision.item_types import RawItemDetection


class YoloItemDetector:
    """YOLO 物品检测器

    Attributes:
        confidence_threshold: 置信度阈值
        iou_threshold: NMS IOU 阈值
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
    ):
        """初始化

        Args:
            model_path: YOLO 模型路径 (.pt)
            confidence_threshold: 置信度阈值 (0-1)
            iou_threshold: NMS IOU 阈值
        """
        if YOLO is None:
            raise ImportError("ultralytics 未安装，请运行: pip install ultralytics")
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"YOLO 模型不存在: {model_file}")

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self._model = YOLO(str(model_file))

    def detect(self, image) -> List[RawItemDetection]:
        """检测物品

        Args:
            image: BGR 格式图像

        Returns:
            RawItemDetection 列表
        """
        # 转换 BGRA -> BGR
        work_img = image
        if len(image.shape) == 3 and image.shape[2] == 4:
            work_img = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        results = self._model(
            work_img,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )

        detections = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                detections.append(
                    RawItemDetection(
                        x=int(x1),
                        y=int(y1),
                        w=int(x2 - x1),
                        h=int(y2 - y1),
                        confidence=conf,
                        source="yolo",
                    )
                )
        return detections
