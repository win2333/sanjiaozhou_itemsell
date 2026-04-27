"""候选整理 Pipeline - 坐标换算 → 去重 → 排序 → 生成摘要"""

from typing import List, Tuple

from vision.item_types import (
    RawItemDetection,
    ItemCandidate,
    EliminatedCandidate,
    RoundSummary,
)
from vision.candidate_utils import deduplicate_candidates, sort_candidates


class ItemCandidatePipeline:
    """候选整理 Pipeline

    固定处理顺序（不可配置）：
    1. 坐标换算（ROI 局部 → 全屏）
    2. 去重（框中心距 < 阈值，保留置信度最高的）
    3. 排序（y 升序，同行内 x 升序）
    4. 生成摘要

    Attributes:
        dedup_distance_px: 去重中心距阈值（像素）
    """

    def __init__(
        self,
        dedup_distance_px: int = 20,
    ) -> None:
        """初始化

        Args:
            dedup_distance_px: 去重中心距阈值（像素）
        """
        self.dedup_distance_px = dedup_distance_px

    def process(
        self,
        raw_detections: List[RawItemDetection],
        roi_origin_x: int,
        roi_origin_y: int,
    ) -> Tuple[List[ItemCandidate], List[EliminatedCandidate], RoundSummary]:
        """处理原始检测结果，产出候选列表、淘汰列表和本轮摘要

        Args:
            raw_detections: 原始检测框列表（ROI 局部坐标）
            roi_origin_x: ROI 区域在全屏中的左上角 x
            roi_origin_y: ROI 区域在全屏中的左上角 y

        Returns:
            (candidates, eliminated, summary)
        """
        raw_count = len(raw_detections)
        eliminated: List[EliminatedCandidate] = []

        # 步骤 1: 坐标换算
        converted = self._convert_coordinates(
            raw_detections, roi_origin_x, roi_origin_y
        )

        # 步骤 2: 去重
        after_dedup, dedup_eliminated = deduplicate_candidates(
            converted, self.dedup_distance_px
        )
        eliminated.extend(dedup_eliminated)
        dedup_count = len(dedup_eliminated)

        # 步骤 3: 排序
        sorted_items = sort_candidates(after_dedup)

        # 步骤 4: 赋 rank，生成候选列表
        candidates: List[ItemCandidate] = []
        for rank, item in enumerate(sorted_items, start=1):
            item.rank = rank
            candidates.append(item)

        final_count = len(candidates)
        first_candidate = candidates[0] if candidates else None

        summary = RoundSummary(
            raw_count=raw_count,
            filtered_count=0,
            dedup_count=dedup_count,
            template_match_count=raw_count,  # In template mode, raw_detections are already template matches
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
