"""批量裁剪模板图片四周边框（每边2像素）- 支持中文文件名"""
import cv2
import numpy as np
from pathlib import Path

# 使用相对于当前脚本的路径
templates_dir = Path(__file__).parent.parent / "templates"
crop = 2  # 每边裁剪像素数

def imread(path):
    """支持中文路径的图片读取"""
    with open(path, 'rb') as f:
        data = np.frombuffer(f.read(), np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

def imwrite(path, img):
    """支持中文路径的图片保存"""
    _, data = cv2.imencode('.png', img)
    with open(path, 'wb') as f:
        f.write(data.tobytes())

count = 0
for png_file in templates_dir.glob("*.png"):
    img = imread(str(png_file))
    if img is None:
        print(f"跳过: {png_file.name} (无法读取)")
        continue

    h, w = img.shape[:2]
    # 确保图片足够大
    if h <= crop * 2 or w <= crop * 2:
        print(f"跳过: {png_file.name} (图片太小 {w}x{h})")
        continue

    cropped = img[crop:h-crop, crop:w-crop]
    imwrite(str(png_file), cropped)
    count += 1
    print(f"裁剪 {count}: {png_file.name}")

print(f"\n完成！共裁剪 {count} 个文件")
