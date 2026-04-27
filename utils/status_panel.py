"""实时状态面板模块"""

import sys
import threading
import time
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from typing import List

# 面板行宽
W = 56
_RENDER_LOCK = threading.RLock()


def _display_width(text: str) -> int:
    width = 0
    for ch in text:
        width += 2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1
    return width


def _fit(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if _display_width(text) <= max_width:
        return text
    ellipsis = "..."
    target = max_width - len(ellipsis)
    if target <= 0:
        return ellipsis[:max_width]

    out = []
    used = 0
    for ch in text:
        ch_width = 2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1
        if used + ch_width > target:
            break
        out.append(ch)
        used += ch_width
    return "".join(out) + ellipsis


@dataclass
class Status:
    """面板状态"""

    # 主状态
    status: str = "初始化中"
    round_num: int = 0

    # 识别
    yolo_count: int = 0
    template_count: int = 0
    type_groups: int = 0
    detect_time_ms: int = 0

    # 清单
    item_preview: List[str] = field(default_factory=list)
    total_types: int = 0

    # 当前任务
    current_group: int = 0
    total_groups: int = 0
    current_item: str = ""
    current_step: str = ""  # 格式: "2/4 设置数量"

    # 统计
    round_sold: int = 0
    total_sold: int = 0
    consecutive_empty: int = 0

    # 空闲
    next_scan_delay: float = 0.0

    # 停止
    stop_requested: bool = False

    # 最近事件（保留最近 3 条）
    recent_events: deque = field(default_factory=lambda: deque(maxlen=3))

    start_time: float = field(default_factory=time.time)

    def add_event(self, msg: str) -> None:
        t = time.strftime("%H:%M:%S")
        self.recent_events.append(f"{t}  {msg}")

    @property
    def detect_time_str(self) -> str:
        if self.detect_time_ms >= 1000:
            return f"{self.detect_time_ms / 1000:.1f}s"
        return f"{self.detect_time_ms}ms"

    @property
    def runtime_str(self) -> str:
        elapsed = int(time.time() - self.start_time)
        h, remainder = divmod(elapsed, 3600)
        m, s = divmod(remainder, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


def _row(label: str, value: str, right: str = "") -> str:
    """label  值 [右对齐]"""
    label_text = str(label)
    right_text = str(right)
    value_width = W - _display_width(label_text) - 2
    if right_text:
        value_width -= _display_width(right_text) + 1
    value_text = _fit(str(value), max(0, value_width))
    middle = f"{label_text}  {value_text}"
    if right:
        gap = W - _display_width(middle) - _display_width(right_text)
        if gap > 0:
            return f"{middle}{' ' * gap}{right_text}"
        return f"{middle} {right_text}"
    return middle


def render(status: Status) -> None:
    """清屏并绘制状态面板"""
    with _RENDER_LOCK:
        sys.stdout.write("\033[H\033[J")

        sep = "─" * W

        lines = [
            "三角洲仓库售卖脚本",
            sep,
            _row("状态", status.status),
            _row("轮次", str(status.round_num)),
            _row("运行", status.runtime_str),
            "",
        ]

        # ── 识别 ──
        mid = f"识别  {status.yolo_count}候选 -> {status.template_count}有效"
        lines.append(_row(mid, "", f"耗时: {status.detect_time_str}"))

        # ── 清单 ──
        if status.item_preview:
            preview = ", ".join(str(item) for item in status.item_preview[:3])
            rest = f" ... 共{status.total_types}种" if status.total_types > 3 else ""
            lines.append(_row("清单", f"{preview}{rest}"))
        else:
            lines.append(_row("清单", "无"))

        lines.append("")

        # ── 当前物品 ──
        if status.current_item:
            lines.append(_row("当前", status.current_item))
        else:
            lines.append(_row("当前", "无"))

        # ── 步骤 ──
        if status.current_step:
            lines.append(_row("步骤", status.current_step))
        else:
            lines.append(_row("步骤", "等待下次扫描"))

        # ── 进度 / 下次扫描 ──
        if status.next_scan_delay > 0:
            lines.append(_row("下次", f"{status.next_scan_delay:.1f}s 后"))
        elif status.total_groups > 0:
            lines.append(_row("进度", f"{status.current_group}/{status.total_groups}"))

        # ── 统计 ──
        stats = (
            f"本轮{status.round_sold} | 总计{status.total_sold}"
            f" | 连续无候选{status.consecutive_empty}"
        )
        lines.append(_row("统计", stats))

        # ── 停止 ──
        if status.stop_requested:
            lines.append(_row("停止", "已请求，当前任务完成后退出"))
        else:
            lines.append(_row("停止", "未请求"))

        lines.append("")

        lines.append("最近事件")
        for ev in status.recent_events:
            lines.append(f"  {_fit(ev, W - 2)}")

        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
