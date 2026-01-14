"""自动卖货助手 - 主入口"""

import signal
import sys
import threading
import time
from pathlib import Path

from vision.capture import ScreenCapture
from vision.recognizer import TemplateRecognizer
from vision.price_reader import PriceReader, get_ocr_reader
from control.mouse import MouseController
from control.keyboard import KeyboardController
from core.hotkey import HotkeyManager
from core.loop import AutoSellLoop
from core.menu import SimpleMenu
from config import (
    TEMPLATE_MATCH_THRESHOLD,
    UI_TEMPLATE_THRESHOLD,
    TEMPLATES_DIR,
    UI_TEMPLATES_DIR,
)


# 全局实例（重新开始时复用）
_loop: AutoSellLoop = None
_menu: SimpleMenu = None
_hotkey: HotkeyManager = None
_logs_dir = Path(__file__).parent / "logs"  # 缓存日志目录


def signal_handler(signum, frame):
    """信号处理"""
    from utils.logger import close_logger
    close_logger()
    print("\n正在退出...")
    sys.exit(0)


def init_components() -> tuple:
    """初始化所有组件（只执行一次）"""
    global _loop, _menu, _hotkey

    if _loop is not None:
        return _loop, _menu, _hotkey

    _hotkey = HotkeyManager()

    # 加载物品模板
    item_recognizer = TemplateRecognizer(
        str(TEMPLATES_DIR), threshold=TEMPLATE_MATCH_THRESHOLD
    )
    item_templates = item_recognizer.load_templates()
    print(f"已加载 {len(item_templates)} 个物品模板")

    if not item_templates:
        print("\n警告: 没有找到物品模板图片！")
        print(f"请将物品截图放到: {TEMPLATES_DIR}")

    # 加载UI模板
    ui_recognizer = TemplateRecognizer(
        str(UI_TEMPLATES_DIR), threshold=UI_TEMPLATE_THRESHOLD
    )
    ui_templates = ui_recognizer.load_templates()

    # 初始化价格识别器
    price_reader = PriceReader()

    # 创建主循环
    _loop = AutoSellLoop(
        item_recognizer=item_recognizer,
        ui_recognizer=ui_recognizer,
        capture=ScreenCapture(),
        mouse=MouseController(),
        keyboard=KeyboardController(),
        price_reader=price_reader,
    )

    # 初始化菜单
    _menu = SimpleMenu(
        get_stats_func=lambda: _loop.get_stats(),
        get_logs_dir_func=lambda: _logs_dir
    )

    return _loop, _menu, _hotkey


def main():
    """主函数"""
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 50)
    print("FPS 游戏自动卖货助手")
    print("按 F8 开始/停止")
    print("=" * 50)

    # 预加载 OCR（首次运行会下载模型，需等待）
    print("\n正在初始化 OCR（首次运行会下载模型，请稍候）...")
    ocr = get_ocr_reader()
    if ocr is None:
        print("[警告] OCR 初始化失败，价格识别功能不可用")
    else:
        print("OCR 初始化完成！")

    # 初始化组件
    loop, menu, hotkey = init_components()

    # 状态: 'idle', 'running', 'menu'
    state = 'idle'
    menu_action = None

    # 菜单模式下的热键回调
    def on_restart():
        nonlocal menu_action, state
        menu_action = "restart"
        state = 'running'

    def on_exit():
        nonlocal menu_action
        menu_action = "exit"

    # 运行模式下的热键回调
    def on_toggle():
        nonlocal state
        if state == 'running':
            state = 'menu'
            loop.stop()
            menu.show()
        else:
            state = 'running'
            thread = threading.Thread(target=_run_loop, args=(loop, lambda: state == 'running'), daemon=True)
            thread.start()

    # 注册热键
    hotkey.register_start_stop("f8", on_toggle, on_toggle)

    # 菜单模式监听 F8/F9
    def start_menu_listener():
        nonlocal menu_action
        hotkey.register("f8", on_restart)
        hotkey.register("f9", on_exit)
        while menu_action is None:
            hotkey.process_once()
            time.sleep(0.05)

    # 监听循环
    while True:
        if state == 'running':
            hotkey.start_listening()
        elif state == 'menu':
            menu_action = None
            start_menu_listener()
            if menu_action == "restart":
                print("\n重新开始...")
            elif menu_action == "exit":
                print("\n正在退出...")
                from utils.logger import close_logger
                close_logger()
                hotkey.stop_listening()
                sys.exit(0)
        else:  # idle
            hotkey.start_listening()


def _run_loop(loop: AutoSellLoop, is_running_check):
    """运行主循环（用于线程）"""
    while is_running_check():
        action = loop.start()
        if action == "exit":
            break


if __name__ == "__main__":
    main()
