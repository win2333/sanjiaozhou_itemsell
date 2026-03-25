"""AutoSellLoop 集成测试（新架构 pipeline + 模式切换）"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


def _make_loop(run_mode: str = "observe", detector_mode: str = "template"):
    """构造带 mock 依赖的 AutoSellLoop 实例"""
    from core.loop import AutoSellLoop

    item_rec = MagicMock()
    item_rec.recognize_as_raw_detections.return_value = []
    ui_rec = MagicMock()
    capture = MagicMock()
    capture.capture_full_screen.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
    mouse = MagicMock()
    keyboard = MagicMock()
    price_reader = MagicMock()

    with patch('core.loop.ITEM_DETECTOR_MODE', detector_mode), \
         patch('core.loop.RUN_MODE', run_mode):
        loop = AutoSellLoop(
            item_recognizer=item_rec,
            ui_recognizer=ui_rec,
            capture=capture,
            mouse=mouse,
            keyboard=keyboard,
            price_reader=price_reader,
        )
        loop.state.is_running = True

    return loop, mouse, capture, item_rec


class TestLoopIntegration:
    def test_observe_mode_does_not_click(self):
        """observe 模式：pipeline 返回候选，verify 通过，不调用 mouse.click"""
        from vision.item_types import RawItemDetection, ItemCandidate, EliminatedCandidate, RoundSummary

        loop, mouse, capture, item_rec = _make_loop(run_mode="observe")

        # Mock pipeline 返回一个候选
        first = ItemCandidate(
            screen_x=100, screen_y=200, screen_w=50, screen_h=50,
            click_x=125, click_y=225, confidence=0.9, rank=1,
            passed_icon_filter=True, keep_reason="normal"
        )
        summary = RoundSummary(
            raw_count=1, filtered_count=0, dedup_count=0, final_count=1,
            first_candidate=first
        )

        with patch('core.loop.ITEM_DETECTOR_MODE', 'template'), \
             patch('core.loop.RUN_MODE', 'observe'), \
             patch('core.loop.SAVE_DEBUG_IMAGES', False), \
             patch.object(loop._candidate_pipeline, 'process', return_value=([first], [], summary)), \
             patch.object(loop, '_verify_candidate', return_value=True):
            loop._run_one_cycle_new()

        mouse.click.assert_not_called()

    def test_empty_pipeline_result_continues(self):
        """pipeline 返回空候选，loop 继续不报错"""
        from vision.item_types import RoundSummary

        loop, mouse, _, item_rec = _make_loop()
        summary = RoundSummary(
            raw_count=0, filtered_count=0, dedup_count=0, final_count=0
        )

        with patch('core.loop.ITEM_DETECTOR_MODE', 'template'), \
             patch('core.loop.RUN_MODE', 'observe'), \
             patch('core.loop.SAVE_DEBUG_IMAGES', False), \
             patch.object(loop._candidate_pipeline, 'process', return_value=([], [], summary)):
            # Should not raise
            loop._run_one_cycle_new()

        mouse.click.assert_not_called()

    def test_verify_fail_skips_round(self):
        """verify 失败，loop 跳过本轮，不点击"""
        from vision.item_types import ItemCandidate, RoundSummary

        loop, mouse, _, _ = _make_loop(run_mode="live")

        first = ItemCandidate(
            screen_x=100, screen_y=200, screen_w=50, screen_h=50,
            click_x=125, click_y=225, confidence=0.9, rank=1,
            passed_icon_filter=True, keep_reason="normal"
        )
        summary = RoundSummary(
            raw_count=1, filtered_count=0, dedup_count=0, final_count=1,
            first_candidate=first
        )

        with patch('core.loop.ITEM_DETECTOR_MODE', 'template'), \
             patch('core.loop.RUN_MODE', 'live'), \
             patch('core.loop.SAVE_DEBUG_IMAGES', False), \
             patch.object(loop._candidate_pipeline, 'process', return_value=([first], [], summary)), \
             patch.object(loop, '_verify_candidate', return_value=False):
            loop._run_one_cycle_new()

        mouse.click.assert_not_called()
