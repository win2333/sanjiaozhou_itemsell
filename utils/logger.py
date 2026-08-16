"""日志工具类 - 详细日志输出到控制台和文件"""

import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import DEBUG_MODE


class Logger:
    """日志记录器"""

    def __init__(self, log_dir: Optional[str] = None):
        """初始化

        Args:
            log_dir: 日志目录,缺省用环境变量 SELLING_LOG_DIR 或 "logs"
        """
        self.log_dir = Path(log_dir or os.environ.get("SELLING_LOG_DIR", "logs"))
        self.log_dir.mkdir(exist_ok=True)

        # 生成日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"selling_{timestamp}.txt"

        # 文件缓冲区
        self._buffer: list[str] = []
        self._flush_interval = 2.0  # 2秒刷新一次
        self._last_flush = time.time()

    def _write(self, text: str) -> None:
        """写入日志（DEBUG模式写文件+控制台，正式模式仅写文件）"""
        # 文件缓冲 - 始终写入
        self._buffer.append(text)

        # 控制台输出 - 仅 DEBUG 模式
        if DEBUG_MODE:
            print(text)

        # 定期刷新
        now = time.time()
        if now - self._last_flush > self._flush_interval:
            self._flush()

    def _flush(self) -> None:
        """刷新缓冲区到文件"""
        if self._buffer:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write("\n".join(self._buffer) + "\n")
            self._buffer.clear()
            self._last_flush = time.time()

    def close(self) -> None:
        """关闭日志，刷新所有缓冲区"""
        self._flush()

    # ========== 通用日志方法 ==========

    def log(self, prefix: str, message: str) -> None:
        """通用日志 - 写入文件，正式模式不输出控制台"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._buffer.append(f"[{timestamp}] {prefix} {message}")
        self._flush()

    def separator(self) -> None:
        """分隔线 - 写入文件"""
        self._buffer.append("━" * 60)
        self._flush()

    def stats(self, message: str) -> None:
        """统计信息 - 写入文件"""
        self._buffer.append(f"[统计] {message}")
        self._flush()

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

    def scan(self, message: str) -> None:
        """扫描日志 - YOLO/识别阶段输出"""
        self.log("[扫描]", message)

    def progress(self, message: str) -> None:
        """进度日志 - 写入文件，DEBUG_MODE下同时输出到控制台"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._buffer.append(f"[{timestamp}] [进度] {message}")
        self._flush()
        if DEBUG_MODE:
            print(f"[{timestamp}] {message}")

    def error(self, message: str, include_traceback: bool = False) -> None:
        """错误"""
        self.log("[错误]", message)
        if include_traceback:
            tb = traceback.format_exc()
            if tb and tb.strip() != "NoneType: None":
                self.log("[错误]", tb.rstrip())

    def print_only(self, message: str) -> None:
        """输出到控制台，并写入文件（DEBUG_MODE下控制台输出，正式模式只写文件）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._buffer.append(f"[{timestamp}] [控制台] {message}")
        self._flush()
        if DEBUG_MODE:
            print(message)

    def step(self, message: str) -> None:
        """步骤日志 - 写入文件，DEBUG模式同时输出控制台"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [步骤] {message}"
        self._buffer.append(line)
        self._flush()
        if DEBUG_MODE:
            print(line)

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
