import cv2
import time
from datetime import datetime
from vision import *
from utils import adb_tap, base_dir_path
from config import *
import os
import pytesseract
import re

log_path = os.path.join(base_dir_path(), "log.txt")

class RaceRecorder:
    def __init__(self, device_id):
        self.device_id = device_id
        self.last_record_time = None
        self.screenshot_count = 1
        self.prev_diamond = None
        self.last_diamond_time = None
        self.last_record = {
            "type": None,
            "level": None,
            "name": None,
            "info": None,
            "position": None,
            "timestamp": None
        }
        # 初始化日志文件
        if not os.path.isfile(log_path):
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("")

    def process_frame(self, screen_bgr):
        gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        self._match_template_and_ocr(screen_bgr, gray)

    def _match_template_and_ocr(self, screen_bgr, screen_gray):
        """主处理逻辑"""
        now_dt = datetime.now()
        
        # 检查 skip / yinzi 模板
        loc = match_template_loc(screen_gray, TEMPLATE_Skip, threshold=MATCH_ITEM) or \
              match_template_loc(screen_gray, TEMPLATE_Yinzi, threshold=MATCH_ITEM)
        if loc:
            cx, cy = loc[0], loc[1]
            adb_tap(self.device_id, cx, cy)
            return

        # 检查 jitaend 模板
        loc = match_template_loc(screen_gray, TEMPLATE_JitaEnd, threshold=MATCH_THRESHOLD)
        if loc:
            cx, cy = loc[0], loc[1]
            adb_tap(self.device_id, cx, cy)
            time.sleep(1)
            adb_tap(self.device_id, 520, 1070)
            time.sleep(1)
            adb_tap(self.device_id, 700, 40)
            time.sleep(1)
            adb_tap(self.device_id, 700, 40)
            time.sleep(1)
            adb_tap(self.device_id, 490, 180)
            time.sleep(5)
            adb_tap(self.device_id, 360, 1210)
            return

        # 检查 home 模板（钻石识别）
        loc = match_template_loc(screen_gray, TEMPLATE_Home, threshold=0.6)
        if loc:
            self._process_diamond(screen_bgr, now_dt)
            return

        # 检查角色
        if not (match_template(screen_gray, TEMPLATE_Seiunsky, threshold=MATCH_ITEM) or \
                match_template(screen_gray, TEMPLATE_SeiunskyDFB, threshold=MATCH_ITEM)):
            return

        # 匹配竞赛等级
        level_templates = {"G1": TEMPLATE_G1, "G2": TEMPLATE_G2, "G3": TEMPLATE_G3, "URA": TEMPLATE_SP}
        race_level = match_template_label(screen_gray, REGION1, level_templates)
        if not race_level:
            return

        # OCR 比赛名和信息
        race_name = ocr_region(REGION2, screen_bgr)
        race_info = ocr_region(REGION3, screen_bgr)

        # 匹配身位差
        position_templates = {"8 身位": TEMPLATE_8L, "9 身位": TEMPLATE_9L, "10身位": TEMPLATE_10L, "大差距": TEMPLATE_LON}
        position_result = match_template_label(screen_gray, REGION4, position_templates) or "身位不足"

        # 去重：5秒内相同race类型不记录
        if self.last_record["type"] == "race" and self.last_record["timestamp"] and \
           (now_dt - self.last_record["timestamp"]).total_seconds() < time_window:
            return

        # 写race日志
        ts = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{self.screenshot_count:05d} | {ts} | 等级:{race_level} | 比赛:{race_name} | 信息:{race_info} | 身位:{position_result}\n")
        
        # 彩色输出
        if position_result == "大差距":
            print(f"{self.screenshot_count:05d} | {ts} | \033[32m{position_result}\033[0m")
        elif position_result == "身位不足":
            print(f"{self.screenshot_count:05d} | {ts} | \033[31m{position_result}\033[0m")
        else:
            print(f"{self.screenshot_count:05d} | {ts} | {position_result}")

        self.screenshot_count += 1
        self.last_record.update({
            "type": "race",
            "timestamp": now_dt,
            "level": race_level,
            "name": race_name,
            "info": race_info,
            "position": position_result
        })

    def _process_diamond(self, screen_bgr, now_dt):
        """处理钻石识别逻辑"""
        ocr_region_coords = (420, 94, 515, 120)
        text = pytesseract.image_to_string(
            screen_bgr[ocr_region_coords[1]:ocr_region_coords[3],
                       ocr_region_coords[0]:ocr_region_coords[2]],
            config='--psm 7 -c tessedit_char_whitelist=0123456789'
        ).strip()
        
        m = re.search(r'^\d+$', text.replace(',', ''))
        if not m:
            return

        current = int(m.group())
        now_ts = datetime.now()

        if self.prev_diamond is None:
            self.prev_diamond = current
            self.last_diamond_time = now_ts
            print(f"当前钻石：{current}")
            ts = now_ts.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{self.screenshot_count:05d} | {ts} | 等级:- | 比赛:- | 信息:- | 身位:- | 钻石：{current}\n")
        else:
            diff = current - self.prev_diamond
            self.prev_diamond = current
            # 300秒限制
            if self.last_diamond_time is None or (now_ts - self.last_diamond_time).total_seconds() > 300:
                print(f"当前钻石：{current}，相比上局增加：{diff}")
                ts = now_ts.strftime("%Y-%m-%d %H:%M:%S")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"{self.screenshot_count-1:05d} | {ts} | 等级:- | 比赛:- | 信息:- | 身位:- | 钻石：{current}\n")
                self.last_diamond_time = now_ts