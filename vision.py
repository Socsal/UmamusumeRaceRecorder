import cv2
import pytesseract
from utils import resource_path
from config import REGION5, MATCH_THRESHOLD
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



# OCR
pytesseract.pytesseract.tesseract_cmd = resource_path("assets/tessdata/tesseract.exe")
os.environ['TESSDATA_PREFIX'] = resource_path("assets/tessdata/tessdata")
MATCH_THRESHOLD = 0.99
MATCH_ITEM = 0.8


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


# ========= OCR辅助函数 =========
def ocr_region(region, image_bgr):
    x1, y1, x2, y2 = region
    roi = image_bgr[y1:y2, x1:x2]
    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    #allowed_chars = "京皋青东小札紫神菊全挑中日钻阪天新目鸣宝函白都月叶仓幌苑户花国战山经石王潟黑尾冢馆银总初奖优纪锦杯大邀级闻骏念标春请赛决秋预半德比顺逆外内中长距离草地URAm0123456789·()"
    text = pytesseract.image_to_string(roi_rgb, lang='chi_sim', config=f'--psm 7 ').strip()
    return text