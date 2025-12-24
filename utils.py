import os
import sys
import subprocess
import cv2
import numpy as np

# ========= 获取资源路径 =========
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ========= 获取应用路径 =========
def base_dir_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

# ========= ADB路径配置 =========
ADB_PATH = resource_path("assets/adbtools/adb.exe")

# ========= 列出ADB设备 =========
def list_connected_devices():
    try:
        raw = subprocess.check_output([ADB_PATH, "devices"], stderr=subprocess.DEVNULL).decode('utf-8')
        lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("List of devices")]
        devices = []
        for line in lines:
            parts = line.split()
            if parts[1] == "device":
                devices.append(parts[0])
        return devices
    except Exception:
        print("未检测到连接的设备，请连接设备后重试。")        

# ========= 选择ADB设备 =========
def choose_device_interactively(devices):
    """交互式列出设备并让用户通过序号选择"""
    print("检测到以下在线设备：")
    for idx, dev in enumerate(devices, start=1):
        print(f"  [{idx}] {dev}")
    while True:
        choice = input(f"请输入要监控的设备序号（1–{len(devices)}），或直接输入设备ID：").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(devices):
                return devices[idx-1]
        elif choice in devices:
            return choice
        print("输入不合法，请重新输入。")

# ========= ADB截图 =========
def adb_screenshot(device_id):
    """从指定设备截图并返回 OpenCV BGR 图像，失败返回 None"""
    try:
        cmd = [ADB_PATH, "-s", device_id, "exec-out", "screencap", "-p"]
        png_bytes = subprocess.check_output(cmd)
        img = cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)
        return img
    except subprocess.CalledProcessError as e:
        print(f"[错误] ADB 截图失败 (设备: {device_id})：{e}")
        return None
    
# ========= ADB触摸 =========
def adb_tap(device_id, x, y):
    """使用 adb 点击设备坐标 (x,y)"""
    try:
        subprocess.check_call([ADB_PATH, "-s", device_id, "shell", "input", "tap", str(int(x)), str(int(y))],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[错误] 点击失败: {e}")