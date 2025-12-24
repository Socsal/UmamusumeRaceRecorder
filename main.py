import time
import argparse
from utils import list_connected_devices, choose_device_interactively, adb_screenshot
from logic import RaceRecorder

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device")
    args = parser.parse_args()

    devices = list_connected_devices()
    if not devices:
        print("没有检测到设备")
        return

    device_id = args.device if args.device in devices else choose_device_interactively(devices)
    recorder = RaceRecorder(device_id)

    print(f"监听设备：{device_id}")
    try:
        while True:
            img = adb_screenshot(device_id)
            if img is not None:
                recorder.process_frame(img)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("退出")

if __name__ == "__main__":
    main()
