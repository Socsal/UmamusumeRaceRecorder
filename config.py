from utils import resource_path

# ========= 模板路径配置 =========
TEMPLATE_Seiunsky = resource_path("assets/templates/TEMPLATE_Seiunsky.png")
TEMPLATE_Maruzensky = resource_path("assets/templates/TEMPLATE_Maruzensky.png")


TEMPLATE_G1 = resource_path("assets/templates/TEMPLATE_G1.png")
TEMPLATE_G2 = resource_path("assets/templates/TEMPLATE_G2.png")
TEMPLATE_G3 = resource_path("assets/templates/TEMPLATE_G3.png")
TEMPLATE_SP = resource_path("assets/templates/TEMPLATE_SP.png")


TEMPLATE_8L = resource_path("assets/templates/TEMPLATE_8L.png")
TEMPLATE_9L = resource_path("assets/templates/TEMPLATE_9L.png")
TEMPLATE_10L = resource_path("assets/templates/TEMPLATE_10L.png")
TEMPLATE_LON = resource_path("assets/templates/TEMPLATE_LON.png")


TEMPLATE_Gem = resource_path("assets/templates/TEMPLATE_Gem.png")
TEMPLATE_Godness = resource_path("assets/templates/TEMPLATE_Godness.png")

TEMPLATE_Skip = resource_path("assets/templates/TEMPLATE_Skip.png")
TEMPLATE_JitaEnd = resource_path("assets/templates/TEMPLATE_JitaEnd.png")
TEMPLATE_Home = resource_path("assets/templates/TEMPLATE_Home.png")
TEMPLATE_Yinzi = resource_path("assets/templates/TEMPLATE_Yinzi.png")


# ========= 匹配与识别参数 =========
MATCH_THRESHOLD = 0.99  # 模板匹配阈值
MATCH_ITEM = 0.8       # 道具匹配阈值


# ========= 区域定义 =========
REGION1 = (20, 500, 110, 550)      # 区域1
REGION2 = (95, 500, 350, 550)      # 区域2
REGION3 = (40, 550, 400, 580)      # 区域3
REGION4 = (550, 800, 700, 900)     # 区域4
REGION5 = (30, 930, 700, 1070)     # 掉落区域


# ========= 时间与去重参数 =========
CAPTURE_INTERVAL = 0.1  # 截图间隔（秒）
TIME_WINDOW = 5         # 去重时间窗口（秒）
LAST_DIAMOND_TIME = None  # 上次钻石记录时间
PREV_DIAMOND = None     # 上次钻石数值