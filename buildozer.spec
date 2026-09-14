[app]

# ============================================
# 离线搜题宝 - Buildozer APK打包配置
# 最小测试版本 - 验证基础打包
# ============================================

# 应用基本信息
title = 离线搜题宝
package.name = offlineqa
package.domain = org.offlineqa
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt

# 版本
version = 1.0.0

# ============================================
# Python依赖（最小测试集）
# ============================================
requirements = python3==3.11.9,kivy

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
# 构建配置
# ============================================
[buildozer]
log_level = 2
warn_on_root = 1
build_dir = .buildozer
bin_dir = bin
