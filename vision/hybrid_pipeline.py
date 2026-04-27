"""混合识别 Pipeline - YOLO粗识别 + 模板精确识别

工作流程:
1. YOLO快速扫描全图，定位候选区域
2. 裁剪ROI小图
3. 多线程模板匹配精识别
4. 合并去重，输出ItemCandidate列表
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from utils.logger import get_logger
from vision.item_types import (
    EliminatedCandidate,
    ItemCandidate,
    RawItemDetection,
    RoundSummary,
)
from vision.yolo_item_detector import YoloItemDetector
from vision.candidate_utils import deduplicate_candidates, sort_candidates
from config import TEMPLATE_MATCH_THRESHOLD, COLOR_MATCH_THRESHOLD

# ROI 提取时扩展边框像素数
_ROI_PADDING: int = 10


@dataclass
class _RoiWorkItem:
    image: np.ndarray
    detection: RawItemDetection
    x_offset: int
    y_offset: int


class HybridPipeline:
    """混合识别Pipeline: YOLO粗识别 + 模板精确识别

    工作流程:
    1. YOLO快速扫描全图，定位候选区域
    2. 裁剪ROI小图
    3. 多线程模板匹配精识别
    4. 合并去重，输出ItemCandidate列表

    Attributes:
        yolo_detector: YOLO检测器
        template_recognizer: 模板识别器
        max_workers: 模板匹配线程数
        dedup_distance_px: 去重中心距阈值（像素）
    """

    def __init__(
        self,
        yolo_detector: YoloItemDetector,
        template_recognizer,  # TemplateRecognizer
        max_workers: int = 8,
        dedup_distance_px: int = 20,
    ):
        """初始化

        Args:
            yolo_detector: YOLO检测器实例
            template_recognizer: 模板识别器实例
            max_workers: 模板匹配最大线程数
            dedup_distance_px: 去重中心距阈值
        """
        self.yolo = yolo_detector
        self.template = template_recognizer
        self.max_workers = max_workers
        self.dedup_distance_px = dedup_distance_px
        self._template_match_count: int = 0

    def process(
        self,
        full_screen: np.ndarray,
        roi_origin_x: int = 0,
        roi_origin_y: int = 0,
    ) -> Tuple[List[ItemCandidate], List[EliminatedCandidate], RoundSummary]:
        """处理完整屏幕截图，返回候选列表

        Args:
            full_screen: BGR格式截图（可以是全屏或局部ROI）
            roi_origin_x: 截图左上角在屏幕上的x坐标（用于坐标转换）
            roi_origin_y: 截图左上角在屏幕上的y坐标

        Returns:
            (candidates, eliminated, summary) - 与ItemCandidatePipeline接口兼容
        """
        logger = get_logger()
        start_time = time.time()
        round_n = getattr(self, "_round_counter", 0) + 1
        self._round_counter = round_n

        # Step 1: YOLO粗识别
        logger.scan(f"[轮次{round_n}] YOLO扫描中... (0ms)")
        yolo_start = time.time()
        yolo_detections = self.yolo.detect(full_screen)
        yolo_time = (time.time() - yolo_start) * 1000

        if not yolo_detections:
            logger.scan(f"[轮次{round_n}] YOLO完成: 0个候选区域 ({yolo_time:.0f}ms)")
            summary = RoundSummary(
                raw_count=0,
                filtered_count=0,
                dedup_count=0,
                template_match_count=0,
                final_count=0,
                first_candidate=None,
            )
            return [], [], summary

        logger.scan(
            f"[轮次{round_n}] YOLO完成: {len(yolo_detections)}个候选区域 ({yolo_time:.0f}ms)"
        )

        # Step 2: 提取ROI
        roi_start = time.time()
        rois = self._extract_rois(full_screen, yolo_detections)
        roi_time = (time.time() - roi_start) * 1000
        logger.scan(f"[轮次{round_n}] ROI提取完成: {len(rois)}个ROI ({roi_time:.0f}ms)")

        # Step 3: 多线程模板匹配
        match_start = time.time()
        logger.scan(f"[轮次{round_n}] 模板识别中...")
        template_results = self._parallel_template_match(
            rois, yolo_detections, roi_origin_x, roi_origin_y
        )
        match_time = (time.time() - match_start) * 1000
        logger.scan(
            f"[轮次{round_n}] 模板匹配完成: {len(template_results)}个有效 ({match_time:.0f}ms)"
        )

        total_time = (time.time() - start_time) * 1000
        logger.scan(f"[轮次{round_n}] 混合识别总耗时: {total_time:.0f}ms")

        # Step 4: 去重
        deduplicated, eliminated = deduplicate_candidates(
            template_results, self.dedup_distance_px
        )

        # Step 5: 排序
        sorted_candidates = sort_candidates(deduplicated)

        # Step 7: 赋rank
        final_candidates: List[ItemCandidate] = []
        for rank, item in enumerate(sorted_candidates, start=1):
            item.rank = rank
            final_candidates.append(item)

        first_candidate = final_candidates[0] if final_candidates else None

        summary = RoundSummary(
            raw_count=len(yolo_detections),
            filtered_count=0,
            dedup_count=len(eliminated),
            template_match_count=self._template_match_count,
            final_count=len(final_candidates),
            first_candidate=first_candidate,
            raw_yolo_detections=yolo_detections,
        )

        return final_candidates, eliminated, summary

    def _extract_rois(
        self,
        image: np.ndarray,
        detections: List[RawItemDetection],
    ) -> List[_RoiWorkItem]:
        """从全图中提取ROI区域

        Args:
            image: 全图
            detections: YOLO检测结果

        Returns:
            ROI 工作项列表，包含实际裁剪偏移和 detection 元数据。
        """
        rois: List[_RoiWorkItem] = []
        for det in detections:
            x1 = max(0, det.x)
            y1 = max(0, det.y)
            x2 = min(image.shape[1], det.x + det.w)
            y2 = min(image.shape[0], det.y + det.h)

            # 边框扩展一些像素用于模板匹配
            x1_pad = max(0, x1 - _ROI_PADDING)
            y1_pad = max(0, y1 - _ROI_PADDING)
            x2_pad = min(image.shape[1], x2 + _ROI_PADDING)
            y2_pad = min(image.shape[0], y2 + _ROI_PADDING)

            roi = image[y1_pad:y2_pad, x1_pad:x2_pad]
            rois.append(_RoiWorkItem(roi, det, x1_pad, y1_pad))

        return rois

    def _parallel_template_match(
        self,
        rois: List[_RoiWorkItem],
        detections: List[RawItemDetection],
        roi_origin_x: int = 0,
        roi_origin_y: int = 0,
    ) -> List[ItemCandidate]:
        """多线程模板匹配

        Args:
            rois: ROI 工作项列表
            detections: 对应的检测元数据
            roi_origin_x: ROI图像左上角在屏幕上的x坐标
            roi_origin_y: ROI图像左上角在屏幕上的y坐标

        Returns:
            List[ItemCandidate]: 匹配成功的物品
        """
        results: List[ItemCandidate] = []

        if not rois:
            return results

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, item in enumerate(rois):
                future = executor.submit(
                    self._match_single_roi,
                    item.image,
                    item.detection,
                    item.x_offset,
                    item.y_offset,
                    i,
                    len(rois),
                    roi_origin_x,
                    roi_origin_y,
                )
                futures[future] = (item.detection, i)

            for future in as_completed(futures):
                det, idx = futures[future]
                try:
                    item = future.result()
                    if item is not None:
                        results.append(item)
                except Exception as e:
                    get_logger().warning(f"ROI[{idx}] 匹配失败: {e}")

        self._template_match_count = len(results)
        return results

    def _match_single_roi(
        self,
        roi: np.ndarray,
        detection: RawItemDetection,
        roi_x_offset: int,
        roi_y_offset: int,
        index: int,
        total: int,
        roi_origin_x: int = 0,
        roi_origin_y: int = 0,
    ) -> Optional[ItemCandidate]:
        """单个ROI的模板匹配

        Args:
            roi: ROI图像
            detection: YOLO检测元数据
            roi_x_offset: 当前 ROI 图块在 full_screen 中的实际 x 偏移
            roi_y_offset: 当前 ROI 图块在 full_screen 中的实际 y 偏移
            index: 当前索引
            total: 总数
            roi_origin_x: ROI图像左上角在屏幕上的x坐标
            roi_origin_y: ROI图像左上角在屏幕上的y坐标

        Returns:
            ItemCandidate或None
        """
        # 转换BGRA -> BGR
        work_img = roi
        if len(roi.shape) == 3 and roi.shape[2] == 4:
            work_img = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        roi_h, roi_w = work_img.shape[:2]

        best_match = None
        best_confidence = 0.0
        # 记录颜色验证失败的最佳候选（用于调试）
        best_color_fail_name = ""
        best_color_fail_conf = 0.0
        best_color_fail_sim = 0.0

        # 直接在ROI上做模板匹配，跳过TemplateRecognizer的x>=1150裁剪逻辑
        # 只用匹配阈值过滤

        for template_name, template in self.template.templates.items():
            tmpl_h, tmpl_w = template.shape[:2]

            # 跳过比ROI大的模板
            if tmpl_h > roi_h or tmpl_w > roi_w:
                continue

            # 模板匹配
            try:
                result = cv2.matchTemplate(work_img, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val >= TEMPLATE_MATCH_THRESHOLD and max_val > best_confidence:
                    # 九宫格逐点颜色验证
                    grid = self._grid_points(tmpl_w, tmpl_h)
                    similarities = []
                    all_valid = True
                    for gx, gy in grid:
                        # B图（模板）上该点的颜色
                        if 0 <= gx < tmpl_w and 0 <= gy < tmpl_h:
                            t_color = template[gy, gx]
                        else:
                            all_valid = False
                            break
                        # A图（ROI）上对应点的颜色
                        ax = max_loc[0] + gx
                        ay = max_loc[1] + gy
                        if 0 <= ax < roi_w and 0 <= ay < roi_h:
                            m_color = work_img[ay, ax]
                        else:
                            all_valid = False
                            break
                        sim = self._color_similarity(
                            t_color.astype(float), m_color.astype(float)
                        )
                        similarities.append(sim)
                    if all_valid and len(similarities) == 9:
                        avg_sim = sum(similarities) / len(similarities)
                        if avg_sim < COLOR_MATCH_THRESHOLD:
                            if max_val > best_color_fail_conf:
                                best_color_fail_name = template_name
                                best_color_fail_conf = max_val
                                best_color_fail_sim = avg_sim
                            continue  # 颜色不匹配，跳过
                    best_confidence = max_val
                    best_match = {
                        "name": template_name,
                        "x": max_loc[0],
                        "y": max_loc[1],
                        "w": tmpl_w,
                        "h": tmpl_h,
                        "confidence": max_val,
                    }
            except Exception:
                continue

        if best_match is None:
            if total > 0:
                reason = f"最高 {best_confidence:.2f}, 阈值 {TEMPLATE_MATCH_THRESHOLD}"
                if best_color_fail_conf > 0:
                    reason += (
                        f" | 颜色验证失败: {best_color_fail_name}"
                        f" ({best_color_fail_conf:.2f}, 相似度 {best_color_fail_sim:.2f})"
                    )
                get_logger().log_only(
                    "[识别]",
                    f"ROI[{index}/{total}] ({detection.w}x{detection.h}) 无匹配 ({reason})",
                )
            return None

        # 构建ItemCandidate，使用屏幕绝对坐标
        # detection.x/y 是 YOLO 在 full_screen 中的坐标（full_screen 左上角为 roi_origin）
        # best_match.x/y 是模板在 roi（图块）中的坐标
        # 图块左上角在 full_screen 中的位置需要使用实际 clamp 后的偏移。
        screen_x = roi_origin_x + roi_x_offset + best_match["x"]
        screen_y = roi_origin_y + roi_y_offset + best_match["y"]
        click_x = screen_x + best_match["w"] // 2
        click_y = screen_y + best_match["h"] // 2

        candidate = ItemCandidate(
            screen_x=screen_x,
            screen_y=screen_y,
            screen_w=best_match["w"],
            screen_h=best_match["h"],
            click_x=click_x,
            click_y=click_y,
            confidence=best_match["confidence"],
            rank=0,
            passed_icon_filter=True,
            keep_reason="hybrid_template_match",
            template_name=best_match["name"],
        )

        return candidate

    def _grid_points(self, w: int, h: int) -> List[Tuple[int, int]]:
        """生成九宫格 9 个点的坐标（相对位置）。

        Args:
            w: 宽度
            h: 高度

        Returns:
            9个点坐标列表，t ∈ {0.25, 0.5, 0.75}
        """
        t = [0.25, 0.5, 0.75]
        return [(round(w * x), round(h * y)) for x in t for y in t]

    def _color_similarity(self, color1: np.ndarray, color2: np.ndarray) -> float:
        """计算两个 BGR 颜色的余弦相似度。

        Args:
            color1: 颜色1 (BGR)
            color2: 颜色2 (BGR)

        Returns:
            相似度 (0-1)
        """
        c1 = color1 / (np.linalg.norm(color1) + 1e-6)
        c2 = color2 / (np.linalg.norm(color2) + 1e-6)
        return float(np.dot(c1, c2))
