"""图像识别模块 - 模板匹配"""

import cv2
import numpy as np
from pathlib import Path
from config import DEBUG_DIR
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from utils.logger import get_logger

# 中文字体路径（Windows）
CHINESE_FONTS = [
    "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",    # 黑体
    "C:/Windows/Fonts/simfang.ttf",   # 仿宋
    "C:/Windows/Fonts/simsun.ttc",    # 宋体
]

def get_chinese_font():
    """获取可用的中文字体"""
    import os
    for font_path in CHINESE_FONTS:
        if os.path.exists(font_path):
            return font_path
    return None


@dataclass
class MatchResult:
    """匹配结果"""

    template_name: str  # 模板名称
    x: int  # 左上角 x 坐标
    y: int  # 左上角 y 坐标
    width: int  # 宽度
    height: int  # 高度
    confidence: float  # 置信度 (0-1)
    center_x: int  # 中心 x 坐标
    center_y: int  # 中心 y 坐标


# 颜色匹配阈值 (0-1)，越高颜色越要接近模板
COLOR_THRESHOLD = 0.85


class TemplateRecognizer:
    """模板识别器"""

    def __init__(
        self,
        templates_dir: str,
        threshold: float = 0.7,
        color_threshold: float = COLOR_THRESHOLD,
    ):
        """初始化

        Args:
            templates_dir: 模板图片目录
            threshold: 匹配阈值 (0-1)，默认 0.7
            color_threshold: 颜色匹配阈值 (0-1)，默认 0.85
        """
        self.templates_dir = Path(templates_dir)
        self.threshold = threshold
        self.color_threshold = color_threshold
        self.templates: Dict[str, np.ndarray] = {}
        self.template_colors: Dict[str, np.ndarray] = {}  # 存储模板平均颜色

    def load_templates(self) -> List[str]:
        """加载所有模板图片（支持中文文件名）

        Returns:
            加载的模板名称列表
        """
        loaded = []
        import os

        for filename in os.listdir(self.templates_dir):
            if filename.lower().endswith('.png'):
                template_path = os.path.join(self.templates_dir, filename)
                # 使用二进制读取再解码的方式支持中文路径
                with open(template_path, 'rb') as f:
                    data = np.frombuffer(f.read(), dtype=np.uint8)
                    template = cv2.imdecode(data, cv2.IMREAD_COLOR)

                if template is not None:
                    # 确保是 3 通道 BGR 格式
                    if template.shape[2] == 4:
                        template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
                    # 去掉扩展名作为名称
                    name = os.path.splitext(filename)[0]
                    self.templates[name] = template

                    # 计算模板的平均颜色 (BGR)
                    avg_color = cv2.mean(template)[:3]
                    self.template_colors[name] = np.array(avg_color)
                    loaded.append(name)
        return loaded

    def recognize(
        self, image: np.ndarray, draw_debug: bool = False
    ) -> List[MatchResult]:
        """在图像中识别所有匹配的模板（多线程并行）

        Args:
            image: 待检测的图像（numpy.ndarray）
            draw_debug: 是否绘制调试框（画红框）

        Returns:
            匹配结果列表
        """
        start_time = time.time()
        start_time_str = time.strftime("%H:%M:%S")

        # 转换图像格式：BGRA -> BGR（mss 返回的是 4 通道）
        work_image = image
        if image.shape[2] == 4:
            work_image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        # 只识别右半边（x >= 1150），减少匹配面积，提升速度
        # 假设屏幕宽度约 1920，右半边从 1150 开始
        if work_image.shape[1] > 1150:
            work_image = work_image[:, 1150:]

        results = []

        # 多线程并行匹配所有模板
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {
                executor.submit(self._match_template, work_image, template, name): name
                for name, template in self.templates.items()
            }
            for future in as_completed(futures):
                results.extend(future.result())

        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)

        # 计算耗时
        end_time = time.time()
        end_time_str = time.strftime("%H:%M:%S")
        elapsed_ms = (end_time - start_time) * 1000

        # 输出识别报告
        if results:
            item_names = [f"{r.template_name}({r.confidence:.2f})" for r in results[:5]]
            more = f" 等{len(results)}个" if len(results) > 5 else ""
            get_logger().log_only("[识别报告]", f"{start_time_str} → {end_time_str} | 耗时: {elapsed_ms:.1f}ms | 识别到: {', '.join(item_names)}{more}")
        else:
            get_logger().log_only("[识别报告]", f"{start_time_str} → {end_time_str} | 耗时: {elapsed_ms:.1f}ms | 未识别到物品")

        # 绘制调试框
        if draw_debug and results:
            # 在 BGR 图像上画红框，然后保存
            self._draw_debug_boxes(work_image, results)
            # 保存带置信度标记的图片
            import os
            save_path = str(DEBUG_DIR / "debug_item_recognize.png")
            self.save_debug_image(work_image, save_path)
            get_logger().log_only("[调试]", f"已保存识别结果图片: {save_path}")

        # 恢复原始坐标（加上裁剪偏移量）
        if work_image.shape[1] > 0 and image.shape[1] > 1150:
            for r in results:
                r.x += 1150
                r.center_x += 1150

        return results

    def _match_template(
        self, image: np.ndarray, template: np.ndarray, template_name: str
    ) -> List[MatchResult]:
        """执行模板匹配（包含颜色验证）

        Args:
            image: 待检测的图像
            template: 模板图像
            template_name: 模板名称

        Returns:
            匹配结果列表
        """
        results = []
        h, w = template.shape[:2]

        # 模板匹配
        res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)

        # 找到所有超过阈值的匹配
        locations = np.where(res >= self.threshold)

        # 获取模板的平均颜色
        template_avg_color = self.template_colors.get(template_name)

        for y, x in zip(*locations):
            confidence = res[y, x]

            # 颜色验证
            if template_avg_color is not None:
                # 提取匹配区域的图像
                roi = image[y : y + h, x : x + w]
                if roi.size > 0:
                    roi_avg_color = cv2.mean(roi)[:3]

                    # 计算颜色相似度 (余弦相似度)
                    color_sim = self._color_similarity(template_avg_color, roi_avg_color)

                    if color_sim < self.color_threshold:
                        # 颜色不匹配，跳过
                        continue

            results.append(
                MatchResult(
                    template_name=template_name,
                    x=int(x),
                    y=int(y),
                    width=int(w),
                    height=int(h),
                    confidence=float(confidence),
                    center_x=int(x + w // 2),
                    center_y=int(y + h // 2),
                )
            )

        return results

    def _color_similarity(self, color1: np.ndarray, color2: np.ndarray) -> float:
        """计算两个颜色的相似度（余弦相似度）

        Args:
            color1: 颜色1 (BGR)
            color2: 颜色2 (BGR)

        Returns:
            相似度 (0-1)
        """
        # 归一化
        c1 = color1 / (np.linalg.norm(color1) + 1e-6)
        c2 = color2 / (np.linalg.norm(color2) + 1e-6)
        # 余弦相似度
        return float(np.dot(c1, c2))

    def deduplicate(self, results: List[MatchResult], min_distance: int = 30) -> List[MatchResult]:
        """去重 - 合并距离过近的匹配框

        Args:
            results: 匹配结果列表
            min_distance: 最小距离阈值（像素）

        Returns:
            去重后的结果列表
        """
        if not results:
            return []

        # 按置信度排序，保留最高的
        results.sort(key=lambda x: x.confidence, reverse=True)

        keep = []
        for result in results:
            is_duplicate = False
            for kept in keep:
                dist = np.sqrt(
                    (result.center_x - kept.center_x) ** 2
                    + (result.center_y - kept.center_y) ** 2
                )
                if dist < min_distance:
                    is_duplicate = True
                    break
            if not is_duplicate:
                keep.append(result)

        return keep

    def deduplicate_by_name(self, results: List[MatchResult]) -> List[MatchResult]:
        """按模板名称分组去重 - 同名物品只保留置信度最高的

        用于批量卖出场景：同种物品在游戏中可以一次性全部卖出，
        因此只需要保留一个代表项即可。

        Args:
            results: 匹配结果列表

        Returns:
            去重后的结果列表，每种物品只保留置信度最高的一个
        """
        if not results:
            return []

        # 按名称分组
        groups: Dict[str, List[MatchResult]] = {}
        for r in results:
            if r.template_name not in groups:
                groups[r.template_name] = []
            groups[r.template_name].append(r)

        # 每组只保留置信度最高的
        deduped = []
        for name, items in groups.items():
            best = max(items, key=lambda x: x.confidence)
            deduped.append(best)

        return deduped

    def _draw_debug_boxes(
        self, image: np.ndarray, results: List[MatchResult]
    ) -> None:
        """绘制调试框（红框 + 置信度文字，支持中文）

        Args:
            image: 图像（会被修改）
            results: 匹配结果列表
        """
        # 获取中文字体
        font_path = get_chinese_font()

        for result in results:
            # 画红框
            cv2.rectangle(
                image,
                (result.x, result.y),
                (result.x + result.width, result.y + result.height),
                (0, 0, 255),  # 红色
                2,  # 线宽
            )

            # 显示置信度文字
            conf_text = f"{result.template_name}: {result.confidence:.2f}"

            # 尝试用 Pillow 渲染中文
            if font_path:
                try:
                    from PIL import Image, ImageDraw, ImageFont

                    # OpenCV BGR 转 PIL RGB
                    pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(pil_img)

                    # 加载字体
                    font_size = int(16 * 0.6)  # 根据 cv2 字体大小调整
                    font = ImageFont.truetype(font_path, font_size)

                    # 绘制文字 (绿色)
                    draw.text((result.x, result.y - 20), conf_text, font=font, fill=(0, 255, 0))

                    # 转回 OpenCV
                    image[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                    continue
                except Exception:
                    pass

            # 回退到 cv2（英文或数字）
            try:
                cv2.putText(
                    image,
                    conf_text,
                    (result.x, result.y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
            except Exception:
                pass

    def save_debug_image(self, image: np.ndarray, path: str) -> None:
        """保存调试图像

        Args:
            image: 图像
            path: 保存路径
        """
        cv2.imwrite(path, image)
