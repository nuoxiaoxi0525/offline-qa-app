[app]

# ============================================
# 离线搜题宝 - Buildozer APK打包配置
# 第3步：添加OCR识别依赖
# ============================================

# 应用基本信息
title = 离线搜题宝
package.name = offlineqa
package.domain = org.offlineqa
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt,onnx

# 版本
version = 1.0.0

# ============================================
# Python依赖
# 第3步：添加OCR识别依赖
# ============================================
requirements = python3==3.11.9,hostpython3==3.11.9,kivy,numpy,Pillow,plyer,onnxruntime,rapidocr-onnxruntime

# ============================================
# 安卓配置
# ============================================
orientation = portrait
fullscreen = 0
android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
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
