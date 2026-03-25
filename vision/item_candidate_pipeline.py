"""候选整理 Pipeline - 坐标换算 → icon filter → 去重 → 排序 → 生成摘要"""

import cv2
import numpy as np
from typing import List, Tuple, Optional

from vision.item_types import (
    RawItemDetection,
    ItemCandidate,
    EliminatedCandidate,
    RoundSummary,
)
from vision.candidate_utils import deduplicate_candidates, sort_candidates

# Icon filter 搜索区域扩展边距（像素）
_ICON_SEARCH_MARGIN: int = 10


class ItemCandidatePipeline:
    """候选整理 Pipeline

    固定处理顺序（不可配置）：
    1. 坐标换算（ROI 局部 → 全屏）
    2. Icon filter（过滤不能卖的物品）
    3. 去重（框中心距 < 阈值，保留置信度最高的）
    4. 排序（y 升序，同行内 x 升序）
    5. 生成摘要

    Attributes:
        icon_filter_threshold: 不能卖图标匹配阈值
        dedup_distance_px: 去重中心距阈值（像素）
        icon_templates: 不能卖图标模板列表（可选，None 则跳过 icon filter）
    """

    def __init__(
        self,
        icon_filter_threshold: float = 0.8,
        dedup_distance_px: int = 20,
        icon_templates: Optional[List[np.ndarray]] = None,
    ) -> None:
        """初始化

        Args:
            icon_filter_threshold: 不能卖图标匹配阈值 (0-1)
            dedup_distance_px: 去重中心距阈值（像素）
            icon_templates: 不能卖图标模板列表，None 表示不启用 icon filter
        """
        self.icon_filter_threshold = icon_filter_threshold
        self.dedup_distance_px = dedup_distance_px
        self.icon_templates: List[np.ndarray] = icon_templates or []

    def process(
        self,
        raw_detections: List[RawItemDetection],
        roi_origin_x: int,
        roi_origin_y: int,
        roi_img: Optional[np.ndarray] = None,
    ) -> Tuple[List[ItemCandidate], List[EliminatedCandidate], RoundSummary]:
        """处理原始检测结果，产出候选列表、淘汰列表和本轮摘要

        Args:
            raw_detections: 原始检测框列表（ROI 局部坐标）
            roi_origin_x: ROI 区域在全屏中的左上角 x
            roi_origin_y: ROI 区域在全屏中的左上角 y
            roi_img: ROI 图像（用于 icon filter，可为 None）

        Returns:
            (candidates, eliminated, summary)
        """
        raw_count = len(raw_detections)
        eliminated: List[EliminatedCandidate] = []

        # 步骤 1: 坐标换算
        converted = self._convert_coordinates(raw_detections, roi_origin_x, roi_origin_y)

        # 步骤 2: Icon filter
        after_filter, filter_eliminated = self._apply_icon_filter(converted, roi_img, roi_origin_x, roi_origin_y)
        eliminated.extend(filter_eliminated)
        filtered_count = len(filter_eliminated)

        # 步骤 3: 去重
        after_dedup, dedup_eliminated = deduplicate_candidates(
            after_filter, self.dedup_distance_px
        )
        eliminated.extend(dedup_eliminated)
        dedup_count = len(dedup_eliminated)

        # 步骤 4: 排序
        sorted_items = sort_candidates(after_dedup)

        # 步骤 5: 赋 rank，生成候选列表
        candidates: List[ItemCandidate] = []
        for rank, item in enumerate(sorted_items, start=1):
            item.rank = rank
            candidates.append(item)

        final_count = len(candidates)
        first_candidate = candidates[0] if candidates else None

        summary = RoundSummary(
            raw_count=raw_count,
            filtered_count=filtered_count,
            dedup_count=dedup_count,
            final_count=final_count,
            first_candidate=first_candidate,
        )

        return candidates, eliminated, summary

    def _convert_coordinates(
        self,
        raw_detections: List[RawItemDetection],
        roi_origin_x: int,
        roi_origin_y: int,
    ) -> List[ItemCandidate]:
        """步骤 1: ROI 局部坐标换算为全屏坐标

        Args:
            raw_detections: 原始检测框列表
            roi_origin_x: ROI 原点 x
            roi_origin_y: ROI 原点 y

        Returns:
            转换后的候选列表（rank=0，待排序后赋值）
        """
        candidates: List[ItemCandidate] = []
        for det in raw_detections:
            sx = det.x + roi_origin_x
            sy = det.y + roi_origin_y
            cx = sx + det.w // 2
            cy = sy + det.h // 2
            candidates.append(
                ItemCandidate(
                    screen_x=sx,
                    screen_y=sy,
                    screen_w=det.w,
                    screen_h=det.h,
                    click_x=cx,
                    click_y=cy,
                    confidence=det.confidence,
                    rank=0,
                    passed_icon_filter=True,
                    keep_reason="normal",
                    template_name=det.template_name,
                )
            )
        return candidates

    def _apply_icon_filter(
        self,
        candidates: List[ItemCandidate],
        roi_img: Optional[np.ndarray],
        roi_origin_x: int,
        roi_origin_y: int,
    ) -> Tuple[List[ItemCandidate], List[EliminatedCandidate]]:
        """步骤 2: Icon filter - 过滤含有「不能卖」图标的候选

        如果没有 icon_templates 或 roi_img，直接全部通过。

        Args:
            candidates: 候选列表
            roi_img: ROI 图像（BGR），用于模板匹配

        Returns:
            (通过的候选列表, 淘汰列表)
        """
        if not self.icon_templates or roi_img is None:
            return candidates, []

        passed: List[ItemCandidate] = []
        eliminated: List[EliminatedCandidate] = []

        work = roi_img
        if len(work.shape) == 3 and work.shape[2] == 4:
            work = cv2.cvtColor(work, cv2.COLOR_BGRA2BGR)

        for c in candidates:
            if self._has_no_sell_icon(work, c, roi_origin_x, roi_origin_y):
                c.passed_icon_filter = False
                eliminated.append(
                    EliminatedCandidate(
                        screen_x=c.screen_x,
                        screen_y=c.screen_y,
                        reason="icon_filter",
                    )
                )
            else:
                passed.append(c)

        return passed, eliminated

    def _has_no_sell_icon(
        self, roi_img: np.ndarray, candidate: ItemCandidate,
        roi_origin_x: int, roi_origin_y: int,
    ) -> bool:
        """检测候选框附近是否有「不能卖」图标

        只在候选自身框（扩大一点边距）的区域内搜索，避免整张图搜到无关 icon。

        Args:
            roi_img: ROI 图像（BGR，局部坐标）
            candidate: 候选项（screen_x/screen_y 是全屏坐标）
            roi_origin_x: ROI 区域在全屏中的左上角 x（用于坐标换算）
            roi_origin_y: ROI 区域在全屏中的左上角 y

        Returns:
            True 表示发现不能卖图标
        """
        # 将候选的全屏坐标转为 ROI 局部坐标
        local_x = candidate.screen_x - roi_origin_x
        local_y = candidate.screen_y - roi_origin_y

        # 候选框在 ROI 局部坐标下
        x1 = local_x
        y1 = local_y
        x2 = local_x + candidate.screen_w
        y2 = local_y + candidate.screen_h

        # 扩大搜索区域：框本身 + 周边一小片
        search_x1 = max(0, x1 - _ICON_SEARCH_MARGIN)
        search_y1 = max(0, y1 - _ICON_SEARCH_MARGIN)
        search_x2 = min(roi_img.shape[1], x2 + _ICON_SEARCH_MARGIN)
        search_y2 = min(roi_img.shape[0], y2 + _ICON_SEARCH_MARGIN)

        search_region = roi_img[search_y1:search_y2, search_x1:search_x2]

        if search_region.size == 0:
            return False

        for icon_tmpl in self.icon_templates:
            tmpl_h, tmpl_w = icon_tmpl.shape[:2]
            if tmpl_h > search_region.shape[0] or tmpl_w > search_region.shape[1]:
                continue
            res = cv2.matchTemplate(search_region, icon_tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val >= self.icon_filter_threshold:
                return True
        return False
