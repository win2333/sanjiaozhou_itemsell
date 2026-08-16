"""calculate_price 与 _group_by_type 单元测试（纯函数，无外部依赖）"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import calculate_price
from core.loop import _group_by_type
from vision.item_types import ItemCandidate
from vision.price_reader import PriceReader


def _cand(x: int, y: int, name: str) -> ItemCandidate:
    return ItemCandidate(
        screen_x=x,
        screen_y=y,
        screen_w=50,
        screen_h=50,
        click_x=x + 25,
        click_y=y + 25,
        confidence=0.9,
        rank=0,
        passed_icon_filter=True,
        keep_reason="test",
        template_name=name,
    )


class TestCalculatePrice:
    def test_normal_two_bars(self):
        # 步长 = 2000-1000 = 1000, 分界线 = 0, 安全价 = -10 -> 0 (取整到10)
        # 实际是 floor(-10/10)*10 = -10，负数场景由游戏 P1 足够大时不会触发
        assert calculate_price(1000, 2000) == -10

    def test_realistic_prices(self):
        # P1=50000, P2=52000: step=2000, boundary=48000, safe=47990
        assert calculate_price(50000, 52000) == 47990

    def test_fallback_single_bar(self):
        # 只有一根柱子：95% 定价取整到10
        assert calculate_price(1000) == 950
        assert calculate_price(105) == 90  # 99.75 -> floor(9.975)*10 = 90

    def test_fallback_when_p2_not_greater(self):
        # P2 <= P1 视为异常，走 95% 回退
        assert calculate_price(1000, 1000) == 950
        assert calculate_price(1000, 500) == 950

    def test_rounds_to_ten(self):
        # safe_price 非整十时向下取整: P1=101, P2=201 -> step=100, boundary=1, safe=-9 -> -10
        assert calculate_price(101, 201) == -10


class TestGroupByType:
    def test_groups_by_template_name(self):
        cands = [
            _cand(0, 100, "ak47"),
            _cand(50, 100, "m4"),
            _cand(100, 100, "ak47"),
        ]
        groups = _group_by_type(cands)
        names = [g[0].template_name for g in groups]
        # 组间按最左上角排序: ak47 组首个在 (0,100), m4 在 (50,100)
        assert names == ["ak47", "m4"]
        # ak47 组包含两个成员
        assert len(groups[0]) == 2

    def test_unknown_name_grouped_together(self):
        cands = [_cand(0, 0, None), _cand(50, 0, None)]
        groups = _group_by_type(cands)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_group_order_by_top_left(self):
        # y 更小的组排前面
        cands = [
            _cand(100, 200, "lower"),
            _cand(0, 50, "upper"),
        ]
        groups = _group_by_type(cands)
        assert [g[0].template_name for g in groups] == ["upper", "lower"]

    def test_empty_input(self):
        assert _group_by_type([]) == []


class TestHasSplitRead:
    """OCR 拆读检测: 同一数字被拆成多行时放弃定价,防止拼错价"""

    def test_split_read_detected(self):
        split = [
            ([[0, 0], [10, 0], [10, 5], [0, 5]], "18", 0.8),
            ([[1, 6], [11, 6], [11, 11], [1, 11]], "8542", 0.5),
        ]
        assert PriceReader._has_split_read(split) is True

    def test_two_normal_bars_not_flagged(self):
        normal = [
            ([[0, 0], [30, 0], [30, 8], [0, 8]], "22000", 0.9),
            ([[101, 0], [131, 0], [131, 8], [101, 8]], "24000", 0.9),
        ]
        assert PriceReader._has_split_read(normal) is False

    def test_different_x_not_flagged(self):
        diff = [
            ([[0, 0], [10, 0], [10, 5], [0, 5]], "18", 0.8),
            ([[50, 6], [80, 6], [80, 11], [50, 11]], "22000", 0.9),
        ]
        assert PriceReader._has_split_read(diff) is False

    def test_empty_results(self):
        assert PriceReader._has_split_read([]) is False
