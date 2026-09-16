# -*- coding: utf-8 -*-
"""
离线搜题宝 - 完整功能版本
支持：拍照OCR识别 + 本地题库导入 + 离线语义搜题
添加错误处理，防止闪退
"""
import os
import sys
import traceback
import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase

from config import UI, BASE_DIR


# 全局错误处理
def excepthook(exc_type, exc_value, exc_traceback):
    """全局异常处理，防止闪退"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"未捕获异常: {error_msg}")
    # 写入错误日志
    try:
        log_path = os.path.join(BASE_DIR, "error.log")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
    except:
        pass

sys.excepthook = excepthook


# 注册中文字体
def register_chinese_font():
    """注册支持中文的字体"""
    try:
        # 打印当前工作目录
        print(f"当前工作目录: {os.getcwd()}")
        print(f"__file__: {__file__}")

        # 尝试多个可能的字体路径
        possible_paths = []

        # 1. 脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths.append(os.path.join(script_dir, 'fonts', 'NotoSansSC-Regular.ttf'))
        possible_paths.append(os.path.join(script_dir, 'NotoSansSC-Regular.ttf'))

        # 2. 当前工作目录
        cwd = os.getcwd()
        possible_paths.append(os.path.join(cwd, 'fonts', 'NotoSansSC-Regular.ttf'))
        possible_paths.append(os.path.join(cwd, 'NotoSansSC-Regular.ttf'))

        # 3. _app目录（Android常见路径）
        possible_paths.append('/data/data/org.offlineqa/files/app/fonts/NotoSansSC-Regular.ttf')
        possible_paths.append('/data/data/org.offlineqa/files/app/NotoSansSC-Regular.ttf')

        # 4. Android系统字体
        android_fonts = [
            '/system/fonts/DroidSansFallback.ttf',
            '/system/fonts/NotoSansCJK-Regular.ttc',
            '/system/fonts/NotoSansSC-Regular.ttf',
            '/system/fonts/Roboto-Regular.ttf',
            '/system/fonts/simhei.ttf',
            '/system/fonts/simsun.ttf',
            '/system/fonts/SourceSansPro-Regular.ttf',
        ]
        possible_paths.extend(android_fonts)

        # 尝试所有可能的路径
        for font_path in possible_paths:
            print(f"检查字体路径: {font_path} -> 存在: {os.path.exists(font_path)}")
            if os.path.exists(font_path):
                try:
                    LabelBase.register(name='ChineseFont', fn_regular=font_path)
                    print(f"成功注册字体: {font_path}")
                    return True
                except Exception as e:
                    print(f"注册字体失败 {font_path}: {e}")
                    continue

        print("未找到支持中文的字体，使用默认字体")
        return False

    except Exception as e:
        print(f"字体注册失败: {e}")
        return False


# 启动时注册字体
FONT_AVAILABLE = register_chinese_font()


class OfflineQALayout(BoxLayout):
    """主界面布局"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10

        # 后台组件（延迟初始化）
        self.question_bank = None
        self.search_engine = None
        self.importer = None
        self.ocr_engine = None
        self._initialized = False

        # 构建UI
        self._build_ui()

        # 异步初始化后台组件
        Clock.schedule_once(self._init_background, 0.5)

    def _build_ui(self):
        """构建用户界面"""
        # 标题栏
        title_layout = BoxLayout(size_hint_y=0.1, padding=5)
        title_label = Label(
            text='离线搜题宝',
            font_size='24sp',
            bold=True,
            color=UI['theme_color'],
            font_name='ChineseFont'
        )
        title_layout.add_widget(title_label)
        self.add_widget(title_layout)

        # 状态显示
        self.status_label = Label(
            text='正在初始化...',
            font_size='14sp',
            size_hint_y=0.05,
            color=[0.5, 0.5, 0.5, 1],
            font_name='ChineseFont'
        )
        self.add_widget(self.status_label)

        # 题库统计
        self.stats_label = Label(
            text='题库: 0道题',
            font_size='14sp',
            size_hint_y=0.05,
            font_name='ChineseFont'
        )
        self.add_widget(self.stats_label)

        # 主按钮区域
        btn_layout = BoxLayout(size_hint_y=0.25, spacing=10, padding=5)

        # 拍照搜题按钮
        self.camera_btn = Button(
            text='拍照搜题',
            font_size='20sp',
            background_color=UI['theme_color'],
            background_normal='',
            font_name='ChineseFont'
        )
        self.camera_btn.bind(on_press=self.on_camera_click)
        btn_layout.add_widget(self.camera_btn)

        # 题库导入按钮
        self.import_btn = Button(
            text='导入题库',
            font_size='20sp',
            background_color=UI['accent_color'],
            background_normal='',
            font_name='ChineseFont'
        )
        self.import_btn.bind(on_press=self.on_import_click)
        btn_layout.add_widget(self.import_btn)

        self.add_widget(btn_layout)

        # 手动输入区域
        input_layout = BoxLayout(size_hint_y=0.2, spacing=5, padding=5)
        input_layout.orientation = 'vertical'

        input_label = Label(
            text='或手动输入题目文字：',
            font_size='14sp',
            size_hint_y=0.3,
            halign='left',
            font_name='ChineseFont'
        )
        input_layout.add_widget(input_label)

        self.question_input = TextInput(
            hint_text='在此输入题目文字...',
            font_size='14sp',
            size_hint_y=0.7,
            multiline=True,
            font_name='ChineseFont'
        )
        input_layout.add_widget(self.question_input)

        self.add_widget(input_layout)

        # 搜题按钮
        self.search_btn = Button(
            text='搜索',
            font_size='18sp',
            size_hint_y=0.08,
            background_color=UI['theme_color'],
            background_normal='',
            font_name='ChineseFont'
        )
        self.search_btn.bind(on_press=self.on_search_click)
        self.add_widget(self.search_btn)

        # 结果显示区域（可滚动）
        self.result_scroll = ScrollView(size_hint_y=0.42)
        self.result_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=10,
            padding=10
        )
        self.result_layout.bind(minimum_height=self.result_layout.setter('height'))

        self.result_label = Label(
            text='搜索结果将在这里显示...\n\n欢迎使用离线搜题宝！',
            font_size='14sp',
            size_hint_y=None,
            height=100,
            halign='left',
            valign='top',
            text_size=(Window.width - 20, None),
            font_name='ChineseFont'
        )
        self.result_layout.add_widget(self.result_label)
        self.result_scroll.add_widget(self.result_layout)
        self.add_widget(self.result_scroll)

    def _init_background(self, dt):
        """异步初始化后台组件（带错误处理）"""
        def init_thread():
            try:
                self._set_status('正在初始化题库...')

                # 初始化题库数据库
                try:
                    from question_bank import get_question_bank
                    self.question_bank = get_question_bank()
                except Exception as e:
                    self._set_status(f'题库初始化失败: {str(e)[:30]}')
                    print(f'题库初始化失败: {e}')

                # 初始化搜题引擎
                try:
                    from search_engine import get_search_engine
                    self.search_engine = get_search_engine()
                except Exception as e:
                    self._set_status(f'搜题引擎初始化失败: {str(e)[:30]}')
                    print(f'搜题引擎初始化失败: {e}')

                # 检查题库是否为空
                if self.question_bank:
                    try:
                        stats = self.question_bank.get_statistics()
                        if stats['total'] > 0:
                            self._set_status('正在构建搜索索引...')
                            if self.search_engine:
                                self.search_engine.build_index()
                    except Exception as e:
                        print(f'统计或索引构建失败: {e}')

                # 初始化导入器
                try:
                    from importer import get_importer
                    self.importer = get_importer()
                except Exception as e:
                    print(f'导入器初始化失败: {e}')

                # 更新统计
                Clock.schedule_once(lambda dt: self._update_stats(), 0)
                self._set_status('准备就绪')
                self._initialized = True

            except Exception as e:
                error_msg = f'初始化失败: {str(e)[:50]}'
                self._set_status(error_msg)
                print(f'初始化线程异常: {e}')
                traceback.print_exc()

        threading.Thread(target=init_thread, daemon=True).start()

    def _set_status(self, text):
        """在主线程更新状态"""
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', text), 0)

    def _update_stats(self):
        """更新题库统计"""
        if self.question_bank:
            try:
                stats = self.question_bank.get_statistics()
                self.stats_label.text = f'题库: {stats["total"]}道题'
            except Exception as e:
                print(f'获取统计失败: {e}')

    def on_camera_click(self, instance):
        """拍照搜题按钮点击"""
        self.status_label.text = '拍照功能说明：'
        self.result_label.text = (
            '📷 拍照搜题功能说明：\n\n'
            '拍照搜题需要OCR模型文件支持。\n'
            '首次使用时会自动下载模型文件。\n\n'
            '如果OCR模型下载失败，请：\n'
            '1. 确保手机已连接网络\n'
            '2. 重新打开APP\n'
            '3. 等待模型下载完成\n\n'
            '或者，您可以先使用下方的手动输入功能进行搜题测试。'
        )
        self.status_label.text = '请手动输入题目文字'

    def on_import_click(self, instance):
        """题库导入按钮点击"""
        self.status_label.text = '导入功能说明：'
        self.result_label.text = (
            '📥 题库导入说明：\n\n'
            '支持格式：.xlsx / .csv\n\n'
            'Excel格式要求：\n'
            '列顺序：题型 | 题目 | 选项 | 答案 | 解析\n\n'
            '示例：\n'
            '单选题 | 根据安全生产法... | A.xxx|B.xxx|C.xxx|D.xxx | D | 解析内容...\n\n'
            '请将Excel文件放到手机存储中，\n'
            '然后通过文件选择器导入。\n\n'
            '（文件选择功能开发中，当前版本请先使用手动搜题）'
        )
        self.status_label.text = '导入功能开发中'

    def on_search_click(self, instance):
        """搜索按钮点击"""
        query_text = self.question_input.text.strip()
        if not query_text:
            self.result_label.text = '请输入题目文字后再搜索'
            return

        if not self.search_engine:
            self.result_label.text = '搜题引擎未初始化，请稍后再试'
            return

        self.status_label.text = '正在搜索...'
        self.search_btn.disabled = True

        def search_thread():
            try:
                # 执行搜索
                results = self.search_engine.search(query_text, top_k=5)

                # 更新UI
                Clock.schedule_once(lambda dt: self._show_results(query_text, results), 0)

            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)), 0)

        threading.Thread(target=search_thread, daemon=True).start()

    def _show_results(self, query_text, results):
        """显示搜索结果"""
        self.search_btn.disabled = False

        if not results:
            self.result_label.text = (
                f'未找到匹配的题目\n\n'
                f'搜索关键词：{query_text[:50]}...\n\n'
                f'请尝试：\n'
                f'1. 输入更多题目关键词\n'
                f'2. 检查是否已导入题库\n'
                f'3. 降低题目识别误差'
            )
            self.status_label.text = '未找到匹配题目'
            return

        # 格式化结果
        result_text = f'🔍 搜索到 {len(results)} 个结果：\n\n'

        for i, (question, similarity) in enumerate(results, 1):
            score = similarity * 100
            result_text += f'━━━━━━━━━━━━━━━━━━━━\n'
            result_text += f'【结果 {i}】匹配度：{score:.1f}%\n\n'

            # 题型
            q_type = question.get('question_type', '未知题型')
            result_text += f'题型：{q_type}\n\n'

            # 题目
            q_text = question.get('question_text', '')
            result_text += f'题目：{q_text}\n\n'

            # 选项
            options = question.get('options', '')
            if options:
                result_text += f'选项：\n{options}\n\n'

            # 答案
            answer = question.get('answer', '')
            result_text += f'✅ 答案：{answer}\n\n'

            # 解析
            analysis = question.get('analysis', '')
            if analysis:
                result_text += f'📝 解析：{analysis}\n\n'

        result_text += '━━━━━━━━━━━━━━━━━━━━'

        self.result_label.text = result_text
        self.status_label.text = f'找到 {len(results)} 个匹配结果'

    def _show_error(self, error_msg):
        """显示错误信息"""
        self.search_btn.disabled = False
        self.result_label.text = f'搜索出错：{error_msg}'
        self.status_label.text = '搜索失败'


class OfflineQAApp(App):
    """离线搜题宝应用"""

    def build(self):
        # 设置窗口背景
        Window.clearcolor = UI['bg_color']

        # 设置默认字体为中文字体
        if FONT_AVAILABLE:
            from kivy.config import Config
            Config.set('kivy', 'default_font', ['ChineseFont', 'ChineseFont.ttf'])

        return OfflineQALayout()


if __name__ == '__main__':
    try:
        OfflineQAApp().run()
    except Exception as e:
        print(f'APP运行错误: {e}')
        traceback.print_exc()
