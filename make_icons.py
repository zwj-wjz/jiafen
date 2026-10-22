#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 icon.svg 的设计生成 PNG 图标（iOS / Android 需要位图，SVG 不生效）。

生成：icon-180.png(apple-touch-icon) / icon-192.png / icon-512.png
运行：python make_icons.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

# 与 icon.svg 保持一致的设计参数
C0 = (102, 126, 234)   # #667eea
C1 = (118, 75, 162)    # #764ba2
WHITE = (255, 255, 255, 242)   # opacity 0.95
SIZES = [180, 192, 512]

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",   # Arial Bold
    r"C:\Windows\Fonts\ariblk.ttf",    # Arial Black
    r"C:\Windows\Fonts\arial.ttf",
]


def pick_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def bezier_points(p0, p1, p2, steps=48):
    """二次贝塞尔采样（对应 SVG 的 Q 指令）"""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def make(size):
    s = float(size)
    k = s / 512.0            # 缩放系数
    radius = 110 * k

    # 1) 对角线渐变背景
    grad = Image.new("RGBA", (size, size))
    px = []
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2.0 * size)
            if t > 1.0:
                t = 1.0
            px.append((int(C0[0] + (C1[0] - C0[0]) * t),
                       int(C0[1] + (C1[1] - C0[1]) * t),
                       int(C0[2] + (C1[2] - C0[2]) * t), 255))
    grad.putdata(px)

    # 2) 圆角矩形裁切
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=radius, fill=255)

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(out)

    # 3) 学士帽顶部（白色圆）
    cx, cy, r = 256 * k, 200 * k, 70 * k
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)

    # 4) 帽檐 / 书本（SVG path: M120 400 Q256 300 392 400 L392 430 Q256 360 120 430 Z）
    top = bezier_points((120 * k, 400 * k), (256 * k, 300 * k), (392 * k, 400 * k))
    bottom = bezier_points((392 * k, 430 * k), (256 * k, 360 * k), (120 * k, 430 * k))
    d.polygon(top + bottom, fill=WHITE)

    # 5) +1 文字
    font = pick_font(int(round(72 * k)))
    d.text((256 * k, 448 * k), "+1", font=font, fill=WHITE, anchor="mm")

    return out


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    for size in SIZES:
        img = make(size)
        path = os.path.join(base, "icon-%d.png" % size)
        img.save(path, "PNG", optimize=True)
        print("已生成 %s (%dx%d)" % (os.path.basename(path), size, size))


if __name__ == "__main__":
    main()
