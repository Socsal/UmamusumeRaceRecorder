import os
import sys
import subprocess
import time
import cv2
import numpy as np
from PIL import Image
import pytesseract
from datetime import datetime
import argparse
import re



# ========= 路径工具函数 =========
def resource_path(relative_path):
    """兼容 PyInstaller 打包后的路径，用于读取打包资源（模板图）"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def base_dir_path():
    """返回 EXE 所在目录，用于读写外部文件（ADB、OCR、日志）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return os.path.dirname(sys.executable)
    else:
        # 脚本运行时
        return os.path.abspath(".")


adb_path = resource_path("assets/adbtools/adb.exe")
pytesseract.pytesseract.tesseract_cmd = resource_path("assets/tessdata/tesseract.exe")
os.environ['TESSDATA_PREFIX'] = resource_path("assets/tessdata/tessdata")

# ========= 模板路径配置 =========
TEMPLATE_Seiunsky   = resource_path("assets/templates/TEMPLATE_Seiunsky.png")
TEMPLATE_SeiunskyDFB = resource_path("assets/templates/TEMPLATE_SeiunskyDFB.png")
#TEMPLATE_Kitasanblack = resource_path("assets/templates/TEMPLATE_Kitasanblack.png")
TEMPLATE_Maruzensky = resource_path("assets/templates/TEMPLATE_Maruzensky.png")

TEMPLATE_G1 = resource_path("assets/templates/TEMPLATE_G1.png")
TEMPLATE_G2 = resource_path("assets/templates/TEMPLATE_G2.png")
TEMPLATE_G3 = resource_path("assets/templates/TEMPLATE_G3.png")
TEMPLATE_SP = resource_path("assets/templates/TEMPLATE_SP.png")
TEMPLATE_8L  = resource_path("assets/templates/TEMPLATE_8L.png")
TEMPLATE_9L  = resource_path("assets/templates/TEMPLATE_9L.png")
TEMPLATE_10L = resource_path("assets/templates/TEMPLATE_10L.png")
TEMPLATE_LON = resource_path("assets/templates/TEMPLATE_LON.png")
TEMPLATE_Gem = resource_path("assets/templates/TEMPLATE_Gem.png")
# 新增三个模板：skip, jitaend, home
TEMPLATE_Skip = resource_path("assets/templates/TEMPLATE_Skip.png")
TEMPLATE_JitaEnd = resource_path("assets/templates/TEMPLATE_JitaEnd.png")
TEMPLATE_Home = resource_path("assets/templates/TEMPLATE_Home.png")
TEMPLATE_Yinzi = resource_path("assets/templates/TEMPLATE_Yinzi.png")



# ========= 配置区域与参数 =========
MATCH_THRESHOLD = 0.99  # 匹配阈值（可调）
MATCH_ITEM = 0.8  # 道具匹配阈值（可调）
REGION1 = (20, 500, 110, 550)
REGION2 = (95, 500, 350, 550)
REGION3 = (40, 550, 400, 580)
REGION4 = (550, 800, 700, 900)
REGION5 = (30, 930, 700, 1070)   # 掉落区域
CAPTURE_INTERVAL = 0.1  # 秒
time_window = 5  # 秒，去重时间窗口
last_diamond_time = None  # 新增变量，记录上次钻石记录时间
prev_diamond = None


# ========= 日志文件路径 =========
log_path = os.path.join(base_dir_path(), "log.txt")
if not os.path.isfile(log_path):
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("")

# 初始化“上次记录”的字段
last_record = {
    "type": None,        # 'race' 或 'gem'
    "level": None,
    "name": None,
    "info": None,
    "position": None,
    "timestamp": None
}
screenshot_count = 1




def list_connected_devices():
    """返回通过 adb devices 列出的在线设备 ID 列表"""
    raw = subprocess.check_output([adb_path, "devices"], stderr=subprocess.DEVNULL).decode('utf-8')
    lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("List of devices")]
    devices = []
    for line in lines:
        parts = line.split()
        if parts[1] == "device":
            devices.append(parts[0])
    return devices

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

def adb_screenshot(device_id):
    """从指定设备截图并返回 OpenCV BGR 图像，失败返回 None"""
    try:
        cmd = [adb_path, "-s", device_id, "exec-out", "screencap", "-p"]
        png_bytes = subprocess.check_output(cmd)
        img = cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)
        return img
    except subprocess.CalledProcessError as e:
        print(f"[错误] ADB 截图失败 (设备: {device_id})：{e}")
        return None
    




# ========= 模板匹配函数 =========
def match_template(img_gray, template_path, threshold=MATCH_THRESHOLD):
    tmpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tmpl is None:
        print(f"[错误] 模板不存在：{template_path}")
        return False
    res = cv2.matchTemplate(img_gray, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= threshold




# ========= 匹配道具模板函数 =========
def match_itemtemplate(img_gray, template_path, threshold=MATCH_ITEM):
    # 只在REGION5区域内进行匹配
    x1, y1, x2, y2 = REGION5
    roi = img_gray[y1:y2, x1:x2]
    tmpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tmpl is None:
        print(f"[错误] 模板不存在：{template_path}")
        return False
    if roi.shape[0] < tmpl.shape[0] or roi.shape[1] < tmpl.shape[1]:
        print("[错误] ROI区域小于模板，无法匹配")
        return False
    res = cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= threshold

# ========= 匹配模板标签函数 =========
def match_template_label(img_gray, roi_coords, template_dict):
    x1, y1, x2, y2 = roi_coords
    roi = img_gray[y1:y2, x1:x2]
    best_label = None
    best_score = 0
    for label, path in template_dict.items():
        tmpl = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if tmpl is None or roi.shape[0] < tmpl.shape[0] or roi.shape[1] < tmpl.shape[1]:
            continue
        res = cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        #print(f"[匹配度] 模板 {label} 最大匹配值: {max_val:.4f}")
        if max_val > best_score and max_val >= MATCH_THRESHOLD:
            best_score = max_val
            best_label = label
    return best_label

# ========= OCR辅助函数 =========
def ocr_region(region, image_bgr):
    x1, y1, x2, y2 = region
    roi = image_bgr[y1:y2, x1:x2]
    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    #allowed_chars = "京皋青东小札紫神菊全挑中日钻阪天新目鸣宝函白都月叶仓幌苑户花国战山经石王潟黑尾冢馆银总初奖优纪锦杯大邀级闻骏念标春请赛决秋预半德比顺逆外内中长距离草地URAm0123456789·()"
    text = pytesseract.image_to_string(roi_rgb, lang='chi_sim', config=f'--psm 7 ').strip()






    return text




def adb_tap(device_id, x, y):
    """使用 adb 点击设备坐标 (x,y)"""
    try:
        subprocess.check_call([adb_path, "-s", device_id, "shell", "input", "tap", str(int(x)), str(int(y))],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[错误] adb tap 失败: {e}")

def match_template_loc(img_gray, template_path, threshold=MATCH_THRESHOLD):
    """
    在整张灰度图上匹配模板，返回匹配中心坐标 (cx, cy) 和匹配矩形 (x, y, w, h)
    若未达到阈值返回 None
    """
    tmpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tmpl is None:
        # 模板不存在
        return None
    if img_gray.shape[0] < tmpl.shape[0] or img_gray.shape[1] < tmpl.shape[1]:
        return None
    res = cv2.matchTemplate(img_gray, tmpl, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val < threshold:
        return None
    tx, ty = max_loc
    h, w = tmpl.shape
    cx = tx + w // 2
    cy = ty + h // 2
    return (cx, cy, tx, ty, w, h, max_val)




# ========= 主处理逻辑 =========
def match_template_and_ocr(screen_bgr):
    global screenshot_count, last_record, prev_diamond
    now_dt = datetime.now()
    screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
    # 先检查 skip / jitaend / home 模板并执行相应点击与操作
    # skip: 点击模板中心
    loc = match_template_loc(screen_gray, TEMPLATE_Skip, threshold=MATCH_ITEM) or match_template_loc(screen_gray, TEMPLATE_Yinzi, threshold=MATCH_ITEM)
    if loc:
        cx, cy = loc[0], loc[1]
        if 'device_id' in globals():
            adb_tap(device_id, cx, cy)
        else:
            # 如果没有全局 device_id，尝试从 last_record 中取（不会有），以防崩溃
            pass
        return
    # jitaend: 点击模板中心 -> 点击 (300,400) -> 等待1s -> 点击 (500,600)
    loc = match_template_loc(screen_gray, TEMPLATE_JitaEnd, threshold=MATCH_THRESHOLD)
    if loc:
        cx, cy = loc[0], loc[1]
        if 'device_id' in globals():
            adb_tap(device_id, cx, cy)   # 点击“结束”按钮
            time.sleep(1)
            adb_tap(device_id, 520, 1070)   #点击养成结束
            time.sleep(1)
            adb_tap(device_id, 700, 40) #点击右上角姬塔
            time.sleep(1)
            adb_tap(device_id, 700, 40) #展开姬塔
            time.sleep(1)
            adb_tap(device_id, 490, 180) #点击绿色箭头
            time.sleep(5)
            adb_tap(device_id, 360, 1210) #点击开始使用
        return

    loc = match_template_loc(screen_gray, TEMPLATE_Home, threshold=0.6)
    if loc:
        # OCR 指定区域 (500,100)-(700,150)
        ocr_region_coords = (420, 94, 515, 120)
        text = pytesseract.image_to_string(
            screen_bgr[ocr_region_coords[1]:ocr_region_coords[3], 
                  ocr_region_coords[0]:ocr_region_coords[2]],
            config='--psm 7 -c tessedit_char_whitelist=0123456789'  # 仅允许数字
        ).strip()
        m = re.search(r'^\d+$', text.replace(',', ''))
        if m:
            current = int(m.group())
            global last_diamond_time
            now_ts = datetime.now()
            if prev_diamond is None:
                prev_diamond = current
                last_diamond_time = now_ts
                print(f"当前钻石：{current}")
                ts = now_ts.strftime("%Y-%m-%d %H:%M:%S")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"{screenshot_count:05d} | {ts} | 等级:- | 比赛:- | 信息:- | 身位:- | 钻石：{current}\n")
            else:
                diff = current - prev_diamond
                prev_diamond = current
                # 60秒限制
                if last_diamond_time is None or (now_ts - last_diamond_time).total_seconds() > 300:
                    print(f"当前钻石：{current}，相比上局增加：{diff}")
                    ts = now_ts.strftime("%Y-%m-%d %H:%M:%S")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"{screenshot_count-1:05d} | {ts} | 等级:- | 比赛:- | 信息:- | 身位:- | 钻石：{current}\n")
                    last_diamond_time = now_ts
            return




    # 以下保持原有流程：检测掉钻、角色、等级、OCR、身位等
    # Step 0: 检查掉钻 (gem)
##    if match_itemtemplate(screen_gray, TEMPLATE_Gem):
 #       # 去重：5秒以内相同类型不记录
 #       if last_record["type"] == "gem" and last_record["timestamp"] and (now_dt - last_record["timestamp"]).total_seconds() < time_window:
 #           return
 #       ts = now_dt.strftime("%Y-%m-%d %H:%M:%S")
 #       with open(log_path, "a", encoding="utf-8") as f:
 #           f.write(f"{(screenshot_count-1):05d} | {ts} | 等级:- | 比赛:- | 信息:- | 身位:- | 掉落钻石\n")
 #       print(f"\033[32m{(screenshot_count-1):05d} | {ts} | 掉落钻石\033[0m")
 #       last_record.update({"type": "gem", "timestamp": now_dt, "level": None, "name": None, "info": None, "position": None})
 #       return

    # Step 1: 匹配角色
    if not (match_template(screen_gray, TEMPLATE_Seiunsky, threshold=MATCH_ITEM) or match_template(screen_gray, TEMPLATE_SeiunskyDFB, threshold=MATCH_ITEM)):
        return

    # Step 2: 匹配竞赛等级 (race)
    level_templates = {"G1": TEMPLATE_G1, "G2": TEMPLATE_G2, "G3": TEMPLATE_G3, "URA": TEMPLATE_SP}
    race_level = match_template_label(screen_gray, REGION1, level_templates)
    if not race_level:
        return

    # Step 3: OCR 比赛名和信息
    race_name = ocr_region(REGION2, screen_bgr)
    race_info = ocr_region(REGION3, screen_bgr)

    # Step 4: 匹配身位差
    position_templates = {"8 身位": TEMPLATE_8L, "9 身位": TEMPLATE_9L, "10身位": TEMPLATE_10L, "大差距": TEMPLATE_LON}
    position_result = match_template_label(screen_gray, REGION4, position_templates) or "身位不足"

    # 去重：5秒内相同race类型不记录
    if last_record["type"] == "race" and last_record["timestamp"] and (now_dt - last_record["timestamp"]).total_seconds() < time_window:
        return

    # 写race日志
    ts = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{screenshot_count:05d} | {ts} | 等级:{race_level} | 比赛:{race_name} | 信息:{race_info} | 身位:{position_result}\n")
    if position_result == "大差距":
        print(f"{screenshot_count:05d} | {ts} | \033[32m{position_result}\033[0m")
    elif position_result == "身位不足":
        print(f"{screenshot_count:05d} | {ts} | \033[31m{position_result}\033[0m")
    else:
        print(f"{screenshot_count:05d} | {ts} | {position_result}")


    screenshot_count += 1
    last_record.update({"type": "race", "timestamp": now_dt, "level": race_level, "name": race_name, "info": race_info, "position": position_result})




# ========= 主循环 =========
def main():
    parser = argparse.ArgumentParser(description="多开模拟器竞赛结果监听器")
    parser.add_argument("--device", "-d", help="要监控的ADB设备ID，如 127.0.0.1:16384 或 emulator-5554")
    args = parser.parse_args()

    devices = list_connected_devices()
    if not devices:
        print("未检测到任何在线设备，请检查 adb 连接后重试。")
        sys.exit(1)

    if args.device:
        if args.device not in devices:
            print(f"指定的设备 {args.device} 不在线。可用设备：{devices}")
            sys.exit(1)
        global device_id
        device_id = args.device
    else:
        device_id = choose_device_interactively(devices)

    print(f"→ 已选择设备：{device_id}，开始监听… (按 Ctrl+C 退出)\n")
    try:
        while True:
#            print("=" * 40)
            screen_bgr = adb_screenshot(device_id)
            if screen_bgr is not None:
                match_template_and_ocr(screen_bgr)
            time.sleep(CAPTURE_INTERVAL)
    except KeyboardInterrupt:
        print("\n监听结束，程序退出。")

if __name__ == "__main__":
    main()