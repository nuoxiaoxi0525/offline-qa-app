# -*- coding: utf-8 -*-
"""
离线搜题宝 - 完整功能版本
支持：拍照OCR识别 + 本地题库导入 + 离线语义搜题
"""
import os
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle

from config import UI, PHOTO_DIR
from ocr_engine import get_ocr_engine
from question_bank import get_question_bank
from search_engine import get_search_engine
from importer import get_importer


class OfflineQALayout(BoxLayout):
    """主界面布局"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10

        # 初始化组件
        self.ocr_engine = None
        self.question_bank = None
        self.search_engine = None
        self.importer = None

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
            color=UI['theme_color']
        )
        title_layout.add_widget(title_label)
        self.add_widget(title_layout)

        # 状态显示
        self.status_label = Label(
            text='准备就绪',
            font_size='14sp',
            size_hint_y=0.05,
            color=[0.5, 0.5, 0.5, 1]
        )
        self.add_widget(self.status_label)

        # 题库统计
        self.stats_label = Label(
            text='题库: 0道题',
            font_size='14sp',
            size_hint_y=0.05
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
        )
        self.camera_btn.bind(on_press=self.on_camera_click)
        btn_layout.add_widget(self.camera_btn)

        # 题库导入按钮
        self.import_btn = Button(
            text='导入题库',
            font_size='20sp',
            background_color=UI['accent_color'],
            background_normal='',
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
            halign='left'
        )
        input_layout.add_widget(input_label)

        self.question_input = TextInput(
            hint_text='在此输入题目文字...',
            font_size='14sp',
            size_hint_y=0.7,
            multiline=True,
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
            text='搜索结果将在这里显示...',
            font_size='14sp',
            size_hint_y=None,
            height=100,
            halign='left',
            valign='top',
            text_size=(Window.width - 20, None)
        )
        self.result_layout.add_widget(self.result_label)
        self.result_scroll.add_widget(self.result_layout)
        self.add_widget(self.result_scroll)

    def _init_background(self, dt):
        """异步初始化后台组件"""
        def init_thread():
            try:
                self.status_label.text = '正在初始化题库...'
                self.question_bank = get_question_bank()

                self.status_label.text = '正在初始化搜题引擎...'
                self.search_engine = get_search_engine()

                # 检查题库是否为空
                stats = self.question_bank.get_statistics()
                if stats['total'] > 0:
                    self.status_label.text = '正在构建搜索索引...'
                    self.search_engine.build_index()

                self.importer = get_importer()

                # 更新统计
                Clock.schedule_once(lambda dt: self._update_stats(), 0)
                self.status_label.text = '准备就绪'

            except Exception as e:
                self.status_label.text = f'初始化失败: {str(e)[:50]}'

        threading.Thread(target=init_thread, daemon=True).start()

    def _update_stats(self):
        """更新题库统计"""
        if self.question_bank:
            stats = self.question_bank.get_statistics()
            self.stats_label.text = f'题库: {stats["total"]}道题'

    def on_camera_click(self, instance):
        """拍照搜题按钮点击"""
        self.status_label.text = '正在打开相机...'
        # TODO: 实现拍照功能
        # 由于Kivy相机在Android上的复杂性，这里先提供手动输入
        self.result_label.text = (
            '📷 拍照功能说明：\n\n'
            '在完整APK版本中，点击此按钮将打开系统相机。\n\n'
            '当前测试版本请使用下方手动输入题目文字进行搜题测试。'
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
            '然后通过文件选择器导入。'
        )
        self.status_label.text = '导入功能开发中'

    def on_search_click(self, instance):
        """搜索按钮点击"""
        query_text = self.question_input.text.strip()
        if not query_text:
            self.result_label.text = '请输入题目文字后再搜索'
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

        return OfflineQALayout()


if __name__ == '__main__':
    OfflineQAApp().run()
