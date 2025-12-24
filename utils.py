import os
import sys
import subprocess
import cv2
import numpy as np

# ========= 路径工具 =========
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def base_dir_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

ADB_PATH = resource_path("adbtools/adb.exe")

# ========= ADB =========
def list_connected_devices():
    raw = subprocess.check_output([ADB_PATH, "devices"], stderr=subprocess.DEVNULL).decode()
    lines = [l for l in raw.splitlines() if "\tdevice" in l]
    return [l.split()[0] for l in lines]

def choose_device_interactively(devices):
    for i, d in enumerate(devices, 1):
        print(f"[{i}] {d}")
    while True:
        s = input("选择设备序号或直接输入ID：").strip()
        if s.isdigit() and 1 <= int(s) <= len(devices):
            return devices[int(s) - 1]
        if s in devices:
            return s

def adb_screenshot(device_id):
    try:
        data = subprocess.check_output(
            [ADB_PATH, "-s", device_id, "exec-out", "screencap", "-p"]
        )
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return None

def adb_tap(device_id, x, y):
    subprocess.call(
        [ADB_PATH, "-s", device_id, "shell", "input", "tap", str(x), str(y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
