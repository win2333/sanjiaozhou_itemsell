"""截图测试脚本 - 用于验证截图功能是否正常"""

import sys
sys.path.insert(0, '.')

from vision.capture import ScreenCapture


def main():
    """测试截图"""
    print("=" * 50)
    print("截图测试（全屏模式）")
    print("=" * 50)

    capture = ScreenCapture()

    # 1. 获取屏幕尺寸
    width, height = capture.get_screen_size()
    print(f"[1] 屏幕尺寸: {width}x{height}")

    # 2. 截取全屏
    print("[2] 截取全屏...")
    image = capture.capture_full_screen()
    print(f"    全屏图像尺寸: {image.shape}")

    # 3. 保存截图
    print("[3] 保存截图...")
    capture.save_image(image, "test_fullscreen.png")
    print("    已保存到: test_fullscreen.png")

    # 4. 显示截图
    print("[4] 即将显示截图...")
    capture.show_image(image, "全屏截图测试")

    print("\n" + "=" * 50)
    print("测试完成！")
    print("请确认弹出的图片窗口是否清晰显示全屏内容。")
    print("=" * 50)


if __name__ == "__main__":
    main()
