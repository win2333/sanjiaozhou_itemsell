"""AutoSellLoop 集成测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pytest
from unittest.mock import MagicMock, patch


def _make_loop(run_mode: str = "observe"):
    """构造带 mock 依赖的 AutoSellLoop 实例"""
    from core.loop import AutoSellLoop

    item_rec = MagicMock()
    ui_rec = MagicMock()
    capture = MagicMock()
    capture.capture_full_screen.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
    mouse = MagicMock()
    keyboard = MagicMock()
    price_reader = MagicMock()

    loop = AutoSellLoop(
        item_recognizer=item_rec,
        ui_recognizer=ui_rec,
        capture=capture,
        mouse=mouse,
        keyboard=keyboard,
        price_reader=price_reader,
    )
    loop.state.is_running = True

    # Mock detector to avoid real YOLO init
    loop._detector = MagicMock()
    return loop, mouse, capture, item_rec


class TestLoopIntegration:
    def test_empty_pipeline_result_continues(self):
        """pipeline 返回空候选，loop 继续不报错"""
        from vision.item_types import RoundSummary

        loop, mouse, _, _ = _make_loop()
        summary = RoundSummary(
            raw_count=0, filtered_count=0, dedup_count=0, final_count=0
        )

        loop._detector.process.return_value = ([], [], summary)

        with patch('core.loop.SAVE_DEBUG_IMAGES', False):
            # Should not raise
            loop._run_one_cycle_new()

        mouse.click.assert_not_called()

    def test_detector_result_goes_to_sell_flow(self):
        """pipeline 返回候选，进入卖出流程"""
        from vision.item_types import ItemCandidate, RoundSummary

        loop, mouse, _, _ = _make_loop()
        first = ItemCandidate(
            screen_x=100, screen_y=200, screen_w=50, screen_h=50,
            click_x=125, click_y=225, confidence=0.9, rank=1,
            passed_icon_filter=True, keep_reason="normal"
        )
        summary = RoundSummary(
            raw_count=1, filtered_count=0, dedup_count=0, final_count=1,
            first_candidate=first
        )

        loop._detector.process.return_value = ([first], [], summary)

        with patch('core.loop.SAVE_DEBUG_IMAGES', False):
            loop._run_one_cycle_new()

        # 检测到候选后会进入卖出流程（至少会调用 _sell_item_with_log）
        # 这个流程会用到 mouse, keyboard 等，验证不崩溃即可
