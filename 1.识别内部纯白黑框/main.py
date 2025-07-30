import time, os, sys
from media.sensor import *
from media.display import *
from media.media import *

def rgb565_to_luminance(pixel):
    """
    将像素值转换为亮度值(0-255)，处理None值情况
    """
    if pixel is None:
        return 0  # 默认返回黑色亮度
    
    # 如果是RGB565格式的整数
    if isinstance(pixel, int):
        try:
            # 提取RGB分量 (RGB565格式)
            r = (pixel >> 11) & 0x1F  # 5位红色
            g = (pixel >> 5) & 0x3F   # 6位绿色
            b = pixel & 0x1F          # 5位蓝色
            # 转换为8位并计算亮度
            return (r * 299 + g * 587 + b * 114) // 1000
        except:
            return 0
    
    # 如果是元组格式(RGB)
    elif isinstance(pixel, tuple):
        if len(pixel) >= 3:  # RGB格式
            r, g, b = pixel[:3]
            return (r * 299 + g * 587 + b * 114) // 1000
        elif len(pixel) == 1:  # 灰度格式
            return pixel[0]
    
    return 0  # 其他未知格式返回0

def safe_get_pixel(img, x, y):
    """
    安全获取像素值，防止越界和None值
    """
    if x < 0 or y < 0 or x >= img.width() or y >= img.height():
        return 0  # 越界返回黑色
    pixel = img.get_pixel(x, y)
    return pixel if pixel is not None else 0

def is_white_inside_black_rect(img, rect):
    """
    检查矩形区域是否是边缘黑色、内部白色
    rect格式: (x, y, w, h)
    """
    x, y, w, h = rect
    if w < 20 or h < 20:  # 忽略太小的矩形
        return False
    
    edge_thickness = 3
    edge_samples = []
    
    # 采样边缘像素
    for i in [x, x + w - 1]:  # 左右边缘
        for j in range(y, y + h, max(1, h//10)):
            luminance = rgb565_to_luminance(safe_get_pixel(img, i, j))
            edge_samples.append(luminance)
    
    for j in [y, y + h - 1]:  # 上下边缘
        for i in range(x, x + w, max(1, w//10)):
            luminance = rgb565_to_luminance(safe_get_pixel(img, i, j))
            edge_samples.append(luminance)
    
    if not edge_samples:
        return False
    
    edge_avg = sum(edge_samples) / len(edge_samples)
    if edge_avg > 100:  # 边缘不够黑
        return False
    
    # 检查内部是否为白色
    inner_x = x + edge_thickness
    inner_y = y + edge_thickness
    inner_w = max(0, w - 2 * edge_thickness)
    inner_h = max(0, h - 2 * edge_thickness)
    
    if inner_w <= 0 or inner_h <= 0:
        return False
    
    # 采样内部区域
    center_x = inner_x + inner_w // 2
    center_y = inner_y + inner_h // 2
    sample_size = min(inner_w, inner_h) // 3
    
    inner_samples = []
    for i in range(center_x - sample_size//2, center_x + sample_size//2 + 1, 2):
        for j in range(center_y - sample_size//2, center_y + sample_size//2 + 1, 2):
            luminance = rgb565_to_luminance(safe_get_pixel(img, i, j))
            inner_samples.append(luminance)
    
    if not inner_samples:
        return False
    
    inner_avg = sum(inner_samples) / len(inner_samples)
    return inner_avg > 180  # 内部足够白

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
            rect = r.rect()  # (x, y, w, h)
            
            if is_white_inside_black_rect(img, rect):
                # 绘制红色矩形框
                img.draw_rectangle([v for v in rect], color=(0, 255, 0))
#                # 显示文字
#                x, y, w, h = rect
#                try:
#                    img.draw_string(x + w//2 - 20, y + h//2 - 5, 
#                                  "Target", color=(255, 0, 0))
#                except:
#                    try:
#                        # 尝试使用高级绘制
#                        img.draw_string_advanced(x + w//2 - 20, y + h//2 - 5,
#                                               "Target", color=(255, 0, 0),
#                                               scale=1, mono_space=False)
#                    except:
#                        pass  # 如果都不可用则跳过文字
        
        Display.show_image(img, x=round((640 - img.width()) / 2), 
                          y=round((480 - img.height()) / 2))
        print(f"FPS: {clock.fps()}")

except KeyboardInterrupt as e:
    print("用户停止:", e)
except BaseException as e:
    print(f"异常: {e}")
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()