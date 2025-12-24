from utils import resource_path 
from utils import base_dir_path
import os
import sys
import subprocess
import cv2
import numpy as np


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


