# sanjiaozhou_itemsell

FPS 游戏自动卖货助手 - 自动识别物品并上架交易行。

> 使用 Claude Code（MiniMax 2.1 模型）辅助开发

## 功能

- 自动识别仓库物品（模板匹配 + 多线程加速）
- 一键卖出到交易行（9 步自动化流程）
- OCR 价格识别与智能定价（P1*0.95 算法）
- MSE 图像验证，防止误操作
- F8 开始/停止，Ctrl+C 退出
- 卖出统计与详细日志

## 环境要求

- Python 3.10+
- Windows 10/11
- NVIDIA GPU（推荐，用于 OCR 加速）

## 安装

```bash
pip install -r requirements.txt
```

## 使用

1. 进入游戏，打开仓库界面
2. 运行 `python main.py`
3. 按 **F8** 开始自动卖货
4. 再次按 **F8** 停止，显示统计
5. 按 **F8** 重新开始，**Ctrl+C** 退出

## 项目结构

```
sanjiaozhouGame/
+-- main.py                    # 主入口程序
+-- config.py                  # 全局配置（参数、路径）
+-- core/                      # 核心控制模块
|   +-- loop.py               # 主循环逻辑（AutoSellLoop）
|   +-- hotkey.py             # 热键监听管理（HotkeyManager）
|   +-- menu.py               # 简洁菜单系统（SimpleMenu）
+-- vision/                    # 视觉识别模块
|   +-- capture.py            # 屏幕截图（ScreenCapture）
|   +-- recognizer.py         # 模板识别（TemplateRecognizer）
|   +-- price_reader.py       # 价格识别（PriceReader + OCR）
+-- control/                   # 输入控制模块
|   +-- mouse.py              # 鼠标控制（MouseController）
|   +-- keyboard.py           # 键盘控制（KeyboardController）
+-- utils/                     # 工具模块
|   +-- logger.py             # 日志系统（双通道输出）
+-- templates/                 # 模板图片目录
|   +-- ui/                   # UI元素模板（sell1, upload1, upload2）
|   +-- [200+个物品模板]      # 物品截图模板
+-- logs/                      # 日志输出目录
```

## 核心模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 入口 | main.py | 程序启动、状态机、信号处理 |
| 核心 | core/loop.py | 主循环、卖出逻辑、验证 |
| 视觉 | vision/capture.py | 屏幕截图 |
| 视觉 | vision/recognizer.py | 模板匹配、多线程识别 |
| 视觉 | vision/price_reader.py | OCR 价格识别 |
| 控制 | control/mouse.py | 鼠标移动、点击、右键 |
| 控制 | control/keyboard.py | 键盘输入、组合键 |
| 热键 | core/hotkey.py | F8/F9 热键监听 |
| 工具 | utils/logger.py | 双通道日志 |

## 执行流程

```
main.py: main()
|
+-- [初始化阶段]
|   +-- signal.signal(SIGINT, signal_handler)
|   +-- get_ocr_reader()  # 延迟加载 EasyOCR
|   +-- init_components()
|       +-- HotkeyManager()
|       +-- TemplateRecognizer(物品模板) -> load_templates()
|       +-- TemplateRecognizer(UI模板) -> load_templates()
|       +-- PriceReader()
|       +-- AutoSellLoop(注入所有组件)
|       +-- SimpleMenu(统计回调)
|
+-- [状态机循环]
|
+-- F8 按下 -> on_toggle()
|   +-- state = 'running'
|   +-- threading.Thread(target=_run_loop)
|       +-- loop.start()
|           +-- while self.state.is_running:
|               +-- _run_one_cycle()
|                   |
|                   +-- 1. capture_full_screen()  # 全屏截图
|                   +-- 2. item_recognizer.recognize()  # 物品识别
|                   +-- 3. deduplicate()  # 空间去重
|                   +-- 4. deduplicate_by_name()  # 名称去重
|                   |
|                   +-- 遍历每个物品:
|                   |   |
|                   |   +-- _verify_item()  # MSE 图像比较
|                   |   +-- _sell_item_with_log()  # 9 步卖出
|                   |
|                   +-- time.sleep(idle_delay)
|
+-- 再次 F8 -> on_toggle()
    +-- state = 'menu'
    +-- menu.show()
        +-- F8 -> restart -> state = 'running'
        +-- F9/Ctrl+C -> exit
```

## 卖出流程（9 步）

```
_sell_item_with_log(record)
|
+-- 步骤 1: 鼠标移动到 (x, y)
+-- 步骤 2: 右键点击 (x, y)
+-- 步骤 3: 识别 sell1 -> 点击
+-- 步骤 4: 识别 upload1 -> 点击
+-- 步骤 5: 识别 upload2 -> 点击
+-- 步骤 6: 点击数量按钮 3 次
+-- 步骤 7: OCR 识别价格（P1/P2）
+-- 步骤 8: 计算售价 (P1*0.95) -> 输入
+-- 步骤 9: 点击 upload2 确认卖出
```

## 配置参数

修改 `config.py`：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TEMPLATE_MATCH_THRESHOLD` | 0.98 | 物品匹配阈值 |
| `UI_TEMPLATE_THRESHOLD` | 0.9 | UI 元素匹配阈值 |
| `DEDUP_DISTANCE` | 30 | 去重距离（像素） |
| `VERIFY_MSE_THRESHOLD` | 500 | 验证 MSE 阈值 |
| `USE_FIXED_COORDINATES` | True | 使用固定坐标 |
| `USE_CLIPBOARD_INPUT` | True | 剪贴板输入价格 |

## 添加新物品模板

1. 截图保存到 `templates/` 目录
2. 文件名即为物品名称（如 `AK47.png`）
3. 建议四边各留 2px 空白
4. 支持中文文件名

## 日志

- 位置：`logs/selling_YYYYMMDD_HHMMSS.txt`
- 控制台：简洁输出（卖出状态、统计）
- 文件：详细记录（所有操作、识别结果）

## 注意事项

- 确保游戏窗口可见，不要最小化
- 分辨率建议 1920x1080 或更高
- 首次运行 OCR 会下载模型，需等待
- 物品识别区域：x >= 1150（右半边）
