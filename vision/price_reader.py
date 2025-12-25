"""价格识别模块 - OCR识别价格并计算最优价格"""

import re
import math
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict

# 全局 OCR 实例（单例）
_ocr_reader = None


def get_ocr_reader():
    """获取 OCR 读者（延迟初始化，单例模式）"""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
            print("[PriceReader] OCR 初始化成功")
        except Exception as e:
            print(f"[PriceReader] OCR 初始化失败: {e}")
            _ocr_reader = False  # 标记初始化失败，避免重复尝试
    return _ocr_reader if _ocr_reader else None


class PriceReader:
    """价格识别器"""

    def __init__(self):
        self.reader = None  # 不再自动初始化

    def read_prices(self, image: np.ndarray) -> List[Tuple[int, int, int]]:
        """读取价格区域内的所有价格数字

        Args:
            image: 屏幕截图

        Returns:
            [(价格值, x, y), ...] 按价格从小到大排序
        """
        reader = get_ocr_reader()
        if reader is None:
            print("[PriceReader] OCR 未初始化")
            return []

        # 价格区域（5个价格显示的位置）
        # 坐标：左上 (440, 734)，右下 (1050, 770)
        price_region = image[734:770, 440:1050]

        # 保存原始区域用于调试
        cv2.imwrite("debug_price_region.png", price_region)

        # 图片预处理：转灰度
        gray = cv2.cvtColor(price_region, cv2.COLOR_BGR2GRAY)

        # 保存预处理后的图片用于调试
        cv2.imwrite("debug_price_gray.png", gray)

        # OCR 识别（使用灰度图）
        try:
            results = reader.readtext(gray, detail=1)
        except Exception as e:
            print(f"[PriceReader] OCR 识别失败: {e}")
            return []

        # print(f"[PriceReader] OCR 原始结果: {[(bbox, text, conf) for bbox, text, conf in results]}")

        prices = []
        for bbox, text, confidence in results:
            # 提取数字（格式如 "15.922" 或 "15922"）
            # 先移除空格和逗号
            clean_text = text.replace(' ', '').replace(',', '')

            # 处理小数点格式（如 "15.922" -> "15922"）
            clean_text = clean_text.replace('.', '')

            # 验证是否是纯数字
            if clean_text.isdigit():
                try:
                    price_value = int(clean_text)
                    # 过滤掉太小的值（可能是误识别）
                    if price_value < 100:
                        print(f"[PriceReader] 忽略过小值: {price_value}")
                        continue
                    # 计算在原图中的位置
                    x = int(bbox[0][0]) + 440
                    y = int(bbox[0][1]) + 734
                    prices.append((price_value, x, y))
                    print(f"[PriceReader] 识别到价格: {price_value} (置信度: {confidence:.2f})")
                except ValueError:
                    pass

        # 按价格排序（从小到大）
        prices.sort(key=lambda p: p[0])
        return prices

    def get_p1_p2(self, image: np.ndarray) -> Tuple[Optional[int], Optional[int]]:
        """获取 P1 和 P2（最低价和第二低价）

        Args:
            image: 屏幕截图

        Returns:
            (P1价格, P2价格)，识别失败返回 (None, None)
        """
        prices = self.read_prices(image)

        if len(prices) >= 2:
            p1 = prices[0][0]  # 最低价
            p2 = prices[1][0]  # 第二低价
            return p1, p2
        elif len(prices) == 1:
            return prices[0][0], None
        else:
            return None, None


def calculate_optimal_price(p1: int, p2: int) -> int:
    """对称减法算法 - 计算最优价格

    核心逻辑：
    1. 计算步长 = P2 - P1（图表上一格代表多少钱）
    2. 分界线 = P1 - 步长（低于这个价格会显示在左侧空白区间）
    3. 安全下沉 = 分界线 - 10（防止卡在边界上）
    4. 取整到10

    Args:
        p1: 第一根柱子（最低价）
        p2: 第二根柱子下方的数字

    Returns:
        计算出的最优价格
    """
    # 计算步长
    step = p2 - p1

    # 计算分界线
    boundary = p1 - step

    # 安全下沉
    safe_price = boundary - 10

    # 抹零取整到10
    final_price = math.floor(safe_price / 10) * 10

    return final_price


def calculate_price_with_fallback(p1: int, p2: Optional[int] = None) -> int:
    """计算价格（带回退逻辑）

    Args:
        p1: 第一根柱子的价格
        p2: 第二根柱子的价格（可选）

    Returns:
        计算出的价格
    """
    if p2 is not None and p2 > p1:
        # 正常情况：使用对称减法算法
        price = calculate_optimal_price(p1, p2)
        print(f"  [价格计算] P1={p1}, P2={p2}, 步长={p2-p1}, 结果={price}")
        return price
    else:
        # 异常情况：只有一根柱子，回退到 95% 定价
        fallback_price = int(p1 * 0.95)
        fallback_price = math.floor(fallback_price / 10) * 10
        print(f"  [价格计算] 只有一根柱子，回退到 P1*0.95 = {fallback_price}")
        return fallback_price


def test_price_reader():
    """测试价格识别"""
    import sys
    sys.path.insert(0, '.')
    from vision.capture import ScreenCapture

    print("=" * 50)
    print("价格识别测试")
    print("=" * 50)

    capture = ScreenCapture()
    reader = PriceReader()

    print("\n按 Enter 截图并识别价格...")
    input()

    image = capture.capture_full_screen()

    # 获取 P1, P2
    p1, p2 = reader.get_p1_p2(image)

    if p1 is not None:
        print(f"\nP1 (最低价): {p1}")
        print(f"P2 (第二低价): {p2}")

        # 计算最优价格
        price = calculate_price_with_fallback(p1, p2)
        print(f"\n建议售价: {price}")
    else:
        print("未能识别到价格")


if __name__ == "__main__":
    test_price_reader()

