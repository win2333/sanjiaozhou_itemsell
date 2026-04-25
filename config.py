"""配置文件 - 可根据需要调整参数"""

import math
from pathlib import Path
from typing import Optional

# 项目根目录
BASE_DIR = Path(__file__).parent

TEMPLATES_DIR = BASE_DIR / "templates"
DEBUG_DIR = BASE_DIR / "debug"


# 模板匹配
TEMPLATE_MATCH_THRESHOLD = 0.70
COLOR_MATCH_THRESHOLD = 0.85

# YOLO
YOLO_MODEL_PATH: str = "models/item_detector.pt"
YOLO_CONFIDENCE_THRESHOLD: float = 0.90
YOLO_IOU_THRESHOLD: float = 0.45

# Hybrid 模板匹配线程数
HYBRID_MAX_WORKERS: int = 8

# 候选整理
ICON_FILTER_THRESHOLD: float = 0.8
ICON_TEMPLATE_PATH: str = ""  # 不能卖图标模板，为空则跳过
DEDUP_DISTANCE_PX: int = 20

# 调试截图
SAVE_DEBUG_IMAGES: bool = False

# 运行模式
# DEBUG_MODE: True=控制台+文件详细日志 | False=仅写文件，控制台简洁
DEBUG_MODE = False
LOOP_DELAY = 0.1
IDLE_DELAYS = [0.1, 0.5, 1.0, 3.0, 5.0, 10.0, 15.0]

# 性能优化
USE_FIXED_COORDINATES = True
USE_GPU_TEMPLATE_RECOGNITION = False

# 固定坐标（1920×1080）
BACKPACK_LEFT = 1200
BACKPACK_TOP = 100
BACKPACK_WIDTH = 650
BACKPACK_HEIGHT = 900

UPLOAD1_X = 1403
UPLOAD1_Y = 700

UPLOAD2_X = 1311
UPLOAD2_Y = 749

PRICE_DIRECT_CLICK_X = 860
PRICE_OFFSET_X = 1
PRICE_OFFSET_Y = -104
QUANTITY_OFFSET_X = 139
QUANTITY_OFFSET_Y = -189


# 价格计算函数 - 对称减法算法
def calculate_price(p1: int, p2: Optional[int] = None) -> int:
    """对称减法算法 - 计算最优价格

    核心逻辑：
    1. 计算步长 = P2 - P1（图表上一格代表多少钱）
    2. 分界线 = P1 - 步长（低于这个价格会显示在左侧空白区间）
    3. 安全下沉 = 分界线 - 10（防止卡在边界上）
    4. 取整到10

    Args:
        p1: 第一根柱子的价格（最低价）
        p2: 第二根柱子的价格（可选）

    Returns:
        计算出的最优价格
    """
    if p2 is not None and p2 > p1:
        step = p2 - p1  # 步长
        boundary = p1 - step  # 分界线
        safe_price = boundary - 10  # 安全下沉
        final_price = math.floor(safe_price / 10) * 10  # 取整到10
        return final_price
    else:
        # 异常情况：只有一根柱子，回退到 95% 定价
        fallback_price = int(p1 * 0.95)
        fallback_price = math.floor(fallback_price / 10) * 10
        return fallback_price
