import cv2
import pytesseract
from utils import resource_path
from config import REGION5, MATCH_FINE, MATCH_ROUGH
import os
import re



# OCR
pytesseract.pytesseract.tesseract_cmd = resource_path("assets/tessdata/tesseract.exe")
os.environ['TESSDATA_PREFIX'] = resource_path("assets/tessdata/tessdata")
MATCH_FINE = 0.99
MATCH_ROUGH = 0.8


# ========= 模板匹配函数 =========
def match_template(img_gray, template_path, threshold=MATCH_FINE):
    tmpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tmpl is None:
        print(f"[错误] 模板不存在：{template_path}")
        return False
    res = cv2.matchTemplate(img_gray, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= threshold




# ========= 匹配道具模板函数 =========
def MATCH_ROUGHtemplate(img_gray, template_path, threshold=MATCH_ROUGH):
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
        if max_val > best_score and max_val >= MATCH_FINE:
            best_score = max_val
            best_label = label
    return best_label











def match_template_loc(img_gray, template_path, threshold=MATCH_FINE):
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


def match_template_in_region(img_gray, template_path, region, threshold=MATCH_FINE):
    """
    在指定区域 (x1,y1,x2,y2) 内匹配模板，返回与 match_template_loc 相同的元组 (cx,cy,tx,ty,w,h,val)
    未达到阈值返回 None
    """
    x1, y1, x2, y2 = region
    roi = img_gray[y1:y2, x1:x2]
    tmpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tmpl is None:
        return None
    if roi.shape[0] < tmpl.shape[0] or roi.shape[1] < tmpl.shape[1]:
        return None
    res = cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val < threshold:
        return None
    tx, ty = max_loc
    h, w = tmpl.shape
    cx = x1 + tx + w // 2
    cy = y1 + ty + h // 2

    return (cx, cy, x1 + tx, y1 + ty, w, h, max_val)




def ocr_number_region(region, image_bgr, psm=7):
    """在指定区域进行数字 OCR，返回纯数字字符串或空字符串；同时保存二值化图片用于调试"""
    x1, y1, x2, y2 = region
    roi = image_bgr[y1:y2, x1:x2]
    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)

    # 转灰度并做 Otsu 二值化，提高识别率
    roi_gray = cv2.cvtColor(roi_rgb, cv2.COLOR_RGB2GRAY)
    _, roi_bin = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 用二值图做 OCR（只允许数字）
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(roi_bin, lang='chi_sim', config=config)
    text = re.sub(r'[^0-9]', '', text or '')
    return text


# ========= OCR辅助函数 =========
def ocr_region(region, image_bgr):
    x1, y1, x2, y2 = region
    roi = image_bgr[y1:y2, x1:x2]
    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    #allowed_chars = "京皋青东小札紫神菊全挑中日钻阪天新目鸣宝函白都月叶仓幌苑户花国战山经石王潟黑尾冢馆银总初奖优纪锦杯大邀级闻骏念标春请赛决秋预半德比顺逆外内中长距离草地URAm0123456789·()"
    text = pytesseract.image_to_string(roi_rgb, lang='chi_sim', config=f'--psm 7 ').strip()
    return text