"""候选处理共享工具函数 - 供 ItemCandidatePipeline 和 HybridPipeline 共用"""

import math
from typing import List, Tuple

from vision.item_types import EliminatedCandidate, ItemCandidate


# 默认去重距离（像素）
DEFAULT_DEDUP_DISTANCE_PX: int = 20


def deduplicate_candidates(
    candidates: List[ItemCandidate],
    dedup_distance_px: int = DEFAULT_DEDUP_DISTANCE_PX,
) -> Tuple[List[ItemCandidate], List[EliminatedCandidate]]:
    """去重 - 中心距小于阈值时保留置信度最高的

    贪心算法：按置信度降序遍历，每项与已保留项比较，距离小于阈值视为重复。

    Args:
        candidates: 待去重候选列表
        dedup_distance_px: 去重中心距阈值（像素）

    Returns:
        (去重后候选列表, 淘汰列表)
    """
    if not candidates:
        return [], []

    sorted_by_conf = sorted(candidates, key=lambda c: c.confidence, reverse=True)
    kept: List[ItemCandidate] = []
    eliminated: List[EliminatedCandidate] = []

    for c in sorted_by_conf:
        is_dup = False
        for k in kept:
            dist = math.sqrt(
                (c.click_x - k.click_x) ** 2 + (c.click_y - k.click_y) ** 2
            )
            if dist < dedup_distance_px:
                is_dup = True
                break
        if is_dup:
            eliminated.append(
                EliminatedCandidate(
                    screen_x=c.screen_x,
                    screen_y=c.screen_y,
                    reason="dedup",
                )
            )
        else:
            kept.append(c)

    return kept, eliminated


def sort_candidates(candidates: List[ItemCandidate]) -> List[ItemCandidate]:
    """排序 - y 升序，同行内 x 升序"""
    return sorted(candidates, key=lambda c: (c.screen_y, c.screen_x))
