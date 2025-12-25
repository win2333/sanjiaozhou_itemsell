"""热键监听模块"""

import keyboard
import threading
from typing import Callable, Optional


class HotkeyManager:
    """热键管理器"""

    def __init__(self):
        self.running = False
        self.is_started = False
        self._start_callback: Optional[Callable[[], None]] = None
        self._stop_callback: Optional[Callable[[], None]] = None
        self._thread: Optional[threading.Thread] = None

    def register_start_stop(
        self,
        hotkey: str,
        on_start: Callable[[], None],
        on_stop: Optional[Callable[[], None]] = None,
    ) -> None:
        """注册开始/停止热键

        Args:
            hotkey: 热键，如 "f8"
            on_start: 开始时的回调
            on_stop: 停止时的回调（可选）
        """
        self._start_callback = on_start
        self._stop_callback = on_stop

        # 使用 toggle 模式
        def toggle_handler():
            self.is_started = not self.is_started
            if self.is_started:
                if self._start_callback:
                    self._start_callback()
            else:
                if self._stop_callback:
                    self._stop_callback()

        keyboard.add_hotkey(hotkey, toggle_handler)

    def start_listening(self) -> None:
        """开始监听热键（阻塞）"""
        self.running = True
        print(f"热键监听已启动，按 F8 开始/停止...")
        keyboard.wait()

    def start_non_blocking(self) -> None:
        """开始非阻塞监听"""
        self.running = True
        self._thread = threading.Thread(target=self.start_listening, daemon=True)
        self._thread.start()

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        """注册单个热键

        Args:
            hotkey: 热键，如 "f8"
            callback: 回调函数
        """
        keyboard.add_hotkey(hotkey, callback)

    def process_once(self) -> None:
        """处理一次键盘事件（非阻塞）"""
        keyboard.read_event(suppress=True)

    def stop(self) -> None:
        """停止监听"""
        self.running = False
        keyboard.unhook_all()
