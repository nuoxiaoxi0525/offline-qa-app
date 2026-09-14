# GitHub Actions 在线打包APK - 详细操作指南

## 📋 准备工作

### 1. 注册GitHub账号（如果还没有）
- 访问 https://github.com
- 点击右上角 "Sign up" 注册
- 免费账号即可，建议创建**公开仓库**（公开仓库Actions无限免费使用）

---

## 🚀 第一步：创建新仓库

1. 登录GitHub后，点击右上角 **+** 号 → **New repository**
2. 填写仓库信息：
   - **Repository name**: `offline-qa-app`（随便起，英文即可）
   - **Description**: 离线拍照搜题APP（可选）
   - **Public / Private**: 选择 **Public**（公开，Actions免费无限用）
   - **Initialize this repository with**: 全部不勾选
3. 点击绿色按钮 **Create repository**

---

## 📤 第二步：上传项目文件

### 方式A：网页直接上传（最简单，推荐新手）

1. 创建仓库后，你会看到 "Quick setup" 页面
2. 点击 **uploading an existing file** 链接
3. 打开文件资源管理器，进入以下目录：
   ```
   C:\Users\admin\Doubao\chats\2026-09-14\new-chat-1\offline_qa_app
   ```
4. **全选所有文件和文件夹**（Ctrl+A），包括：
   - `.github` 文件夹（隐藏文件夹，需要显示隐藏文件才能看到）
   - `main.py`, `config.py`, `ocr_engine.py` 等所有.py文件
   - `buildozer.spec`, `requirements.txt`
   - `BUILD.md`, `build.sh`, `GITHUB打包指南.md`
   - `assets`, `models`, `temp`, `ui`, `export` 等文件夹
5. 把所有文件**拖拽**到GitHub网页的上传区域
6. 等待上传完成（大文件可能需要几分钟）
7. 页面底部点击绿色按钮 **Commit changes**

> ⚠️ **重要**：必须包含 `.github/workflows/build_apk.yml` 文件，否则不会自动打包！
> 如果看不到 `.github` 文件夹，请在文件资源管理器中开启"显示隐藏项目"（查看 → 显示 → 隐藏的项目）

### 方式B：使用Git命令行（适合有Git基础的用户）

```bash
# 在 offline_qa_app 目录下执行
cd C:\Users\admin\Doubao\chats\2026-09-14\new-chat-1\offline_qa_app
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/offline-qa-app.git
git push -u origin main
```

---

## ⏳ 第三步：等待自动打包

1. 上传完成后，进入你的仓库页面
2. 点击顶部的 **Actions** 标签页
3. 你会看到一个正在运行的工作流：**Build Android APK**
4. 点击进入可以查看实时日志
5. **打包时间约20-40分钟**（首次需要下载Android SDK/NDK）

### 打包过程说明
- 🟡 黄色 = 正在运行
- 🟢 绿色 = 打包成功
- 🔴 红色 = 打包失败（点击查看日志，把错误发给我帮你排查）

---

## 📥 第四步：下载APK

1. 打包成功后（显示绿色 ✓），点击进入该工作流
2. 页面最底部找到 **Artifacts** 区域
3. 点击 **offline-qa-apk** 下载
4. 下载的是一个ZIP压缩包，解压后得到APK文件
5. APK文件名类似：`offlineqa-1.0.0-arm64-v8a-debug.apk`

---

## 📱 第五步：安装到手机

1. 把APK文件传到手机（微信/QQ/数据线/U盘均可）
2. 手机设置中开启"安装未知来源应用"
3. 点击APK文件安装
4. 首次启动允许**相机**和**存储**权限
5. 导入题库Excel，开始拍照搜题！

---

## ❓ 常见问题

### Q1: Actions页面没有看到工作流？
**A**: 检查 `.github/workflows/build_apk.yml` 文件是否上传成功。在仓库首页点击 `.github` → `workflows`，确认 `build_apk.yml` 存在。

### Q2: 打包失败了怎么办？
**A**: 
1. 点击失败的工作流，查看红色错误信息
2. 把错误日志截图或复制发给我
3. 我会帮你排查并修复配置

### Q3: 打包时间太长？
**A**: 首次打包需要下载Android SDK(1GB)+NDK(1GB)，约30-40分钟。后续打包有缓存，约10-20分钟。

### Q4: 下载的ZIP解压后没有APK？
**A**: 检查Artifacts名称是否为 `offline-qa-apk`，解压后APK可能在 `bin/` 子目录下。

### Q5: 可以打包Release版本吗？
**A**: 当前配置打包的是Debug版本（可直接安装使用）。Release版本需要签名密钥，后续需要可以再配置。

### Q6: 如何更新APP重新打包？
**A**: 修改代码后重新上传到GitHub，Actions会自动触发重新打包。或者在Actions页面手动点击 **Run workflow**。

---

## 📞 需要帮助？

如果遇到任何问题：
1. 截图Actions页面的错误信息
2. 把错误日志发给我
3. 我会帮你修改配置文件，你重新上传即可

---

**祝打包顺利！** 🎉
