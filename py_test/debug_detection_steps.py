"""逐步调试：截图保存 → YOLO 标注 → 候选列表标注"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import cv2
import numpy as np
from pathlib import Path

DEBUG_DIR = Path(__file__).parent.parent / "debug"
DEBUG_DIR.mkdir(exist_ok=True)

from config import (
    BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT,
    YOLO_MODEL_PATH, YOLO_CONFIDENCE_THRESHOLD, YOLO_IOU_THRESHOLD,
)
from vision.capture import ScreenCapture

# ====== 步骤 1: 截图 ======
print("=" * 60)
print("步骤 1: 截图")
print("=" * 60)

capture = ScreenCapture()
roi = capture.capture_region(BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT)

# 保存原始截图
img1_path = str(DEBUG_DIR / "01_raw_screenshot.png")
cv2.imwrite(img1_path, roi)
print(f"  保存: {img1_path}")

# ====== 步骤 2: YOLO 检测 ======
print("\n" + "=" * 60)
print("步骤 2: YOLO 检测 + 标注")
print("=" * 60)

from vision.yolo_item_detector import YoloItemDetector

yolo = YoloItemDetector(YOLO_MODEL_PATH, YOLO_CONFIDENCE_THRESHOLD, YOLO_IOU_THRESHOLD)
detections = yolo.detect(roi)
print(f"  YOLO 检测到: {len(detections)} 个物品")

# 在截图上画 YOLO 框
img2 = roi.copy()
if len(img2.shape) == 3 and img2.shape[2] == 4:
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGRA2BGR)

for i, det in enumerate(detections):
    color = (0, 255, 0)  # 绿色
    cv2.rectangle(img2, (det.x, det.y), (det.x + det.w, det.y + det.h), color, 2)
    label = f"[{i+1}] {det.confidence:.2f}"
    cv2.putText(img2, label, (det.x, det.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

img2_path = str(DEBUG_DIR / "02_yolo_detections.png")
cv2.imwrite(img2_path, img2)
print(f"  保存: {img2_path}")

# ====== 步骤 3: 模板匹配 + 候选列表 ======
print("\n" + "=" * 60)
print("步骤 3: 模板匹配 → 最终候选列表")
print("=" * 60)

from config import TEMPLATE_MATCH_THRESHOLD
from vision.recognizer import TemplateRecognizer
from vision.hybrid_pipeline import HybridPipeline

templates_dir = str(Path(__file__).parent.parent / "templates")
template_recognizer = TemplateRecognizer(templates_dir, threshold=TEMPLATE_MATCH_THRESHOLD)
template_recognizer.load_templates()

hybrid = HybridPipeline(yolo, template_recognizer)
candidates, eliminated, summary = hybrid.process(roi, BACKPACK_LEFT, BACKPACK_TOP)

print(f"  最终候选: {len(candidates)} 个")
print(f"  摘要: 原始={summary.raw_count} 过滤={summary.filtered_count} 去重={summary.dedup_count} 保留={summary.final_count}")

# 在截图上画最终候选框
img3 = roi.copy()
if len(img3.shape) == 3 and img3.shape[2] == 4:
    img3 = cv2.cvtColor(img3, cv2.COLOR_BGRA2BGR)

for i, c in enumerate(candidates, 1):
    # 候选框坐标是屏幕坐标，需要转回 ROI 局部坐标
    lx = c.screen_x - BACKPACK_LEFT
    ly = c.screen_y - BACKPACK_TOP

    color = (0, 255, 255)  # 黄色
    cv2.rectangle(img3, (lx, ly), (lx + c.screen_w, ly + c.screen_h), color, 2)
    name = c.template_name or "unknown"
    label = f"[{i}] {name} ({c.confidence:.2f})"
    cv2.putText(img3, label, (lx, ly - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # 标点击点（红点）
    cx = c.click_x - BACKPACK_LEFT
    cy = c.click_y - BACKPACK_TOP
    cv2.circle(img3, (cx, cy), 4, (0, 0, 255), -1)

img3_path = str(DEBUG_DIR / "03_final_candidates.png")
cv2.imwrite(img3_path, img3)
print(f"  保存: {img3_path}")

# ====== 按类型分组 ======
print("\n" + "=" * 60)
print("步骤 4: 按类型分组 (模拟售卖顺序)")
print("=" * 60)

from core.loop import _group_by_type
groups = _group_by_type(candidates)
print(f"  共 {len(groups)} 组\n")

for i, group in enumerate(groups, 1):
    first = group[0]
    name = first.template_name or "unknown"
    print(f"  [{i}] {name} × {len(group)}")
    print(f"      入口: ({first.click_x}, {first.click_y})")

# ====== 列出文件 ======
print("\n" + "=" * 60)
print("输出文件:")
print("=" * 60)
for f in sorted(DEBUG_DIR.glob("0*.png")):
    print(f"  {f}")
