# YOLO 数据集设计

## 目标

为 FPS 游戏物品检测训练 YOLO 模型，数据集采用全合成方式生成。

## 数据集设计

### 基础数据

| 项目 | 值 |
|------|-----|
| 普通物品模板 | 955个 (templates/) |
| 金色物品 | **完全不参与** |
| 背景图 | 1张 (backgrounds/empty.png, 675x908) |

### 训练集

| 项目 | 值 |
|------|-----|
| 图片数量 | ~114张（3轮 x 38张） |
| 每张物品数 | 50个（固定） |
| 物品缩放 | 0.8x - 1.2x |
| 放置区域 | x: 50-1750, y: 100-1000 |
| 物品间距 | 最小3像素 |

### 验证集

| 项目 | 值 |
|------|-----|
| 图片数量 | 50-100张 |
| 每张物品数 | 50个（固定） |
| 其他参数 | 与训练集一致 |

### 类别定义

| Class ID | 名称 | 说明 |
|----------|------|------|
| 0 | item | 普通可卖物品 |

金色物品不参与训练，真实游戏环境中通过其他机制过滤。

## YOLO 格式

标注文件格式：`class_id x_center y_center width height`（归一化到 [0,1]）

## 目录结构

```
yolo_train/
├── dataset/
│   ├── images/
│   │   ├── train/  (~114张 .png)
│   │   └── val/    (50-100张 .png)
│   └── labels/
│       ├── train/  (~114个 .txt)
│       └── val/    (50-100个 .txt)
├── dataset.yaml    # YOLO 训练配置
└── generate_dataset.py  # 数据集生成脚本
```

## 生成参数

```python
MIN_ITEMS_PER_IMAGE = 50
MAX_ITEMS_PER_IMAGE = 50
MIN_SCALE = 0.8
MAX_SCALE = 1.2
PLACE_X_OFFSET = 50
PLACE_Y_OFFSET = 100
PLACE_WIDTH = 1700
PLACE_HEIGHT = 900
MIN_ITEM_SPACING = 3
```

## 训练配置 (dataset.yaml)

```yaml
path: .../yolo_train/dataset
train: images/train
val: images/val
nc: 1
names: [item]
```

## 下一步

1. 运行 generate_dataset.py 生成数据集
2. 使用 YOLO 训练（建议 ultralytics）
3. 在真实游戏环境中测试检测效果
