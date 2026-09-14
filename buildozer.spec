[app]

# ============================================
# 离线搜题宝 - Buildozer APK打包配置
# OCR引擎：RapidOCR (PP-OCRv4) 中文识别率97%+
# ============================================

# 应用基本信息
title = 离线搜题宝
package.name = offlineqa
package.domain = org.offlineqa
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt,onnx,xml

# 版本
version = 1.0.0

# ============================================
# Python依赖（核心）
# ============================================
requirements = python3,kivy,opencv-python-headless,numpy,pandas,openpyxl,scikit-learn,rapidocr-onnxruntime,onnxruntime,Pillow,plyer

# ============================================
# 安卓配置
# ============================================
orientation = portrait
fullscreen = 0
android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.allow_native = True
android.accept_sdk_license = True

# ============================================
# 应用图标和启动画面
# ============================================
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png
# presplash.color = #2196F3

# ============================================
# OCR模型文件打包
# RapidOCR模型会自动包含在rapidocr-onnxruntime包中
# 如需使用自定义模型，取消下面的注释并将模型放入models/rapidocr/目录
# ============================================
# source.include_patterns = assets/*,models/*

# ============================================
# 构建配置
# ============================================
[buildozer]
log_level = 2
warn_on_root = 1
build_dir = .buildozer
bin_dir = bin

# ============================================
# 安卓NDK和SDK配置（自动下载）
# ============================================
# android.sdk_path = 
# android.ndk_path = 
# android.ndk_version = 25b
# android.build_tools_version = 33.0.2

# ============================================
# 高级配置
# ============================================
# android.meta_data = 
# android.add_libs = 
# android.add_jars = 
# android.add_aars = 
# p4a.source_dir = 
# p4a.local_recipes = 
# p4a.bootstrap = sdl2
