"""ItemCandidatePipeline 单元测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from vision.item_types import RawItemDetection
from vision.item_candidate_pipeline import ItemCandidatePipeline


def make_det(x: int, y: int, w: int = 50, h: int = 50, conf: float = 0.9, template_name: str = "测试物品") -> RawItemDetection:
    return RawItemDetection(x=x, y=y, w=w, h=h, confidence=conf, source="template", template_name=template_name)


class TestItemCandidatePipeline:
    def setup_method(self):
        self.pipeline = ItemCandidatePipeline(
            dedup_distance_px=20,
        )

    def test_coordinate_conversion(self):
        """ROI 局部坐标 + origin → 全屏坐标"""
        dets = [make_det(10, 20, w=40, h=40)]
        candidates, _, summary = self.pipeline.process(dets, roi_origin_x=100, roi_origin_y=200)

        assert len(candidates) == 1
        c = candidates[0]
        assert c.screen_x == 110   # 10 + 100
        assert c.screen_y == 220   # 20 + 200
        assert c.click_x == 130    # 110 + 40//2
        assert c.click_y == 240    # 220 + 40//2

    def test_dedup_keeps_highest_confidence(self):
        """两个距离很近的框，保留置信度高的"""
        dets = [
            make_det(10, 10, conf=0.6),   # 低置信度
            make_det(12, 12, conf=0.95),  # 高置信度，与上面很近
        ]
        candidates, eliminated, summary = self.pipeline.process(
            dets, roi_origin_x=0, roi_origin_y=0
        )

        assert len(candidates) == 1
        assert candidates[0].confidence == pytest.approx(0.95)
        assert summary.dedup_count == 1
        assert eliminated[0].reason == "dedup"

    def test_sort_order(self):
        """多个候选应按 y 升序、同行 x 升序排列"""
        dets = [
            make_det(50, 100),  # rank 2
            make_det(10, 200),  # rank 3
            make_det(10, 50),   # rank 1
        ]
        candidates, _, _ = self.pipeline.process(
            dets, roi_origin_x=0, roi_origin_y=0
        )

        ys = [c.screen_y for c in candidates]
        assert ys == sorted(ys), "应按 y 升序排列"

        # rank 字段
        assert candidates[0].rank == 1
        assert candidates[1].rank == 2
        assert candidates[2].rank == 3

    def test_empty_input_returns_empty_summary(self):
        """空输入不报错，摘要 final_count==0"""
        candidates, eliminated, summary = self.pipeline.process(
            [], roi_origin_x=0, roi_origin_y=0
        )

        assert len(candidates) == 0
        assert summary.final_count == 0
        assert summary.first_candidate is None
        assert summary.raw_count == 0
