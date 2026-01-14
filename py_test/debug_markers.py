"""坐标标记工具 - 在截图上标记所有UI元素"""

import sys
sys.path.insert(0, '.')

import cv2
from PIL import Image, ImageDraw, ImageFont
from vision.capture import ScreenCapture
from config import DEBUG_DIR


def draw_chinese_text(img, text, pos, font_size=20, color=(255, 255, 255)):
    """在图片上绘制中文"""
    # 转换 OpenCV 图片为 PIL
    img_pil = Image.fromarray(img)
    draw = ImageDraw.Draw(img_pil)

    # 尝试加载中文字体
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simsun.ttc",     # 宋体
    ]

    font = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except:
            continue

    if font is None:
        # 如果找不到中文字体，使用默认
        font = ImageFont.load_default()

    # 绘制文字
    draw.text(pos, text, font=font, fill=color)

    # 转回 OpenCV 图片
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def main():
    print("=" * 50)
    print("坐标标记工具")
    print("=" * 50)

    capture = ScreenCapture()

    print("\n按 Enter 截图并标记...")
    input()

    # 截图
    image = capture.capture_full_screen()
    original_image = image.copy()

    # 定义所有UI元素坐标
    elements = {
        "价格输入框": {"left": 1160, "top": 626, "right": 1463, "bottom": 662, "color": (0, 255, 0)},  # 绿色
        "价格减(-1)": {"left": 1112, "top": 625, "right": 1150, "bottom": 662, "color": (255, 0, 0)},  # 蓝色
        "价格加(+1)": {"left": 1475, "top": 625, "right": 1510, "bottom": 662, "color": (0, 0, 255)},  # 红色
        "数量减(-1)": {"left": 1112, "top": 542, "right": 1150, "bottom": 580, "color": (255, 255, 0)},  # 青色
        "数量加(+1)": {"left": 1474, "top": 540, "right": 1510, "bottom": 580, "color": (0, 255, 255)},  # 黄色
        "滑块区域": {"left": 1165, "top": 546, "right": 1455, "bottom": 572, "color": (128, 0, 128)},  # 紫色
    }

    # 标记所有元素
    for name, elem in elements.items():
        x1, y1 = elem["left"], elem["top"]
        x2, y2 = elem["right"], elem["bottom"]
        color = elem["color"]

        # 画矩形框
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

        # 画中心点
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        cv2.circle(image, (cx, cy), 6, color, -1)

        # 打印坐标
        print(f"{name}: 中心 ({cx}, {cy})")

    # 保存原图（不含中文）
    output_path = str(DEBUG_DIR / "debug_markers.png")
    cv2.imwrite(output_path, image)
    print(f"\n图片已保存到: {output_path}")
    print("（不含中文标签，矩形框位置正确）")

    # 显示
    capture.show_image(image, "坐标标记")


if __name__ == "__main__":
    import numpy as np
    main()
