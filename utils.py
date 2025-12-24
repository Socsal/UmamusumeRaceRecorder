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

# ========= 定义ADB路径 =========
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
    for i, d in enumerate(devices, 1):
        print(f"[{i}] {d}")
    while True:
        s = input("选择设备序号或直接输入ID：").strip()
        if s.isdigit() and 1 <= int(s) <= len(devices):
            return devices[int(s) - 1]
        if s in devices:
            return s

# ========= ADB截图 =========
def adb_screenshot(device_id):
    try:
        data = subprocess.check_output(
            [ADB_PATH, "-s", device_id, "exec-out", "screencap", "-p"]
        )
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return None

# ========= ADB触摸 =========
def adb_tap(device_id, x, y):
    subprocess.call(
        [ADB_PATH, "-s", device_id, "shell", "input", "tap", str(x), str(y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
