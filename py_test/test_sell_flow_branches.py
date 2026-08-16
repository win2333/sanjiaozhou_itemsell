"""卖出流程关键分支单元测试: OCR 定价输入 / 固定坐标回退 / 验证重试

覆盖 _sell_item_with_log 新增路径(不实际点击,全 mock):
1. OCR 读到价格 -> 键盘逐位输入数字
2. OCR 失败 -> 回退 PRICE_DIRECT_CLICK_X 固定坐标
3. 验证: 格子清空 -> 计入卖出
4. 验证: 3 次重试均未清空 -> 不计入卖出,返回 False
5. 验证: 背包关闭 -> 立即失败
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch, call

from core.loop import AutoSellLoop, ItemRecord


def _make_record() -> ItemRecord:
    return ItemRecord(
        name="测试物品", x=1500, y=200, width=50, height=50, confidence=0.9
    )


def _make_loop() -> AutoSellLoop:
    item_rec = MagicMock()
    capture = MagicMock()
    mouse = MagicMock()
    keyboard = MagicMock()
    price_reader = MagicMock()
    loop = AutoSellLoop(
        item_recognizer=item_rec,
        capture=capture,
        mouse=mouse,
        keyboard=keyboard,
        price_reader=price_reader,
    )
    loop._detector = MagicMock()
    # 背包锚点已采集且始终匹配(验证时背包视为可见)
    loop._backpack_ref = [((1185, 155), (30, 30, 30))]
    capture.get_screen_size.return_value = (1920, 1080)
    return loop, mouse, keyboard, capture, price_reader


def _record_pixels(loop, pre_click_has_item: bool, post_click_empty: bool = True):
    """控制 _is_empty_slot 的阶段行为。

    _is_empty_slot 在卖出流程中被调用两次,语义不同:
    1. 点击物品前: 判断格子里有没有东西(有物品 -> False 才继续卖)
    2. 确认上架后: 判断格子是否已清空(空了 -> True 验证通过)
    """
    calls = {"n": 0}

    def fake(x, y):
        calls["n"] += 1
        if calls["n"] == 1:
            return not pre_click_has_item  # 第一次: 空=True 表示跳过
        return post_click_empty  # 第二次起: 空=True 表示卖出成功

    loop._is_empty_slot = fake


class TestSellOcrPricing:
    @patch("core.loop.VERIFY_SELL_RESULT", False)
    def test_ocr_price_types_digits(self):
        """OCR 读到价格 -> 逐位键盘输入"""
        loop, mouse, keyboard, _, price_reader = _make_loop()
        loop._read_sell_price = lambda: 8542

        ok = loop._sell_item_with_log(_make_record())

        assert ok is True
        pressed = [c.args[0] for c in keyboard.press.call_args_list]
        # 退格 + 8542 四位数字
        assert pressed[0] == "backspace"
        assert pressed[1:] == ["8", "5", "4", "2"]
        # 不应点击固定价格坐标
        assert not any(
            c.args[0] == 860 for c in mouse.click.call_args_list if c.args
        )

    @patch("core.loop.VERIFY_SELL_RESULT", False)
    def test_ocr_none_falls_back_to_fixed_click(self):
        """OCR 失败 -> 回退固定坐标点击"""
        loop, mouse, keyboard, _, _ = _make_loop()
        loop._read_sell_price = lambda: None

        ok = loop._sell_item_with_log(_make_record())

        assert ok is True
        pressed = [c.args[0] for c in keyboard.press.call_args_list]
        assert pressed == ["backspace"]  # 没有数字输入
        # 应有点击 x=860 的固定坐标
        assert any(c.args[0] == 860 for c in mouse.click.call_args_list if c.args)


class TestSellVerification:
    def _run_sell(self, loop):
        return loop._sell_item_with_log(_make_record())

    @patch("core.loop.USE_OCR_PRICE", False)
    @patch("core.loop.SELL_VERIFY_WAIT_S", 0)
    def test_slot_cleared_counts_as_sold(self):
        """验证通过: 点击前有物品,确认后格子清空 -> total_sold +1"""
        loop, *_ = _make_loop()
        _record_pixels(loop, pre_click_has_item=True, post_click_empty=True)

        ok = self._run_sell(loop)

        assert ok is True
        assert loop.state.total_sold == 1

    @patch("core.loop.USE_OCR_PRICE", False)
    @patch("core.loop.SELL_VERIFY_WAIT_S", 0)
    def test_slot_not_cleared_fails_after_retries(self):
        """验证失败: 3 次重试格子未清空 -> 不计入,返回 False"""
        loop, *_ = _make_loop()
        _record_pixels(loop, pre_click_has_item=True, post_click_empty=False)

        ok = self._run_sell(loop)

        assert ok is False
        assert loop.state.total_sold == 0

    @patch("core.loop.USE_OCR_PRICE", False)
    @patch("core.loop.SELL_VERIFY_WAIT_S", 0)
    def test_backpack_closed_fails_immediately(self):
        """验证失败: 背包关闭 -> 立即 False"""
        loop, *_ = _make_loop()
        loop._is_backpack_visible = lambda: False

        ok = self._run_sell(loop)

        assert ok is False
        assert loop.state.total_sold == 0

    @patch("core.loop.USE_OCR_PRICE", False)
    @patch("core.loop.SELL_VERIFY_WAIT_S", 0)
    def test_stacked_item_slot_change_verifies(self):
        """堆叠物品: 格子未清空但内容变化(数量徽章) -> 验证通过"""
        import numpy as np

        loop, *_ = _make_loop()
        calls = {"n": 0}

        # 点击前(n=1):有物品,非空;确认后(n>=2):堆叠剩余,仍非空
        def fake_empty(x, y):
            calls["n"] += 1
            return False  # 始终非空: 点击前有物品,上架后堆叠剩余

        loop._is_empty_slot = fake_empty

        # 格子图像: 基准(徽章亮) vs 上架后(徽章变暗=数量减少)
        base = np.zeros((40, 40, 3), np.uint8)
        base[30:34, 30:34] = 200  # 数量徽章
        after = base.copy()
        after[30:34, 30:34] = 120

        def fake_capture(x, y):
            # 基准截取(n=0,在第一次空格检查前)与点击前(n=1)返回 base;
            # 上架确认后(n>=2)返回 after(数量徽章变化)
            return base.copy() if calls["n"] <= 1 else after.copy()

        loop._capture_slot_image = fake_capture

        ok = self._run_sell(loop)

        assert ok is True
        assert loop.state.total_sold == 1


class TestSlotChanged:
    """_slot_changed 合成图验证: 变化超阈值/微小动画不误判"""

    def _loop(self):
        from unittest.mock import MagicMock

        loop = AutoSellLoop.__new__(AutoSellLoop)
        loop.status = MagicMock()
        loop.state = MagicMock()
        return loop

    def test_badge_change_detected(self):
        import numpy as np

        loop = self._loop()
        base = np.zeros((40, 40, 3), np.uint8)
        base[30:34, 30:34] = 200
        after = base.copy()
        after[30:34, 30:34] = 120
        loop._capture_slot_image = lambda x, y: after
        assert loop._slot_changed(base, 0, 0) is True

    def test_unchanged_not_detected(self):
        import numpy as np

        loop = self._loop()
        base = np.zeros((40, 40, 3), np.uint8)
        base[30:34, 30:34] = 200
        loop._capture_slot_image = lambda x, y: base.copy()
        assert loop._slot_changed(base, 0, 0) is False

    def test_tiny_animation_not_detected(self):
        import numpy as np

        loop = self._loop()
        base = np.zeros((40, 40, 3), np.uint8)
        base[30:34, 30:34] = 200
        anim = base.copy()
        anim[0, 1] = 15  # 1 个像素轻微变化(低于 5% 阈值)
        loop._capture_slot_image = lambda x, y: anim
        assert loop._slot_changed(base, 0, 0) is False
