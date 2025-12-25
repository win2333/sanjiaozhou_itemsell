"""键盘控制模块"""

import pydirectinput
import time
import random
from typing import List, Optional

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False
    print("[键盘控制] 警告: pyperclip 未安装，剪贴板功能不可用")


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

    def key_down(self, key: str) -> None:
        """按下键（不释放）"""
        pydirectinput.keyDown(key)

    def key_up(self, key: str) -> None:
        """释放键"""
        pydirectinput.keyUp(key)

    def combo(self, keys: List[str]) -> None:
        """组合键

        Args:
            keys: 按键列表，如 ["alt", "d"]
        """
        for key in keys:
            pydirectinput.keyDown(key)
            time.sleep(0.05)

        for key in reversed(keys):
            pydirectinput.keyUp(key)

        self._random_delay()

    def type_text(self, text: str) -> None:
        """输入文本（只输入数字，过滤其他字符）

        Args:
            text: 要输入的文本
        """
        # 过滤只保留数字（防止多余字符如小数点）
        filtered_text = ''.join(c for c in text if c.isdigit())
        pydirectinput.write(filtered_text)
        self._random_delay()

    def alt_d(self) -> None:
        """Alt + D 组合键"""
        self.combo(["alt", "d"])

    def press_enter(self) -> None:
        """按回车"""
        self.press("enter")

    def press_escape(self) -> None:
        """按 Esc"""
        self.press("esc")

    def ctrl_a(self) -> None:
        """Ctrl + A 全选"""
        self.combo(["ctrl", "a"])

    def delete(self) -> None:
        """Delete 删除"""
        self.press("delete")

    def copy_to_clipboard(self, text: str) -> bool:
        """复制文本到剪贴板

        Args:
            text: 要复制的文本

        Returns:
            是否成功
        """
        if not HAS_PYPERCLIP:
            return False
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False

    def paste(self) -> None:
        """粘贴（Ctrl+V）

        使用剪贴板输入，比逐字符输入快得多
        """
        self.combo(["ctrl", "v"])
        self._random_delay()
