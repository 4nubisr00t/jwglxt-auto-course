"""
make_icon.py - 为「湘大选课·漆黑结界」生成桌面快捷方式图标（.ico）
视觉方案：基于用户指定的二次元手绘风【红瞳结界·契约之眼】原图
规格：输出包含 [16, 24, 32, 48, 64, 128, 256] 尺寸的 assets/icon.ico，
      以及 assets/logo_preview.png (256x256) 与 assets/icon_16px_check.png (16px 放大 8 倍自检图)。
"""

import os
import sys
import shutil
import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SOURCE_IMG = os.path.join(ASSETS_DIR, "logo_source.jpg")


def process_master_image():
    """读取母图并应用平滑抗锯齿圆形蒙版"""
    if not os.path.exists(SOURCE_IMG):
        raise FileNotFoundError(f"未找到母图: {SOURCE_IMG}")

    im = Image.open(SOURCE_IMG).convert("RGBA")
    w, h = im.size
    cx, cy = w / 2.0, h / 2.0 + 1.0  # 图像中心微调以精准居中魔法阵 (512, 513)

    # 圆形遮罩半径 (R=504 精准包络外围结界光环与樱刃余辉，平滑羽化抗锯齿)
    r_mask = 504.0
    feather_width = 3.0

    y_coords, x_coords = np.ogrid[:h, :w]
    dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)
    alpha = np.clip((r_mask - dist) / feather_width, 0.0, 1.0) * 255.0

    arr = np.array(im)
    arr[:, :, 3] = alpha.astype(np.uint8)
    master_canvas = Image.fromarray(arr, "RGBA")
    return master_canvas


def generate_all_assets():
    """生成所有规格的图标与预览文件"""
    print("[*] 正在处理 1024x1024 高清二次元手绘红瞳结界母图...")
    master = process_master_image()

    # 目标尺寸列表
    sizes = [16, 24, 32, 48, 64, 128, 256]
    resized_images = []

    print("[*] 正在通过 LANCZOS 降采样生成多尺寸图像梯队...")
    for s in sizes:
        img_s = master.resize((s, s), Image.Resampling.LANCZOS)
        resized_images.append(img_s)

    # 1. 保存 assets/icon.ico（含所有尺寸）
    ico_path = os.path.join(ASSETS_DIR, "icon.ico")
    print(f"[*] 保存图标文件到: {ico_path}")
    img_256 = resized_images[-1]
    other_sizes = [(s, s) for s in sizes]
    img_256.save(ico_path, format="ICO", sizes=other_sizes)

    # 2. 保存 256x256 高清预览 PNG
    preview_path = os.path.join(ASSETS_DIR, "logo_preview.png")
    print(f"[*] 保存 256x256 预览图到: {preview_path}")
    img_256.save(preview_path, format="PNG")

    # 3. 生成 16px 放大 8 倍自检图 (128x128)
    img_16 = resized_images[0]
    img_16_upscaled = img_16.resize((128, 128), Image.Resampling.NEAREST)
    check_path = os.path.join(ASSETS_DIR, "icon_16px_check.png")
    print(f"[*] 保存 16px 自检放大图到: {check_path}")
    img_16_upscaled.save(check_path, format="PNG")

    print("[OK] 全部图标及预览资源生成完毕！")


if __name__ == "__main__":
    generate_all_assets()
