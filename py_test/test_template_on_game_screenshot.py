"""模板匹配在实际游戏截图上的检测效果测试"""

import sys
sys.path.insert(0, '.')

import cv2
import time
from pathlib import Path

from vision.recognizer import TemplateRecognizer
from config import TEMPLATES_DIR, TEMPLATE_MATCH_THRESHOLD

DEBUG_DIR = Path("debug")
OUTPUT_DIR = Path("debug/template_test")
OUTPUT_DIR.mkdir(exist_ok=True)

recognizer = TemplateRecognizer(
    templates_dir=str(TEMPLATES_DIR),
    threshold=TEMPLATE_MATCH_THRESHOLD,
    use_gpu=False,  # 默认 CPU 模式更稳定
)
loaded = recognizer.load_templates()
print(f"加载了 {len(loaded)} 个模板")

screenshots = sorted(DEBUG_DIR.glob("000[1-9].png"))
if not screenshots:
    print("未找到 000[1-9].png 截图，请先获取游戏截图")
    exit(1)

for img_path in screenshots:
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"无法读取图片: {img_path.name}")
        continue

    start = time.time()
    results = recognizer.recognize(img)
    elapsed = (time.time() - start) * 1000

    # 绘制结果
    for r in results:
        x1, y1 = r.x, r.y
        x2, y2 = r.x + r.width, r.y + r.height
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(img, f"{r.confidence:.2f}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    out_path = OUTPUT_DIR / img_path.name
    cv2.imwrite(str(out_path), img)
    print(f"{img_path.name}: {len(results)} 个检测，耗时 {elapsed:.1f}ms，保存至 {out_path}")
