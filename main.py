"""自动卖货助手 - 主入口"""

import time

import keyboard

from vision.capture import ScreenCapture
from vision.recognizer import TemplateRecognizer
from vision.price_reader import PriceReader
from control.mouse import MouseController
from control.keyboard import KeyboardController
from core.loop import AutoSellLoop
from config import (
    TEMPLATE_MATCH_THRESHOLD,
    TEMPLATES_DIR,
    USE_GPU_TEMPLATE_RECOGNITION,
)


def init_components() -> AutoSellLoop:
    """初始化所有组件"""
    # 加载物品模板
    item_recognizer = TemplateRecognizer(
        str(TEMPLATES_DIR), threshold=TEMPLATE_MATCH_THRESHOLD, use_gpu=USE_GPU_TEMPLATE_RECOGNITION
    )
    item_templates = item_recognizer.load_templates()

    if not item_templates:
        print(f"\n警告: 没有找到物品模板图片！")
        print(f"请将物品截图放到: {TEMPLATES_DIR}")

    # 创建主循环
    return AutoSellLoop(
        item_recognizer=item_recognizer,
        capture=ScreenCapture(),
        mouse=MouseController(),
        keyboard=KeyboardController(),
        price_reader=PriceReader(),
    )


def main():
    """主函数"""
    # 控制台窗口保持最前
    from core.loop import AutoSellLoop
    AutoSellLoop._keep_console_topmost()

    # 初始化组件
    loop = init_components()

    # F8 停止回调（仅设标志位，由主线程处理）
    def on_f8():
        if not loop.status.stop_requested:
            loop.status.stop_requested = True
            loop.status.status = "停止请求中"

    # 注册 F8 热键（全局生效，游戏前台也能用）
    keyboard.add_hotkey("f8", on_f8)

    # 倒计时 3 秒
    for _ in range(3):
        if loop.status.stop_requested:
            break
        time.sleep(1)

    # 运行，直到 F8 或 Ctrl+C
    try:
        while not loop.status.stop_requested:
            action = loop.start()
            if action == "exit":
                break
    except KeyboardInterrupt:
        loop.status.stop_requested = True
        loop.status.status = "已停止"
        from utils.status_panel import render
        render(loop.status)
    finally:
        from utils.logger import close_logger
        close_logger()
        keyboard.unhook_all()


if __name__ == "__main__":
    main()
