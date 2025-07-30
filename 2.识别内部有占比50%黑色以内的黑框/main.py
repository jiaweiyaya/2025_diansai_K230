import time, os, sys
from media.sensor import *
from media.display import *
from media.media import *
import math

def rgb565_to_luminance(pixel):
    """将像素值转换为亮度值，处理None值情况"""
    if pixel is None: return 0
    if isinstance(pixel, int):
        r = (pixel >> 11) & 0x1F
        g = (pixel >> 5) & 0x3F
        b = pixel & 0x1F
        return (r * 299 + g * 587 + b * 114) // 1000
    elif isinstance(pixel, tuple):
        if len(pixel) >= 3: return (pixel[0]*299 + pixel[1]*587 + pixel[2]*114)//1000
        return pixel[0] if pixel else 0
    return 0

def safe_get_pixel(img, x, y):
    """安全获取像素值"""
    if 0 <= x < img.width() and 0 <= y < img.height():
        return img.get_pixel(x, y) or 0
    return 0

def has_black_shapes(img, x, y, w, h):
    """检测内部区域是否包含黑色形状"""
    center_x, center_y = x + w//2, y + h//2
    radius = min(w, h) // 3
    black_pixels = 0
    total_pixels = 0
    
    # 采样内部区域
    for i in range(x, x + w, 2):
        for j in range(y, y + h, 2):
            if (center_x - radius <= i <= center_x + radius and 
                center_y - radius <= j <= center_y + radius):
                luminance = rgb565_to_luminance(safe_get_pixel(img, i, j))
                if luminance < 50:  # 黑色像素
                    black_pixels += 1
                total_pixels += 1
    
    # 黑色像素占比应在25%-50%之间
    if total_pixels == 0: return False
    return 0 <= (black_pixels / total_pixels) <= 0.5

def is_target_rect(img, rect):
    """检查是否符合目标矩形条件"""
    x, y, w, h = rect
    if w < 30 or h < 30: return False
    
    # 检查黑色边缘
    edge_samples = []
    for i in [x, x + w - 1]:  # 左右边缘
        for j in range(y, y + h, max(1, h//5)):
            edge_samples.append(rgb565_to_luminance(safe_get_pixel(img, i, j)))
    for j in [y, y + h - 1]:  # 上下边缘
        for i in range(x, x + w, max(1, w//5)):
            edge_samples.append(rgb565_to_luminance(safe_get_pixel(img, i, j)))
    
    if not edge_samples or sum(edge_samples)/len(edge_samples) > 100:
        return False
    
    # 检查内部白色背景和黑色形状
    inner_x, inner_y = x + 3, y + 3
    inner_w, inner_h = max(0, w - 6), max(0, h - 6)
    if inner_w <= 0 or inner_h <= 0: return False
    
    inner_samples = []
    for i in range(inner_x, inner_x + inner_w, max(1, inner_w//10)):
        for j in range(inner_y, inner_y + inner_h, max(1, inner_h//10)):
            inner_samples.append(rgb565_to_luminance(safe_get_pixel(img, i, j)))
    
    if not inner_samples: return False
    
    # 内部平均亮度应较高（白色背景）
    if sum(inner_samples)/len(inner_samples) < 100: return False
    
    # 检查是否有黑色形状
    return has_black_shapes(img, inner_x, inner_y, inner_w, inner_h)

try:
    sensor = Sensor(width=1280, height=960)
    sensor.reset()
    sensor.set_framesize(Sensor.QVGA)
    sensor.set_pixformat(Sensor.RGB565)
    
    Display.init(Display.ST7701, width=640, height=480, to_ide=True)
    MediaManager.init()
    sensor.run()
    clock = time.clock()

    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot()
        
        for r in img.find_rects(threshold=8000):
            rect = r.rect()
            if is_target_rect(img, rect):
                # 绘制红色矩形框
                img.draw_rectangle([v for v in rect], color=(0, 255, 0), thickness=2)
                # 绘制中心标记
                x, y, w, h = rect
                img.draw_circle(x + w//2, y + h//2, 5, color=(0, 255, 0), thickness=-1)
        
        Display.show_image(img, x=round((640 - img.width()) / 2), 
                          y=round((480 - img.height()) / 2))
        print(f"FPS: {clock.fps()}")

except KeyboardInterrupt as e:
    print("程序停止:", e)
except Exception as e:
    print(f"发生错误: {e}")
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    MediaManager.deinit()
    time.sleep_ms(100)