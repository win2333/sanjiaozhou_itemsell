"""屏幕截图模块"""

import mss
import mss.tools
import numpy as np
from PIL import Image
from typing import Tuple, Optional, Callable


class ScreenCapture:
    """屏幕截图管理器（线程安全）"""

    def __init__(self):
        self._sct_getter: Callable = None
        self._init_thread_local()

    def _init_thread_local(self):
        """初始化线程本地 mss 实例"""
        import threading
        self._local = threading.local()

    def _get_sct(self):
        """获取当前线程的 mss 实例"""
        if not hasattr(self._local, 'sct') or self._local.sct is None:
            self._local.sct = mss.mss()
        return self._local.sct

    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        sct = self._get_sct()
        monitor = sct.monitors[1]  # 主显示器
        return monitor["width"], monitor["height"]

    def capture_region(
        self, left: int, top: int, width: int, height: int
    ) -> np.ndarray:
        """截取指定区域

        Args:
            left: 左上角 x 坐标
            top: 左上角 y 坐标
            width: 区域宽度
            height: 区域高度

        Returns:
            numpy.ndarray 格式的图像
        """
        sct = self._get_sct()
        monitor = {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }
        screenshot = sct.grab(monitor)
        return np.array(screenshot)

    def capture_center_region(self, screen_width: int, screen_height: int) -> np.ndarray:
        """截取屏幕中心区域（约占 1/9）

        Args:
            screen_width: 屏幕宽度
            screen_height: 屏幕高度

        Returns:
            numpy.ndarray 格式的图像
        """
        # 屏幕中心 1/9 区域
        region_width = screen_width // 3
        region_height = screen_height // 3

        left = (screen_width - region_width) // 2
        top = (screen_height - region_height) // 2

        return self.capture_region(left, top, region_width, region_height)

    def capture_full_screen(self) -> np.ndarray:
        """截取全屏"""
        sct = self._get_sct()
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        return np.array(screenshot)

    def save_image(self, image: np.ndarray, path: str) -> None:
        """保存图像到文件

        Args:
            image: numpy.ndarray 格式的图像
            path: 保存路径
        """
        img = Image.fromarray(image)
        img.save(path)

    def show_image(self, image: np.ndarray, window_name: str = "debug") -> None:
        """显示图像（用于调试）

        Args:
            image: numpy.ndarray 格式的图像
            window_name: 窗口名称
        """
        # OpenCV BGR 转 RGB
        img_rgb = image[:, :, :3][:, :, ::-1]
        from PIL import ImageShow
        Image.fromarray(img_rgb).show(title=window_name)
