[app]

# ============================================
# 离线搜题宝 - Buildozer APK打包配置
# 第4步修正2：移除pandas，用openpyxl读取Excel
# ============================================

# 应用基本信息
title = 离线搜题宝
package.name = offlineqa
package.domain = org.offlineqa
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt,onnx,ttf,xlsx,xls,csv,txt

# 版本
version = 1.0.0

# ============================================
# Python依赖
# 第4步修正2：移除pandas，用openpyxl读取Excel
# 纯Python实现TF-IDF搜题匹配
# ============================================
requirements = python3==3.11.9,hostpython3==3.11.9,kivy,numpy,Pillow,plyer,onnxruntime,rapidocr-onnxruntime,openpyxl

# ============================================
# 安卓配置
# ============================================
orientation = portrait
fullscreen = 0
android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE,RECORD_AUDIO
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.allow_backup = True
android.allow_native = True
android.accept_sdk_license = True

# ============================================
# p4a配置
# 使用master分支（支持Python 3.12及以下）
# ============================================
p4a.branch = master

# ============================================
# 构建配置
# ============================================
[buildozer]
log_level = 2
warn_on_root = 1
build_dir = .buildozer
bin_dir = bin
