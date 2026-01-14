"""简洁菜单 - 显示统计，按 F8/F9 退出"""

from pathlib import Path
from typing import Callable


class SimpleMenu:
    """简洁菜单系统"""

    def __init__(self, get_stats_func: Callable, get_logs_dir_func: Callable):
        """初始化

        Args:
            get_stats_func: 获取统计信息的函数
            get_logs_dir_func: 获取日志目录的函数
        """
        self.get_stats = get_stats_func
        self.get_logs_dir = get_logs_dir_func

    def show(self) -> str:
        """显示统计信息

        Returns:
            操作指令: "restart", "exit"
        """
        self._print_stats()
        return "wait"  # 等待 F8/F9

    def _format_duration(self, seconds: float) -> str:
        """格式化运行时间"""
        if seconds >= 3600:
            return f"{seconds/3600:.1f} 小时"
        elif seconds >= 60:
            return f"{seconds/60:.1f} 分钟"
        else:
            return f"{seconds:.1f} 秒"

    def _print_stats(self) -> None:
        """打印统计信息"""
        stats = self.get_stats()
        total_sold = stats.get('total_sold', 0)
        duration = stats.get('duration', 0)
        avg_time = stats.get('avg_time', 0)

        print("\n" + "=" * 40)
        print("             统计")
        print("=" * 40)
        print(f"  总共卖出:    {total_sold} 个")
        print(f"  运行时间:    {self._format_duration(duration)}")
        print(f"  平均速度:    {avg_time:.1f} 秒/个")
        print("=" * 40)
        print()
        print("  [F8] 重新开始   [Ctrl+C] 退出程序")
        print()
