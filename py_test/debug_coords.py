"""坐标偏移调试工具 - 点击设置价格输入框位置"""

import sys
sys.path.insert(0, '.')

import cv2
import numpy as np
from vision.capture import ScreenCapture
from vision.recognizer import TemplateRecognizer
from config import UI_TEMPLATES_DIR, UI_TEMPLATE_THRESHOLD, DEBUG_DIR


def main():
    print("=" * 50)
    print("坐标偏移调试工具")
    print("=" * 50)

    capture = ScreenCapture()
    recognizer = TemplateRecognizer(str(UI_TEMPLATES_DIR), threshold=UI_TEMPLATE_THRESHOLD)
    templates = recognizer.load_templates()
    print(f"已加载 {len(templates)} 个UI模板: {templates}")

    if not templates:
        print("没有找到UI模板！")
        print(f"模板目录: {UI_TEMPLATES_DIR}")
        return

    print("\n操作步骤：")
    print("1. 确保游戏窗口打开，可以看到 upload2 和价格输入框")
    print("2. 按 Enter 截图")
    print("3. 用鼠标点击价格输入框的位置")
    print("4. 程序会计算偏移量并显示结果")
    print("5. 根据图片调整，如果不对可以重新操作")
    print("6. 确认后把偏移量填到代码里")

    input("\n按 Enter 截图（然后用鼠标点击价格输入框）...")

    # 截图
    image = capture.capture_full_screen()
    height, width = image.shape[:2]

    # 识别UI元素
    results = recognizer.recognize(image, draw_debug=False)

    if not results:
        print("未找到任何UI模板！")
        return

    print(f"找到 {len(results)} 个UI元素:")
    for r in results:
        print(f"  {r.template_name}: ({r.center_x}, {r.center_y})")

    # 找 upload2
    upload2 = None
    for r in results:
        if r.template_name == "upload2":
            upload2 = r
            break

    if not upload2:
        print("未找到 upload2 模板！")
        return

    # 在图片上画红框
    cv2.rectangle(image, (upload2.x, upload2.y),
                 (upload2.x + upload2.width, upload2.y + upload2.height),
                 (0, 0, 255), 3)
    cv2.circle(image, (upload2.center_x, upload2.center_y), 8, (0, 255, 0), -1)

    # 保存图片用于点击
    click_img_path = str(DEBUG_DIR / "debug_click.png")
    cv2.imwrite(click_img_path, image)

    print(f"\n图片已保存，请查看并点击价格输入框位置")
    print(f"点击后把坐标告诉程序")

    # 显示图片
    window_name = "点击价格输入框位置"
    cv2.imshow(window_name, image)

    # 鼠标点击回调
    click_pos = [None]

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            click_pos[0] = (x, y)
            print(f"你点击的位置: ({x}, {y})")

    cv2.setMouseCallback(window_name, mouse_callback)

    print("\n请用鼠标点击价格输入框的位置...")
    print("点击后会显示坐标")

    # 等待点击
    while True:
        cv2.imshow(window_name, image)
        key = cv2.waitKey(100)

        if click_pos[0] is not None:
            break

    cv2.destroyAllWindows()

    # 计算偏移量
    click_x, click_y = click_pos[0]
    offset_x = click_x - upload2.center_x
    offset_y = click_y - upload2.center_y

    print("\n" + "=" * 50)
    print("计算结果：")
    print("=" * 50)
    print(f"upload2 中心: ({upload2.center_x}, {upload2.center_y})")
    print(f"你点击的位置: ({click_x}, {click_y})")
    print(f"\n偏移量 (offset_x, offset_y): ({offset_x}, {offset_y})")
    print("=" * 50)

    # 生成验证图片
    verification_image = image.copy()

    # 画从 upload2 到点击位置的线
    cv2.line(verification_image, (upload2.center_x, upload2.center_y),
            (click_x, click_y), (255, 0, 0), 2)

    # 画点击位置
    cv2.circle(verification_image, (click_x, click_y), 10, (255, 0, 0), -1)

    # 用偏移量再画一个预测点
    pred_x = upload2.center_x + offset_x
    pred_y = upload2.center_y + offset_y
    cv2.circle(verification_image, (pred_x, pred_y), 15, (0, 165, 255), -1)

    cv2.imwrite(str(DEBUG_DIR / "debug_verification.png"), verification_image)

    print(f"\n验证图片已保存: {DEBUG_DIR / \"debug_verification.png\"}")
    print("红色=upload2 绿色=upload2中心 蓝色=你点击的位置 橙色=预测点")

    # 显示验证
    print("\n按 Enter 退出...")
    input()


if __name__ == "__main__":
    main()
