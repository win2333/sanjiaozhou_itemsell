"""配置文件 - 可根据需要调整参数"""

import math
from pathlib import Path
from typing import Optional

# 项目根目录
BASE_DIR = Path(__file__).parent

# 模板图片目录
TEMPLATES_DIR = BASE_DIR / "templates"
UI_TEMPLATES_DIR = BASE_DIR / "templates" / "ui"  # UI元素模板目录

# Debug 图片目录
DEBUG_DIR = BASE_DIR / "debug"

# 模板匹配参数
TEMPLATE_MATCH_THRESHOLD = 0.95  # 匹配阈值 (0-1)，从严调整以提升精度
COLOR_MATCH_THRESHOLD = 0.95  # 颜色验证阈值 (0-1)，调整以过滤误匹配
UI_TEMPLATE_THRESHOLD = 0.75  # UI元素匹配阈值，降低以提升鲁棒性
DEDUP_DISTANCE = 30  # 去重距离（像素），小于此距离的框视为同一物品

# ── YOLO 改造配置 ────────────────────────────────────────────────────────────
# 运行模式
ITEM_DETECTOR_MODE = "hybrid"  # "template" | "yolo" | "hybrid"
RUN_MODE: str = "live"  # "observe" | "live"

# YOLO 专用
YOLO_MODEL_PATH: str = "models/item_detector.pt"
YOLO_CONFIDENCE_THRESHOLD: float = 0.90
YOLO_IOU_THRESHOLD: float = 0.45

# Hybrid 专用
HYBRID_MAX_WORKERS: int = 8  # 模板匹配线程数

# 候选整理
ICON_FILTER_THRESHOLD: float = 0.8
ICON_TEMPLATE_PATH: str = str(BASE_DIR / "templates" / "icon_01.png")  # 不能卖图标模板
DEDUP_DISTANCE_PX: int = 20

# 调试输出
SAVE_DEBUG_IMAGES: bool = False
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 运行模式配置
# ─────────────────────────────────────────────────────────────────────────────
# DEBUG_MODE: True=全部日志输出到控制台+文件（含步骤详情）
#             False=全部写文件，控制台仅显示：标题/待出售/正在出售/已出售/跳过/本轮统计/冷却中
DEBUG_MODE = False

# 主循环间隔（秒）
LOOP_DELAY = 0.1

# 空闲延迟阶梯（连续识别失败时递增）
IDLE_DELAYS = [0.1, 0.5, 1.0, 3.0, 5.0, 10.0, 15.0]  # 递增延迟列表，最后一级一直用

# 性能优化配置
USE_FIXED_COORDINATES = True  # 使用固定坐标代替图像识别（更快）
USE_CLIPBOARD_INPUT = True  # 使用剪贴板输入价格（更快）
USE_GPU_TEMPLATE_RECOGNITION = False  # 全部用 CPU

# 固定 UI 坐标（无需识别，直接点击）
# 这些坐标在游戏窗口位置固定，可大幅提升性能
UPLOAD1_X = 1403  # 第一次上架按钮
UPLOAD1_Y = 700

# 背包区域截图坐标（绝对屏幕坐标，用于主循环截图）
BACKPACK_LEFT = 1200
BACKPACK_TOP = 0
BACKPACK_WIDTH = 720  # 1920 - 1200
BACKPACK_HEIGHT = 1080

UPLOAD2_X = 1311  # 第二次上架按钮（确认）
UPLOAD2_Y = 749

# 价格输入框相对于 upload2 中心的偏移量
PRICE_OFFSET_X = 1
PRICE_OFFSET_Y = -104

# 价格输入方式
USE_NEW_PRICE_METHOD = True  # True: 退格后点击860 | False: Ctrl+A复制粘贴
PRICE_DIRECT_CLICK_X = 860  # 新方式中点击的X坐标

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


# 启动时打印阈值配置
if __name__ != "__main__":
    import sys

    print(
        f"[初始化] 阈值配置: TEMPLATE_MATCH_THRESHOLD={TEMPLATE_MATCH_THRESHOLD}, COLOR_MATCH_THRESHOLD={COLOR_MATCH_THRESHOLD}",
        file=sys.stderr,
    )
