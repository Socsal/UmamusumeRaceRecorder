import argparse
import time
from datetime import datetime
import cv2

from utils import list_connected_devices, choose_device_interactively, adb_screenshot
from vision import match_template_in_region
from config import *


def main():
    parser = argparse.ArgumentParser(description="调试：在截图上运行 match_template_in_region 并保存图片")
    parser.add_argument("--device", "-d", help="ADB 设备 ID 或序号")
    args = parser.parse_args()

    devices = list_connected_devices()
    if not devices:
        print("未检测到任何设备，退出。")
        return
    if args.device and args.device in devices:
        device_id = args.device
    else:
        device_id = choose_device_interactively(devices)

    print(f"→ 已选择设备：{device_id}，正在截屏并运行模板匹配...")
    screen_bgr = adb_screenshot(device_id)
    if screen_bgr is None:
        print("未能获取截图（adb_screenshot 返回 None）。")
        return

    screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

    # 运行 match_template_in_region（与 logic.py 中相同的调用）

    rs = match_template_in_region(screen_gray, TEMPLATE_RACE_ITEM, ROI_ITEM_DROP, threshold=MATCH_FINE)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_full = f"debug_racestats_full_{ts}.png"
    out_roi = f"debug_racestats_roi_{ts}.png"
    out_annot = f"debug_racestats_annot_{ts}.png"

    # 保存整张截图
    cv2.imwrite(out_full, screen_bgr)
    print(f"已保存整张截图: {out_full}")

    # 保存 ROI 区域的裁剪图（如果 ROI 定义为 (x1,y1,x2,y2) 或 (x,y,w,h) 需按 vision/config 约定）
    try:
        # 假设 ROI_RACE_STATS 为 (x1, y1, x2, y2)
        x1, y1, x2, y2 = ROI_ITEM_DROP
        roi_img = screen_bgr[y1:y2, x1:x2]
        cv2.imwrite(out_roi, roi_img)
        print(f"已保存 ROI 裁剪图: {out_roi}")
    except Exception:
        print("无法按 (x1,y1,x2,y2) 解包 ROI_RACE_STATS，跳过 ROI 裁剪保存。")

    # 如果匹配到，绘制标注并保存
    annotated = screen_bgr.copy()
    if rs:
        try:
            cx, cy = int(rs[0]), int(rs[1])
            # 用圆圈标注匹配中心点
            cv2.circle(annotated, (cx, cy), 20, (0, 0, 255), 3)
            cv2.putText(annotated, "MATCH", (cx+25, cy), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
            cv2.imwrite(out_annot, annotated)
            print(f"匹配坐标: ({cx}, {cy})，已保存标注图: {out_annot}")
        except Exception as e:
            print(f"处理匹配结果时出错: {e}")
    else:
        cv2.imwrite(out_annot, annotated)
        print(f"未匹配到模板，已保存未标注图: {out_annot}")


if __name__ == "__main__":
    main()
