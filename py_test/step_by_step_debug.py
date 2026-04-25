"""逐步调试脚本 - 手动跑一遍检测流程

用法:
    python py_test/step_by_step_debug.py

流程:
    1. 截取背包区域截图
    2. YOLO 检测，显示候选框，等待回车
    3. 逐个 ROI 显示，展示模板匹配结果，等待回车
    4. 显示最终候选列表
"""

import sys
import time
import os
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 中文字体（Windows 微软雅黑）
_CN_FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)


def _draw_cn(img: np.ndarray, text: str, x: int, y: int, color: tuple = (255, 255, 255)) -> np.ndarray:
    """在 BGR 图像上用 PIL 渲染中文（返回副本）"""
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    rgb = (color[2], color[1], color[0])  # BGR → RGB
    # 黑色描边
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        draw.text((x + dx, y + dy), text, font=_CN_FONT, fill=(0, 0, 0))
    # 主文字
    draw.text((x, y), text, font=_CN_FONT, fill=rgb)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

from vision.capture import ScreenCapture
from vision.yolo_item_detector import YoloItemDetector
from vision.hybrid_pipeline import HybridPipeline
from vision.recognizer import TemplateRecognizer
from config import (
    BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT,
    YOLO_MODEL_PATH, YOLO_CONFIDENCE_THRESHOLD, YOLO_IOU_THRESHOLD,
    TEMPLATE_MATCH_THRESHOLD, TEMPLATES_DIR,
    USE_GPU_TEMPLATE_RECOGNITION,
    HYBRID_MAX_WORKERS,
)
from vision.item_types import RawItemDetection


def wait_for_enter(msg: str = ""):
    """等待用户按回车继续"""
    prompt = msg + " [按回车继续]" if msg else "按回车继续..."
    input(f"\n  {prompt}")


# 调试输出目录（在 main() 中创建）
DEBUG_STEP_DIR: Path = Path("debug_step")
_roi_counter = 0


def save_roi_debug(roi_img: np.ndarray, suffix: str, match_info: str = ""):
    """保存 ROI 调试图到 debug_step 目录"""
    global _roi_counter
    out = DEBUG_STEP_DIR / f"roi_{_roi_counter:02d}_{suffix}.png"
    cv2.imwrite(str(out), roi_img)
    print(f"  [已保存] {out.name}" + (f" ({match_info})" if match_info else ""))
    _roi_counter += 1


def mark_yolo_boxes(img: np.ndarray, detections: list) -> np.ndarray:
    """在图上标注 YOLO 检测框（蓝色），返回副本"""
    out = img.copy()
    for i, det in enumerate(detections):
        x1, y1 = det.x, det.y
        x2, y2 = det.x + det.w, det.y + det.h
        cv2.rectangle(out, (x1, y1), (x2, y2), (255, 100, 0), 2)
        label = f"#{i} {det.confidence:.2f}"
        out = _draw_cn(out, label, x1, max(y1 - 5, 10), (255, 100, 0))
    return out


def main():
    # ===== 1. 截图 =====
    print("\n" + "=" * 60)
    print("  步骤1: 截图")
    print("=" * 60)
    capture = ScreenCapture()
    image = capture.capture_region(
        BACKPACK_LEFT, BACKPACK_TOP, BACKPACK_WIDTH, BACKPACK_HEIGHT
    )
    if image is None or image.size == 0:
        print("  截图失败！请确保游戏窗口已打开且背包可见。")
        return

    # 转 BGR
    if len(image.shape) == 3 and image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    print(f"  截图成功: {image.shape[1]}x{image.shape[0]}")
    print(f"  背包区域: ({BACKPACK_LEFT}, {BACKPACK_TOP}) - "
          f"({BACKPACK_LEFT + BACKPACK_WIDTH}, {BACKPACK_TOP + BACKPACK_HEIGHT})")

    # 保存原始截图
    global _roi_counter
    _roi_counter = 0
    DEBUG_STEP_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(DEBUG_STEP_DIR / "00_original.png"), image)
    print(f"  已保存: {DEBUG_STEP_DIR / '00_original.png'}")

    wait_for_enter("截图完成")

    # ===== 2. 初始化检测器 =====
    print("\n" + "=" * 60)
    print("  步骤2: 初始化 YOLO 检测器")
    print("=" * 60)
    print(f"  模型: {YOLO_MODEL_PATH}")
    yolo = YoloItemDetector(
        model_path=YOLO_MODEL_PATH,
        confidence_threshold=YOLO_CONFIDENCE_THRESHOLD,
        iou_threshold=YOLO_IOU_THRESHOLD,
    )
    print("  YOLO 加载完成")

    wait_for_enter("YOLO 加载完成")

    # ===== 3. YOLO 检测 =====
    print("\n" + "=" * 60)
    print("  步骤3: YOLO 检测")
    print("=" * 60)
    yolo_start = time.time()
    yolo_detections = yolo.detect(image)
    yolo_ms = (time.time() - yolo_start) * 1000

    print(f"  YOLO 耗时: {yolo_ms:.0f}ms")
    print(f"  检测到 {len(yolo_detections)} 个候选区域:")
    for i, det in enumerate(yolo_detections):
        print(f"    #{i}: ({det.x}, {det.y}) {det.w}x{det.h}  "
              f"置信度={det.confidence:.3f}")

    if not yolo_detections:
        print("\n  YOLO 没有检测到任何候选，流程结束。")
        print(f"  (可能原因: 背包里没有物品，或 YOLO 模型不适合当前场景)")
        return

    # 绘制 YOLO 检测框
    img_yolo = mark_yolo_boxes(image, yolo_detections)
    yolo_path = DEBUG_STEP_DIR / "01_yolo.png"
    cv2.imwrite(str(yolo_path), img_yolo)
    print(f"\n  已保存: {yolo_path}")
    print("  → 打开这张图片查看 YOLO 标注框的位置")

    wait_for_enter("YOLO 检测完成，打开图片查看后继续")

    # ===== 3.5 提取 ROI =====
    print("\n" + "=" * 60)
    print("  步骤4: ROI 提取")
    print("=" * 60)

    padding = 10  # ROI 外边扩张像素
    rois = []
    for i, det in enumerate(yolo_detections):
        x1 = max(0, det.x)
        y1 = max(0, det.y)
        x2 = min(image.shape[1], det.x + det.w)
        y2 = min(image.shape[0], det.y + det.h)

        x1_pad = max(0, x1 - padding)
        y1_pad = max(0, y1 - padding)
        x2_pad = min(image.shape[1], x2 + padding)
        y2_pad = min(image.shape[0], y2 + padding)

        roi = image[y1_pad:y2_pad, x1_pad:x2_pad]

        print(f"    #{i}: YOLO 框=({det.x},{det.y},{det.w},{det.h})  "
              f"→ ROI区域=({x1_pad},{y1_pad},{x2_pad - x1_pad},{y2_pad - y1_pad})  "
              f"ROI大小={roi.shape[1]}x{roi.shape[0]}")
        rois.append((roi, det))

    wait_for_enter("ROI 提取完成")

    # ===== 4. 加载模板 =====
    print("\n" + "=" * 60)
    print("  步骤5: 加载物品模板")
    print("=" * 60)
    print(f"  模板目录: {TEMPLATES_DIR}")

    recognizer = TemplateRecognizer(
        str(TEMPLATES_DIR),
        threshold=TEMPLATE_MATCH_THRESHOLD,
        use_gpu=USE_GPU_TEMPLATE_RECOGNITION,
    )
    templates = recognizer.load_templates()
    print(f"  加载了 {len(recognizer.templates)} 个模板")

    # 按大小分组显示
    size_groups = {}
    for name, tmpl in recognizer.templates.items():
        h, w = tmpl.shape[:2]
        key = f"{w}x{h}"
        if key not in size_groups:
            size_groups[key] = []
        size_groups[key].append(name)

    print(f"  模板大小分布:")
    for size_key in sorted(size_groups.keys()):
        names = size_groups[size_key]
        print(f"    {size_key}: {len(names)} 个 (如 {names[0]}, {names[1] if len(names) > 1 else ''}...)")

    wait_for_enter("模板加载完成，准备逐个 ROI 测试匹配")

    # ===== 5. 逐个 ROI 模板匹配 =====
    print("\n" + "=" * 60)
    print("  步骤6: 逐个 ROI 模板匹配")
    print("=" * 60)

    total_matched = 0
    color_threshold = 0.85  # COLOR_MATCH_THRESHOLD
    match_threshold = 0.70  # TEMPLATE_MATCH_THRESHOLD (从0.85调低)

    all_matches = []

    for i, (roi, det) in enumerate(rois):
        print(f"\n  --- ROI #{i}/{len(rois)} (原始YOLO: {det.w}x{det.h}) ---")
        print(f"  ROI 实际大小: {roi.shape[1]}x{roi.shape[0]}")

        if roi.shape[0] < 10 or roi.shape[1] < 10:
            print(f"  [跳过] ROI 太小，无法匹配")
            continue

        # BGRA -> BGR
        work_img = roi
        if len(roi.shape) == 3 and roi.shape[2] == 4:
            work_img = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        best_match = None
        best_confidence = 0.0  # 经过阈值+颜色验证后的最佳匹配
        best_color_fail = None
        template_too_large = 0
        highest_raw_score = 0.0  # 所有模板的原始最高 TM_CCOEFF_NORMED 值（不管阈值）
        highest_raw_name = ""
        # TOP-5 最佳匹配（原始分数）
        top_scores: list = []

        for tname, tmpl in recognizer.templates.items():
            th, tw = tmpl.shape[:2]

            # 跳过比 ROI 大的模板
            if th > work_img.shape[0] or tw > work_img.shape[1]:
                template_too_large += 1
                continue

            result = cv2.matchTemplate(work_img, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            # 始终记录全局最高分（不管阈值）
            if max_val > highest_raw_score:
                highest_raw_score = max_val
                highest_raw_name = tname
            # TOP-5 榜单
            top_scores.append((max_val, tname))
            top_scores.sort(key=lambda x: -x[0])
            top_scores = top_scores[:5]

            if max_val >= match_threshold and max_val > best_confidence:
                # 颜色验证
                grid = []
                for gx in [0.25, 0.5, 0.75]:
                    for gy in [0.25, 0.5, 0.75]:
                        grid.append((round(tw * gx), round(th * gy)))

                similarities = []
                valid = True
                for gx, gy in grid:
                    if 0 <= gx < tw and 0 <= gy < th:
                        t_color = tmpl[gy, gx]
                    else:
                        valid = False
                        break
                    ax = max_loc[0] + gx
                    ay = max_loc[1] + gy
                    if 0 <= ax < work_img.shape[1] and 0 <= ay < work_img.shape[0]:
                        m_color = work_img[ay, ax]
                    else:
                        valid = False
                        break

                    # 余弦相似度
                    def cos_sim(a, b):
                        a_n = a.astype(float) / (np.linalg.norm(a.astype(float)) + 1e-6)
                        b_n = b.astype(float) / (np.linalg.norm(b.astype(float)) + 1e-6)
                        return float(np.dot(a_n, b_n))

                    sim = cos_sim(t_color, m_color)
                    similarities.append(sim)

                if valid and len(similarities) == 9:
                    avg_sim = sum(similarities) / len(similarities)
                    if avg_sim < color_threshold:
                        if best_color_fail is None or max_val > best_color_fail[0]:
                            best_color_fail = (max_val, tname, avg_sim)
                        continue

                best_confidence = max_val
                best_match = {
                    "name": tname,
                    "x": max_loc[0],
                    "y": max_loc[1],
                    "w": tw,
                    "h": th,
                    "confidence": max_val,
                }

        # 输出该 ROI 的匹配结果
        if best_match:
            total_matched += 1
            # 存储匹配信息和ROI在全图中的起始坐标（后续用于画最终标注图）
            best_match["_roi_x"] = max(0, det.x - padding)
            best_match["_roi_y"] = max(0, det.y - padding)
            all_matches.append(best_match)
            print(f"  ✓ 匹配成功: {best_match['name']} "
                  f"(置信度={best_match['confidence']:.3f}, "
                  f"位置=({best_match['x']},{best_match['y']}), "
                  f"大小={best_match['w']}x{best_match['h']})")

            # 在 ROI 上画匹配框（含中文物品名）
            roi_display = work_img.copy()
            mx, my = best_match['x'], best_match['y']
            cv2.rectangle(roi_display, (mx, my),
                          (mx + best_match['w'], my + best_match['h']),
                          (0, 220, 0), 2)
            label = f"{best_match['name']} {best_match['confidence']:.2f}"
            roi_display = _draw_cn(roi_display, label, mx, max(my - 5, 10), (0, 220, 0))
            save_roi_debug(roi_display, "match", best_match['name'])
        else:
            reason_parts = []
            if best_color_fail:
                reason_parts.append(f"颜色筛选失败: {best_color_fail[1]} "
                                    f"(分={best_color_fail[0]:.3f}, "
                                    f"颜色相似度={best_color_fail[2]:.3f})")
            if template_too_large > 0:
                reason_parts.append(f"{template_too_large}个模板超尺寸跳过")
            reason_parts.append(f"最高分={highest_raw_score:.3f} ({highest_raw_name})")

            print(f"  ✗ 无匹配: {'; '.join(reason_parts)}")
            print(f"    TOP-5 最佳匹配:")
            for rank, (score, name) in enumerate(top_scores[:5], 1):
                print(f"      #{rank}: {name} ({score:.3f})")

            # 显示 ROI 原图
            save_roi_debug(work_img, "no_match")

        # 每个 ROI 后等待
        # 原为按回车继续，现改为一次性跑完

    # ===== 6. 总结 =====
    print("\n" + "=" * 60)
    print("  最终结果汇总")
    print("=" * 60)
    print(f"  YOLO 候选: {len(yolo_detections)}")
    print(f"  模板匹配成功: {total_matched}")

    if all_matches:
        print(f"\n  匹配到的物品:")
        for m in all_matches:
            print(f"    {m['name']:20s}  置信度={m['confidence']:.3f}")

        # 在全图上绘制最终标注图
        img_final = image.copy()
        for m in all_matches:
            mx = m["_roi_x"] + m["x"]
            my = m["_roi_y"] + m["y"]
            cv2.rectangle(img_final, (mx, my),
                          (mx + m["w"], my + m["h"]),
                          (0, 220, 0), 2)
            label = f"{m['name']} {m['confidence']:.2f}"
            img_final = _draw_cn(img_final, label, mx, max(my - 5, 10), (0, 220, 0))
        final_path = DEBUG_STEP_DIR / "03_final_matches.png"
        cv2.imwrite(str(final_path), img_final)
    else:
        print(f"\n  ⚠ 没有匹配到任何物品！")

    print(f"\n  所有调试图片保存在: {DEBUG_STEP_DIR.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
