"""主循环模块"""

import time
import random
import cv2
import numpy as np
from typing import List, Optional, Set, Dict, Tuple
from dataclasses import dataclass

from vision.capture import ScreenCapture
from vision.recognizer import TemplateRecognizer, MatchResult
from vision.price_reader import PriceReader
from control.mouse import MouseController
from control.keyboard import KeyboardController
from utils.logger import get_logger
from config import (
    TEMPLATE_MATCH_THRESHOLD,
    UI_TEMPLATE_THRESHOLD,
    DEDUP_DISTANCE,
    LOOP_DELAY,
    IDLE_DELAYS,
    calculate_price,
    PRICE_OFFSET_X,
    PRICE_OFFSET_Y,
    QUANTITY_OFFSET_X,
    QUANTITY_OFFSET_Y,
    USE_FIXED_COORDINATES,
    USE_CLIPBOARD_INPUT,
    USE_NEW_PRICE_METHOD,
    PRICE_DIRECT_CLICK_X,
    UPLOAD1_X,
    UPLOAD1_Y,
    UPLOAD2_X,
    UPLOAD2_Y,
    ITEM_DETECTOR_MODE,
    YOLO_MODEL_PATH,
    YOLO_CONFIDENCE_THRESHOLD,
    YOLO_IOU_THRESHOLD,
    ICON_FILTER_THRESHOLD,
    ICON_TEMPLATE_PATH,
    DEDUP_DISTANCE_PX,
    SAVE_DEBUG_IMAGES,
    DEBUG_DIR,
    HYBRID_MAX_WORKERS,
)
from vision.item_types import ItemCandidate, RoundSummary
from vision.item_candidate_pipeline import ItemCandidatePipeline
from utils.debug_visualizer import save_debug_frame

# 验证参数
VERIFY_MARGIN = 10  # 验证区域边距（像素）
VERIFY_MSE_THRESHOLD = 500  # MSE 阈值（基本相同的判断标准）


def compare_images_mse(img1: np.ndarray, img2: np.ndarray) -> float:
    """计算两张图片的 MSE（均方误差）

    Args:
        img1: 图片1
        img2: 图片2

    Returns:
        MSE 值，越小说明越相似
    """
    if img1.shape != img2.shape:
        # 调整大小到较小的那一个
        h = min(img1.shape[0], img2.shape[0])
        w = min(img1.shape[1], img2.shape[1])
        img1 = cv2.resize(img1, (w, h))
        img2 = cv2.resize(img2, (w, h))

    return np.mean((img1.astype(float) - img2.astype(float)) ** 2)


@dataclass
class SellState:
    """卖出状态"""

    processed_positions: Set[tuple]  # 已处理的位置集合
    total_sold: int  # 总共卖出的数量
    is_running: bool  # 是否正在运行
    consecutive_empty: int  # 连续未识别次数（用于空闲检测）
    idle_delay: float  # 当前空闲延迟时间（秒）
    menu_visible: bool = False  # 菜单是否正在显示（显示时停止控制台输出）

    def __init__(self):
        self.processed_positions = set()
        self.total_sold = 0
        self.is_running = False
        self.consecutive_empty = 0
        self.idle_delay = LOOP_DELAY


@dataclass
class ItemRecord:
    """物品记录（用于验证）"""

    name: str  # 物品名称
    x: int  # 中心 x 坐标
    y: int  # 中心 y 坐标
    width: int  # 模板宽度
    height: int  # 模板高度
    confidence: float  # 识别置信度
    snapshot: Optional[np.ndarray]  # 区域截图


class AutoSellLoop:
    """自动卖出主循环"""

    def __init__(
        self,
        item_recognizer: TemplateRecognizer,
        ui_recognizer: TemplateRecognizer,
        capture: ScreenCapture,
        mouse: MouseController,
        keyboard: KeyboardController,
        price_reader: Optional[PriceReader] = None,
    ):
        """初始化

        Args:
            item_recognizer: 物品识别器
            ui_recognizer: UI元素识别器
            capture: 屏幕截图器
            mouse: 鼠标控制器
            keyboard: 键盘控制器
            price_reader: 价格识别器（可选）
        """
        self.item_recognizer = item_recognizer
        self.ui_recognizer = ui_recognizer
        self.capture = capture
        self.mouse = mouse
        self.keyboard = keyboard
        self.price_reader = price_reader or PriceReader()
        self.state = SellState()
        self.start_time: Optional[float] = None  # 运行开始时间

        # 新架构：候选 pipeline 和轮次计数器
        # 加载 icon 模板（不能卖图标）
        icon_templates: List[np.ndarray] = []
        icon_path = ICON_TEMPLATE_PATH
        if icon_path:
            try:
                icon_img = cv2.imread(icon_path, cv2.IMREAD_COLOR)
                if icon_img is not None:
                    icon_templates.append(icon_img)
                    get_logger().log_only("[初始化]", f"已加载 icon 模板: {icon_path}")
                else:
                    get_logger().log_only(
                        "[初始化]", f"无法读取 icon 模板: {icon_path}"
                    )
            except Exception as e:
                get_logger().log_only("[初始化]", f"加载 icon 模板失败: {e}")

        self._candidate_pipeline = ItemCandidatePipeline(
            icon_filter_threshold=ICON_FILTER_THRESHOLD,
            dedup_distance_px=DEDUP_DISTANCE_PX,
            icon_templates=icon_templates,
        )
        self._round_counter: int = 0
        self._detector = None  # 延迟初始化（YOLO 模型加载较慢）

    def start(self) -> str:
        """开始自动卖出

        Returns:
            操作指令: "continue", "restart", "exit"
        """
        return self.run()

    def run(self) -> str:
        """Hybrid 循环：检测用新架构 pipeline，卖出用旧架构完整流程

        Returns:
            操作指令: "menu", "exit"
        """
        self.state = SellState()
        self.state.is_running = True
        self.start_time = time.time()
        print("自动卖出已启动！", flush=True)

        try:
            while self.state.is_running:
                self._run_one_cycle_new()
            return "menu"
        except KeyboardInterrupt:
            print("\n用户中断")
            return "exit"

    def stop(self) -> str:
        """停止自动卖出

        Returns:
            操作指令: "menu", "exit"
        """
        from utils.logger import close_logger, get_logger

        logger = get_logger()
        logger.stats(f"程序停止，共卖出 {self.state.total_sold} 个物品")
        close_logger()
        self.state.is_running = False
        self.state.menu_visible = True
        return "menu"

    def get_stats(self) -> dict:
        """获取统计信息"""
        duration = 0.0
        if self.start_time:
            duration = time.time() - self.start_time

        avg_time = 0.0
        if self.state.total_sold > 0:
            avg_time = duration / self.state.total_sold

        return {
            "total_sold": self.state.total_sold,
            "duration": duration,
            "avg_time": avg_time,
        }

    def _get_detector(self):
        """延迟初始化物品检测器（第一次调用时初始化）

        Returns:
            检测器实例（TemplateRecognizer 或 YoloItemDetector 或 HybridPipeline）
        """
        if self._detector is not None:
            return self._detector

        if ITEM_DETECTOR_MODE == "hybrid":
            from vision.yolo_item_detector import YoloItemDetector
            from vision.hybrid_pipeline import HybridPipeline

            yolo_detector = YoloItemDetector(
                model_path=YOLO_MODEL_PATH,
                confidence_threshold=YOLO_CONFIDENCE_THRESHOLD,
                iou_threshold=YOLO_IOU_THRESHOLD,
            )
            self._detector = HybridPipeline(
                yolo_detector=yolo_detector,
                template_recognizer=self.item_recognizer,
                max_workers=HYBRID_MAX_WORKERS,
            )
            get_logger().log_only("[初始化]", f"使用 Hybrid 检测器 (YOLO+模板)")
        else:
            # template 模式：复用已有的 item_recognizer
            self._detector = self.item_recognizer
            get_logger().log_only("[初始化]", "使用模板匹配检测器")

        return self._detector

    def _run_one_cycle_new(self) -> None:
        """Hybrid 架构一轮：检测用 pipeline，卖出用完整流程"""
        # 菜单已显示时，直接跳过本轮所有输出
        if self.state.menu_visible:
            return
        logger = get_logger()
        self._round_counter += 1
        round_n = self._round_counter
        print(f"开始截图识别...", flush=True)

        # 1. 截图（背包区域）
        from config import BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT
        image = self.capture.capture_region(
            BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT
        )
        roi_img = image
        roi_origin_x = BACKPACK_LEFT
        roi_origin_y = BACKPACK_TOP

        # 3. 检测 + 整理候选
        detector = self._get_detector()
        if ITEM_DETECTOR_MODE == "hybrid":
            # Hybrid模式：直接用HybridPipeline处理，返回(candidates, eliminated, summary)
            candidates, eliminated, summary = detector.process(roi_img, roi_origin_x, roi_origin_y)
            raw_detections = []  # HybridPipeline内部处理，无需传调试图
        else:
            # template模式：模板匹配 + pipeline整理
            raw_detections = detector.recognize_as_raw_detections(roi_img)

            # pipeline整理候选
            candidates, eliminated, summary = self._candidate_pipeline.process(
                raw_detections, roi_origin_x, roi_origin_y, roi_img
            )

        # 5. 输出日志摘要
        status = (
            "无候选"
            if summary.final_count == 0
            else f"第一名:({summary.first_candidate.click_x},{summary.first_candidate.click_y})"
        )
        logger.log_only(
            "[摘要]",
            f"[轮次 {round_n}] 原始:{summary.raw_count} 过滤:{summary.filtered_count} "
            f"去重:{summary.dedup_count} 保留:{summary.final_count} | {status}",
        )

        # 5b. 显示待出售物品清单（控制台 + 文件）
        if self.state.menu_visible:
            return
        if candidates:
            lines = ["待出售:"]
            for i, c in enumerate(candidates, 1):
                lines.append(f"  [{i}] {c.template_name}")
            item_text = "\n".join(lines)
            logger.log_only("[清单]", f"待出售: " + " | ".join(c.template_name for c in candidates))
            print(item_text, flush=True)
        else:
            logger.log_only("[清单]", f"待出售: 无")
            print(f"待出售: 无", flush=True)

        # 6. 保存调试图
        save_debug_frame(
            roi_img=roi_img,
            raw_detections=raw_detections,
            candidates=candidates,
            eliminated=eliminated,
            summary=summary,
            round_n=round_n,
            roi_origin_x=roi_origin_x,
            roi_origin_y=roi_origin_y,
            debug_dir=str(DEBUG_DIR),
            save=SAVE_DEBUG_IMAGES,
        )

        if not candidates:
            # 空闲检测：递增连续未识别次数
            self.state.consecutive_empty += 1
            # 根据连续失败次数选择延迟（阶梯递增）
            delay_idx = min(self.state.consecutive_empty - 1, len(IDLE_DELAYS) - 1)
            self.state.idle_delay = IDLE_DELAYS[delay_idx]
            logger.log_only(
                "[识别]",
                f"未识别到物品 (连续{self.state.consecutive_empty}次, 延迟{self.state.idle_delay:.1f}s)",
            )
            print(
                f"冷却中... ({self.state.idle_delay:.1f}s)   按 F8 暂停",
                flush=True,
            )
            # 可中断的睡眠（按 F8 显示菜单后立即退出）
            elapsed = 0.0
            while elapsed < self.state.idle_delay and not self.state.menu_visible:
                time.sleep(0.1)
                elapsed += 0.1
            # 退出前清除"冷却中..."行（用空格覆盖，回到行首）
            if self.state.menu_visible:
                print("\r" + " " * 50 + "\r", end="", flush=True)
            return

        # 8. 逐个处理候选（按 pipeline 排序）
        sold_count = 0
        skipped_names: set = set()  # 记录因验证失败而跳过的物品名

        # 7. 重置空闲检测（检测到物品后立即重置，不等循环处理完）
        self.state.consecutive_empty = 0
        self.state.idle_delay = LOOP_DELAY

        for candidate in candidates:
            if not self.state.is_running:
                break

            logger.print_only(f"正在出售: {candidate.template_name}")
            if self.state.menu_visible:
                break

            # 如果这个物品名之前已经验证失败过（同名物品已卖出），直接跳过
            if candidate.template_name in skipped_names:
                logger.log_only(
                    "[操作]",
                    f"跳过 {candidate.template_name} (同名物品已卖出)",
                )
                logger.print_only(f"跳过: {candidate.template_name} (同名物品已卖出)")
                continue

            logger.log_only(
                "[操作]",
                f"准备处理: {candidate.template_name} ({candidate.click_x}, {candidate.click_y})",
            )

            # 9. 截取候选区域快照（用于验证和卖出流程，只截取一次）
            snap_width = candidate.screen_w + VERIFY_MARGIN * 2
            snap_height = candidate.screen_h + VERIFY_MARGIN * 2
            snapshot = self._capture_region(
                candidate.click_x, candidate.click_y, snap_width, snap_height
            )

            # 10. 验证候选仍在原位（使用已捕获的快照，不重复截图）
            verified = self._verify_candidate(candidate, snapshot)
            if not verified:
                # 记录这个物品名，下次遇到同名物品直接跳过
                skipped_names.add(candidate.template_name)
                logger.log_only(
                    "[验证]",
                    f"验证失败，跳过同名物品: {candidate.template_name}",
                )
                continue  # 继续处理下一个物品，而不是 break

            # 11. 构造 ItemRecord 并执行完整卖出流程（复用已捕获的快照）
            record = ItemRecord(
                name=candidate.template_name,
                x=candidate.click_x,
                y=candidate.click_y,
                width=candidate.screen_w,
                height=candidate.screen_h,
                confidence=candidate.confidence,
                snapshot=snapshot,
            )
            self._sell_item_with_log(record, skipped_names)
            sold_count += 1
            logger.print_only(f"已出售: {record.name}")
            self.state.processed_positions.add(
                (
                    candidate.click_x // DEDUP_DISTANCE,
                    candidate.click_y // DEDUP_DISTANCE,
                )
            )

        # 11. 输出统计
        if self.state.menu_visible:
            return
        logger.print_only(f"本轮: 卖出 {sold_count}/{len(candidates)}   按 F8 暂停")
        logger.log_only(
            "[统计]",
            f"本轮: 卖出 {sold_count}/{len(candidates)}",
        )

        # 循环间隔
        time.sleep(LOOP_DELAY)

    def _verify_candidate(
        self, candidate: ItemCandidate, snapshot: Optional[np.ndarray]
    ) -> bool:
        """对候选进行最终确认（鼠标移动前验证）

        拍当前画面与 snapshot 做 MSE 对比，物品已消失则跳过。

        Args:
            candidate: 候选物品
            snapshot: 已捕获的候选区域快照

        Returns:
            True 表示确认通过，False 表示物品已变化
        """
        if snapshot is None:
            return True

        # 拍当前画面
        check_width = candidate.screen_w + VERIFY_MARGIN * 2
        check_height = candidate.screen_h + VERIFY_MARGIN * 2
        current = self._capture_region(
            candidate.click_x, candidate.click_y, check_width, check_height
        )
        if current is None:
            return True

        mse = compare_images_mse(snapshot, current)
        if mse >= VERIFY_MSE_THRESHOLD:
            return False
        return True


    def _sell_item_with_log(self, record: ItemRecord, skipped_names: set) -> None:
        """卖出单个物品（分层重试机制）。

        Args:
            record: 物品记录
            skipped_names: 因卖出失败而跳过的物品名集合，调用方传入同一集合
        """
        logger = get_logger()
        item_name = record.name
        x = record.x
        y = record.y
        sell_start = time.time()
        logger.print_only(f"正在出售: {item_name}")

        def _skip(reason: str) -> None:
            skipped_names.add(item_name)
            logger.log_only("[操作]", f"[{item_name}] {reason}，跳过")
            logger.print_only(f"跳过: {item_name} ({reason})")

        # ========== 步骤 1: 鼠标移动 ==========
        logger.step(f"[{item_name}] 鼠标移动到 ({x}, {y})")
        self.mouse.move_to(x, y)
        time.sleep(random.uniform(0.1, 0.15))

        # ========== 检查是否为空格子 ==========
        if self._is_empty_slot(x, y):
            _skip("空白格子")
            return

        # ========== 步骤 2: 按 Alt+D ==========
        self.keyboard.alt_d()
        logger.step(f"[{item_name}] 按下 Alt+D")
        time.sleep(random.uniform(0.3, 0.4))

        # ========== 步骤 3: upload1 ==========
        if USE_FIXED_COORDINATES:
            # 先验证 upload1 区域有没有绿色，没有绿色则跳过
            if not self._has_green_button(1300, 670, 1500, 720):
                _skip("upload1 区域无绿色")
                self.keyboard.press("escape")
                time.sleep(random.uniform(0.2, 0.3))
                return
            self.mouse.click(UPLOAD1_X, UPLOAD1_Y)
            logger.step(f"[{item_name}] 点击 upload1 (固定坐标: {UPLOAD1_X}, {UPLOAD1_Y})")
        else:
            upload1_result = self._find_ui_element("upload1", x, y)
            if not upload1_result:
                logger.step(f"[{item_name}] 未找到 upload1，第1次重试...")
                time.sleep(0.3)
                upload1_result = self._find_ui_element("upload1", x, y)
                if not upload1_result:
                    logger.step(f"[{item_name}] 未找到 upload1，ESC 退回，跳过")
                    self.keyboard.press("escape")
                    time.sleep(random.uniform(0.2, 0.3))
                    _skip("未找到 upload1")
                    return
            self.mouse.click(upload1_result.center_x, upload1_result.center_y)
            logger.step(
                f"[{item_name}] 点击 upload1 ({upload1_result.center_x}, {upload1_result.center_y})"
            )
            time.sleep(random.uniform(0.15, 0.2))

        # ========== 步骤 5: upload2 ==========
        if USE_FIXED_COORDINATES:
            upload2_x = UPLOAD2_X
            upload2_y = UPLOAD2_Y
        else:
            upload2_result = self._find_ui_element("upload2", x, y)
            if not upload2_result:
                logger.step(f"[{item_name}] 未找到 upload2，第1次重试...")
                time.sleep(0.3)
                upload2_result = self._find_ui_element("upload2", x, y)
                if not upload2_result:
                    logger.step(f"[{item_name}] 未找到 upload2，ESC 退回，跳过")
                    self.keyboard.press("escape")
                    time.sleep(random.uniform(0.2, 0.3))
                    _skip("未找到 upload2")
                    return
            upload2_x = upload2_result.center_x
            upload2_y = upload2_result.center_y

        # ========== 步骤 6: 点击数量按钮 ==========
        quantity_x = upload2_x + QUANTITY_OFFSET_X
        quantity_y = upload2_y + QUANTITY_OFFSET_Y
        for i in range(3):
            self.mouse.click(quantity_x, quantity_y)
            time.sleep(random.uniform(0.05, 0.1))
        logger.step(
            f"[{item_name}] 点击数量按钮 3次 ({quantity_x}, {quantity_y})"
        )
        time.sleep(random.uniform(0.1, 0.2))

        # ========== 步骤 7: 输入价格 ==========
        price_input_x = upload2_x + PRICE_OFFSET_X
        price_input_y = upload2_y + PRICE_OFFSET_Y

        self.mouse.click(price_input_x, price_input_y)
        time.sleep(0.1)
        self.keyboard.press("backspace")
        time.sleep(0.1)
        self.mouse.click(PRICE_DIRECT_CLICK_X, price_input_y)
        logger.step(
            f"[{item_name}] 输入价格: 退格后点击{PRICE_DIRECT_CLICK_X}坐标"
        )
        time.sleep(random.uniform(0.1, 0.2))

        # ========== 步骤 8: 点击 upload2 确认 ==========
        self.mouse.click(upload2_x, upload2_y)
        logger.step(
            f"[{item_name}] 点击 upload2 确认 ({upload2_x}, {upload2_y})"
        )

        # 成功完成
        sell_time = time.time() - sell_start
        self.state.total_sold += 1
        logger.log_only("[统计]", f"卖出 {item_name} (耗时 {sell_time:.1f}s)")

    def _has_green_button(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """检查指定区域是否有绿色按钮

        Args:
            x1, y1: 左上角
            x2, y2: 右下角

        Returns:
            True 表示有绿色，False 表示没有
        """
        region = self._capture_region_by_coords(x1, y1, x2, y2)
        if region is None or region.size == 0:
            return False

        # 转 HSV，检测绿色
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        # 绿色范围：H=35~85（OpenCV中），S>40，V>40
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        green_ratio = np.count_nonzero(mask) / mask.size
        return green_ratio > 0.05  # 超过 5% 像素是绿色

    def _is_empty_slot(self, x: int, y: int) -> bool:
        """检查指定坐标是否是空白格子

        取 3x3 区域的 9 个像素点，检测：
        1. 9 个格子颜色是否一致（相互间容差小）
        2. 且都接近 RGB(26, 31, 34)

        Args:
            x: 物品中心 x 坐标
            y: 物品中心 y 坐标

        Returns:
            True 表示是空白格子，False 表示有物品
        """
        # 截取 3x3 区域
        region = self._capture_region_by_coords(x - 1, y - 1, x + 2, y + 2)
        if region is None or region.size == 0:
            return False

        # 参考颜色 RGB(26, 31, 34)
        ref_r, ref_g, ref_b = 26, 31, 34

        # 收集 9 个像素的 RGB 值
        pixels = []
        for dy in range(3):
            for dx in range(3):
                b, g, r = int(region[dy, dx, 0]), int(region[dy, dx, 1]), int(region[dy, dx, 2])
                pixels.append((r, g, b))

        # 检查 9 个格子相互之间是否一致（最大差异 <= 5）
        min_r, max_r = min(p[0] for p in pixels), max(p[0] for p in pixels)
        min_g, max_g = min(p[1] for p in pixels), max(p[1] for p in pixels)
        min_b, max_b = min(p[2] for p in pixels), max(p[2] for p in pixels)
        if max_r - min_r > 5 or max_g - min_g > 5 or max_b - min_b > 5:
            # 9 个格子颜色不统一，有物品
            return False

        # 检查 9 个格子是否都接近参考颜色 RGB(26, 31, 34)
        for r, g, b in pixels:
            if abs(r - ref_r) > 5 or abs(g - ref_g) > 5 or abs(b - ref_b) > 5:
                # 有格子颜色不接近参考色，不是空格子
                return False

        # 9 个格子颜色一致且都接近 RGB(26, 31, 34)
        avg_r = sum(p[0] for p in pixels) // 9
        avg_g = sum(p[1] for p in pixels) // 9
        avg_b = sum(p[2] for p in pixels) // 9
        get_logger().log_only("[检测]", f"空白格子 ({x}, {y}) - RGB均值:({avg_r},{avg_g},{avg_b}), 范围:R[{min_r},{max_r}] G[{min_g},{max_g}] B[{min_b},{max_b}]")
        return True

    def _capture_region_by_coords(self, x1: int, y1: int, x2: int, y2: int) -> Optional[np.ndarray]:
        """按绝对坐标截取区域"""
        width = x2 - x1
        height = y2 - y1
        return self.capture.capture_region(x1, y1, width, height)

    def _find_ui_element(
        self, element_name: str, anchor_x: int, anchor_y: int
    ) -> Optional[MatchResult]:
        REGION_HALF_WIDTH = 150
        REGION_HALF_HEIGHT = 150

        # 全屏截图
        image = self.capture.capture_full_screen()
        if image is None:
            return None

        # 检查区域尺寸是否比所有模板都大
        # 如果区域太小（模板比区域还大），cv2.matchTemplate 会崩溃，直接回退到全屏匹配
        min_template_w = 0
        min_template_h = 0
        for template in self.ui_recognizer.templates.values():
            h, w = template.shape[:2]
            if h > min_template_h:
                min_template_h = h
            if w > min_template_w:
                min_template_w = w

        # 以鼠标为中心，左右上下各 150px
        h, w = image.shape[:2]
        half_w = REGION_HALF_WIDTH
        half_h = REGION_HALF_HEIGHT

        # 计算各方向到屏幕边缘的距离
        left_space   = anchor_x
        right_space  = w - anchor_x
        top_space    = anchor_y
        bottom_space = h - anchor_y

        # 溢出量：超过屏幕边界的部分
        overflow_left   = max(0, half_w - left_space)
        overflow_right  = max(0, half_w - right_space)
        overflow_top    = max(0, half_h - top_space)
        overflow_bottom = max(0, half_h - bottom_space)

        # 实际裁剪区域：溢出叠加到对侧，保持总宽度不变
        x1 = anchor_x - half_w - overflow_right
        x2 = anchor_x + half_w + overflow_left
        y1 = anchor_y - half_h - overflow_bottom
        y2 = anchor_y + half_h + overflow_top

        # 裁剪局部区域（始终为 300×300，溢出叠加到对侧）
        region = image[y1:y2, x1:x2]

        # 如果区域比最小模板还小，回退到全屏截图
        region_h, region_w = region.shape[:2]
        if min_template_h > 0 and min_template_w > 0:
            if region_h < min_template_h or region_w < min_template_w:
                results = self.ui_recognizer.recognize(image, draw_debug=False)
                for result in results:
                    if result.template_name == element_name:
                        return result
                return None

        # DEBUG: 保存局部区域截图供查看
        if SAVE_DEBUG_IMAGES:
            debug_sell_region = DEBUG_DIR / "debug_sell1_region.png"
            cv2.imwrite(str(debug_sell_region), region)

        # 在局部区域中匹配（阈值已降至 0.75）
        results = self.ui_recognizer.recognize(region, draw_debug=False)

        # 按 element_name 过滤，并将结果坐标转换为屏幕绝对坐标
        for result in results:
            if result.template_name == element_name:
                result.center_x += x1
                result.center_y += y1
                result.x += x1
                result.y += y1
                return result
        return None

    def _capture_region(
        self, center_x: int, center_y: int, width: int, height: int
    ) -> Optional[np.ndarray]:
        """截取指定区域

        Args:
            center_x: 中心 x 坐标
            center_y: 中心 y 坐标
            width: 区域宽度
            height: 区域高度

        Returns:
            区域截图，失败返回 None
        """
        # 计算左上角坐标
        x1 = center_x - width // 2
        y1 = center_y - height // 2
        x2 = x1 + width
        y2 = y1 + height

        # 全屏截图
        image = self.capture.capture_full_screen()

        # 检查边界
        if x1 < 0 or y1 < 0 or x2 > image.shape[1] or y2 > image.shape[0]:
            return None

        # 裁剪区域
        region = image[y1:y2, x1:x2]
        return region

