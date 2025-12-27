import os
import sys
import subprocess
import cv2
import numpy as np
from functools import lru_cache

# ========= 获取资源路径 =========
@lru_cache(maxsize=1)
def resource_path(relative_path):
    """获取资源路径，支持开发和 PyInstaller 打包"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ========= 获取应用路径 =========
@lru_cache(maxsize=1)
def base_dir_path():
    """获取应用根目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

# ========= ADB路径配置 =========
ADB_PATH = resource_path("assets/adbtools/adb.exe")

# ========= 列出ADB设备 =========
def list_connected_devices():
    """列出所有已连接的 ADB 设备"""
    try:
        raw = subprocess.check_output(
            [ADB_PATH, "devices"], 
            stderr=subprocess.DEVNULL
        ).decode('utf-8')
        
        devices = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices"):
                continue
            
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        
        return devices
    except FileNotFoundError:
        print("错误：ADB 工具未找到，请检查 assets/adbtools/adb.exe 路径。")
        return []
    except Exception as e:
        print(f"错误：列举设备失败：{e}")
        return []

# ========= 选择ADB设备 =========
def choose_device_interactively(devices):
    """交互式列出设备并让用户通过序号选择"""
    print("检测到以下在线设备：")
    for idx, dev in enumerate(devices, start=1):
        print(f"  [{idx}] {dev}")
    
    while True:
        choice = input(f"请输入要监控的设备序号（1-{len(devices)}），或直接输入设备ID：").strip()
        
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(devices):
                return devices[idx - 1]
        elif choice in devices:
            return choice
        
        print("输入不合法，请重新输入。")

# ========= ADB截图 =========
def adb_screenshot(device_id):
    """从指定设备截图并返回 OpenCV BGR 图像，失败返回 None"""
    try:
        cmd = [ADB_PATH, "-s", device_id, "exec-out", "screencap", "-p"]
        png_bytes = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        
        img = cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"警告：截图数据无效（设备: {device_id}）")
            return None
        
        return img
    except subprocess.CalledProcessError:
        print(f"警告：ADB 截图失败（设备: {device_id}）")
        return None
    except Exception as e:
        print(f"错误：截图异常：{e}")
        return None

# ========= ADB触摸 =========
def adb_tap(device_id, x, y):
    """使用 ADB 点击设备坐标 (x, y)"""
    try:
        subprocess.check_call(
            [ADB_PATH, "-s", device_id, "shell", "input", "tap", str(int(x)), str(int(y))],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        print(f"警告：点击失败（坐标: {x}, {y}）")
    except Exception as e:
        print(f"错误：点击异常：{e}")
