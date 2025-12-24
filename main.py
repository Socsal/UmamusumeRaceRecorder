import time
import argparse
from utils import list_connected_devices, choose_device_interactively, adb_screenshot
from logic import RaceRecorder
from config import CAPTURE_INTERVAL

def main():
    parser = argparse.ArgumentParser(description="赛马娘比赛记录")
    parser.add_argument("--device", "-d", help="要监控的ADB设备序号或ID，例如 1 或 emulator-5554")
    args = parser.parse_args()

    devices = list_connected_devices()
    if not devices:
        print("未检测到任何设备，程序退出。")
        return
    if args.device and args.device in devices:
        device_id = args.device
    else:
        device_id = choose_device_interactively(devices)

    recorder = RaceRecorder(device_id)
    print(f"→ 已选择设备：{device_id}，开始监听…\n")

    try:
        while True:
            screen_bgr = adb_screenshot(device_id)
            if screen_bgr is not None:
                try:
                    recorder.process_frame(screen_bgr)
                except Exception as e:
                    print(f"处理帧时出错：{e}")
                    continue
            time.sleep(CAPTURE_INTERVAL)
    except KeyboardInterrupt:
        print("\n监听结束，程序退出。")
    except Exception as e:
        print(f"程序异常终止：{e}")

if __name__ == "__main__":
    main()