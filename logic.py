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
        # 用于去重的最近日志时间字典：key -> datetime
        self.last_logs = {}
        self.next_slow_time = None


        # 线程与队列，用于异步处理截图识别
        self.frame_queue = Queue(maxsize=8)
        self.stop_event = threading.Event()
        self.worker_thread = None
        # 保护 last_logs 和 last_record 的并发访问
        self._lock = threading.Lock()

        # 初始化日志文件
        if not os.path.isfile(log_path):
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("")

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

    def _write_log(self, key, message, now_dt, scount=None):
        """统一写日志并更新去重记录；scount 可覆盖使用的 screenshot_count
        线程安全：在此函数内统一加锁检查并更新去重字典。
        """
        if scount is None:
            scount = self.screenshot_count
        with self._lock:
            if not self._should_write(key, now_dt):
                return False
            self.last_logs[key] = now_dt
        ts = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        # 将文件写入置于锁外以减少临界区时间
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{scount:05d} | {ts} | {message}\n")
        return True

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
        if self.next_slow_time is not None and now_dt >= self.next_slow_time:
            config_module.CAPTURE_INTERVAL = 0.1
            self.next_slow_time = None



        if now_dt is None:
            now_dt = datetime.now()
        if scount is None:
            scount = self.screenshot_count

        
        # 2) 如果没有 race_result，则在 ROI_RACE_NEXT 区域匹配 race_next
        rn = match_template_in_region(screen_gray, TEMPLATE_RACE_NEXT, ROI_RACE_NEXT, threshold=MATCH_FINE)
        if rn:
            # 识别到 race_next 时，过一秒后放慢截图间隔
            if self.next_slow_time is None:
                self.next_slow_time = now_dt + timedelta(seconds=1)




                # 2) 如果没有 race_result，则在 ROI_RACE_NEXT 区域匹配 race_next
        ri = match_template_in_region(screen_gray, TEMPLATE_RACE_ITEM, ROI_ITEM_DROP, threshold=MATCH_FINE)
        if ri:
            # 轮流匹配 item_01 到 item_10 并写入对应道具名
            item_names = {
                1: '钻石', 
                2: '女神像',
                3: '梦想光辉'
            }

            found_items = []  # 存储所有找到的道具

            for i in range(1, 4):
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

            # 根据找到的道具数量处理日志
            if found_items:

                # 如果需要汇总记录
                if len(found_items) > 1:
                    items_str = ', '.join(found_items)

                    print(f"\033[95m掉落{items_str}\033[0m")
                    self._write_log(('item_drop', 'multiple'), f"TYPE:其他 | ITEM:{items_str}", now_dt, scount=scount-1)
                    return
                
                else:
                    # 只有一个道具，记录具体名称
                    item_name = found_items[0]
                    print(f"\033[95m掉落{item_name}\033[0m")
                    self._write_log(('item_drop', item_name), f"TYPE:其他 | ITEM:{item_name}", now_dt, scount=scount-1)
                    return
                
            else:
                # 没有找到任何道具，日志记录：无掉落
                self._write_log(('item_drop', 'none'), f"TYPE:其他 | ITEM:无", now_dt, scount=scount-1)
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
                    # #FFDD50 -> RGB(255,221,80) -> BGR(80,221,255)
                    if (r, g, b) == (255,245,199):
                        win = 1
            except Exception:
                win = 0
            # 识别到 race_result 时加快截图间隔
            try:
                config_module.CAPTURE_INTERVAL = 0.05
            except Exception:
                pass
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
            print("\033[94m金回hint已习得\033[0m")
            self._write_log(('jinhui',), "TYPE:其他 | 事件:金回hint已习得", now_dt, scount=scount-1)
            return

        # 6) 检查跳过/因子
        if AUTO_CLICK_SKIP == 1 and AUTO_CLICK_YINZI == 1:
            loc = match_template_loc(screen_gray, TEMPLATE_Skip, threshold=MATCH_ROUGH) or \
                  match_template_loc(screen_gray, TEMPLATE_Yinzi, threshold=MATCH_ROUGH)
            if loc:
                cx, cy = loc[0], loc[1]
                adb_tap(self.device_id, cx, cy)
                return
        elif AUTO_CLICK_SKIP == 1:
            loc = match_template_loc(screen_gray, TEMPLATE_Skip, threshold=MATCH_ROUGH)
            if loc:
                cx, cy = loc[0], loc[1]
                adb_tap(self.device_id, cx, cy)
                return
        elif AUTO_CLICK_YINZI == 1:
            loc = match_template_loc(screen_gray, TEMPLATE_Yinzi, threshold=MATCH_ROUGH)
            if loc:
                cx, cy = loc[0], loc[1]
                adb_tap(self.device_id, cx, cy)
                return

        # 7) 检查 jitaend 模板
        if AUTO_CLICK_JITAEND == 1:
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
            print(f"当前钻石：{current}")
            # 去重 key 包含当前钻石数
            self._write_log(('diamond', current), f"等级:- | 比赛:- | 信息:- | 身位:- | 钻石：{current}", now_ts, scount=scount)
        else:
            diff = current - self.prev_diamond
            self.prev_diamond = current
            # 300秒限制
            if self.last_diamond_time is None or (now_ts - self.last_diamond_time).total_seconds() > 300:
                print(f"当前钻石：{current}，相比上局增加：{diff}")
                # 写入使用上一次截图编号（使用帧编号 - 1）
                prev_scount = scount - 1 if scount is not None else None
                self._write_log(('diamond_increase', current, diff), f"等级:- | 比赛:- | 信息:- | 身位:- | 钻石：{current} | 增加：{diff}", now_ts, scount=prev_scount)
                self.last_diamond_time = now_ts

    def _record_race(self, screen_bgr, screen_gray, now_dt, success=True, scount=None):
        """根据原逻辑记录 race 日志；若 success=False 则记录为失败（但仍写格式）"""
        # 不再需要角色检测，匹配到 winner 即可记录

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


        msg = f"TYPE:比赛 | 等级:{race_level} | 比赛:{race_name} | 身位:{position_result}"

        key = ('race', race_level, race_name, position_result)
        # 以统一方法写入日志（会做去重）
        wrote = self._write_log(key, msg, now_dt, scount=scount)

        # 打印使用该帧的截图编号（若未提供则使用当前计数）
        use_scount = scount if scount is not None else self.screenshot_count

        if position_result == "大差距":
            print(f"{use_scount:05d} | {ts} | \033[92m{position_result}\033[0m")
        elif position_result == "身位不足":
            print(f"{use_scount:05d} | {ts} | \033[93m{position_result}\033[0m")
        elif position_result == "失败":
            print(f"{use_scount:05d} | {ts} | \033[91m{position_result}\033[0m")
        else:
            print(f"{use_scount:05d} | {ts} | {position_result}")

        # 只有在成功写入比赛日志时，才递增日志编号（线程安全）
        if wrote:
            with self._lock:
                self.screenshot_count += 1

        with self._lock:
            self.last_record.update({
                "type": "race",
                "timestamp": now_dt,
                "level": race_level,
                "name": race_name,
                "position": position_result
            })