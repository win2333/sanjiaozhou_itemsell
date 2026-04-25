"""键盘控制模块"""

import pydirectinput
import time
import random


class KeyboardController:
    """键盘控制器"""

    def __init__(self, min_delay: float = 0.1, max_delay: float = 0.3):
        """初始化

        Args:
            min_delay: 最小延迟（秒）
            max_delay: 最大延迟（秒）
        """
        self.min_delay = min_delay
        self.max_delay = max_delay

    def _random_delay(self) -> None:
        """随机延迟，防检测"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def press(self, key: str) -> None:
        """按下单个键

        Args:
            key: 键名
        """
        pydirectinput.press(key)
        self._random_delay()

