"""物品识别测试 - 支持中文标签显示"""
import cv2
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from vision.capture import ScreenCapture
from vision.recognizer import TemplateRecognizer
from config import TEMPLATES_DIR, TEMPLATE_MATCH_THRESHOLD


def main():
    print("=" * 50)
    print("物品识别测试")
    print("=" * 50)

    # 加载模板
    recognizer = TemplateRecognizer(
        str(TEMPLATES_DIR), threshold=TEMPLATE_MATCH_THRESHOLD
    )
    templates = recognizer.load_templates()
    print(f"已加载 {len(templates)} 个模板: {templates}")
    print(f"置信度阈值: {TEMPLATE_MATCH_THRESHOLD}")

    # 截图
    capture = ScreenCapture()
    print("\n按 Enter 截图并识别...")
    input()

    image = capture.capture_full_screen()

    # 识别
    results = recognizer.recognize(image, draw_debug=False)

    # 按置信度分类
    high_conf = [r for r in results if r.confidence >= 0.9]
    mid_conf = [r for r in results if 0.8 <= r.confidence < 0.9]
    low_conf = [r for r in results if r.confidence < 0.8]

    print(f"\n识别到 {len(results)} 个物品:")
    print(f"  高置信度(≥0.9): {len(high_conf)} 个")
    print(f"  中置信度(0.8-0.9): {len(mid_conf)} 个")
    print(f"  低置信度(<0.8): {len(low_conf)} 个")

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
        if r.confidence >= 0.9:
            color = (0, 255, 0)  # 绿色
        elif r.confidence >= 0.8:
            color = (255, 255, 0)  # 黄色
        else:
            color = (255, 0, 0)  # 红色

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
    print(f"\n已保存调试图片: {debug_path}")
    print(f"绿色=高置信度(≥0.9), 黄色=中(0.8-0.9), 红色=低(<0.8)")


if __name__ == "__main__":
    main()
