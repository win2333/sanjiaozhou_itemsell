"""物品检测相关数据类型定义"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawItemDetection:
    """原始检测结果（局部坐标，不含业务判断）

    由第一段检测器输出，坐标为 ROI 局部坐标。
    """

    x: int  # ROI 局部左上角 x
    y: int  # ROI 局部左上角 y
    w: int  # 宽度
    h: int  # 高度
    confidence: float  # 置信度 (0-1)
    source: str  # "yolo" | "template"
    template_name: Optional[str] = None  # 模板名（仅 template 模式有值）


@dataclass
class ItemCandidate:
    """整理后的物品候选（全屏坐标，已过滤去重排序）

    由第二段 pipeline 输出，坐标为全屏真实坐标。
    """

    screen_x: int  # 全屏左上角 x
    screen_y: int  # 全屏左上角 y
    screen_w: int  # 宽度
    screen_h: int  # 高度
    click_x: int  # 建议点击点 x（框中心）
    click_y: int  # 建议点击点 y（框中心）
    confidence: float  # 置信度
    rank: int  # 本轮排名（1-based）
    passed_icon_filter: bool  # 兼容字段，当前固定为 True
    keep_reason: str  # 保留原因，如 "normal"
    template_name: Optional[str] = None  # 物品模板名称


@dataclass
class EliminatedCandidate:
    """被淘汰的候选（用于调试和日志）"""

    screen_x: int  # 全屏左上角 x
    screen_y: int  # 全屏左上角 y
    reason: str  # "dedup" | "other"
    template_name: Optional[str] = None  # 匹配的模板名称


@dataclass
class RoundSummary:
    """单轮处理摘要（第三段回填 verification_passed 和 action_taken）"""

    raw_count: int  # 原始检测框数量
    filtered_count: int  # 预留过滤淘汰数量，当前主流程为 0
    dedup_count: int  # 去重淘汰数量
    final_count: int = 0  # 最终候选数量
    template_match_count: int = 0  # 模板匹配成功数量（在去重之前）
    first_candidate: Optional[ItemCandidate] = None  # 第一名候选
    verification_passed: Optional[bool] = None  # 第三段回填
    action_taken: bool = False  # 第三段回填
    raw_yolo_detections: list = field(default_factory=list)  # YOLO 原始检测框（用于调试绘图）
