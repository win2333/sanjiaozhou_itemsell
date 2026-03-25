"""调试可视化工具 - 绘制检测框标注图

生成3张调试图，按轮次分文件夹：
  debug/
  └── round_NNNN/
      ├── 00_original.png   - 原图（无标注）
      ├── 01_yolo.png       - YOLO 检测框（蓝色）
      └── 02_pipeline.png    - YOLO框灰色 + 候选绿色 + 淘汰红色 + 物品名
"""

import os
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from vision.item_types import (
    RawItemDetection,
    ItemCandidate,
    EliminatedCandidate,
    RoundSummary,
)
from utils.logger import get_logger


# 框颜色（BGR）
COLOR_YOLO = (255, 100, 0)  # 蓝色 - YOLO 检测框
COLOR_CANDIDATE = (0, 220, 0)  # 绿色 - 候选/模板通过框
COLOR_FIRST = (0, 200, 255)  # 黄色 - 第一名候选框
COLOR_ELIMINATED = (0, 0, 255)  # 红色 - 淘汰框


def save_debug_frame(
    roi_img: np.ndarray,
    raw_detections: List[RawItemDetection],
    candidates: List[ItemCandidate],
    eliminated: List[EliminatedCandidate],
    summary: RoundSummary,
    round_n: int,
    roi_origin_x: int = 0,
    roi_origin_y: int = 0,
    debug_dir: str = "debug",
    save: bool = True,
    all_template_matches: List[ItemCandidate] = None,
) -> None:
    """保存3张调试截图到 debug/round_NNNN/ 目录

    Args:
        roi_img: ROI 局部截图（BGR）
        raw_detections: 原始检测列表（ROI 局部坐标）
        candidates: 最终候选列表（全屏坐标）
        eliminated: 淘汰候选列表（全屏坐标）
        summary: 本轮摘要
        round_n: 轮次编号
        roi_origin_x: ROI 在全屏中的左上角 x
        roi_origin_y: ROI 在全屏中的左上角 y
        debug_dir: 调试图片保存目录
        save: 是否实际保存
    """
    if not save:
        return

    try:
        out_dir = Path(debug_dir) / f"round_{round_n:04d}"
        out_dir.mkdir(parents=True, exist_ok=True)

        # ---------- 图1: 原图 ----------
        img_orig = roi_img.copy()
        if len(img_orig.shape) == 3 and img_orig.shape[2] == 4:
            img_orig = cv2.cvtColor(img_orig, cv2.COLOR_BGRA2BGR)
        cv2.imwrite(str(out_dir / "00_original.png"), img_orig)

        # ---------- 图2: YOLO 识别图 ----------
        img_yolo = img_orig.copy()
        for det in raw_detections:
            if det.source == "yolo":
                cv2.rectangle(
                    img_yolo,
                    (det.x, det.y),
                    (det.x + det.w, det.y + det.h),
                    COLOR_YOLO,
                    1,
                )
                _put_text(
                    img_yolo,
                    f"YOLO {det.confidence:.2f}",
                    det.x,
                    det.y - 4,
                    color=(255, 100, 0),
                )
        cv2.imwrite(str(out_dir / "01_yolo.png"), img_yolo)

        # ---------- 图3: Pipeline 综合结果图 ----------
        img_pipe = img_orig.copy()

        # 3a. YOLO 原始框（灰色）- ROI 局部坐标
        for det in raw_detections:
            if det.source == "yolo":
                cv2.rectangle(
                    img_pipe,
                    (det.x, det.y),
                    (det.x + det.w, det.y + det.h),
                    (150, 150, 150),
                    1,
                )

        # 3a2. ALL template match boxes (green + template name) — per D-07, D-08, D-09
        if all_template_matches is None:
            all_template_matches = []
        for cand in all_template_matches:
            lx = cand.screen_x - roi_origin_x
            ly = cand.screen_y - roi_origin_y
            rx = lx + cand.screen_w
            ry = ly + cand.screen_h
            cv2.rectangle(img_pipe, (lx, ly), (rx, ry), COLOR_CANDIDATE, 1)
            # Label with template name in white (D-09)
            label = cand.template_name if cand.template_name else "?"
            label += f" {cand.confidence:.2f}"
            _put_text(img_pipe, label, lx, ly - 4, color=(255, 255, 255))  # white text

        # 3b. 淘汰框（红色 + 原因）- 全屏坐标转 ROI 局部
        for elim in eliminated:
            lx = elim.screen_x - roi_origin_x
            ly = elim.screen_y - roi_origin_y
            if 0 <= lx < img_pipe.shape[1] - 50 and 0 <= ly < img_pipe.shape[0] - 50:
                cv2.rectangle(
                    img_pipe, (lx, ly), (lx + 50, ly + 50), COLOR_ELIMINATED, 1
                )
                _put_text(img_pipe, elim.reason, lx, ly - 4, color=(0, 0, 255))

        # 3c. 候选/模板通过框（绿色 + 物品名）- 全屏坐标转 ROI 局部
        for cand in candidates:
            lx = cand.screen_x - roi_origin_x
            ly = cand.screen_y - roi_origin_y
            rx = lx + cand.screen_w
            ry = ly + cand.screen_h
            color = COLOR_FIRST if cand.rank == 1 else COLOR_CANDIDATE
            thick = 2 if cand.rank == 1 else 1

            cv2.rectangle(img_pipe, (lx, ly), (rx, ry), color, thick)

            # 标注物品名称 + 排名 + 置信度
            label = cand.template_name if cand.template_name else "item"
            label += f" #{cand.rank} {cand.confidence:.2f}"
            _put_text(img_pipe, label, lx, ly - 4, color=color)

            # 第一名额外画粗边框
            if cand.rank == 1:
                cv2.rectangle(
                    img_pipe, (lx - 2, ly - 2), (rx + 2, ry + 2), COLOR_FIRST, 2
                )

        cv2.imwrite(str(out_dir / "02_pipeline.png"), img_pipe)

    except Exception as e:
        get_logger().log_only("[调试]", f"标注图保存失败: {e}")


def _put_text(
    img: np.ndarray,
    text: str,
    x: int,
    y: int,
    color: tuple = (255, 255, 255),
) -> None:
    """在图像上绘制文字（带黑色描边）"""
    try:
        cv2.putText(
            img, text, (x, max(y, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2
        )
        cv2.putText(img, text, (x, max(y, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    except Exception:
        pass
