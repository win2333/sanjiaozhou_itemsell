"""图像识别模块 - 模板匹配（支持 GPU 加速）"""

import cv2
import numpy as np
from pathlib import Path
from config import DEBUG_DIR
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# GPU 加速支持
try:
    import torch
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from utils.logger import get_logger

# 中文字体路径（Windows）
CHINESE_FONTS = [
    "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",  # 黑体
    "C:/Windows/Fonts/simfang.ttf",  # 仿宋
    "C:/Windows/Fonts/simsun.ttc",  # 宋体
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
    """模板识别器（支持 GPU 加速）"""

    def __init__(
        self,
        templates_dir: str,
        threshold: float = 0.7,
        color_threshold: float = COLOR_THRESHOLD,
        use_gpu: bool = True,
    ):
        """初始化

        Args:
            templates_dir: 模板图片目录
            threshold: 匹配阈值 (0-1)，默认 0.7
            color_threshold: 颜色匹配阈值 (0-1)，默认 0.85
            use_gpu: 是否启用 GPU 模式，默认 True
        """
        self.templates_dir = Path(templates_dir)
        self.threshold = threshold
        self.color_threshold = color_threshold
        self.prefer_gpu = use_gpu
        self.templates: Dict[str, np.ndarray] = {}
        self.template_colors: Dict[str, np.ndarray] = {}  # 存储模板平均颜色

        # GPU 加速相关
        self.use_gpu = False
        self.device = None
        self._gpu_groups: Dict[Tuple[int, int], Dict] = {}  # 按尺寸分组的 GPU 模板

        if not self.prefer_gpu:
            get_logger().log_only("[GPU]", "已禁用 GPU 模板识别，使用 CPU 模式")
        elif TORCH_AVAILABLE:
            if torch.cuda.is_available():
                self.use_gpu = True
                self.device = torch.device("cuda")
                get_logger().log_only(
                    "[GPU]", f"已启用 GPU 加速: {torch.cuda.get_device_name(0)}"
                )
            else:
                get_logger().log_only("[GPU]", "CUDA 不可用，使用 CPU 模式")

    def load_templates(self) -> List[str]:
        """加载所有模板图片（支持中文文件名）

        Returns:
            加载的模板名称列表
        """
        loaded = []
        import os

        if not self.templates_dir.exists():
            get_logger().log_only("[模板]", f"模板目录不存在: {self.templates_dir}")
            return loaded

        for filename in os.listdir(self.templates_dir):
            if filename.lower().endswith(".png"):
                template_path = os.path.join(self.templates_dir, filename)
                # 使用二进制读取再解码的方式支持中文路径
                with open(template_path, "rb") as f:
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

        # 如果启用 GPU，构建 GPU 模板缓存
        if self.use_gpu:
            self._build_gpu_templates()

        return loaded

    def _build_gpu_templates(self) -> None:
        """构建 GPU 模板缓存（按尺寸分组）"""
        if not self.use_gpu:
            return

        # 按尺寸分组
        size_groups: Dict[Tuple[int, int], List[Tuple[str, np.ndarray]]] = {}
        for name, template in self.templates.items():
            h, w = template.shape[:2]
            key = (h, w)
            if key not in size_groups:
                size_groups[key] = []
            size_groups[key].append((name, template))

        # 为每个尺寸组构建 GPU 张量
        for (h, w), items in size_groups.items():
            names = [item[0] for item in items]
            templates_list = [item[1] for item in items]

            # 转换为 float32 并归一化到 [0, 1]
            # OpenCV 是 BGR，保持不变
            templates_np = np.stack(templates_list, axis=0)  # (N, H, W, 3)
            templates_np = templates_np.astype(np.float32) / 255.0
            # 转换为 (N, 3, H, W) 格式用于 conv2d
            templates_np = templates_np.transpose(0, 3, 1, 2)

            # 计算每个模板的均值和标准差（用于 TM_CCOEFF_NORMED）
            # T_mean = mean(T), T_centered = T - T_mean, T_std = std(T_centered)
            t_tensor = torch.from_numpy(templates_np).to(self.device)  # (N, 3, H, W)
            t_mean = t_tensor.mean(dim=(1, 2, 3), keepdim=True)  # (N, 1, 1, 1)
            t_centered = t_tensor - t_mean
            t_std = torch.sqrt(
                (t_centered**2).sum(dim=(1, 2, 3), keepdim=True) + 1e-8
            )  # (N, 1, 1, 1)
            t_normalized = t_centered / t_std

            self._gpu_groups[(h, w)] = {
                "names": names,
                "templates": t_normalized,  # 已中心化并归一化
                "h": h,
                "w": w,
            }

        get_logger().log_only(
            "[GPU]",
            f"已缓存 {len(self._gpu_groups)} 个尺寸组，共 {len(self.templates)} 个模板",
        )

    def recognize(
        self, image: np.ndarray, draw_debug: bool = False
    ) -> List[MatchResult]:
        """在图像中识别所有匹配的模板

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
        if work_image.shape[1] > 1150:
            work_image = work_image[:, 1150:]

        # 选择 GPU 或 CPU 路径
        if self.use_gpu:
            results = self._recognize_gpu(work_image)
        else:
            results = self._recognize_cpu(work_image)

        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)

        # 计算耗时
        end_time = time.time()
        end_time_str = time.strftime("%H:%M:%S")
        elapsed_ms = (end_time - start_time) * 1000

        # 输出识别报告
        mode = "GPU" if self.use_gpu else "CPU"
        if results:
            item_names = [f"{r.template_name}({r.confidence:.2f})" for r in results[:5]]
            more = f" 等{len(results)}个" if len(results) > 5 else ""
            get_logger().log_only(
                "[识别报告]",
                f"{start_time_str} → {end_time_str} | {mode}耗时: {elapsed_ms:.1f}ms | 识别到: {', '.join(item_names)}{more}",
            )
        else:
            get_logger().log_only(
                "[识别报告]",
                f"{start_time_str} → {end_time_str} | {mode}耗时: {elapsed_ms:.1f}ms | 未识别到物品",
            )

        # 绘制调试框
        if draw_debug and results:
            self._draw_debug_boxes(work_image, results)
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

    def _recognize_gpu(self, image: np.ndarray) -> List[MatchResult]:
        """GPU 批量模板匹配（实现 TM_CCOEFF_NORMED）

        Args:
            image: 待检测的 BGR 图像

        Returns:
            匹配结果列表
        """
        results = []
        img_h, img_w = image.shape[:2]

        # 转换图像为 GPU 张量 (1, 3, H, W)，float32 归一化
        img_np = image.astype(np.float32) / 255.0
        img_np = img_np.transpose(2, 0, 1)  # (H, W, 3) -> (3, H, W)
        img_tensor = (
            torch.from_numpy(img_np).unsqueeze(0).to(self.device)
        )  # (1, 3, H, W)

        # 预计算图像的平方（用于方差计算）
        img_sq = img_tensor**2

        # 遍历每个尺寸组
        for (h, w), group in self._gpu_groups.items():
            # 跳过比图像大的模板
            if h > img_h or w > img_w:
                continue

            names = group["names"]
            t_normalized = group["templates"]  # (N, 3, h, w)，已中心化并归一化
            n_templates = len(names)

            # 计算 TM_CCOEFF_NORMED
            # 分子: sum((I - mean_I_local) * (T - mean_T)) / (std_I_local * std_T)
            # 我们已预计算 T_normalized = (T - mean_T) / std_T
            # 所以分子 = conv2d(I, T_normalized) - mean_I_local * sum(T_normalized)
            # 但 sum(T_normalized) ≈ 0（因为已中心化），所以分子 ≈ conv2d(I, T_normalized)

            # 分母: std_I_local = sqrt(sum((I - mean_I_local)^2))
            # = sqrt(sum(I^2) - n * mean_I_local^2)
            # = sqrt(local_sum_I^2 - local_sum_I^2 / n)

            # 卷积计算 sum(I * T_normalized)
            # conv2d 输出形状: (1, N, out_h, out_w)
            numerator = F.conv2d(img_tensor, t_normalized)  # (1, N, out_h, out_w)

            # 计算局部图像能量的分母项
            # 需要计算每个位置的 sum(I^2)，使用 average_pool2d 的技巧
            kernel_size = (h, w)
            local_sum = F.avg_pool2d(img_tensor, kernel_size, stride=1) * (
                h * w
            )  # (1, 3, out_h, out_w)
            local_sum_sq = F.avg_pool2d(img_sq, kernel_size, stride=1) * (
                h * w
            )  # (1, 3, out_h, out_w)

            # std_I_local = sqrt(sum(I^2) - sum(I)^2 / (h*w*3)) * sqrt(h*w*3)
            # 简化: std_I_local = sqrt(local_sum_sq - local_sum^2 / n) * sqrt(n)
            # 其中 n = h * w * 3
            n_pixels = h * w * 3
            local_mean_sq = (local_sum**2).sum(
                dim=1, keepdim=True
            ) / n_pixels  # (1, 1, out_h, out_w)
            local_energy = local_sum_sq.sum(dim=1, keepdim=True)  # (1, 1, out_h, out_w)
            denominator = torch.sqrt(local_energy - local_mean_sq + 1e-8) * (
                n_pixels**0.5
            )  # (1, 1, out_h, out_w)

            # 归一化相关系数
            corr = numerator / (denominator + 1e-8)  # (1, N, out_h, out_w)

            # 阈值过滤
            mask = corr >= self.threshold
            if not mask.any():
                continue

            # 提取超过阈值的位置
            # corr shape: (1, N, out_h, out_w)
            corr_np = corr.squeeze(0).cpu().numpy()  # (N, out_h, out_w)
            mask_np = mask.squeeze(0).cpu().numpy()  # (N, out_h, out_w)

            for idx in range(n_templates):
                name = names[idx]
                template_avg_color = self.template_colors.get(name)
                template = self.templates[name]

                # 找到所有匹配位置
                positions = np.where(mask_np[idx])
                for y, x in zip(*positions):
                    confidence = float(corr_np[idx, y, x])

                    # 颜色验证
                    if template_avg_color is not None:
                        roi = image[y : y + h, x : x + w]
                        if roi.size > 0:
                            roi_avg_color = cv2.mean(roi)[:3]
                            color_sim = self._color_similarity(
                                template_avg_color, roi_avg_color
                            )
                            if color_sim < self.color_threshold:
                                continue

                    results.append(
                        MatchResult(
                            template_name=name,
                            x=int(x),
                            y=int(y),
                            width=int(w),
                            height=int(h),
                            confidence=confidence,
                            center_x=int(x + w // 2),
                            center_y=int(y + h // 2),
                        )
                    )

        return results

    def _recognize_cpu(self, work_image: np.ndarray) -> List[MatchResult]:
        """CPU 多线程模板匹配（原有逻辑）"""
        results = []

        # 多线程并行匹配所有模板
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {
                executor.submit(self._match_template, work_image, template, name): name
                for name, template in self.templates.items()
            }
            for future in as_completed(futures):
                results.extend(future.result())

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
        tmpl_h, tmpl_w = template.shape[:2]
        img_h, img_w = image.shape[:2]

        # 跳过比图像大的模板（与 GPU 路径保持一致）
        if tmpl_h > img_h or tmpl_w > img_w:
            return results

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
                roi = image[y : y + tmpl_h, x : x + tmpl_w]
                if roi.size > 0:
                    roi_avg_color = cv2.mean(roi)[:3]

                    # 计算颜色相似度 (余弦相似度)
                    color_sim = self._color_similarity(
                        template_avg_color, roi_avg_color
                    )

                    if color_sim < self.color_threshold:
                        # 颜色不匹配，跳过
                        continue

            results.append(
                MatchResult(
                    template_name=template_name,
                    x=int(x),
                    y=int(y),
                    width=int(tmpl_w),
                    height=int(tmpl_h),
                    confidence=float(confidence),
                    center_x=int(x + tmpl_w // 2),
                    center_y=int(y + tmpl_h // 2),
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

    def _draw_debug_boxes(self, image: np.ndarray, results: List[MatchResult]) -> None:
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
                    draw.text(
                        (result.x, result.y - 20),
                        conf_text,
                        font=font,
                        fill=(0, 255, 0),
                    )

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
