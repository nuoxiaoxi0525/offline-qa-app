# -*- coding: utf-8 -*-
"""
离线拍照搜题APP - 配置文件
Buildozer APK版本 - 使用RapidOCR (PP-OCRv4)
"""
import os

# 应用基础配置
APP_NAME = "离线搜题宝"
APP_VERSION = "1.0.0"

# 路径配置（安卓环境下使用app私有目录）
try:
    from android.storage import app_storage_path
    BASE_DIR = app_storage_path()
except ImportError:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "question_bank.db")
MODEL_DIR = os.path.join(BASE_DIR, "models")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
EXPORT_DIR = os.path.join(BASE_DIR, "export")
PHOTO_DIR = os.path.join(BASE_DIR, "photos")

# 确保目录存在
for d in [TEMP_DIR, EXPORT_DIR, MODEL_DIR, PHOTO_DIR]:
    os.makedirs(d, exist_ok=True)

# OCR配置 - RapidOCR (PP-OCRv4)
OCR_CONFIG = {
    "engine": "rapidocr",              # OCR引擎：rapidocr (PP-OCRv4)
    "det_model": "ch_PP-OCRv4_det",    # 检测模型
    "rec_model": "ch_PP-OCRv4_rec",    # 识别模型
    "cls_model": "ch_ppocr_mobile_v2.0_cls",  # 方向分类模型
    "use_det": True,                    # 使用文本检测
    "use_cls": True,                    # 使用方向分类
    "det_box_thresh": 0.5,              # 检测框阈值
    "det_unclip_ratio": 1.6,            # 检测框膨胀比例
    "rec_batch_num": 6,                 # 识别批处理数量
    "min_side": 30,                     # 最小边长
    "max_side": 2000,                   # 最大边长
}

# 图像预处理配置
PREPROCESS = {
    "max_width": 2000,
    "contrast_alpha": 1.5,
    "brightness_beta": 20,
    "denoise_h": 10,
    "denoise_templateWindowSize": 7,
    "denoise_searchWindowSize": 21,
    "max_skew_angle": 30,
}

# 搜题匹配配置
SEARCH = {
    "top_k": 5,
    "min_similarity": 0.25,
    "use_tfidf": True,
    "ngram_range": (1, 2),
    "max_features": 50000,
}

# 题库导入配置
IMPORT = {
    "supported_formats": [".xlsx", ".xls", ".csv"],
    "required_columns": ["题目", "答案"],
    "optional_columns": ["题型", "选项", "解析"],
    "batch_size": 1000,
}

# 摄像头配置
CAMERA_CONFIG = {
    "preferred_facing": "back",         # 优先使用后置摄像头
    "resolution": (1920, 1080),         # 拍照分辨率
    "enable_wide_angle": True,           # 启用广角（如果设备支持）
}

# UI配置
UI = {
    "theme_color": [0.13, 0.59, 0.95, 1],
    "accent_color": [1.0, 0.6, 0.0, 1],
    "bg_color": [0.96, 0.96, 0.98, 1],
    "text_color": [0.2, 0.2, 0.2, 1],
    "font_size_title": 24,
    "font_size_normal": 16,
    "font_size_small": 12,
}
