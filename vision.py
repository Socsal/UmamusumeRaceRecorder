import cv2
import pytesseract
from utils import resource_path

# OCR
pytesseract.pytesseract.tesseract_cmd = resource_path("tessdata/tesseract.exe")

MATCH_THRESHOLD = 0.99
MATCH_ITEM = 0.8

def match_template(gray, template_path, threshold):
    tmpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tmpl is None:
        return False
    res = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
    return cv2.minMaxLoc(res)[1] >= threshold

def match_template_loc(gray, template_path, threshold):
    tmpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tmpl is None:
        return None
    res = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val < threshold:
        return None
    h, w = tmpl.shape
    x, y = max_loc
    return (x + w // 2, y + h // 2)

def ocr_region(bgr, region):
    x1, y1, x2, y2 = region
    roi = bgr[y1:y2, x1:x2]
    return pytesseract.image_to_string(
        cv2.cvtColor(roi, cv2.COLOR_BGR2RGB),
        lang="chi_sim",
        config="--psm 7"
    ).strip()
