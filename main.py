# -*- coding: utf-8 -*-
"""
离线拍照搜题APP - 主程序 (Buildozer APK版本)
Kivy UI + RapidOCR (PP-OCRv4) + plyer摄像头 + SQLite + TF-IDF
"""
import os
import sys
import time
import threading

# Kivy配置
from kivy.config import Config
Config.set('graphics', 'width', '1080')
Config.set('graphics', 'height', '1920')
Config.set('graphics', 'resizable', '0')
Config.set('kivy', 'window_icon', '')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.camera import Camera as KivyCamera

# 导入业务模块
from config import APP_NAME, APP_VERSION, UI, TEMP_DIR
from image_processor import get_processor
from ocr_engine import get_ocr_engine
from question_bank import get_question_bank
from search_engine import get_search_engine
from importer import get_importer
from camera_handler import get_camera_handler

# 设置背景色
Window.clearcolor = UI["bg_color"]


class ColoredBoxLayout(BoxLayout):
    """带背景色的BoxLayout"""
    def __init__(self, bg_color=None, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color or UI["bg_color"]
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class SearchResultItem(ColoredBoxLayout):
    """搜索结果项"""
    def __init__(self, question, similarity, **kwargs):
        super().__init__(orientation='vertical', padding=dp(10), spacing=dp(5),
                         bg_color=[1, 1, 1, 1], **kwargs)
        self.question = question

        sim_label = Label(
            text=f"匹配度: {similarity*100:.1f}%",
            size_hint_y=None, height=dp(25),
            font_size=sp(UI["font_size_small"]),
            color=UI["accent_color"],
            halign='right'
        )
        self.add_widget(sim_label)

        q_type = question.get('question_type', '单选题')
        type_label = Label(
            text=f"【{q_type}】",
            size_hint_y=None, height=dp(25),
            font_size=sp(UI["font_size_small"]),
            color=UI["theme_color"],
            halign='left'
        )
        self.add_widget(type_label)

        q_text = question.get('question_text', '')
        if len(q_text) > 200:
            q_text = q_text[:200] + "..."
        question_label = Label(
            text=q_text,
            size_hint_y=None,
            font_size=sp(UI["font_size_normal"]),
            color=UI["text_color"],
            halign='left',
            valign='top',
            text_size=(self.width - dp(20), None)
        )
        question_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1]))
        self.add_widget(question_label)

        answer_btn = Button(
            text="查看答案和解析",
            size_hint_y=None, height=dp(40),
            font_size=sp(UI["font_size_small"]),
            background_color=UI["theme_color"],
            on_press=self._show_answer
        )
        self.add_widget(answer_btn)

    def _show_answer(self, instance):
        q = self.question
        content = f"答案：{q.get('answer', '无')}\n\n"
        options = q.get('options', '')
        if options:
            content += f"选项：\n{options.replace('|', chr(10))}\n\n"
        analysis = q.get('analysis', '')
        if analysis:
            content += f"解析：\n{analysis}"

        popup = Popup(
            title='答案与解析',
            content=ScrollView(
                Label(
                    text=content,
                    font_size=sp(UI["font_size_normal"]),
                    color=UI["text_color"],
                    halign='left',
                    valign='top',
                    text_size=(Window.width - dp(40), None),
                    size_hint_y=None
                )
            ),
            size_hint=(0.9, 0.8),
            background_color=[1, 1, 1, 1]
        )
        popup.open()


class CameraScreen(ColoredBoxLayout):
    """摄像头拍照页面"""
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=0, spacing=0,
                         bg_color=[0, 0, 0, 1], **kwargs)
        self.camera_widget = None
        self._build_ui()

    def _build_ui(self):
        # 顶部状态栏
        self.status_bar = BoxLayout(size_hint_y=None, height=dp(60), padding=dp(10))
        self.status_label = Label(
            text="正在启动摄像头...",
            font_size=sp(UI["font_size_normal"]),
            color=[1, 1, 1, 1],
            halign='center'
        )
        self.status_bar.add_widget(self.status_label)
        self.add_widget(self.status_bar)

        # 相机预览区域
        self.camera_container = BoxLayout()
        self.add_widget(self.camera_container)

        # 取景框提示
        self.frame_hint = Label(
            text="将题目对准画面，保持文字清晰",
            size_hint_y=None, height=dp(40),
            font_size=sp(UI["font_size_small"]),
            color=[1, 1, 1, 0.8],
            halign='center'
        )
        self.add_widget(self.frame_hint)

        # 底部控制栏
        controls = BoxLayout(size_hint_y=None, height=dp(120), padding=dp(20), spacing=dp(20))

        # 相册按钮
        album_btn = Button(
            text="🖼️\n相册",
            font_size=sp(UI["font_size_small"]),
            background_color=[0.2, 0.2, 0.2, 1],
            size_hint_x=0.25,
            on_press=self._choose_photo
        )
        controls.add_widget(album_btn)

        # 拍照按钮
        capture_btn = Button(
            text="📷",
            font_size=sp(40),
            background_color=[1, 1, 1, 1],
            color=[0, 0, 0, 1],
            size_hint_x=0.5,
            on_press=self._capture
        )
        controls.add_widget(capture_btn)

        # 切换摄像头按钮
        switch_btn = Button(
            text="🔄\n切换",
            font_size=sp(UI["font_size_small"]),
            background_color=[0.2, 0.2, 0.2, 1],
            size_hint_x=0.25,
            on_press=self._switch_camera
        )
        controls.add_widget(switch_btn)

        self.add_widget(controls)

        # 返回按钮
        back_btn = Button(
            text="← 返回",
            size_hint_y=None, height=dp(50),
            background_color=[0.1, 0.1, 0.1, 1],
            on_press=self._go_back
        )
        self.add_widget(back_btn)

    def start_camera(self):
        """启动摄像头预览"""
        try:
            # 先清除旧的相机组件
            self.camera_container.clear_widgets()

            # 创建Kivy相机组件（使用后置摄像头index=0）
            self.camera_widget = KivyCamera(
                index=0,
                resolution=(1920, 1080),
                play=True,
                allow_stretch=True
            )
            self.camera_container.add_widget(self.camera_widget)
            self.status_label.text = "摄像头已就绪，点击拍照按钮"
        except Exception as e:
            self.status_label.text = f"摄像头启动失败: {e}"
            print(f"摄像头启动失败: {e}")

    def stop_camera(self):
        """停止摄像头"""
        if self.camera_widget:
            self.camera_widget.play = False
            self.camera_container.clear_widgets()
            self.camera_widget = None

    def _capture(self, instance):
        """拍照"""
        if not self.camera_widget:
            App.get_running_app().show_toast("摄像头未就绪")
            return

        try:
            # 捕获当前帧
            texture = self.camera_widget.texture
            if texture:
                import cv2
                import numpy as np

                buf = texture.pixels
                w, h = texture.size
                arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
                img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
                img = cv2.flip(img, 0)  # 垂直翻转

                # 保存照片
                filepath = os.path.join(TEMP_DIR, f"capture_{int(time.time())}.jpg")
                cv2.imwrite(filepath, img)

                # 停止摄像头
                self.stop_camera()

                # 处理图像
                App.get_running_app().process_image(filepath)

        except Exception as e:
            App.get_running_app().show_toast(f"拍照失败: {e}")
            print(f"拍照失败: {e}")

    def _choose_photo(self, instance):
        """从相册选择"""
        self.stop_camera()
        App.get_running_app().open_file_chooser()

    def _switch_camera(self, instance):
        """切换摄像头"""
        # Kivy的Camera组件切换index需要重新创建
        current_index = self.camera_widget.index if self.camera_widget else 0
        new_index = 1 if current_index == 0 else 0

        try:
            self.stop_camera()
            self.camera_widget = KivyCamera(
                index=new_index,
                resolution=(1920, 1080),
                play=True,
                allow_stretch=True
            )
            self.camera_container.add_widget(self.camera_widget)
            self.status_label.text = f"已切换到{'前置' if new_index == 1 else '后置'}摄像头"
        except Exception as e:
            self.status_label.text = f"切换失败: {e}"

    def _go_back(self, instance):
        """返回首页"""
        self.stop_camera()
        App.get_running_app().show_page('home')


class MainScreen(ColoredBoxLayout):
    """主屏幕"""

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(20), spacing=dp(15), **kwargs)

        # 标题
        title = Label(
            text=f"{APP_NAME}\nv{APP_VERSION}",
            size_hint_y=None, height=dp(80),
            font_size=sp(UI["font_size_title"]),
            color=UI["theme_color"],
            bold=True
        )
        self.add_widget(title)

        # 题库统计
        self.stats_label = Label(
            text="题库加载中...",
            size_hint_y=None, height=dp(40),
            font_size=sp(UI["font_size_normal"]),
            color=UI["text_color"]
        )
        self.add_widget(self.stats_label)

        # 功能按钮区域
        btn_layout = GridLayout(cols=2, spacing=dp(15), size_hint_y=None, height=dp(300))

        self.camera_btn = Button(
            text="📷\n拍照搜题",
            font_size=sp(UI["font_size_title"]),
            background_color=UI["theme_color"],
            on_press=self._open_camera
        )
        btn_layout.add_widget(self.camera_btn)

        self.text_btn = Button(
            text="🔍\n文字搜题",
            font_size=sp(UI["font_size_title"]),
            background_color=[0.2, 0.7, 0.4, 1],
            on_press=self._open_text_search
        )
        btn_layout.add_widget(self.text_btn)

        self.import_btn = Button(
            text="📥\n导入题库",
            font_size=sp(UI["font_size_title"]),
            background_color=[0.9, 0.5, 0.1, 1],
            on_press=self._open_import
        )
        btn_layout.add_widget(self.import_btn)

        self.manage_btn = Button(
            text="📊\n题库管理",
            font_size=sp(UI["font_size_title"]),
            background_color=[0.6, 0.4, 0.8, 1],
            on_press=self._open_manage
        )
        btn_layout.add_widget(self.manage_btn)

        self.add_widget(btn_layout)

        # 底部说明
        footer = Label(
            text="离线运行 · 无需联网 · 保护隐私\nRapidOCR (PP-OCRv4) 中文识别率97%+",
            size_hint_y=None, height=dp(50),
            font_size=sp(UI["font_size_small"]),
            color=[0.5, 0.5, 0.5, 1]
        )
        self.add_widget(footer)

        # 初始化题库统计
        Clock.schedule_once(self._update_stats, 0.5)

    def _update_stats(self, dt):
        try:
            bank = get_question_bank()
            stats = bank.get_statistics()
            total = stats['total']
            subjects = stats.get('by_subject', {})
            subject_text = '、'.join([f"{k}:{v}题" for k, v in subjects.items() if k])
            self.stats_label.text = f"题库共 {total} 道题{' | ' + subject_text if subject_text else ''}"
        except Exception as e:
            self.stats_label.text = f"题库加载失败: {e}"

    def _open_camera(self, instance):
        App.get_running_app().open_camera()

    def _open_text_search(self, instance):
        App.get_running_app().show_page('textsearch')

    def _open_import(self, instance):
        App.get_running_app().show_page('import')

    def _open_manage(self, instance):
        App.get_running_app().show_page('manage')


class OfflineQAApp(App):
    """离线拍照搜题APP"""

    def build(self):
        self.title = APP_NAME
        self.icon = ''

        # 主容器
        self.root = BoxLayout(orientation='vertical')

        # 页面容器
        self.page_container = BoxLayout()
        self.root.add_widget(self.page_container)

        # 创建各页面
        self.pages = {}
        self.pages['home'] = MainScreen()
        self.pages['camera'] = CameraScreen()
        self.pages['result'] = self._build_result_page()
        self.pages['textsearch'] = self._build_textsearch_page()
        self.pages['import'] = self._build_import_page()
        self.pages['manage'] = self._build_manage_page()

        # 默认显示首页
        self.show_page('home')

        return self.root

    def _build_result_page(self):
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))

        back_btn = Button(text="← 返回首页", size_hint_y=None, height=dp(45),
                          on_press=lambda x: self.show_page('home'))
        layout.add_widget(back_btn)

        self.ocr_result_label = Label(
            text="", size_hint_y=None, height=dp(100),
            font_size=sp(UI["font_size_small"]),
            color=[0.4, 0.4, 0.4, 1],
            halign='left', valign='top'
        )
        layout.add_widget(self.ocr_result_label)

        self.result_scroll = ScrollView()
        self.result_container = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
        self.result_container.bind(minimum_height=self.result_container.setter('height'))
        self.result_scroll.add_widget(self.result_container)
        layout.add_widget(self.result_scroll)

        return layout

    def _build_textsearch_page(self):
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

        back_btn = Button(text="← 返回首页", size_hint_y=None, height=dp(45),
                          on_press=lambda x: self.show_page('home'))
        layout.add_widget(back_btn)

        title = Label(text="文字搜题", font_size=sp(UI["font_size_title"]),
                      color=UI["theme_color"], size_hint_y=None, height=dp(50))
        layout.add_widget(title)

        self.text_search_input = TextInput(
            hint_text="输入题目内容...",
            size_hint_y=None, height=dp(150),
            font_size=sp(UI["font_size_normal"]),
            multiline=True
        )
        layout.add_widget(self.text_search_input)

        search_btn = Button(text="搜索", size_hint_y=None, height=dp(50),
                            background_color=UI["theme_color"],
                            on_press=self._do_text_search)
        layout.add_widget(search_btn)

        layout.add_widget(Label())  # 占位
        return layout

    def _build_import_page(self):
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

        back_btn = Button(text="← 返回首页", size_hint_y=None, height=dp(45),
                          on_press=lambda x: self.show_page('home'))
        layout.add_widget(back_btn)

        title = Label(text="导入题库", font_size=sp(UI["font_size_title"]),
                      color=UI["theme_color"], size_hint_y=None, height=dp(50))
        layout.add_widget(title)

        subject_label = Label(text="科目名称", font_size=sp(UI["font_size_normal"]),
                              halign='left', size_hint_y=None, height=dp(30))
        layout.add_widget(subject_label)

        self.import_subject_input = TextInput(
            hint_text="如：安全生产法律法规",
            size_hint_y=None, height=dp(45),
            font_size=sp(UI["font_size_normal"])
        )
        layout.add_widget(self.import_subject_input)

        file_label = Label(text="选择题库文件（Excel/CSV）", font_size=sp(UI["font_size_normal"]),
                           halign='left', size_hint_y=None, height=dp(30))
        layout.add_widget(file_label)

        self.import_file_label = Label(
            text="未选择文件", font_size=sp(UI["font_size_small"]),
            color=[0.5, 0.5, 0.5, 1], size_hint_y=None, height=dp(30)
        )
        layout.add_widget(self.import_file_label)

        choose_btn = Button(text="选择文件", size_hint_y=None, height=dp(45),
                            background_color=[0.2, 0.7, 0.4, 1],
                            on_press=self.open_file_chooser)
        layout.add_widget(choose_btn)

        import_btn = Button(text="开始导入", size_hint_y=None, height=dp(50),
                            background_color=[0.9, 0.5, 0.1, 1],
                            on_press=self._do_import)
        layout.add_widget(import_btn)

        format_label = Label(
            text="支持格式：题型、题目、选项（用|分隔）、答案、解析\n兼容刷刷题APP导入格式",
            font_size=sp(UI["font_size_small"]),
            color=[0.4, 0.4, 0.4, 1],
            size_hint_y=None, height=dp(60)
        )
        layout.add_widget(format_label)

        layout.add_widget(Label())  # 占位
        return layout

    def _build_manage_page(self):
        layout = ColoredBoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

        back_btn = Button(text="← 返回首页", size_hint_y=None, height=dp(45),
                          on_press=lambda x: self.show_page('home'))
        layout.add_widget(back_btn)

        title = Label(text="题库管理", font_size=sp(UI["font_size_title"]),
                      color=UI["theme_color"], size_hint_y=None, height=dp(50))
        layout.add_widget(title)

        self.manage_stats_label = Label(
            text="", font_size=sp(UI["font_size_normal"]),
            color=UI["text_color"], size_hint_y=None, height=dp(100),
            halign='left', valign='top'
        )
        layout.add_widget(self.manage_stats_label)

        rebuild_btn = Button(text="重建搜索索引", size_hint_y=None, height=dp(50),
                             background_color=[0.2, 0.7, 0.4, 1],
                             on_press=self._rebuild_index)
        layout.add_widget(rebuild_btn)

        clear_btn = Button(text="清空所有题库（谨慎操作）", size_hint_y=None, height=dp(50),
                           background_color=[0.9, 0.2, 0.2, 1],
                           on_press=self._confirm_clear)
        layout.add_widget(clear_btn)

        ocr_info = Label(
            text="\nOCR引擎：RapidOCR (PP-OCRv4)\n中文识别率：97%+\n模型：内置，完全离线",
            font_size=sp(UI["font_size_small"]),
            color=[0.4, 0.4, 0.4, 1],
            size_hint_y=None, height=dp(80)
        )
        layout.add_widget(ocr_info)

        layout.add_widget(Label())  # 占位
        return layout

    def show_page(self, page_name):
        """切换页面"""
        self.page_container.clear_widgets()
        if page_name in self.pages:
            self.page_container.add_widget(self.pages[page_name])

        # 如果是管理页面，更新统计
        if page_name == 'manage':
            self._update_manage_stats()

    def open_camera(self):
        """打开摄像头页面"""
        self.show_page('camera')
        # 延迟启动摄像头（等待页面渲染）
        Clock.schedule_once(lambda dt: self.pages['camera'].start_camera(), 0.5)

    def open_file_chooser(self):
        """打开文件选择器"""
        content = BoxLayout(orientation='vertical', spacing=dp(10))
        filechooser = FileChooserListView(
            path='/sdcard/' if os.path.exists('/sdcard/') else os.path.expanduser('~'),
            filters=['*.xlsx', '*.xls', '*.csv'],
            size_hint_y=0.8
        )
        content.add_widget(filechooser)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        select_btn = Button(text="选择", background_color=UI["theme_color"],
                            on_press=lambda x: self._on_file_selected(filechooser.selection))
        cancel_btn = Button(text="取消", on_press=lambda x: self._file_popup.dismiss())
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        self._file_popup = Popup(title='选择题库文件', content=content,
                                 size_hint=(0.9, 0.9), background_color=[1, 1, 1, 1])
        self._file_popup.open()

    def _on_file_selected(self, selection):
        if selection:
            self.selected_file = selection[0]
            self.import_file_label.text = os.path.basename(selection[0])
            self._file_popup.dismiss()
            self.show_page('import')

    def process_image(self, image_path):
        """处理图像（拍照或选择文件后）"""
        self.show_loading('图像预处理中...')

        def worker():
            try:
                # 1. 图像预处理
                processor = get_processor()
                processed_img = processor.process(image_path, save_debug=False)

                # 2. OCR识别
                Clock.schedule_once(lambda dt: self.update_loading('OCR文字识别中...'))
                ocr = get_ocr_engine()
                raw_text = ocr.recognize(processed_img)
                clean_text = ocr.post_process(raw_text)
                question_text = ocr.extract_question_text(clean_text)

                # 3. 题库匹配
                Clock.schedule_once(lambda dt: self.update_loading('题库匹配中...'))
                search_engine = get_search_engine()
                if not search_engine._index_built:
                    search_engine.build_index()
                results = search_engine.search(question_text, 5)

                # 4. 显示结果
                Clock.schedule_once(lambda dt: self._show_results(clean_text, question_text, results))

            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _show_results(self, ocr_text, question_text, results):
        self.hide_loading()
        self.show_page('result')

        self.ocr_result_label.text = f"识别文本：\n{ocr_text[:300]}{'...' if len(ocr_text) > 300 else ''}"

        self.result_container.clear_widgets()
        if not results:
            empty = Label(text="未找到匹配的题目\n请检查图片清晰度，或确认已导入相关题库",
                          font_size=sp(UI["font_size_normal"]), color=[0.5, 0.5, 0.5, 1],
                          size_hint_y=None, height=dp(100))
            self.result_container.add_widget(empty)
            return

        for question, similarity in results:
            item = SearchResultItem(question, similarity, size_hint_y=None)
            item.height = dp(180)
            self.result_container.add_widget(item)

    def _show_error(self, error):
        self.hide_loading()
        self.show_toast(f"处理失败: {error}")

    def _do_text_search(self, instance):
        query = self.text_search_input.text.strip()
        if not query:
            self.show_toast("请输入题目内容")
            return

        self.show_loading('搜索中...')

        def worker():
            try:
                search_engine = get_search_engine()
                if not search_engine._index_built:
                    search_engine.build_index()
                results = search_engine.search(query, 5)
                Clock.schedule_once(lambda dt: self._show_results(query, query, results))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _do_import(self, instance):
        if not hasattr(self, 'selected_file') or not self.selected_file:
            self.show_toast("请选择题库文件")
            return

        subject = self.import_subject_input.text.strip()
        self.show_loading('导入中...')

        def worker():
            try:
                importer = get_importer()
                success, fail, error = importer.import_file(self.selected_file, subject=subject)
                Clock.schedule_once(lambda dt: self._import_finished(success, fail, error))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _import_finished(self, success, fail, error):
        self.hide_loading()
        if error:
            self.show_toast(f"导入失败: {error}")
        else:
            self.show_toast(f"导入完成！成功{success}道，失败{fail}道")
            self.pages['home']._update_stats(0)
            self.show_page('home')

    def _update_manage_stats(self):
        try:
            bank = get_question_bank()
            stats = bank.get_statistics()
            text = f"题库总数：{stats['total']}道\n\n"
            text += "按题型：\n"
            for k, v in stats.get('by_type', {}).items():
                text += f"  {k}: {v}道\n"
            text += "\n按科目：\n"
            for k, v in stats.get('by_subject', {}).items():
                if k:
                    text += f"  {k}: {v}道\n"
            self.manage_stats_label.text = text
        except Exception as e:
            self.manage_stats_label.text = f"统计失败: {e}"

    def _rebuild_index(self, instance):
        self.show_loading('重建索引中...')

        def worker():
            try:
                search_engine = get_search_engine()
                search_engine.rebuild_index()
                Clock.schedule_once(lambda dt: (self.hide_loading(), self.show_toast("索引重建完成")))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _confirm_clear(self, instance):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
        content.add_widget(Label(text="确定要清空所有题库吗？\n此操作不可恢复！",
                                 font_size=sp(UI["font_size_normal"]), color=[0.9, 0.2, 0.2, 1]))
        btn_layout = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(50))
        yes_btn = Button(text="确定清空", background_color=[0.9, 0.2, 0.2, 1],
                         on_press=lambda x: self._do_clear())
        no_btn = Button(text="取消", on_press=lambda x: self._confirm_popup.dismiss())
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)

        self._confirm_popup = Popup(title='确认操作', content=content,
                                    size_hint=(0.7, 0.4), background_color=[1, 1, 1, 1])
        self._confirm_popup.open()

    def _do_clear(self):
        self._confirm_popup.dismiss()
        self.show_loading('清空中...')

        def worker():
            try:
                bank = get_question_bank()
                subjects = bank.get_subjects()
                for subj in subjects:
                    bank.clear_subject(subj['name'])
                bank.clear_subject('')
                search_engine = get_search_engine()
                search_engine.rebuild_index()
                Clock.schedule_once(lambda dt: (
                    self.hide_loading(),
                    self.show_toast("题库已清空"),
                    self.pages['home']._update_stats(0),
                    self._update_manage_stats()
                ))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def show_loading(self, text='处理中...'):
        self._loading_popup = Popup(
            title='',
            content=Label(text=text, font_size=sp(UI["font_size_normal"])),
            size_hint=(0.6, 0.3),
            auto_dismiss=False,
            background_color=[1, 1, 1, 1]
        )
        self._loading_popup.open()

    def update_loading(self, text):
        if hasattr(self, '_loading_popup') and self._loading_popup:
            self._loading_popup.content.text = text

    def hide_loading(self):
        if hasattr(self, '_loading_popup') and self._loading_popup:
            self._loading_popup.dismiss()
            self._loading_popup = None

    def show_toast(self, message):
        popup = Popup(
            title='提示',
            content=Label(text=message, font_size=sp(UI["font_size_normal"])),
            size_hint=(0.7, 0.3),
            background_color=[1, 1, 1, 1]
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)

    def on_start(self):
        """应用启动时初始化"""
        try:
            # 请求安卓权限
            self._request_android_permissions()
            # 预加载引擎
            get_processor()
            get_question_bank()
            search_engine = get_search_engine()
            search_engine.build_index()
            print("应用初始化完成")
        except Exception as e:
            print(f"初始化失败: {e}")

    def _request_android_permissions(self):
        """请求安卓权限"""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
            ])
        except ImportError:
            pass


if __name__ == '__main__':
    OfflineQAApp().run()
