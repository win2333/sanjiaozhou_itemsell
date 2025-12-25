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
        results = self.item_recognizer.deduplicate(results, DEDUP_DISTANCE)

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

            logger.recognize(f"未识别到物品 (连续{self.state.consecutive_empty}次, 延迟{self.state.idle_delay:.1f}s)")
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

        # 输出识别结果
        items_info = ", ".join(
            f"{r.name}({r.confidence:.2f})" for r in item_records[:5]
        )
        more = f" 等{len(item_records)}个" if len(item_records) > 5 else ""
        logger.recognize(f"识别到 {len(item_records)} 个物品: {items_info}{more}")

        # 重置空闲检测计数器
        self.state.consecutive_empty = 0
        self.state.idle_delay = LOOP_DELAY

        # 5. 处理每个物品
        sold_count = 0
        for record in item_records:
            if not self.state.is_running:
                return

            logger.operation(f"准备处理: {record.name} ({record.x}, {record.y})")

            # === 验证阶段 ===
            passed, mse = self._verify_item(record)

            if passed:
                logger.verify(f"MSE={mse:.1f} < {VERIFY_MSE_THRESHOLD} | 验证通过 ✓")
                # 验证通过，处理物品
                self._sell_item_with_log(record)
                sold_count += 1
                self.state.processed_positions.add(
                    (record.x // DEDUP_DISTANCE, record.y // DEDUP_DISTANCE)
                )
            else:
                logger.verify(f"MSE={mse:.1f} | 验证失败，仓库变了，重新识别")
                break  # 跳出循环，重新全屏识别

        # 6. 输出统计
        cycle_time = time.time() - cycle_start
        logger.stats(f"本轮: 卖出 {sold_count}/{len(item_records)} | 耗时: {cycle_time:.1f}s")

        # 7. 延迟后继续（使用空闲检测的延迟时间）
        time.sleep(self.state.idle_delay)

    def _sell_item_with_log(self, record: ItemRecord) -> None:
        """卖出单个物品（带详细日志）"""
        logger = get_logger()
        item_name = record.name
        x = record.x
        y = record.y
        sell_start = time.time()

        logger.operation(f"鼠标移动到 ({x}, {y})")

        # 1. 鼠标移动到物品上（悬停）
        self.mouse.move_to(x, y)
        time.sleep(random.uniform(0.1, 0.15))

        # 2. 右键点击（打开菜单）
        self.mouse.right_click(x, y)
        logger.operation(f"右键点击 ({x}, {y})")
        time.sleep(random.uniform(0.1, 0.15))

        # 3. 识别 sell1 并点击
        sell1_result = self._find_ui_element("sell1")
        if sell1_result:
            self.mouse.click(sell1_result.center_x, sell1_result.center_y)
            logger.operation(f"点击 sell1 ({sell1_result.center_x}, {sell1_result.center_y})")
        else:
            logger.warning("未找到 sell1 按钮")
            return
        time.sleep(random.uniform(0.1, 0.15))

        # 4. 点击 upload1（选择上架到交易行）
        if USE_FIXED_COORDINATES:
            # 使用固定坐标
            self.mouse.click(UPLOAD1_X, UPLOAD1_Y)
            logger.operation(f"点击 upload1 (固定: {UPLOAD1_X}, {UPLOAD1_Y})")
            upload2_x = UPLOAD2_X
            upload2_y = UPLOAD2_Y
        else:
            # 使用图像识别
            upload1_result = self._find_ui_element("upload1")
            if upload1_result:
                self.mouse.click(upload1_result.center_x, upload1_result.center_y)
                logger.operation(f"点击 upload1 ({upload1_result.center_x}, {upload1_result.center_y})")
            else:
                logger.warning("未找到 upload1 按钮")
                return

            # 5. 找到 upload2
            upload2_result = self._find_ui_element("upload2")
            if not upload2_result:
                logger.warning("未找到 upload2 按钮")
                return
            upload2_x = upload2_result.center_x
            upload2_y = upload2_result.center_y

        time.sleep(random.uniform(0.1, 0.15))

        # 计算坐标
        price_input_x = upload2_x + PRICE_OFFSET_X
        price_input_y = upload2_y + PRICE_OFFSET_Y
        quantity_x = upload2_x + QUANTITY_OFFSET_X
        quantity_y = upload2_y + QUANTITY_OFFSET_Y

        logger.calculate(f"价格输入框: ({price_input_x}, {price_input_y})")
        logger.calculate(f"数量按钮: ({quantity_x}, {quantity_y})")

        # 6. 点击数量按钮（点满，重复3次确保点满）
        for i in range(3):
            self.mouse.click(quantity_x, quantity_y)
            time.sleep(random.uniform(0.05, 0.1))
        logger.operation(f"点击数量按钮 3次 ({quantity_x}, {quantity_y})")
        time.sleep(random.uniform(0.1, 0.2))

        # 7. 截图识别价格（带验证，最多重试3次）
        price = None
        for retry in range(3):
            screenshot = self.capture.capture_full_screen()
            p1, p2 = self.price_reader.get_p1_p2(screenshot)
            if p1 is None:
                logger.warning(f"第{retry+1}次: 未能识别到价格")
                if retry < 2:
                    time.sleep(0.2)
                    continue
                else:
                    # 重试失败，从价格输入框识别默认价格
                    default_price = self._get_default_price(price_input_x, price_input_y)
                    price = default_price
                    logger.warning(f"重试失败，使用系统默认价格: {price}")
                    break

            logger.calculate(f"价格识别: P1={p1}, P2={p2}")

            # 计算最优价格
            calculated_price = calculate_price(p1, p2)
            logger.calculate(f"计算结果: 售价={calculated_price}")

            # 获取默认价格用于验证
            default_price = self._get_default_price(price_input_x, price_input_y)

            # 验证结果
            if calculated_price <= 0:
                logger.warning(f"第{retry+1}次: 计算结果为负数 ({calculated_price})")
            elif default_price > 0 and calculated_price > default_price * 1.5:
                logger.warning(f"第{retry+1}次: 价格偏高 ({calculated_price} > {default_price * 1.5})")
            elif default_price > 0 and calculated_price < default_price * 0.5:
                logger.warning(f"第{retry+1}次: 价格偏低 ({calculated_price} < {default_price * 0.5})")
            else:
                # 价格合理
                price = calculated_price
                logger.calculate(f"价格验证通过: {price}")
                break

            # 价格不合理，重试
            if retry < 2:
                logger.operation("重新识别价格...")
                time.sleep(0.2)
            else:
                price = default_price
                logger.warning(f"重试失败，使用系统默认价格: {price}")

        # 9. 点击价格输入框
        self.mouse.click(price_input_x, price_input_y)
        logger.operation(f"点击价格输入框 ({price_input_x}, {price_input_y})")
        time.sleep(random.uniform(0.1, 0.2))

        # 10. 输入价格
        self.keyboard.ctrl_a()
        time.sleep(random.uniform(0.05, 0.1))

        if USE_CLIPBOARD_INPUT:
            # 使用剪贴板输入（更快）
            self.keyboard.copy_to_clipboard(str(price))
            self.keyboard.paste()
            logger.operation(f"输入价格(剪贴板): {price}")
        else:
            # 使用键盘逐字符输入
            self.keyboard.type_text(str(price))
            logger.operation(f"输入价格: {price}")
        time.sleep(random.uniform(0.1, 0.2))

        # 11. 点击 upload2 确认
        self.mouse.click(upload2_x, upload2_y)
        logger.operation(f"点击 upload2 ({upload2_x}, {upload2_y})")

        # 完成
        sell_time = time.time() - sell_start
        self.state.total_sold += 1
        logger.complete(f"已卖出 {item_name} | 耗时: {sell_time:.1f}s")

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
