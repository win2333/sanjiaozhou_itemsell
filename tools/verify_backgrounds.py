"""背景图验证脚本

使用现有的 TemplateRecognizer 检测每张背景图是否"干净"（无物品可见）。
如果识别到物品，说明这张图不适合作为背景，需要重新截图。

用法:
    python tools/verify_backgrounds.py [--backgrounds-dir backgrounds]
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="验证背景图是否干净（无物品）")
    parser.add_argument(
        "--backgrounds-dir",
        default="backgrounds",
        help="背景图目录（默认: backgrounds/）",
    )
    parser.add_argument(
        "--templates-dir",
        default="templates",
        help="物品模板目录（默认: templates/）",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="模板匹配阈值（默认: 0.85）",
    )
    parser.add_argument(
        "--roi-x",
        type=int,
        default=1150,
        help="只检查 ROI 右半边 x>=ROI_X（默认: 1150）",
    )
    return parser.parse_args()


def load_template_colors(templates_dir: Path) -> dict:
    """收集所有模板的颜色均值（用于快速预检）

    Returns:
        dict: {template_name: avg_bgr_color}
    """
    import os

    colors = {}
    for filename in os.listdir(templates_dir):
        if not filename.lower().endswith(".png"):
            continue
        if "ui" in filename.split("/")[-1].lower():
            continue
        path = templates_dir / filename
        with open(path, "rb") as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
            tmpl = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if tmpl is not None:
            avg = cv2.mean(tmpl)[:3]
            colors[filename] = np.array(avg)
    return colors


def quick_color_check(
    bg_roi: np.ndarray,
    template_colors: dict,
    color_sim_threshold: float = 0.80,
) -> List[Tuple[str, float]]:
    """快速颜色预检：找出背景中可能存在物品的区域

    Args:
        bg_roi: 背景 ROI 区域 (BGR)
        template_colors: {name: avg_bgr}
        color_sim_threshold: 颜色相似度阈值

    Returns:
        [(name, similarity), ...] 匹配度超过阈值的模板列表
    """
    import math

    matches = []
    bg_h, bg_w = bg_roi.shape[:2]

    # 采样背景中的若干区块（避免全图逐像素比较）
    # 将背景分成 8x8 的格子，检查每个格子的平均颜色
    grid_size = 8
    cell_h = max(bg_h // grid_size, 1)
    cell_w = max(bg_w // grid_size, 1)

    bg_colors = []
    for gy in range(0, bg_h, cell_h):
        for gx in range(0, bg_w, cell_w):
            cell = bg_roi[gy : gy + cell_h, gx : gx + cell_w]
            if cell.size > 0:
                bg_colors.append(cv2.mean(cell)[:3])

    if not bg_colors:
        return []

    # 对每个模板颜色，检查是否有区域与之相似
    for name, t_color in template_colors.items():
        t_color_norm = t_color / (math.sqrt(sum(t_color * t_color)) + 1e-6)
        for bg_c in bg_colors:
            bg_c_norm = np.array(bg_c) / (math.sqrt(sum(np.array(bg_c) ** 2)) + 1e-6)
            sim = float(np.dot(t_color_norm, bg_c_norm))
            if sim >= color_sim_threshold:
                matches.append((name, sim))

    return matches


def full_template_match(
    bg_roi: np.ndarray,
    templates_dir: Path,
    threshold: float,
) -> List[Tuple[str, float, int, int]]:
    """在 ROI 区域做完整模板匹配

    Returns:
        [(name, confidence, x, y), ...]
    """
    import os

    results = []
    bg_h, bg_w = bg_roi.shape[:2]

    for filename in os.listdir(templates_dir):
        if not filename.lower().endswith(".png"):
            continue
        if "ui" in filename.split("/")[-1].lower():
            continue

        path = templates_dir / filename
        with open(path, "rb") as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
            tmpl = cv2.imdecode(data, cv2.IMREAD_COLOR)

        if tmpl is None:
            continue

        t_h, t_w = tmpl.shape[:2]
        if t_h > bg_h or t_w > bg_w:
            continue

        res = cv2.matchTemplate(bg_roi, tmpl, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            results.append((filename, float(max_val), max_loc[0], max_loc[1]))

    return results


def verify_background(
    bg_path: Path,
    templates_dir: Path,
    threshold: float,
    roi_x: int,
) -> Tuple[bool, List[str]]:
    """验证单张背景图是否干净

    Returns:
        (is_clean, messages)
    """
    messages = []

    bg = cv2.imread(str(bg_path))
    if bg is None:
        return False, [f"无法读取图片: {bg_path}"]

    # 裁剪到 ROI 区域（x >= roi_x）
    if bg.shape[1] > roi_x:
        bg_roi = bg[:, roi_x:]
    else:
        bg_roi = bg

    if bg_roi.size == 0:
        return False, ["ROI 区域为空"]

    # Step 1: 快速颜色预检（筛选出最可疑的模板）
    template_colors = load_template_colors(templates_dir)
    color_matches = quick_color_check(bg_roi, template_colors)

    if not color_matches:
        # 颜色预检无匹配 → 干净
        return True, []

    # Step 2: 对颜色匹配度高的模板做完整匹配
    suspicious_names = [name for name, _ in color_matches]
    results = []
    for name in suspicious_names:
        with open(templates_dir / name, "rb") as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
            tmpl = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if tmpl is None:
            continue
        t_h, t_w = tmpl.shape[:2]
        if t_h > bg_roi.shape[0] or t_w > bg_roi.shape[1]:
            continue
        res = cv2.matchTemplate(bg_roi, tmpl, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            results.append((name, float(max_val), max_loc[0], max_loc[1]))

    if results:
        # 按置信度排序，只保留最高的前3个
        results.sort(key=lambda x: x[1], reverse=True)
        for name, conf, x, y in results[:3]:
            short_name = name.replace(".png", "")[:40]
            messages.append(f"  识别到物品: {short_name} (conf={conf:.3f}, x={x}, y={y})")
        return False, messages

    return True, []


def main() -> None:
    args = parse_args()

    backgrounds_dir = Path(args.backgrounds_dir)
    templates_dir = Path(args.templates_dir)

    if not backgrounds_dir.exists():
        print(f"❌ 背景目录不存在: {backgrounds_dir}")
        print("   请先创建目录并放入背景截图，参见 backgrounds/README.md")
        sys.exit(1)

    if not templates_dir.exists():
        print(f"❌ 模板目录不存在: {templates_dir}")
        sys.exit(1)

    # 收集所有背景图
    bg_files = sorted(
        [p for p in backgrounds_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")]
    )

    if not bg_files:
        print(f"❌ 在 {backgrounds_dir} 中未找到图片文件 (.png/.jpg/.jpeg)")
        print("   请先放入 30~50 张空背包截图")
        sys.exit(1)

    print(f"=== 背景图验证 ===")
    print(f"  背景目录: {backgrounds_dir.resolve()}")
    print(f"  模板目录: {templates_dir.resolve()}")
    print(f"  匹配阈值: {args.threshold}")
    print(f"  ROI x>=  {args.roi_x}")
    print(f"  图片数量: {len(bg_files)}")
    print()

    clean_count = 0
    dirty_count = 0
    error_count = 0

    for bg_path in bg_files:
        is_clean, messages = verify_background(
            bg_path, templates_dir, args.threshold, args.roi_x
        )

        if is_clean:
            status = "✅ 干净"
            clean_count += 1
        else:
            status = "❌ 有物品" if messages else "⚠️ 错误"
            if messages:
                dirty_count += 1
            else:
                error_count += 1

        msg = messages[0] if messages else ""
        print(f"  {bg_path.name:30s}  {status}  {msg}")

    print()
    print(f"=== 汇总 ===")
    print(f"  干净: {clean_count} 张")
    print(f"  有物品: {dirty_count} 张  ← 需要重新截图")
    print(f"  错误: {error_count} 张")
    print()

    if dirty_count > 0:
        print(f"⚠️  有 {dirty_count} 张背景图检测到物品，需要重新截图。")
        print("   建议：确保截图时背包尽量为空，或物品数量较少时再截图。")
    else:
        print("✅ 所有背景图均干净，数据集生成可以使用。")
