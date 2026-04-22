import glob
import sys
import time
from collections import deque
from datetime import datetime

sys.path.insert(0, "lib")

import psutil
from PIL import Image, ImageDraw
from library.lcd.lcd_comm_weact_b import LcdCommWeActB
from library.lcd.lcd_comm import Orientation


def find_font(name):
    for path in glob.glob(f"/usr/share/fonts/**/{name}", recursive=True):
        return path
    return name


FONT = find_font("NotoSans-Bold.ttf")
FONT_SM = find_font("NotoSans-Regular.ttf")
W = 80
WHITE = (255, 255, 255)
GRAY = (160, 160, 160)
BLACK = (0, 0, 0)
LIGHT_BLUE = (100, 180, 255)
RED = (255, 60, 60)

GRAPH_H = 50
GRAPH_Y = 88

lcd = LcdCommWeActB(com_port="AUTO", display_width=80, display_height=160)
lcd.InitializeComm()
lcd.SetBrightness(50)
lcd.SetOrientation(Orientation.PORTRAIT)
lcd.Clear()

net_prev = psutil.net_io_counters()
net_time = time.time()

# History buffers — one sample per column
up_history = deque([0.0] * W, maxlen=W)
dn_history = deque([0.0] * W, maxlen=W)


def draw_line(y, label, value):
    lcd.DisplayText(f"{label} {value}", x=2, y=y, width=W - 2, height=14,
                    font=FONT_SM, font_size=11,
                    font_color=WHITE, background_color=BLACK)


def draw_net_label(up_speed, dn_speed):
    from PIL import ImageFont
    font = ImageFont.truetype(FONT_SM, 11)
    img = Image.new("RGB", (W, 14), BLACK)
    draw = ImageDraw.Draw(img)
    up_mb = up_speed / (1024 * 1024)
    dn_mb = dn_speed / (1024 * 1024)
    up_txt = f"↑{up_mb:.0f}" if up_mb >= 10 else f"↑{up_mb:.1f}"
    dn_txt = f"↓{dn_mb:.0f}" if dn_mb >= 10 else f"↓{dn_mb:.1f}"
    draw.text((2, 0), up_txt, fill=RED, font=font)
    up_w = draw.textlength(up_txt, font=font)
    draw.text((2 + up_w + 4, 0), dn_txt, fill=LIGHT_BLUE, font=font)
    dn_w = draw.textlength(dn_txt, font=font)
    draw.text((2 + up_w + 4 + dn_w + 2, 0), "MB/s", fill=WHITE, font=font)
    lcd.DisplayPILImage(img, x=0, y=GRAPH_Y + GRAPH_H)


def draw_net_graph():
    img = Image.new("RGB", (W, GRAPH_H), BLACK)
    draw = ImageDraw.Draw(img)

    # Find the peak across both to use a shared scale
    peak = max(max(up_history), max(dn_history), 1024)  # at least 1KB floor

    up_list = list(up_history)
    dn_list = list(dn_history)

    dn_points = [(x, GRAPH_H - 1 - int(dn_list[x] / peak * (GRAPH_H - 1))) for x in range(W)]
    up_points = [(x, GRAPH_H - 1 - int(up_list[x] / peak * (GRAPH_H - 1))) for x in range(W)]

    if len(dn_points) > 1:
        draw.line(dn_points, fill=LIGHT_BLUE, width=1)
    if len(up_points) > 1:
        draw.line(up_points, fill=RED, width=1)

    lcd.DisplayPILImage(img, x=0, y=GRAPH_Y)


last_clock = ""
while True:
    now = datetime.now().strftime("%H:%M")
    if now != last_clock:
        lcd.DisplayText(now, x=0, y=0, width=W, height=36,
                        font=FONT, font_size=31, align="center",
                        font_color=WHITE, background_color=BLACK)
        last_clock = now

    y = 40

    # CPU
    cpu = psutil.cpu_percent(interval=None)
    temps = psutil.sensors_temperatures()
    cpu_temp = temps.get("k10temp", [{}])[0]
    cpu_temp_str = f" {cpu_temp.current:.0f}°C" if hasattr(cpu_temp, "current") else ""
    draw_line(y, "CPU", f"{cpu:.0f}%{cpu_temp_str}")
    y += 16

    # RAM
    mem = psutil.virtual_memory()
    draw_line(y, "RAM", f"{mem.percent:.0f}%")
    y += 16

    # GPU temp
    gpu_temp = temps.get("radeon", [{}])[0]
    if hasattr(gpu_temp, "current"):
        draw_line(y, "GPU", f"{gpu_temp.current:.0f}°C")
    y += 16

    # Network — compute speeds and store in history
    net_now = psutil.net_io_counters()
    t_now = time.time()
    dt = t_now - net_time
    up, dn = 0.0, 0.0
    if dt > 0:
        up = (net_now.bytes_sent - net_prev.bytes_sent) / dt
        dn = (net_now.bytes_recv - net_prev.bytes_recv) / dt
        up_history.append(up)
        dn_history.append(dn)
    net_prev = net_now
    net_time = t_now

    draw_net_label(up, dn)
    draw_net_graph()

    time.sleep(0.1)
