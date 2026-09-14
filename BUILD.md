# 离线搜题宝 - Buildozer APK 完整打包指南

## 📱 项目概述

**离线搜题宝**是一款完全离线运行的安卓拍照搜题APP，基于Kivy框架开发，使用RapidOCR (PP-OCRv4)进行文字识别，支持导入自有题库（Excel/CSV），拍照识别题目后与本地题库语义匹配返回答案解析。

### 核心特性
- ✅ **完全离线**：所有识别和匹配均在本地完成，无需联网
- ✅ **高识别率**：RapidOCR (PP-OCRv4) 中文识别率97%+
- ✅ **广角拍照**：支持后置/广角摄像头，大视野拍摄
- ✅ **题库导入**：支持Excel/CSV格式，兼容刷刷题APP格式
- ✅ **语义匹配**：TF-IDF + 余弦相似度 + 三级校验，支持题目变种识别
- ✅ **多科目管理**：支持法规/管理/技术/实务等多科目分类

### 技术架构
```
┌─────────────────────────────────────────┐
│              Kivy UI层                   │
│  首页/拍照/结果/导入/管理 五大页面       │
├─────────────────────────────────────────┤
│           业务逻辑层                     │
│  图像预处理 → OCR识别 → 题库匹配 → 展示  │
├─────────────────────────────────────────┤
│           核心引擎层                     │
│  OpenCV  │ RapidOCR  │ SQLite │ TF-IDF │
│  (预处理) │ (PP-OCRv4)│ (题库) │ (匹配) │
├─────────────────────────────────────────┤
│           硬件访问层                     │
│  plyer相机  │ 安卓存储权限  │ 传感器    │
└─────────────────────────────────────────┘
```

---

## 🛠️ 打包环境准备（WSL2 Ubuntu）

### 方式一：WSL2（推荐Windows用户）

#### 1. 安装WSL2
以管理员身份打开PowerShell，执行：
```powershell
wsl --install -d Ubuntu
```
安装完成后重启电脑，设置Ubuntu用户名和密码。

#### 2. 进入WSL2并更新系统
```bash
wsl
sudo apt update && sudo apt upgrade -y
```

#### 3. 安装系统依赖
```bash
sudo apt install -y \
    git \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    zlib1g-dev \
    ncurses-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libtinfo5 \
    cmake \
    libffi-dev \
    libssl-dev \
    autoconf \
    libtool \
    pkg-config \
    libsqlite3-dev \
    openjdk-17-jdk \
    unzip \
    zip \
    wget \
    curl \
    libgl1-mesa-dev \
    libgles2-mesa-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libmtdev-dev \
    xclip \
    xsel
```

#### 4. 安装Python打包工具
```bash
pip3 install --upgrade pip
pip3 install buildozer==1.5.0 cython==0.29.36
```

#### 5. 配置Java环境
```bash
# 检查Java版本（需要JDK 17）
java -version

# 如果版本不对，设置JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### 方式二：原生Linux（Ubuntu 22.04+）
直接执行上面的步骤3-5即可。

### 方式三：在线打包（GitHub Actions）
如果没有Linux环境，可以使用GitHub Actions在线打包：
1. 将项目上传到GitHub
2. 创建 `.github/workflows/build.yml`
3. 使用 `ArtemSBulgakov/buildozer-action@v1` 自动打包
4. 从Actions产物中下载APK

---

## 📦 打包步骤

### 1. 准备项目文件
将 `offline_qa_app` 目录复制到WSL2环境中：
```bash
# 在Windows PowerShell中（假设项目在C:\Users\admin\Doubao\chats\2026-09-14\new-chat-1\）
wsl
cd /mnt/c/Users/admin/Doubao/chats/2026-09-14/new-chat-1/offline_qa_app

# 或者复制到WSL2主目录（推荐，避免文件系统权限问题）
cp -r /mnt/c/Users/admin/Doubao/chats/2026-09-14/new-chat-1/offline_qa_app ~/
cd ~/offline_qa_app
```

### 2. 检查项目文件
```bash
ls -la
# 应该包含：
# main.py, config.py, image_processor.py, ocr_engine.py
# question_bank.py, search_engine.py, importer.py, camera_handler.py
# buildozer.spec, requirements.txt, BUILD.md
```

### 3. 首次打包（会自动下载SDK/NDK，约30-60分钟）
```bash
buildozer android debug
```

**首次打包会自动下载：**
- Android SDK (约1GB)
- Android NDK r25b (约1GB)
- Python-for-android依赖
- 所有Python包的安卓编译版本

### 4. 后续打包（增量编译，约5-15分钟）
```bash
buildozer android debug
```

### 5. 打包Release版本（可选，需要签名）
```bash
# 生成签名密钥
keytool -genkey -v -keystore my-release-key.keystore -alias alias_name -keyalg RSA -keysize 2048 -validity 10000

# 打包Release
buildozer android release
```

### 6. 查找生成的APK
```bash
ls -la bin/
# 输出示例：
# offlineqa-1.0.0-arm64-v8a-debug.apk
# offlineqa-1.0.0-armeabi-v7a-debug.apk
```

---

## 📱 APK安装和使用

### 1. 传输APK到手机
```bash
# 方式一：通过WSL2复制到Windows，再传到手机
cp bin/offlineqa-1.0.0-arm64-v8a-debug.apk /mnt/c/Users/admin/Desktop/

# 方式二：通过adb直接安装（手机开启USB调试）
adb install bin/offlineqa-1.0.0-arm64-v8a-debug.apk
```

### 2. 手机安装
1. 将APK文件传到手机（微信/QQ/U盘/数据线均可）
2. 手机设置中允许"安装未知来源应用"
3. 点击APK文件安装
4. 首次启动会请求**相机**和**存储**权限，请允许

### 3. 使用流程
```
安装APP
    ↓
首次启动（请求权限）
    ↓
导入题库（首页 → 导入题库 → 选择Excel文件 → 开始导入）
    ↓
拍照搜题（首页 → 拍照搜题 → 对准题目 → 点击拍照按钮）
    ↓
自动识别 + 题库匹配 → 显示答案和解析
```

### 4. 题库Excel格式
| 列名 | 必填 | 说明 | 示例 |
|------|------|------|------|
| 题型 | 否 | 单选题/多选题 | 单选题 |
| 题目 | 是 | 题干内容 | 根据《安全生产法》... |
| 选项 | 否 | 用\|分隔 | A.xxx\|B.xxx\|C.xxx\|D.xxx |
| 答案 | 是 | A-D字母 | D 或 ABD |
| 解析 | 否 | 答案解析 | 根据《安全生产法》... |

---

## 🔧 常见问题和解决方案

### Q1: 打包时报错 `SDK/NDK not found`
**解决方案**：
```bash
# 手动指定SDK/NDK路径（如果自动下载失败）
export ANDROIDSDK=~/.buildozer/android/platform/android-sdk
export ANDROIDNDK=~/.buildozer/android/platform/android-ndk-r25b

# 或者删除.buildozer目录重新开始
rm -rf .buildozer
buildozer android debug
```

### Q2: 打包时报错 `Java not found` 或 `JAVA_HOME not set`
**解决方案**：
```bash
# 安装JDK 17
sudo apt install openjdk-17-jdk

# 设置环境变量
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# 验证
java -version
```

### Q3: RapidOCR在APK中无法加载模型
**解决方案**：
RapidOCR的模型文件会自动包含在 `rapidocr-onnxruntime` 包中。如果加载失败：
1. 检查 `buildozer.spec` 中的 `source.include_exts` 是否包含 `onnx`
2. 手动将模型文件复制到项目目录：
```bash
# 找到rapidocr的模型路径
python3 -c "import rapidocr_onnxruntime; print(rapidocr_onnxruntime.__path__)"

# 复制模型到项目目录
cp -r <rapidocr_path>/models ~/offline_qa_app/models/
```

### Q4: 摄像头无法启动或黑屏
**解决方案**：
1. 检查是否授予相机权限
2. 在 `buildozer.spec` 中确认 `android.permissions` 包含 `CAMERA`
3. 部分手机需要在设置中手动开启相机权限
4. Kivy的Camera组件在部分设备上可能不兼容，可尝试使用plyer的camera接口

### Q5: APK体积过大（超过200MB）
**解决方案**：
1. 只打包需要的架构：修改 `android.archs = arm64-v8a`（只打包64位）
2. 使用 `opencv-python-headless` 替代 `opencv-python`（已配置）
3. 清理不必要的依赖
4. 使用Release版本并开启压缩

### Q6: 打包时内存不足（OOM）
**解决方案**：
```bash
# 增加WSL2内存限制（在Windows的用户目录创建.wslconfig）
# C:\Users\admin\.wslconfig
[wsl2]
memory=8GB
processors=4

# 然后重启WSL
wsl --shutdown
wsl
```

### Q7: OCR识别速度慢
**解决方案**：
1. RapidOCR首次加载模型需要2-3秒，后续识别约0.5-1秒/题
2. 确保使用 `arm64-v8a` 架构（64位性能更好）
3. 图像预处理时限制最大宽度为2000px（已配置）
4. 可以在 `config.py` 中调整 `OCR_CONFIG["rec_batch_num"]` 优化批处理

---

## 📊 离线能力说明

### 完全离线的功能
| 功能 | 离线支持 | 说明 |
|------|----------|------|
| 摄像头拍照 | ✅ | 本地调用，无需网络 |
| 图像预处理 | ✅ | OpenCV本地计算 |
| OCR文字识别 | ✅ | RapidOCR模型内置在APK中 |
| 题库存储 | ✅ | SQLite本地数据库 |
| 搜题匹配 | ✅ | TF-IDF本地计算 |
| 题库导入 | ✅ | 读取本地Excel文件 |
| 答案解析展示 | ✅ | 本地数据展示 |

### 需要联网的场景
1. **首次下载APK安装包**（约80-120MB）
2. **用户自己准备题库Excel文件**（从电脑传输到手机）
3. **APP更新升级**（下载新版本APK）

### APK体积构成
| 组件 | 体积 | 说明 |
|------|------|------|
| Python运行时 | ~30MB | CPython for Android |
| Kivy + SDL2 | ~15MB | UI框架 |
| OpenCV | ~20MB | 图像处理 |
| RapidOCR + ONNX | ~25MB | OCR引擎+模型 |
| scikit-learn + numpy | ~15MB | 机器学习 |
| pandas + openpyxl | ~10MB | 数据处理 |
| 其他依赖 | ~10MB | plyer, Pillow等 |
| **总计** | **~125MB** | 实际APK约80-120MB（压缩后） |

---

## 🚀 快速开始（一键打包脚本）

项目根目录提供了 `build.sh` 一键打包脚本：

```bash
# 赋予执行权限
chmod +x build.sh

# 执行打包
./build.sh
```

脚本会自动：
1. 检查环境依赖
2. 清理旧的构建文件
3. 执行Buildozer打包
4. 显示生成的APK路径
5. 复制APK到Windows桌面（如果是WSL2环境）

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2026-09-14 | 首个版本，支持拍照搜题、题库导入、多科目管理 |

---

## 📞 技术支持

如遇打包问题，请检查：
1. WSL2/Ubuntu版本是否为22.04+
2. JDK版本是否为17
3. 网络是否能访问Google（下载SDK/NDK需要）
4. 内存是否至少8GB
5. 磁盘空间是否至少20GB（构建过程需要）

---

**祝打包顺利！** 🎉
