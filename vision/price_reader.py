"""价格识别模块 - OCR识别价格并计算最优价格"""

import re
import math
import cv2
from config import DEBUG_DIR
import numpy as np
from typing import List, Tuple, Optional, Dict

from utils.logger import get_logger

# 全局 OCR 实例（单例）
_ocr_reader = None


def get_ocr_reader():
    """获取 OCR 读者（延迟初始化，单例模式）"""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
            get_logger().log_only("[PriceReader]", "OCR 初始化成功")
        except Exception as e:
            get_logger().log_only("[PriceReader]", f"OCR 初始化失败: {e}")
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
            get_logger().log_only("[PriceReader]", "OCR 未初始化")
            return []

        # 价格区域（5个价格显示的位置）
        # 坐标：左上 (440, 734)，右下 (1050, 770)
        if image is None or image.shape[0] < 770 or image.shape[1] < 1050:
            get_logger().log_only("[PriceReader]", "截图尺寸不足，无法裁剪价格区域")
            return []

        price_region = image[734:770, 440:1050]
        if price_region.size == 0:
            get_logger().log_only("[PriceReader]", "价格区域为空")
            return []

        # 保存原始区域用于调试
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(DEBUG_DIR / "debug_price_region.png"), price_region)

        # 图片预处理：转灰度 → 放大4倍 → 对比度归一化
        # 实测: 游戏暗色 UI 下 1x 原始灰度 OCR 基本读不出,
        # 4x 放大 + NORM_MINMAX 归一化 + 数字白名单才稳定
        gray = cv2.cvtColor(price_region, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

        # 保存预处理后的图片用于调试
        cv2.imwrite(str(DEBUG_DIR / "debug_price_gray.png"), gray)

        # OCR 识别（预处理后的图, 仅允许数字和小数点）
        try:
            results = reader.readtext(gray, detail=1, allowlist="0123456789.,")
        except Exception as e:
            get_logger().log_only("[PriceReader]", f"OCR 识别失败: {e}")
            return []

        # print(f"[PriceReader] OCR 原始结果: {[(bbox, text, conf) for bbox, text, conf in results]}")

        if self._has_split_read(results):
            get_logger().log_only(
                "[PriceReader]", "检测到拆读(同一数字分多行), 识别不可信, 放弃本轮定价"
            )
            return []

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
                        get_logger().log_only("[PriceReader]", f"忽略过小值: {price_value}")
                        continue
                    # 计算在原图中的位置
                    x = int(bbox[0][0]) + 440
                    y = int(bbox[0][1]) + 734
                    prices.append((price_value, x, y))
                    get_logger().log_only("[PriceReader]", f"识别到价格: {price_value} (置信度: {confidence:.2f})")
                except ValueError:
                    pass

        # 按价格排序（从小到大）
        prices.sort(key=lambda p: p[0])
        return prices

    @staticmethod
    def _has_split_read(results: List[Tuple[List, str, float]]) -> bool:
        """检测同一数字被 OCR 拆成多行读的情况。

        实测: 游戏暗色 UI 下一个价格可能被拆成 '18' 和 '8542' 两次读出,
        两者 x 范围重叠、y 垂直交错。此时无法可靠还原真实数字
        (拼接实测会得出 188542 这类错误值),必须放弃本次识别,
        由调用方回退到固定坐标定价,避免输错价。

        判定: 两个含数字的框 x 重叠超过较小宽度的 50%,
        且 y 范围交错或紧邻(间距小于较矮框高度)。
        不同价格柱的标签横向错开且同一行,不会触发。

        Args:
            results: EasyOCR 原始结果 [(bbox, text, conf), ...]

        Returns:
            True 表示存在拆读,本次识别不可信
        """
        parsed = []
        for bbox, text, conf in results:
            if not text or not any(ch.isdigit() for ch in text):
                continue
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            parsed.append((min(xs), max(xs), min(ys), max(ys)))

        for i in range(len(parsed)):
            for j in range(i + 1, len(parsed)):
                a, b = parsed[i], parsed[j]
                overlap = min(a[1], b[1]) - max(a[0], b[0])
                min_w = max(1, min(a[1] - a[0], b[1] - b[0]))
                if overlap <= min_w * 0.5:
                    continue
                gap = max(a[2], b[2]) - min(a[3], b[3])  # 负值=交错
                min_h = max(1, min(a[3] - a[2], b[3] - b[2]))
                if gap < min_h:
                    return True
        return False

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
        get_logger().log_only("[价格计算]", f"P1={p1}, P2={p2}, 步长={p2-p1}, 结果={price}")
        return price
    else:
        # 异常情况：只有一根柱子，回退到 95% 定价
        fallback_price = int(p1 * 0.95)
        fallback_price = math.floor(fallback_price / 10) * 10
        get_logger().log_only("[价格计算]", f"只有一根柱子，回退到 P1*0.95 = {fallback_price}")
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
