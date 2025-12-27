import cv2
import time
from datetime import datetime, timedelta
from vision import *
from utils import adb_tap, base_dir_path
from config import *
import config as config_module
import os
import pytesseract
import re
import threading
from queue import Queue, Empty

# 改为CSV日志路径
log_path = os.path.join(base_dir_path(), "log.csv")

# 控制台输出去重缓存：key->最后输出时间
console_last_output = {}
CONSOLE_DUPLICATE_WINDOW = 3  # 3秒内不重复输出同一类型

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
        # 用于去重的最近日志时间字典：key -> datetime
        self.last_logs = {}
        self.next_slow_time = None

        # 新增：缓存上一个比赛日志的信息（用于追加道具）
        self.last_race_log = {
            "scount": None,
            "ts": None,
            "level": None,
            "name": None,
            "position": None,
            "items": []  # 存储该比赛对应的掉落道具
        }

        # 线程与队列，用于异步处理截图识别
        self.frame_queue = Queue(maxsize=8)
        self.stop_event = threading.Event()
        self.worker_thread = None
        # 保护 last_logs 和 last_record 的并发访问
        self._lock = threading.Lock()
        # 保护 last_race_log 的并发访问
        self._race_log_lock = threading.Lock()

        # 初始化CSV日志文件
        if not os.path.isfile(log_path):
            with open(log_path, "w", encoding="utf-8-sig") as f:
                # 写入CSV表头
                f.write("序号,时间,类型,等级,名称,身位,其他\n")

    def _console_output_duplicate_check(self, key, message):
        """控制台输出去重：3秒内不重复显示同一类型信息"""
        now = datetime.now()
        with self._lock:
            last_time = console_last_output.get(key)
            if last_time and (now - last_time).total_seconds() < CONSOLE_DUPLICATE_WINDOW:
                return False
            console_last_output[key] = now
        print(message)
        return True

    def process_frame(self, screen_bgr):
        # 快速转换并入队，主线程尽量不阻塞
        gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        now_dt = datetime.now()
        scount = self.screenshot_count

        # lazy start worker
        if self.worker_thread is None:
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()

        try:
            # 若队列已满，丢弃最旧的一帧以保证最新帧能入队
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except Exception:
                    pass
            self.frame_queue.put_nowait((screen_bgr, gray, now_dt, scount))
        except Exception:
            # 入队失败时直接进行同步处理以避免丢帧过多
            self._match_template_and_ocr(screen_bgr, gray, now_dt=now_dt, scount=scount)

    def _should_write(self, key, now_dt):
        """判断给定 key 的日志是否需要写入（基于 TIME_WINDOW 去重）"""
        last = self.last_logs.get(key)
        if last and (now_dt - last).total_seconds() < TIME_WINDOW:
            return False
        return True

    def _write_log(self, key, message_parts, now_dt, scount=None):
        """统一写CSV日志并更新去重记录；scount 可覆盖使用的 screenshot_count
        线程安全：在此函数内统一加锁检查并更新去重字典。
        message_parts: 元组，对应CSV列（类型,等级,比赛名称,身位,附加道具）
        """
        if scount is None:
            scount = self.screenshot_count
        with self._lock:
            if not self._should_write(key, now_dt):
                return False
            self.last_logs[key] = now_dt
        ts = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        # 构造CSV行（截图编号,时间戳,类型,等级,比赛名称,身位,附加道具）
        csv_parts = [f"{scount:05d}", ts] + list(message_parts)
        # 处理空值，替换为"-"
        csv_parts = [part if part is not None and part != "" else "-" for part in csv_parts]
        csv_line = ",".join(csv_parts) + "\n"
        # 将文件写入置于锁外以减少临界区时间
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(csv_line)
        return True

    def _update_last_race_items(self, items):
        """更新上一个比赛的道具掉落信息，并同步更新CSV日志"""
        with self._race_log_lock:
            if self.last_race_log["scount"] is None:
                return False
            # 添加新道具（去重）
            for item in items:
                if item not in self.last_race_log["items"]:
                    self.last_race_log["items"].append(item)
            items_str = ",".join(self.last_race_log["items"]) if self.last_race_log["items"] else "-"
            
            # 读取原有CSV内容，更新对应行
            temp_log_path = os.path.join(base_dir_path(), "log_temp.csv")
            updated = False
            with open(log_path, "r", encoding="utf-8") as f, open(temp_log_path, "w", encoding="utf-8") as temp_f:
                # 写入表头
                header = f.readline()
                temp_f.write(header)
                # 遍历每一行
                for line in f:
                    line = line.strip()
                    if not line:
                        temp_f.write("\n")
                        continue
                    parts = line.split(",")
                    if len(parts) < 1:
                        temp_f.write(line + "\n")
                        continue
                    # 匹配截图编号
                    if parts[0] == f"{self.last_race_log['scount']:05d}":
                        # 更新附加道具列
                        parts[-1] = items_str
                        updated_line = ",".join(parts)
                        temp_f.write(updated_line + "\n")
                        updated = True
                    else:
                        temp_f.write(line + "\n")
            # 替换原日志文件
            if updated:
                os.replace(temp_log_path, log_path)
            else:
                os.remove(temp_log_path)
            return updated

    def _worker_loop(self):
        """后台消费队列，逐帧调用识别处理函数。"""
        while not self.stop_event.is_set():
            try:
                screen_bgr, screen_gray, now_dt, scount = self.frame_queue.get(timeout=1)
            except Empty:
                continue
            try:
                self._match_template_and_ocr(screen_bgr, screen_gray, now_dt=now_dt, scount=scount)
            except Exception:
                # 捕获单帧处理异常，避免线程退出
                pass

    def stop(self, wait=True):
        """停止后台线程（可在程序退出时调用）。"""
        self.stop_event.set()
        if self.worker_thread is not None and wait:
            self.worker_thread.join(timeout=2)

    def _match_template_and_ocr(self, screen_bgr, screen_gray, now_dt=None, scount=None):
        """主处理逻辑
        支持异步调用：接受 `now_dt`（帧捕获时间）和 `scount`（该帧编号）。
        若未传入则在函数内使用当前时间与默认编号。
        """


        if now_dt is None:
            now_dt = datetime.now()
        if scount is None:
            scount = self.screenshot_count



        # 道具掉落识别（优先处理）
        ri = match_template_in_region(screen_gray, TEMPLATE_RACE_ITEM, ROI_ITEM_DROP, threshold=MATCH_FINE)
        if ri:
            # 轮流匹配 item_01 到 item_10 并写入对应道具名
            item_names = {
                1: '钻石', 
                2: '女神像',
            }

            found_items = []  # 存储所有找到的道具

            for i in range(1, 3):
                tpl = getattr(config_module, f'TEMPLATE_ITEM_{i:02d}', None)
                if tpl is None:
                    # 退回到全局名称（import *）查找
                    tpl = globals().get(f'TEMPLATE_ITEM_{i:02d}')
                if tpl is None:
                    continue
                
                loc = match_template_in_region(screen_gray, tpl, ROI_ITEM_DROP, threshold=0.5)
                if loc:
                    name = item_names.get(i, f'item_{i:02d}')
                    found_items.append(name)

            # 根据找到的道具数量处理（无掉落不输出）
            if found_items:
                # 汇总道具
                if len(found_items) > 1:
                    items_str = ', '.join(found_items)
                    # 控制台输出去重
                    self._console_output_duplicate_check(('item_drop', 'multiple'), f"\033[95m掉落{items_str}\033[0m")
                    # 更新上一个比赛的道具信息
                    self._update_last_race_items(found_items)
                else:
                    item_name = found_items[0]
                    # 控制台输出去重
                    self._console_output_duplicate_check(('item_drop', item_name), f"\033[95m掉落{item_name}\033[0m")
                    # 更新上一个比赛的道具信息
                    self._update_last_race_items(found_items)
            return

        # 1) 在 ROI_RACE_RESULT 区域匹配 race_result 模板
        rr = match_template_in_region(screen_gray, TEMPLATE_RACE_RESULT, ROI_RACE_RESULT, threshold=MATCH_FINE)
        if rr:
            # 在 winner 区域判断胜负（改为检查屏幕上点 (200,300) 的色值是否为 #FFDD50）
            win = 0
            try:
                h, w = screen_bgr.shape[:2]
                px_x, px_y = 500, 700
                if 0 <= px_x < w and 0 <= px_y < h:
                    b = int(screen_bgr[px_y, px_x, 0])
                    g = int(screen_bgr[px_y, px_x, 1])
                    r = int(screen_bgr[px_y, px_x, 2])

                    #FFF5C7 -> RGB(255,245,199) -> BGR(199,245,255)
                    # Allow ±10 tolerance range for RGB values
                    if abs(r - 255) <= 10 and abs(g - 245) <= 10 and abs(b - 199) <= 10:
                        win = 1
            except Exception:
                win = 0

            if win == 1:
                self._record_race(screen_bgr, screen_gray, now_dt, success=True, scount=scount)
            else:
                self._record_race(screen_bgr, screen_gray, now_dt, success=False, scount=scount)
            return

        # 4) 检查 other_home 模板（钻石识别）
        oh = match_template_loc(screen_gray, TEMPLATE_OTHER_HOME, threshold=0.6)
        if oh:
            self._process_diamond(screen_bgr, now_dt, scount=scount)
            return

        # 5) 检查 other_jinhui 模板
        oj = match_template_loc(screen_gray, TEMPLATE_OTHER_JINHUI, threshold=MATCH_ROUGH)
        if oj:
            # 控制台输出去重
            self._console_output_duplicate_check(('jinhui',), "\033[94m金回hint\033[0m")
            self._write_log(('jinhui',), ("其他", "-", "-", "-", "金回hint已习得"), now_dt, scount=scount-1)
            return

        # 6) 检查跳过/因子 (默认开启)
        loc = match_template_loc(screen_gray, TEMPLATE_Skip, threshold=MATCH_ROUGH) or \
              match_template_loc(screen_gray, TEMPLATE_Yinzi, threshold=MATCH_ROUGH)
        if loc:
            cx, cy = loc[0], loc[1]
            adb_tap(self.device_id, cx, cy)
            return

        # 7) 检查 jitaend 模板 (默认开启)
        loc = match_template_loc(screen_gray, TEMPLATE_JitaEnd, threshold=MATCH_ROUGH)
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

    def _process_diamond(self, screen_bgr, now_dt, scount=None):
        """处理钻石识别逻辑
        支持异步传入的 `now_dt` 和 `scount`。
        """
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
            # 控制台输出去重
            self._console_output_duplicate_check(('diamond', current), f"\033[92m当前钻石：{current}\033[0m")
            # 写入CSV日志
            self._write_log(('diamond', current), ("其他", "-", "-", "-", f"钻石：{current}"), now_ts, scount=scount)
        else:
            diff = current - self.prev_diamond
            self.prev_diamond = current
            # 300秒限制
            if self.last_diamond_time is None or (now_ts - self.last_diamond_time).total_seconds() > 300:
                # 控制台输出去重
                self._console_output_duplicate_check(('diamond_increase', current, diff), f"\033[92m当前钻石：{current}，相比上局增加：{diff}\033[0m")
                # 写入CSV日志
                prev_scount = scount - 1 if scount is not None else None
                self._write_log(('diamond_increase', current, diff), ("其他", "-", "-", "-", f"钻石：{current} | 增加：{diff}"), now_ts, scount=prev_scount)
                self.last_diamond_time = now_ts

    def _record_race(self, screen_bgr, screen_gray, now_dt, success=True, scount=None):
        """根据原逻辑记录 race 日志；若 success=False 则记录为失败（但仍写格式）"""

        # 匹配竞赛等级
        level_templates = {"G1": TEMPLATE_G1, "G2": TEMPLATE_G2, "G3": TEMPLATE_G3, "URA": TEMPLATE_SP}
        race_level = match_template_label(screen_gray, REGION1, level_templates) 
        if not race_level:
            return

        # OCR 比赛名和信息
        race_name = ocr_region(REGION2, screen_bgr)

        # 匹配身位差
        position_templates = {"8 身位": TEMPLATE_8L, "9 身位": TEMPLATE_9L, "10身位": TEMPLATE_10L, "大差距": TEMPLATE_LON}
        position_result = match_template_label(screen_gray, REGION4, position_templates) or "身位不足"

        # 去重检查（保留原有逻辑）
        with self._lock:
            if self.last_record["type"] == "race":
                # 比赛名相同则不管时间多久都不新增记录
                if self.last_record["name"] == race_name and race_name != "":
                    return
                # 时间窗口去重
                if self.last_record["timestamp"] and \
                   (now_dt - self.last_record["timestamp"]).total_seconds() < TIME_WINDOW:
                    return

        ts = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        # 若 success=False，标注为失败
        if not success:
            position_result = "失败"  # 身位直接标注为失败

        # 构造日志内容
        msg_parts = ("比赛", race_level, race_name, position_result, "-")  # 初始道具为"-"
        key = ('race', race_level, race_name, position_result)
        # 以统一方法写入CSV日志（会做去重）
        wrote = self._write_log(key, msg_parts, now_dt, scount=scount)

        # 打印使用该帧的截图编号（若未提供则使用当前计数）
        use_scount = scount if scount is not None else self.screenshot_count

        # 控制台输出去重
        console_key = ('race', position_result, race_name)
        if position_result == "大差距":
            self._console_output_duplicate_check(console_key, f"{use_scount:05d} | {ts} | \033[92m{position_result}\033[0m")
        elif position_result == "身位不足":
            self._console_output_duplicate_check(console_key, f"{use_scount:05d} | {ts} | \033[91m{position_result}\033[0m")
        elif position_result == "失败":
            self._console_output_duplicate_check(console_key, f"{use_scount:05d} | {ts} | \033[91m{position_result}\033[0m")
        else:
            self._console_output_duplicate_check(console_key, f"{use_scount:05d} | {ts} | {position_result}")

        # 只有在成功写入比赛日志时，才递增日志编号（线程安全）并缓存比赛信息
        if wrote:
            with self._lock:
                self.screenshot_count += 1
            # 缓存当前比赛信息，用于后续追加道具
            with self._race_log_lock:
                self.last_race_log.update({
                    "scount": use_scount,
                    "ts": ts,
                    "level": race_level,
                    "name": race_name,
                    "position": position_result,
                    "items": []  # 重置道具列表
                })

        with self._lock:
            self.last_record.update({
                "type": "race",
                "timestamp": now_dt,
                "level": race_level,
                "name": race_name,
                "position": position_result
            })