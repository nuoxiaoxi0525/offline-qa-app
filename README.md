# 离线搜题宝 - 离线拍照搜题APP

基于刷刷题拍照搜题技术原理开发的离线搜题APP，支持导入自有题库、拍照识别题目、离线语义匹配返回答案。

## 功能特性

- 📷 **拍照搜题**：拍照或从相册选择题目图片，自动识别并匹配题库
- 🔍 **文字搜题**：直接输入题目文字进行搜索
- 📥 **题库导入**：支持Excel/CSV格式导入，兼容刷刷题APP格式
- 📚 **题库管理**：多科目分类管理，统计题目数量
- 🔒 **完全离线**：所有识别和匹配均在本地完成，无需联网，保护隐私
- 🎯 **三级匹配**：TF-IDF语义匹配 + 关键词重合 + 题目变体识别

## 技术架构

对应刷刷题五段式技术原理：

| 层级 | 刷刷题技术 | 本APP实现 |
|------|-----------|-----------|
| 图像预处理 | 亮度/对比度调整、倾斜矫正、二值化、CNN去噪 | OpenCV CLAHE + minAreaRect倾斜矫正 + 自适应二值化 + 非局部均值去噪 |
| 文本检测 | DBNet可微分二值化网络 | Tesseract内置文本检测 + 置信度过滤 |
| OCR识别 | 自研CNN+Bi-LSTM+CTC引擎（98.7%） | Tesseract 5.x + 中文模型chi_sim（约90-93%） |
| NLP纠错 | 同音字/形近字修正、公式校验 | 正则后处理 + 选项格式规范化 |
| 题库匹配 | 三级校验 + 向量空间语义匹配 | TF-IDF + 余弦相似度 + 关键词重合 + 变体识别 |

## 项目结构

```
offline_qa_app/
├── main.py              # 主程序（Kivy UI）
├── config.py            # 配置文件
├── image_processor.py   # 图像预处理模块
├── ocr_engine.py        # OCR识别引擎
├── question_bank.py     # 题库管理（SQLite）
├── search_engine.py     # 搜题匹配引擎（TF-IDF）
├── importer.py          # 题库导入器（Excel/CSV）
├── buildozer.spec       # APK打包配置
├── ui/                  # UI模块
├── assets/              # 资源文件（图标等）
├── models/              # OCR模型（tessdata）
└── README.md            # 说明文档
```

## 题库导入格式

Excel/CSV文件需包含以下列（兼容刷刷题APP格式）：

| 列名 | 必填 | 说明 | 示例 |
|------|------|------|------|
| 题型 | 否 | 单选题/多选题 | 单选题 |
| 题目 | 是 | 题干内容 | 根据《安全生产法》... |
| 选项 | 否 | 用英文竖线`\|`分隔 | A.xxx\|B.xxx\|C.xxx\|D.xxx |
| 答案 | 是 | A-D字母，多选为组合 | D 或 ABD |
| 解析 | 否 | 答案解析 | 根据《安全生产法》... |

## 桌面端运行（开发测试）

### 环境要求
- Python 3.8+
- Windows/Linux/macOS

### 安装依赖
```bash
pip install kivy opencv-python pytesseract pillow numpy pandas openpyxl scikit-learn
```

### 安装Tesseract OCR
- **Windows**: 下载 https://github.com/UB-Mannheim/tesseract/wiki 安装，安装时勾选中文语言包
- **Linux**: `sudo apt install tesseract-ocr tesseract-ocr-chi-sim`
- **macOS**: `brew install tesseract tesseract-lang`

### 运行
```bash
cd offline_qa_app
python main.py
```

## 打包为安卓APK

### 方法一：Linux环境打包（推荐）

Buildozer需要Linux环境，Windows用户可使用WSL2或虚拟机。

#### 1. 准备Linux环境（WSL2 Ubuntu）
```bash
# 安装依赖
sudo apt update
sudo apt install -y git python3-pip build-essential \
    zlib1g-dev ncurses-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev \
    autoconf libtool pkg-config libsqlite3-dev \
    openjdk-17-jdk unzip zip wget

# 安装Buildozer
pip3 install buildozer cython==0.29.36
```

#### 2. 准备OCR模型
```bash
# 创建tessdata目录
mkdir -p models/tessdata
# 下载中文和英文模型
cd models/tessdata
wget https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata
wget https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
cd ../../
```

#### 3. 修改buildozer.spec
确保以下配置正确：
```
source.include_exts = py,png,jpg,kv,atlas,json,txt,traineddata
source.include_patterns = assets/*,models/tessdata/*
```

#### 4. 打包APK
```bash
cd offline_qa_app
buildozer android debug
```

首次打包会自动下载Android SDK/NDK，约需30-60分钟。
打包完成后APK在 `bin/` 目录下。

### 方法二：在线打包服务

如果没有Linux环境，可使用在线Buildozer打包服务：
- https://github.com/ArtemSBulgakov/buildozer-action （GitHub Actions）
- 将项目上传到GitHub，使用Actions自动打包

### 方法三：PWA网页版（替代方案）

如果APK打包困难，可使用PWA版本（HTML+JS+Tesseract.js），可添加到手机主屏幕，支持离线使用。联系开发者获取PWA版本。

## APK安装和使用

1. 将生成的APK文件传到手机
2. 手机设置中允许安装未知来源应用
3. 点击APK文件安装
4. 首次启动会请求相机和存储权限，请允许
5. 点击"导入题库"选择Excel文件导入
6. 点击"拍照搜题"拍摄题目即可搜索

## 已知限制

1. **OCR识别率**：Tesseract中文印刷体识别率约90-93%，低于刷刷题的98.7%。建议拍摄时保证光线充足、文字清晰、角度端正。
2. **模型体积**：中文OCR模型约50MB，打包后APK约80-100MB。
3. **手写体**：Tesseract对手写体识别效果较差，建议使用印刷体题目。
4. **复杂公式**：数学/物理公式识别可能不准确，本APP主要针对文字类题目（如注安考试）。

## 优化建议

如需更高识别率，可考虑：
1. 替换OCR引擎为PaddleOCR-Lite（模型约200MB，中文识别率97%+）
2. 增加题目图像裁剪功能，只框选题目区域
3. 增加手动修正OCR结果的功能
4. 增加错题本和收藏功能

## 许可证

MIT License
