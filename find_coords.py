"""测试坐标 - 查找数量按钮正确位置"""
import pyautogui
import time

print("=" * 50)
print("坐标测试工具")
print("=" * 50)
print("移动鼠标到数量按钮位置，等待 3 秒...")
print("当前鼠标位置会实时显示")
print("按 Ctrl+C 退出")
print("=" * 50)

try:
    while True:
        x, y = pyautogui.position()
        print(f"位置: ({x}, {y})", end="\r")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n退出")
