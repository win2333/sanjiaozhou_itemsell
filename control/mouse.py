"""鼠标控制模块"""

import pydirectinput
import time
import random
from typing import Tuple, Optional


class MouseController:
    """鼠标控制器"""

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

    def move_to(self, x: int, y: int) -> None:
        """移动鼠标到指定位置

        Args:
            x: x 坐标
            y: y 坐标
        """
        pydirectinput.moveTo(x, y)
        self._random_delay()

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> None:
        """点击鼠标

        Args:
            x: x 坐标（可选）
            y: y 坐标（可选）
            button: 按钮，"left" 或 "right"
        """
        if x is not None and y is not None:
            self.move_to(x, y)

        pydirectinput.click(button=button)
        self._random_delay()

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """双击

        Args:
            x: x 坐标（可选）
            y: y 坐标（可选）
        """
        if x is not None and y is not None:
            self.move_to(x, y)

        pydirectinput.doubleClick()
        self._random_delay()

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """右键点击

        Args:
            x: x 坐标（可选）
            y: y 坐标（可选）
        """
        self.click(x, y, button="right")

    def drag(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """拖拽

        Args:
            x1: 起点 x
            y1: 起点 y
            x2: 终点 x
            y2: 终点 y
        """
        pydirectinput.moveTo(x1, y1)
        pydirectinput.mouseDown()
        pydirectinput.moveTo(x2, y2)
        pydirectinput.mouseUp()
        self._random_delay()

    def get_position(self) -> Tuple[int, int]:
        """获取鼠标当前位置

        Returns:
            (x, y) 坐标
        """
        import win32api
        x, y = win32api.GetCursorPos()
        return x, y
