"""主循环模块"""

import time
import random
import cv2
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass

from vision.capture import ScreenCapture
from vision.recognizer import TemplateRecognizer, MatchResult
from vision.price_reader import PriceReader
from control.mouse import MouseController, focus_window
from control.keyboard import KeyboardController
from utils.logger import get_logger
from config import (
    TEMPLATE_MATCH_THRESHOLD,
    LOOP_DELAY,
    IDLE_DELAYS,
    PRICE_OFFSET_X,
    PRICE_OFFSET_Y,
    QUANTITY_OFFSET_X,
    QUANTITY_OFFSET_Y,
    PRICE_DIRECT_CLICK_X,
    UPLOAD2_X,
    UPLOAD2_Y,
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
from utils.status_panel import Status, render as render_panel


@dataclass
class SellState:
    """卖出状态"""

    total_sold: int  # 总共卖出的数量
    is_running: bool  # 是否正在运行
    consecutive_empty: int  # 连续未识别次数（用于空闲检测）
    idle_delay: float  # 当前空闲延迟时间（秒）
    menu_visible: bool = False  # 菜单是否正在显示（显示时停止控制台输出）

    def __init__(self):
        self.total_sold = 0
        self.is_running = False
        self.consecutive_empty = 0
        self.idle_delay = LOOP_DELAY


@dataclass
class ItemRecord:
    """物品记录"""

    name: str  # 物品名称
    x: int  # 中心 x 坐标
    y: int  # 中心 y 坐标
    width: int  # 模板宽度
    height: int  # 模板高度
    confidence: float  # 识别置信度


def _group_by_type(candidates: List[ItemCandidate]) -> List[List[ItemCandidate]]:
    """按 template_name 分组，组间按最左上角物品排序。

    Args:
        candidates: 已排序的候选列表（y 升序, x 升序）

    Returns:
        分组列表，每组内保持原排序
    """
    groups: dict = {}
    for c in candidates:
        key = c.template_name or "unknown"
        if key not in groups:
            groups[key] = []
        groups[key].append(c)

    result = list(groups.values())

    result.sort(key=lambda g: (g[0].screen_y, g[0].screen_x))
    return result


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
        self._backpack_ref = None  # 背包参考截图，用于验证UI是否仍在
        self.status = Status()  # 状态面板

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
        self.status.status = "运行中"
        self.status.round_num = 0
        self.status.current_item = ""
        self.status.current_step = ""
        self.status.yolo_count = 0
        self.status.template_count = 0
        self.status.type_groups = 0
        self.status.detect_time_ms = 0
        self.status.item_preview = []
        self.status.total_types = 0
        self.status.current_group = 0
        self.status.total_groups = 0
        self.status.round_sold = 0
        self.status.consecutive_empty = 0
        self.status.next_scan_delay = 0
        self.status.start_time = time.time()
        render_panel(self.status)

        try:
            while self.state.is_running:
                self._run_one_cycle_new()
                self._keep_console_topmost()
            return "menu"
        except KeyboardInterrupt:
            self.status.status = "已停止"
            self.status.stop_requested = True
            render_panel(self.status)
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
        """延迟初始化 HybridPipeline（第一次调用时初始化）

        Returns:
            HybridPipeline 实例
        """
        if self._detector is not None:
            return self._detector

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
        get_logger().log_only("[初始化]", "使用 Hybrid 检测器 (YOLO+模板)")
        return self._detector

    def _run_one_cycle_new(self) -> None:
        """Hybrid 架构一轮：检测用 pipeline，卖出用完整流程"""
        # 停止请求：优雅退出，等当前操作完成
        if self.status.stop_requested:
            self.state.is_running = False
            return
        # 菜单已显示时，直接跳过本轮所有输出
        if self.state.menu_visible:
            return
        logger = get_logger()
        self._round_counter += 1
        round_n = self._round_counter
        self.status.round_num = round_n
        self.status.status = "扫描中"
        self.status.current_step = ""
        render_panel(self.status)

        try:
            # 1. 截图（背包区域）
            from config import BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT

            capture_start = time.time()
            image = self.capture.capture_region(
                BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT
            )
            capture_ms = (time.time() - capture_start) * 1000
            roi_img = image
            roi_origin_x = BACKPACK_LEFT
            roi_origin_y = BACKPACK_TOP

            # 3. 检测 + 整理候选
            detector = self._get_detector()
            candidates, eliminated, summary = detector.process(
                roi_img, roi_origin_x, roi_origin_y
            )
            raw_detections = summary.raw_yolo_detections  # YOLO原始框（用于调试绘图）

            # 更新状态面板检测信息
            self.status.yolo_count = summary.raw_count
            self.status.template_count = summary.final_count
            self.status.detect_time_ms = int((time.time() - capture_start) * 1000)
            self.status.consecutive_empty = 0

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

            # DEBUG-01: Detection funnel log (D-01, D-02, D-03)
            from config import DEBUG_MODE

            if DEBUG_MODE:
                template_count = getattr(summary, "template_match_count", 0)
                funnel_str = f"YOLO:{summary.raw_count} → Template:{template_count} → IconFilter:{summary.filtered_count} → Dedup:{summary.dedup_count} → Final:{summary.final_count}"
                logger.log_only("[识别]", funnel_str)

                # DEBUG-02: Stage timing log (D-04, D-05, D-06)
                timing_str = f"[耗时] capture={capture_ms:.0f}ms"
                logger.log_only("[识别]", timing_str)

            # 5b. 更新状态面板识别信息
            if candidates:
                names = list(dict.fromkeys(c.template_name for c in candidates))
                self.status.item_preview = names[:5]
                self.status.total_types = len(names)
                logger.log_only(
                    "[清单]", f"待出售: " + " | ".join(f"{c.template_name}({c.confidence:.2f})" for c in candidates)
                )
            else:
                self.status.item_preview = []
                self.status.total_types = 0
                logger.log_only("[清单]", f"待出售: 无")

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
                all_template_matches=candidates,  # Show ALL boxes with template names
            )

            if not candidates:
                # 空闲检测：递增连续未识别次数
                self.state.consecutive_empty += 1
                delay_idx = min(self.state.consecutive_empty - 1, len(IDLE_DELAYS) - 1)
                self.state.idle_delay = IDLE_DELAYS[delay_idx]
                self.status.status = "等待物品中"
                self.status.consecutive_empty = self.state.consecutive_empty
                self.status.next_scan_delay = self.state.idle_delay
                self.status.current_item = ""
                self.status.current_step = ""
                self.status.item_preview = []
                self.status.total_types = 0
                self.status.add_event(
                    f"未识别到物品，连续{self.state.consecutive_empty}次"
                )
                render_panel(self.status)
                logger.log_only(
                    "[识别]",
                    f"未识别到物品 (连续{self.state.consecutive_empty}次, 延迟{self.state.idle_delay:.1f}s)",
                )
                # 可中断的睡眠
                elapsed = 0.0
                while elapsed < self.state.idle_delay and not self.state.menu_visible:
                    time.sleep(0.1)
                    elapsed += 0.1
                return

            # 捕获背包参考截图（用于验证后续UI是否仍在）
            self._update_backpack_ref()

            # 8. 按类型分组，批量处理所有组
            self.state.consecutive_empty = 0
            self.state.idle_delay = LOOP_DELAY
            self.status.next_scan_delay = 0

            groups = _group_by_type(candidates)
            total_groups = len(groups)
            groups_sold = 0
            self.status.type_groups = total_groups
            self.status.total_groups = total_groups
            self.status.status = "批量处理中"

            logger.log_only(
                "[操作]",
                f"类型分组: {total_groups}组, 开始批量处理",
            )

            # 激活游戏窗口（确保点击生效）
            focus_window("三角洲行动")

            for idx, group in enumerate(groups, 1):
                # 检查停止请求
                if self.status.stop_requested or self.state.menu_visible:
                    logger.log_only("[操作]", "停止请求，中断当前批处理")
                    self.status.add_event("停止请求，中断批处理")
                    break

                target = group[0]
                self.status.current_group = idx
                self.status.current_item = target.template_name or "unknown"
                self.status.current_step = "1/4 移动到物品"
                self.status.round_sold = groups_sold

                logger.log_only(
                    "[操作]",
                    f"处理第{idx}/{total_groups}组: {target.template_name} ({target.click_x}, {target.click_y})",
                )

                record = ItemRecord(
                    name=target.template_name,
                    x=target.click_x,
                    y=target.click_y,
                    width=target.screen_w,
                    height=target.screen_h,
                    confidence=target.confidence,
                )
                ok = self._sell_item_with_log(record)
                if ok:
                    groups_sold += 1
                    self.status.round_sold = groups_sold
                else:
                    logger.log_only("[操作]", f"第{idx}组卖出失败，中断当前批处理")
                    self.status.add_event(f"第{idx}组失败，中断批处理")
                    break

            self.status.total_sold = self.state.total_sold
            self.status.status = "批量完成"
            render_panel(self.status)

            # 循环间隔
            time.sleep(LOOP_DELAY)
        except Exception as e:
            logger.error(f"[轮次 {round_n}] 循环异常: {type(e).__name__}: {e}")
            time.sleep(LOOP_DELAY)

    def _sell_item_with_log(self, record: ItemRecord) -> bool:
        """卖出单个物品（9步流程）。

        Args:
            record: 物品记录
        """
        logger = get_logger()
        item_name = record.name
        x = record.x
        y = record.y
        sell_start = time.time()

        try:

            # ========== 步骤 1: 鼠标移动到目标位置 ==========
            logger.step(f"[{item_name}] [1/4] 鼠标移动到 ({x}, {y})")
            self.status.current_step = "1/4 移动到物品"
            render_panel(self.status)
            self.mouse.move_to(x, y)
            time.sleep(random.uniform(0.1, 0.15))

            # ========== 检查背包页面是否还在 ==========
            if not self._is_backpack_visible():
                logger.log_only("[操作]", f"[{item_name}] 背包页面已关闭，中断批处理")
                self.status.add_event(f"跳过 {item_name} (背包关闭)")
                self.status.current_step = ""
                self.status.current_item = ""
                render_panel(self.status)
                return False

            # ========== 检查是否为空格子 ==========
            _empty = self._is_empty_slot(x, y)
            logger.step(f"[{item_name}] 空格子: {_empty}")
            if _empty:
                logger.log_only("[操作]", f"[{item_name}] 空白格子，跳过")
                self.status.add_event(f"跳过 {item_name} (空格子)")
                self.status.current_step = ""
                self.status.current_item = ""
                render_panel(self.status)
                return False

            # ========== 左键点击（自动弹出上架界面）==========
            self.mouse.click()
            time.sleep(random.uniform(0.05, 0.1))

            upload2_x = UPLOAD2_X
            upload2_y = UPLOAD2_Y

            # ========== 步骤 2: 点击数量按钮 ×3 ==========
            self.status.current_step = "2/4 设置数量"
            render_panel(self.status)
            quantity_x = upload2_x + QUANTITY_OFFSET_X
            quantity_y = upload2_y + QUANTITY_OFFSET_Y
            for i in range(3):
                self.mouse.click(quantity_x, quantity_y)
                time.sleep(random.uniform(0.05, 0.1))
            logger.step(f"[{item_name}] [2/4] 点击数量按钮 3次 ({quantity_x}, {quantity_y})")
            time.sleep(random.uniform(0.1, 0.2))

            # ========== 步骤 3: 输入价格 ==========
            self.status.current_step = "3/4 设置价格"
            render_panel(self.status)
            price_input_x = upload2_x + PRICE_OFFSET_X
            price_input_y = upload2_y + PRICE_OFFSET_Y

            self.mouse.click(price_input_x, price_input_y)
            time.sleep(0.1)
            self.keyboard.press("backspace")
            time.sleep(0.1)
            self.mouse.click(PRICE_DIRECT_CLICK_X, price_input_y)
            logger.step(f"[{item_name}] [3/4] 输入价格: 退格后点击{PRICE_DIRECT_CLICK_X}坐标")
            time.sleep(random.uniform(0.1, 0.2))

            # ========== 步骤 4: 点击 upload2 确认 ==========
            self.status.current_step = "4/4 确认上架"
            render_panel(self.status)
            self.mouse.click(upload2_x, upload2_y)
            logger.step(f"[{item_name}] [4/4] 点击 upload2 确认 ({upload2_x}, {upload2_y})")

            # 成功完成
            sell_time = time.time() - sell_start
            self.state.total_sold += 1
            self.status.total_sold = self.state.total_sold
            self.status.add_event(f"成功卖出 {item_name}，用时 {sell_time:.1f}s")
            logger.log_only("[统计]", f"卖出 {item_name} (耗时 {sell_time:.1f}s)")
            return True
        except Exception as e:
            logger.error(f"[{item_name}] 出售异常: {type(e).__name__}: {e}")
            self.status.add_event(f"异常: {item_name}")
            self.status.current_step = ""
            self.status.current_item = ""
            render_panel(self.status)
            return False

    def _update_backpack_ref(self) -> None:
        """从参考区域 (1180,150)-(1200,170) 采集 10 个锚点像素

        取背包左边框区域（不会因物品变化而改变），用于验证背包UI是否仍在。

        注意：(1180,150)-(1350,170) 的右半部分在背包格子内，
        物品卖出后像素会变，因此只取左半 (1180,150)-(1200,170)。
        """
        # 5 列 × 2 行，均匀分布在 20×20 的边框区域内
        coords = [
            (1180 + 2 + col * 4, 150 + 5 + row * 10)
            for col in range(5) for row in range(2)
        ]
        colors = self._peek_pixels(coords)
        ref_pixels = [
            (coord, color) for coord, color in zip(coords, colors) if color is not None
        ]
        self._backpack_ref = ref_pixels
        if ref_pixels:
            logger = get_logger()
            logger.log_only(
                "[识别]", f"背包锚点: 采集 {len(ref_pixels)}/10 个像素"
            )

    def _is_backpack_visible(self) -> bool:
        """重新读取 10 个像素，与保存的锚点对比

        Returns:
            True 表示背包UI仍在，False 表示可能已关闭
        """
        if not self._backpack_ref:
            return True  # 无参考时放行
        coords = [pxy for (pxy, _) in self._backpack_ref]
        colors = self._peek_pixels(coords)
        mismatches = 0
        for ref_color, current in zip(
            [c for _, c in self._backpack_ref], colors
        ):
            if current is None:
                continue
            # RGB 各通道偏差在 30 以内视为一致
            if not all(abs(current[i] - ref_color[i]) < 30 for i in range(3)):
                mismatches += 1
        # 超过 3 个像素不一致则判定背包已关闭
        return mismatches <= 3

    @staticmethod
    def _peek_pixels(coords: List[Tuple[int, int]]) -> List[Optional[Tuple[int, int, int]]]:
        """用 Win32 API 批量读取屏幕像素 RGB 值（共享 DC，减少开销）

        Args:
            coords: (x, y) 坐标列表

        Returns:
            (r, g, b) 元组列表，失败的条目为 None
        """
        import win32gui
        import win32api
        try:
            hdc = win32gui.GetDC(None)
            results: List[Optional[Tuple[int, int, int]]] = []
            for x, y in coords:
                try:
                    color = win32api.GetPixel(hdc, x, y)
                    r = color & 0xFF
                    g = (color >> 8) & 0xFF
                    b = (color >> 16) & 0xFF
                    results.append((r, g, b))
                except Exception:
                    results.append(None)
            win32gui.ReleaseDC(None, hdc)
            return results
        except Exception:
            return [None] * len(coords)

    @staticmethod
    def _peek_pixel(x: int, y: int) -> Optional[Tuple[int, int, int]]:
        """用 Win32 API 读取屏幕上一个像素的 RGB 值"""
        return AutoSellLoop._peek_pixels([(x, y)])[0]

    @staticmethod
    def _keep_console_topmost() -> None:
        """恢复控制台窗口为置顶状态（每轮调用一次，约 0.1ms）"""
        try:
            import ctypes
            ctypes.windll.user32.SetWindowPos(
                ctypes.windll.kernel32.GetConsoleWindow(),
                -1,  # HWND_TOPMOST
                0, 0, 0, 0,
                0x0001 | 0x0002,  # SWP_NOSIZE | SWP_NOMOVE
            )
        except Exception:
            pass

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
                b, g, r = (
                    int(region[dy, dx, 0]),
                    int(region[dy, dx, 1]),
                    int(region[dy, dx, 2]),
                )
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
        get_logger().log_only(
            "[检测]",
            f"空白格子 ({x}, {y}) - RGB均值:({avg_r},{avg_g},{avg_b}), 范围:R[{min_r},{max_r}] G[{min_g},{max_g}] B[{min_b},{max_b}]",
        )
        return True

    def _capture_region_by_coords(
        self, x1: int, y1: int, x2: int, y2: int
    ) -> Optional[np.ndarray]:
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
        left_space = anchor_x
        right_space = w - anchor_x
        top_space = anchor_y
        bottom_space = h - anchor_y

        # 溢出量：超过屏幕边界的部分
        overflow_left = max(0, half_w - left_space)
        overflow_right = max(0, half_w - right_space)
        overflow_top = max(0, half_h - top_space)
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
