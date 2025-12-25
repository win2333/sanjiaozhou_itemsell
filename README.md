# sanjiaozhou_itemsell

FPS 游戏自动卖货助手 - 自动识别物品并上架交易行。

## 功能

- 自动识别仓库物品（模板匹配）
- 一键卖出到交易行
- OCR 价格识别与智能定价
- F8 开始/停止，F9 退出
- 卖出统计与日志记录

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
5. 按 **F8** 重新开始，**F9** 退出

## 配置

修改 `config.py`：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TEMPLATE_MATCH_THRESHOLD` | 0.98 | 物品识别置信度 |
| `USE_FIXED_COORDINATES` | True | 使用固定坐标加速 |
| `USE_CLIPBOARD_INPUT` | True | 剪贴板输入价格 |

## 项目结构

```
sanjiaozhouGame/
├── main.py              # 主入口
├── config.py            # 配置文件
├── core/                # 核心逻辑
│   ├── loop.py          # 自动卖出循环
│   ├── hotkey.py        # 热键管理
│   └── menu.py          # 统计菜单
├── vision/              # 视觉识别
│   ├── capture.py       # 屏幕截图
│   ├── recognizer.py    # 模板识别
│   └── price_reader.py  # 价格 OCR
├── control/             # 操作控制
│   ├── mouse.py         # 鼠标控制
│   └── keyboard.py      # 键盘控制
├── utils/               # 工具
│   └── logger.py        # 日志系统
└── templates/           # 物品模板图片
```

## 添加新物品模板

1. 截图保存到 `templates/` 目录
2. 文件名即为物品名称（如 `AK47.png`）
3. 建议四边各留 2px 空白

## 日志

日志保存在 `logs/selling_YYYYMMDD_HHMMSS.txt`

## 注意事项

- 确保游戏窗口可见，不要最小化
- 分辨率建议 1920x1080 或更高
- 首次运行 OCR 会下载模型，需等待
