"""配置文件 - 可根据需要调整参数"""

import math
from pathlib import Path
from typing import Optional

# 项目根目录
BASE_DIR = Path(__file__).parent

# 模板图片目录
TEMPLATES_DIR = BASE_DIR / "templates"
UI_TEMPLATES_DIR = BASE_DIR / "templates" / "ui"  # UI元素模板目录

# 模板匹配参数
TEMPLATE_MATCH_THRESHOLD = 0.98  # 匹配阈值 (0-1)，越高越严格
UI_TEMPLATE_THRESHOLD = 0.9      # UI元素匹配阈值（需要更精确）
DEDUP_DISTANCE = 30  # 去重距离（像素），小于此距离的框视为同一物品

# 主循环间隔（秒）
LOOP_DELAY = 0.1

# 性能优化配置
USE_FIXED_COORDINATES = True  # 使用固定坐标代替图像识别（更快）
USE_CLIPBOARD_INPUT = True    # 使用剪贴板输入价格（更快）

# 固定 UI 坐标（无需识别，直接点击）
# 这些坐标在游戏窗口位置固定，可大幅提升性能
UPLOAD1_X = 1403  # 第一次上架按钮
UPLOAD1_Y = 700

UPLOAD2_X = 1311  # 第二次上架按钮（确认）
UPLOAD2_Y = 749

# 价格输入框相对于 upload2 中心的偏移量
PRICE_OFFSET_X = 1
PRICE_OFFSET_Y = -104

# 数量按钮相对于 upload2 中心的偏移量
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
        step = p2 - p1          # 步长
        boundary = p1 - step    # 分界线
        safe_price = boundary - 10  # 安全下沉
        final_price = math.floor(safe_price / 10) * 10  # 取整到10
        return final_price
    else:
        # 异常情况：只有一根柱子，回退到 95% 定价
        fallback_price = int(p1 * 0.95)
        fallback_price = math.floor(fallback_price / 10) * 10
        return fallback_price
