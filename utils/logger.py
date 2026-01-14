"""日志工具类 - 详细日志输出到控制台和文件"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    """日志记录器"""

    def __init__(self, log_dir: str = "logs"):
        """初始化

        Args:
            log_dir: 日志目录
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # 生成日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"selling_{timestamp}.txt"

        # 文件缓冲区
        self._buffer: list[str] = []
        self._flush_interval = 2.0  # 2秒刷新一次
        self._last_flush = time.time()

    def _write(self, text: str) -> None:
        """写入日志（控制台 + 文件）

        Args:
            text: 日志内容
        """
        # 控制台输出
        print(text)

        # 文件缓冲
        self._buffer.append(text)

        # 定期刷新
        now = time.time()
        if now - self._last_flush > self._flush_interval:
            self._flush()

    def _flush(self) -> None:
        """刷新缓冲区到文件"""
        if self._buffer:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write('\n'.join(self._buffer) + '\n')
            self._buffer.clear()
            self._last_flush = time.time()

    def close(self) -> None:
        """关闭日志，刷新所有缓冲区"""
        self._flush()

    # ========== 通用日志方法 ==========

    def log(self, prefix: str, message: str) -> None:
        """通用日志

        Args:
            prefix: 日志前缀（如 [识别]）
            message: 日志内容
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write(f"[{timestamp}] {prefix} {message}")

    def separator(self) -> None:
        """分隔线"""
        self._write("━" * 60)

    def stats(self, message: str) -> None:
        """统计信息"""
        self._write(f"[统计] {message}")

    # ========== 便捷方法 ==========

    def system(self, message: str) -> None:
        """系统状态"""
        self.log("[系统]", message)

    def recognize(self, message: str) -> None:
        """视觉识别"""
        self.log("[识别]", message)

    def verify(self, message: str) -> None:
        """验证结果"""
        self.log("[验证]", message)

    def operation(self, message: str) -> None:
        """鼠标/键盘操作"""
        self.log("[操作]", message)

    def calculate(self, message: str) -> None:
        """价格计算"""
        self.log("[计算]", message)

    def complete(self, message: str) -> None:
        """卖出完成"""
        self.log("[完成]", message)

    def warning(self, message: str) -> None:
        """警告"""
        self.log("[警告]", message)

    def error(self, message: str) -> None:
        """错误"""
        self.log("[错误]", message)

    def print_only(self, message: str) -> None:
        """只输出到控制台，不写入文件"""
        print(message)

    def log_only(self, prefix: str, message: str) -> None:
        """只写入日志文件，不输出到控制台

        Args:
            prefix: 日志前缀（如 [操作]）
            message: 日志内容
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._buffer.append(f"[{timestamp}] {prefix} {message}")
        self._flush()


# 全局日志实例
_logger: Optional[Logger] = None


def get_logger() -> Logger:
    """获取全局日志实例"""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def close_logger() -> None:
    """关闭全局日志"""
    global _logger
    if _logger is not None:
        _logger.close()
        _logger = None
