from utils import resource_path

# ========= 模板路径配置 =========


TEMPLATE_G1 = resource_path("assets/templates/grade_G1.png")
TEMPLATE_G2 = resource_path("assets/templates/grade_G2.png")
TEMPLATE_G3 = resource_path("assets/templates/grade_G3.png")
TEMPLATE_SP = resource_path("assets/templates/grade_SP.png")


TEMPLATE_8L = resource_path("assets/templates/margin_8L.png")
TEMPLATE_9L = resource_path("assets/templates/margin_9L.png")
TEMPLATE_10L = resource_path("assets/templates/margin_10L.png")
TEMPLATE_LON = resource_path("assets/templates/margin_LON.png")

TEMPLATE_Skip = resource_path("assets/templates/other_skip.png")
TEMPLATE_JitaEnd = resource_path("assets/templates/other_jitaend.png")
TEMPLATE_Yinzi = resource_path("assets/templates/other_yinzi.png")

# ========== 额外模板 ==========
TEMPLATE_RACE_RESULT = resource_path("assets/templates/race_result.png")
TEMPLATE_RACE_WINNER = resource_path("assets/templates/race_winner.png")
TEMPLATE_RACE_NEXT = resource_path("assets/templates/race_next.png")
TEMPLATE_ITEM_01 = resource_path("assets/templates/item_01.png")
TEMPLATE_ITEM_02 = resource_path("assets/templates/item_02.png")
TEMPLATE_ITEM_03 = resource_path("assets/templates/item_03.png")
TEMPLATE_ITEM_04 = resource_path("assets/templates/item_04.png")
TEMPLATE_ITEM_05 = resource_path("assets/templates/item_05.png")
TEMPLATE_ITEM_06 = resource_path("assets/templates/item_06.png")
TEMPLATE_ITEM_07 = resource_path("assets/templates/item_07.png")
TEMPLATE_ITEM_08 = resource_path("assets/templates/item_08.png")
TEMPLATE_ITEM_09 = resource_path("assets/templates/item_09.png")
TEMPLATE_ITEM_10 = resource_path("assets/templates/item_10.png")



TEMPLATE_RACE_STATS = resource_path("assets/templates/race_stats.png")
TEMPLATE_RACE_ITEM = resource_path("assets/templates/race_item.png")
TEMPLATE_OTHER_HOME = resource_path("assets/templates/other_home.png")
TEMPLATE_OTHER_JINHUI = resource_path("assets/templates/other_jinhui.png")


# ========= 匹配与识别参数 =========
MATCH_FINE = 0.99  # 模板匹配阈值
MATCH_ROUGH = 0.8       # 道具匹配阈值

# 点击控制：1=匹配成功自动点击中心点，0=不自动点击
AUTO_CLICK_SKIP = 1
AUTO_CLICK_YINZI = 1
AUTO_CLICK_JITAEND = 0


# ========= 区域定义 =========
REGION1 = (20, 500, 110, 550)      # 区域1
REGION2 = (95, 500, 350, 550)      # 区域2
REGION3 = (40, 550, 400, 580)      # 区域3
REGION4 = (550, 800, 700, 900)     # 区域4
REGION5 = (30, 930, 700, 1070)     # 掉落区域

# ========== 逻辑用 ROI 常量（x1,y1,x2,y2） ==========
ROI_RACE_RESULT = (580, 660, 670, 960)
ROI_RACE_WINNER = (160, 160, 250, 220)
ROI_RACE_NEXT = (0, 1100, 720, 1280)
ROI_RACE_STATS = (520, 730, 630, 765)
ROI_ITEM_DROP = (0, 610, 720, 1120)

ROI_RACE_GEMS = (0,0, 720, 1280)




# ========= 时间与去重参数 =========
CAPTURE_INTERVAL = 0.05  # 截图间隔（秒）
TIME_WINDOW = 5         # 去重时间窗口（秒）
LAST_DIAMOND_TIME = None  # 上次钻石记录时间
PREV_DIAMOND = None     # 上次钻石数值