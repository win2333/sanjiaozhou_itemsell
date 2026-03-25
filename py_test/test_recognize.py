"""物品识别测试 - 支持中文标签显示，自动执行"""

import sys
sys.path.insert(0, '.')

import cv2
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import time
from vision.capture import ScreenCapture
from vision.recognizer import TemplateRecognizer
from config import TEMPLATES_DIR, TEMPLATE_MATCH_THRESHOLD

# 置信度阈值配置
HIGH_CONFIDENCE_1 = 0.99  # 第1档: ≥0.99 绿色
HIGH_CONFIDENCE_2 = 0.98  # 第2档: ≥0.98 黄色
HIGH_CONFIDENCE_3 = 0.97  # 第3档: ≥0.97 橙色


def main():
    start_time = time.time()

    print("=" * 50)
    print("      物品识别测试 v2.0")
    print("=" * 50)

    # 加载模板
    print("\n[1/4] 正在加载模板...")
    recognizer = TemplateRecognizer(
        str(TEMPLATES_DIR), threshold=TEMPLATE_MATCH_THRESHOLD, use_gpu=False
    )
    templates = recognizer.load_templates()
    print(f"      已加载 {len(templates)} 个物品模板")
    print(f"      匹配阈值: {TEMPLATE_MATCH_THRESHOLD}")

    # 截图（右半边 x>=1150），与 recognize() 逻辑一致
    print("\n[2/4] 正在截图...")
    capture = ScreenCapture()
    screen_width, screen_height = capture.get_screen_size()
    right_x = 1150
    image = capture.capture_region(right_x, 0, screen_width - right_x, screen_height)
    print(f"      右半边区域尺寸: {image.shape}")

    # 识别
    print("\n[3/4] 正在识别物品...")
    results = recognizer.recognize(image, draw_debug=False)

    # 按置信度分类
    conf_1 = [r for r in results if r.confidence >= HIGH_CONFIDENCE_1]
    conf_2 = [r for r in results if HIGH_CONFIDENCE_2 <= r.confidence < HIGH_CONFIDENCE_1]
    conf_3 = [r for r in results if HIGH_CONFIDENCE_3 <= r.confidence < HIGH_CONFIDENCE_2]
    conf_4 = [r for r in results if r.confidence < HIGH_CONFIDENCE_3]

    print(f"      识别到 {len(results)} 个物品:")
    print(f"        - 第1档(≥{HIGH_CONFIDENCE_1}): {len(conf_1)} 个 (绿色)")
    print(f"        - 第2档(≥{HIGH_CONFIDENCE_2}): {len(conf_2)} 个 (黄色)")
    print(f"        - 第3档(≥{HIGH_CONFIDENCE_3}): {len(conf_3)} 个 (橙色)")
    print(f"        - 第4档(<{HIGH_CONFIDENCE_3}): {len(conf_4)} 个 (红色)")

    # 转换 BGR -> RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(image_rgb)
    draw = ImageDraw.Draw(pil_img)

    # 尝试加载中文字体
    font = None
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simfang.ttf",    # 仿宋
    ]
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 16)
            break
        except:
            continue

    for r in results:
        # 根据置信度选择颜色 (RGB)
        if r.confidence >= HIGH_CONFIDENCE_1:
            color = (0, 255, 0)       # 绿色
        elif r.confidence >= HIGH_CONFIDENCE_2:
            color = (255, 255, 0)     # 黄色
        elif r.confidence >= HIGH_CONFIDENCE_3:
            color = (255, 165, 0)     # 橙色
        else:
            color = (255, 0, 0)       # 红色

        # 画矩形框
        draw.rectangle(
            [r.x, r.y, r.x + r.width, r.y + r.height],
            outline=color,
            width=2
        )

        # 画标签
        label = f"{r.template_name}: {r.confidence:.2f}"
        if font:
            draw.text((r.x, r.y - 18), label, font=font, fill=color)
        else:
            # 回退到英文
            label_en = f"{r.confidence:.2f}"
            draw.text((r.x, r.y - 18), label_en, fill=color)

    # 保存图片
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_path = f"debug_item_recognize_{timestamp}.png"
    pil_img.save(debug_path)

    elapsed = time.time() - start_time
    print(f"\n[4/4] 已保存调试图片: {debug_path}")
    print(f"      绿色=第1档(≥{HIGH_CONFIDENCE_1}), 黄色=第2档(≥{HIGH_CONFIDENCE_2}), "
          f"橙色=第3档(≥{HIGH_CONFIDENCE_3}), 红色=第4档(<{HIGH_CONFIDENCE_3})")

    print("\n" + "=" * 50)
    print(f"      测试完成! (耗时: {elapsed:.2f}s)")
    print("=" * 50)


if __name__ == "__main__":
    main()
