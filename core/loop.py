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
    calculate_price,
    PRICE_OFFSET_X,
    PRICE_OFFSET_Y,
    QUANTITY_OFFSET_X,
    QUANTITY_OFFSET_Y,
    USE_FIXED_COORDINATES,
    USE_CLIPBOARD_INPUT,
    UPLOAD1_X,
    UPLOAD1_Y,
    UPLOAD2_X,
    UPLOAD2_Y,
)

# 预估参数
AVG_SELL_TIME = 10.0  # 每个物品预估耗时（秒）


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds >= 60:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins} 分 {secs} 秒"
    else:
        return f"{seconds:.1f}秒"


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

    def start(self) -> str:
        """开始自动卖出

        Returns:
            操作指令: "continue", "restart", "exit"
        """
        self.state = SellState()
        self.state.is_running = True
        self.start_time = time.time()
        print("自动卖出已启动！")

        try:
            while self.state.is_running:
                self._run_one_cycle()
            # 正常停止，显示菜单
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

    def _run_one_cycle(self) -> None:
        """运行一轮循环（带详细日志和验证）"""
        logger = get_logger()
        cycle_start = time.time()

        logger.separator()
        logger.system("开始识别屏幕")

        # 1. 截图（全屏）
        image = self.capture.capture_full_screen()

        # 2. 识别物品
        results = self.item_recognizer.recognize(image, draw_debug=False)

        # 3. 去重
        # 先空间去重（去除误识别），再按名称分组（同名物品只卖一次）
        results = self.item_recognizer.deduplicate(results, DEDUP_DISTANCE)
        results = self.item_recognizer.deduplicate_by_name(results)

        if not results:
            # 空闲检测：更新连续未识别次数
            self.state.consecutive_empty += 1

            # 指数退避：根据连续未识别次数调整延迟
            if self.state.consecutive_empty >= 10:
                self.state.idle_delay = 5.0  # 连续10次未识别，延迟5秒
            elif self.state.consecutive_empty >= 5:
                self.state.idle_delay = 3.0  # 连续5次未识别，延迟3秒
            else:
                self.state.idle_delay = LOOP_DELAY  # 正常延迟

            # 控制台简化
            logger.print_only(f"未识别到物品 (连续{self.state.consecutive_empty}次, 延迟{self.state.idle_delay:.1f}s)")
            # 日志完整
            logger.log_only("[识别]", f"未识别到物品 (连续{self.state.consecutive_empty}次, 延迟{self.state.idle_delay:.1f}s)")
            time.sleep(self.state.idle_delay)
            return

        # 4. 记录物品信息（包含截图）
        item_records: List[ItemRecord] = []
        for result in results:
            # 计算验证区域大小
            region_width = result.width + VERIFY_MARGIN * 2
            region_height = result.height + VERIFY_MARGIN * 2

            # 截图保存
            snapshot = self._capture_region(
                result.center_x, result.center_y, region_width, region_height
            )

            record = ItemRecord(
                name=result.template_name,
                x=result.center_x,
                y=result.center_y,
                width=result.width,
                height=result.height,
                confidence=result.confidence,
                snapshot=snapshot,
            )
            item_records.append(record)

        # 预估时间
        estimated = len(item_records) * AVG_SELL_TIME
        # 控制台简化版
        logger.print_only(f"识别到 {len(item_records)} 个物品 (预估 ~{format_time(estimated)})")

        # 日志文件记录完整版
        items_info = ", ".join(
            f"{r.name}({r.confidence:.2f})" for r in item_records[:5]
        )
        more = f" 等{len(item_records)}个" if len(item_records) > 5 else ""
        logger.log_only("[识别]", f"识别到 {len(item_records)} 个物品: {items_info}{more}")
        logger.log_only("[预估]", f"平均耗时: {AVG_SELL_TIME:.1f}秒/个 | 预估完成: ~{format_time(estimated)}")

        # 重置空闲检测计数器
        self.state.consecutive_empty = 0
        self.state.idle_delay = LOOP_DELAY

        # 5. 处理每个物品
        sold_count = 0
        for record in item_records:
            if not self.state.is_running:
                return

            # 只写入日志，不输出到控制台
            logger.log_only("[操作]", f"准备处理: {record.name} ({record.x}, {record.y})")

            # === 验证阶段 ===
            passed, mse = self._verify_item(record)

            if passed:
                # 只写入日志，不输出到控制台
                logger.log_only("[验证]", f"MSE={mse:.1f} < {VERIFY_MSE_THRESHOLD} | 验证通过")
                # 验证通过，处理物品
                self._sell_item_with_log(record)
                sold_count += 1
                self.state.processed_positions.add(
                    (record.x // DEDUP_DISTANCE, record.y // DEDUP_DISTANCE)
                )
            else:
                # 只写入日志，不输出到控制台
                logger.log_only("[验证]", f"MSE={mse:.1f} | 验证失败，仓库变了，重新识别")
                break  # 跳出循环，重新全屏识别

        # 6. 输出统计
        cycle_time = time.time() - cycle_start
        # 控制台显示简化版
        logger.print_only(f"  本轮: {sold_count}/{len(item_records)} | 耗时 {cycle_time:.1f}s")
        # 日志文件记录完整版
        logger.log_only("[统计]", f"本轮: 卖出 {sold_count}/{len(item_records)} | 耗时: {cycle_time:.1f}s")

        # 7. 延迟后继续（使用空闲检测的延迟时间）
        time.sleep(self.state.idle_delay)

    def _sell_item_with_log(self, record: ItemRecord) -> None:
        """卖出单个物品（带回退重试机制）"""
        logger = get_logger()
        item_name = record.name
        x = record.x
        y = record.y
        sell_start = time.time()

        # 重试配置
        max_retry = 5  # 最大总重试次数

        for retry_count in range(max_retry):
            try:
                # ========== 步骤 1: 鼠标移动 ==========
                logger.log_only("[操作]", f"鼠标移动到 ({x}, {y})")
                self.mouse.move_to(x, y)
                time.sleep(random.uniform(0.1, 0.15))

                # ========== 步骤 2: 右键点击 ==========
                self.mouse.right_click(x, y)
                logger.log_only("[操作]", f"右键点击 ({x}, {y})")
                time.sleep(random.uniform(0.15, 0.2))

                # ========== 步骤 3: 识别 sell1 ==========
                sell1_result = self._find_ui_element("sell1")
                if not sell1_result:
                    logger.log_only("[警告]", f"第{retry_count+1}次: 未找到 sell1，回退重试...")
                    continue
                self.mouse.click(sell1_result.center_x, sell1_result.center_y)
                logger.log_only("[操作]", f"点击 sell1 ({sell1_result.center_x}, {sell1_result.center_y})")
                time.sleep(random.uniform(0.3, 0.4))

                # ========== 步骤 4: 识别 upload1 ==========
                if USE_FIXED_COORDINATES:
                    # 使用固定坐标
                    self.mouse.click(UPLOAD1_X, UPLOAD1_Y)
                    logger.log_only("[操作]", f"点击 upload1 (固定: {UPLOAD1_X}, {UPLOAD1_Y})")
                    upload2_x = UPLOAD2_X
                    upload2_y = UPLOAD2_Y
                else:
                    upload1_result = self._find_ui_element("upload1")
                    if not upload1_result:
                        logger.log_only("[警告]", f"第{retry_count+1}次: 未找到 upload1，回退重试...")
                        continue
                    self.mouse.click(upload1_result.center_x, upload1_result.center_y)
                    logger.log_only("[操作]", f"点击 upload1 ({upload1_result.center_x}, {upload1_result.center_y})")
                    time.sleep(random.uniform(0.15, 0.2))

                    # ========== 步骤 5: 识别 upload2 ==========
                    upload2_result = self._find_ui_element("upload2")
                    if not upload2_result:
                        logger.log_only("[警告]", f"第{retry_count+1}次: 未找到 upload2，重试 upload1...")
                        # 只回退到 upload1，不重新点击 sell1
                        time.sleep(0.2)
                        continue  # 继续重试，upload1_result 重新识别
                    upload2_x = upload2_result.center_x
                    upload2_y = upload2_result.center_y

                # ========== 步骤 6: 点击数量按钮 ==========
                quantity_x = upload2_x + QUANTITY_OFFSET_X
                quantity_y = upload2_y + QUANTITY_OFFSET_Y
                for i in range(3):
                    self.mouse.click(quantity_x, quantity_y)
                    time.sleep(random.uniform(0.05, 0.1))
                logger.log_only("[操作]", f"点击数量按钮 3次 ({quantity_x}, {quantity_y})")
                time.sleep(random.uniform(0.1, 0.2))

                # ========== 步骤 7: 识别价格并计算 ==========
                price_input_x = upload2_x + PRICE_OFFSET_X
                price_input_y = upload2_y + PRICE_OFFSET_Y

                screenshot = self.capture.capture_full_screen()
                p1, p2 = self.price_reader.get_p1_p2(screenshot)

                if p1 is None:
                    logger.log_only("[警告]", f"第{retry_count+1}次: 未识别到价格，回退重试...")
                    continue

                calculated_price = calculate_price(p1, p2)
                if calculated_price <= 0:
                    logger.log_only("[警告]", f"第{retry_count+1}次: 价格计算异常 ({calculated_price})，回退重试...")
                    continue

                logger.log_only("[计算]", f"P1={p1}, P2={p2}, 售价={calculated_price}")

                # ========== 步骤 8: 输入价格 ==========
                self.mouse.click(price_input_x, price_input_y)
                time.sleep(random.uniform(0.1, 0.2))
                self.keyboard.ctrl_a()
                time.sleep(random.uniform(0.05, 0.1))

                if USE_CLIPBOARD_INPUT:
                    self.keyboard.copy_to_clipboard(str(calculated_price))
                    self.keyboard.paste()
                else:
                    self.keyboard.type_text(str(calculated_price))
                logger.log_only("[操作]", f"输入价格: {calculated_price}")
                time.sleep(random.uniform(0.1, 0.2))

                # ========== 步骤 9: 点击 upload2 确认 ==========
                self.mouse.click(upload2_x, upload2_y)
                logger.log_only("[操作]", f"点击 upload2 ({upload2_x}, {upload2_y})")

                # 成功完成
                sell_time = time.time() - sell_start
                self.state.total_sold += 1
                logger.print_only(f"卖出 {item_name} 售价 {calculated_price} (耗时 {sell_time:.1f}s)")
                logger.log_only("[完成]", f"已卖出 {item_name} | 耗时: {sell_time:.1f}s")
                return

            except Exception as e:
                logger.log_only("[错误]", f"第{retry_count+1}次: {e}")
                continue

        # 重试次数用完，失败
        logger.log_only("[错误]", f"重试{max_retry}次后仍失败，放弃卖出: {item_name}")
        logger.print_only(f"卖出失败 {item_name} (重试{max_retry}次)")

    def _find_ui_element(self, element_name: str) -> Optional[MatchResult]:
        """查找UI元素

        Args:
            element_name: 元素名称（对应模板文件名）

        Returns:
            匹配结果，没有找到返回 None
        """
        # 截图
        image = self.capture.capture_full_screen()

        # 识别（使用更高的阈值）
        results = self.ui_recognizer.recognize(image, draw_debug=False)

        if not results:
            return None

        # 找第一个匹配的
        return results[0]

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

    def _get_default_price(self, price_input_x: int, price_input_y: int) -> int:
        """从价格输入框识别默认价格

        Args:
            price_input_x: 价格输入框 x 坐标
            price_input_y: 价格输入框 y 坐标

        Returns:
            默认价格，识别失败返回 100
        """
        import re
        from vision.price_reader import get_ocr_reader
        logger = get_logger()

        try:
            # 截取价格输入框区域
            region = self._capture_region(price_input_x, price_input_y, 100, 30)
            if region is None:
                return 100

            # 使用 OCR 识别价格
            reader = get_ocr_reader()
            if reader is None:
                return 100

            result = reader.readtext(region, detail=0)
            if result:
                text = " ".join(result)
                numbers = re.findall(r"\d+", text)
                if numbers:
                    return int(numbers[0])

            return 100
        except Exception as e:
            logger.warning(f"识别默认价格失败: {e}")
            return 100

    def _verify_item(self, record: ItemRecord) -> Tuple[bool, float]:
        """验证物品是否还在原位

        Args:
            record: 物品记录

        Returns:
            (是否通过验证, MSE值)
        """
        # 计算验证区域（模板大小 + 边距）
        region_width = record.width + VERIFY_MARGIN * 2
        region_height = record.height + VERIFY_MARGIN * 2

        # 截图当前区域
        current_region = self._capture_region(
            record.x, record.y, region_width, region_height
        )

        if current_region is None:
            return False, float('inf')

        if record.snapshot is None:
            # 没有保存截图，直接通过
            return True, 0

        # 计算 MSE
        mse = compare_images_mse(record.snapshot, current_region)
        passed = mse < VERIFY_MSE_THRESHOLD

        return passed, mse
