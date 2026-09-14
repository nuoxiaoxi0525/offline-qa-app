#!/bin/bash
# ============================================
# 离线搜题宝 - 一键打包脚本
# 适用于 Linux / WSL2 (Ubuntu)
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "============================================"
echo "  离线搜题宝 - Buildozer APK 一键打包"
echo "============================================"
echo ""

# 1. 检查运行环境
info "检查运行环境..."
if [[ "$(uname -s)" == "Linux" ]]; then
    success "运行环境: Linux"
else
    error "此脚本仅支持 Linux / WSL2 环境"
    exit 1
fi

# 2. 检查Python
info "检查Python环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    success "Python版本: $PYTHON_VERSION"
else
    error "未找到Python3，请先安装: sudo apt install python3 python3-pip"
    exit 1
fi

# 3. 检查Buildozer
info "检查Buildozer..."
if command -v buildozer &> /dev/null; then
    BUILDOZER_VERSION=$(buildozer --version 2>&1 | head -1)
    success "Buildozer版本: $BUILDOZER_VERSION"
else
    warning "未找到Buildozer，正在安装..."
    pip3 install buildozer==1.5.0 cython==0.29.36
    success "Buildozer安装完成"
fi

# 4. 检查Java
info "检查Java环境..."
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -1)
    success "Java版本: $JAVA_VERSION"
else
    warning "未找到Java，正在安装OpenJDK 17..."
    sudo apt update
    sudo apt install -y openjdk-17-jdk
    echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
    echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
    export PATH=$JAVA_HOME/bin:$PATH
    success "Java安装完成"
fi

# 5. 检查项目文件
info "检查项目文件..."
REQUIRED_FILES=("main.py" "config.py" "buildozer.spec" "requirements.txt")
MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    error "缺少必要文件: ${MISSING_FILES[*]}"
    error "请确保在项目根目录运行此脚本"
    exit 1
fi
success "项目文件检查通过"

# 6. 检查磁盘空间
info "检查磁盘空间..."
AVAILABLE_SPACE=$(df -h . | tail -1 | awk '{print $4}')
AVAILABLE_GB=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE_GB" -lt 10 ]; then
    warning "磁盘空间不足10GB（当前: $AVAILABLE_SPACE），打包可能失败"
    warning "建议至少保留20GB可用空间"
    read -p "是否继续？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    success "磁盘空间: $AVAILABLE_SPACE"
fi

# 7. 清理旧构建（可选）
echo ""
read -p "是否清理旧的构建文件？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    info "清理旧构建文件..."
    rm -rf .buildozer
    rm -rf bin/*.apk 2>/dev/null || true
    success "清理完成"
fi

# 8. 开始打包
echo ""
info "开始打包APK..."
info "首次打包会自动下载Android SDK/NDK，约需30-60分钟"
info "后续打包约需5-15分钟"
echo ""
echo "============================================"
echo "  打包开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

START_TIME=$(date +%s)

# 执行Buildozer打包
if buildozer android debug 2>&1 | tee build.log; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    DURATION_MIN=$((DURATION / 60))
    DURATION_SEC=$((DURATION % 60))

    echo ""
    echo "============================================"
    success "打包成功！"
    echo "打包耗时: ${DURATION_MIN}分${DURATION_SEC}秒"
    echo "============================================"
    echo ""

    # 9. 查找生成的APK
    info "查找生成的APK文件..."
    APK_FILES=$(find bin -name "*.apk" -type f 2>/dev/null | sort)
    if [ -n "$APK_FILES" ]; then
        echo ""
        success "生成的APK文件:"
        echo "$APK_FILES" | while read -r apk; do
            APK_SIZE=$(du -h "$apk" | cut -f1)
            echo "  - $apk ($APK_SIZE)"
        done
        echo ""

        # 10. 如果是WSL2环境，复制到Windows桌面
        if grep -qi microsoft /proc/version; then
            info "检测到WSL2环境"
            WINDOWS_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')
            if [ -n "$WINDOWS_USER" ]; then
                DESKTOP_PATH="/mnt/c/Users/$WINDOWS_USER/Desktop"
                if [ -d "$DESKTOP_PATH" ]; then
                    read -p "是否将APK复制到Windows桌面？(y/n): " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        cp bin/*.apk "$DESKTOP_PATH/"
                        success "APK已复制到: $DESKTOP_PATH"
                    fi
                fi
            fi
        fi
    else
        warning "未找到APK文件，请检查build.log"
    fi

else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    DURATION_MIN=$((DURATION / 60))
    DURATION_SEC=$((DURATION % 60))

    echo ""
    echo "============================================"
    error "打包失败！"
    echo "打包耗时: ${DURATION_MIN}分${DURATION_SEC}秒"
    echo "============================================"
    echo ""
    error "请查看 build.log 获取详细错误信息"
    echo ""
    echo "常见问题排查:"
    echo "  1. 网络问题: 确保能访问Google（下载SDK/NDK需要）"
    echo "  2. 内存不足: 确保至少8GB内存（WSL2可配置.wslconfig）"
    echo "  3. Java版本: 确保安装JDK 17"
    echo "  4. 磁盘空间: 确保至少20GB可用空间"
    echo "  5. 依赖缺失: 运行 sudo apt install build-essential zlib1g-dev ncurses-dev"
    exit 1
fi

echo ""
info "打包流程结束"
echo ""
