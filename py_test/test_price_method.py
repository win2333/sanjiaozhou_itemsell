"""测试价格输入流程

运行方式:
1. 打开游戏，进入卖货界面
2. 运行: python py_test/test_price_method.py
"""

import sys
import time

sys.path.insert(0, ".")

from config import (
    PRICE_DIRECT_CLICK_X,
    UPLOAD2_X,
    UPLOAD2_Y,
    PRICE_OFFSET_X,
    PRICE_OFFSET_Y,
)
from control.mouse import MouseController
from control.keyboard import KeyboardController

# 价格输入框固定坐标
PRICE_INPUT_X = UPLOAD2_X + PRICE_OFFSET_X
PRICE_INPUT_Y = UPLOAD2_Y + PRICE_OFFSET_Y


def test_price_input_flow():
    """测试价格输入流程"""
    print("=" * 50)
    print("价格输入方法测试")
    print("=" * 50)

    print(f"\n[配置]")
    print(f"  PRICE_DIRECT_CLICK_X = {PRICE_DIRECT_CLICK_X}")

    mouse = MouseController()
    keyboard = KeyboardController()

    print(f"\n[流程说明]")
    print(f"  1. 点击价格输入框（当前鼠标位置）")
    print(f"  2. 等待0.5秒")
    print(f"  3. 按Backspace清除")
    print(f"  4. 等待0.1秒")
    print(f"  5. 点击坐标 ({PRICE_DIRECT_CLICK_X}, 当前鼠标Y)")

    print(f"\n[价格输入框坐标]")
    print(f"  UPLOAD2 = ({UPLOAD2_X}, {UPLOAD2_Y})")
    print(f"  PRICE_OFFSET = ({PRICE_OFFSET_X}, {PRICE_OFFSET_Y})")
    print(f"  PRICE_INPUT = ({PRICE_INPUT_X}, {PRICE_INPUT_Y})")

    print(f"\n[等待3秒后开始执行...]")
    print("  请确保游戏窗口可见！")
    time.sleep(3)

    # Step 1: 点击价格输入框
    print(f"[Step 1] 点击价格输入框 ({PRICE_INPUT_X}, {PRICE_INPUT_Y})...")
    mouse.click(PRICE_INPUT_X, PRICE_INPUT_Y)
    time.sleep(0.5)

    # Step 2: 按Backspace
    print(f"[Step 2] 按 Backspace...")
    keyboard.press("backspace")
    time.sleep(0.1)

    # Step 3: 点击860位置（Y坐标固定）
    print(f"[Step 3] 点击 ({PRICE_DIRECT_CLICK_X}, {PRICE_INPUT_Y})...")
    mouse.click(PRICE_DIRECT_CLICK_X, PRICE_INPUT_Y)

    print("\n[完成] 测试执行完毕！")
    print(f"\n如果价格输入成功（显示0），说明新方法有效")
    print(f"如果价格输入失败（显示其他值），需要调整坐标或时机")


if __name__ == "__main__":
    test_price_input_flow()
