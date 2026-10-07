# -*- coding: utf-8 -*-
"""
离线搜题宝 - 完整功能版本
支持：拍照→裁剪→识别→搜题完整流程 + 本地题库导入 + 离线语义搜题
"""
import os
import sys
import traceback
import threading
import time

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.graphics import Color, Line, Rectangle

from config import UI, BASE_DIR, TEMP_DIR


def excepthook(exc_type, exc_value, exc_traceback):
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"未捕获异常: {error_msg}")
    try:
        log_path = os.path.join(BASE_DIR, "error.log")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
    except:
        pass

sys.excepthook = excepthook


def register_chinese_font():
    try:
        possible_paths = []
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cwd = os.getcwd()
        possible_paths.append(os.path.join(script_dir, 'fonts', 'NotoSansSC-Regular.ttf'))
        possible_paths.append(os.path.join(cwd, 'fonts', 'NotoSansSC-Regular.ttf'))
        android_fonts = [
            '/system/fonts/DroidSansFallback.ttf',
            '/system/fonts/NotoSansCJK-Regular.ttc',
            '/system/fonts/NotoSansSC-Regular.ttf',
            '/system/fonts/simhei.ttf',
        ]
        possible_paths.extend(android_fonts)
        for font_path in possible_paths:
            if os.path.exists(font_path):
                try:
                    LabelBase.register(name='ChineseFont', fn_regular=font_path)
                    print(f"成功注册字体: {font_path}")
                    return True
                except Exception as e:
                    print(f"注册失败: {e}")
                    continue
        print("未找到中文字体")
        return False
    except Exception as e:
        print(f"字体注册失败: {e}")
        return False


FONT_AVAILABLE = register_chinese_font()


class FileChooserPopup(Popup):
    def __init__(self, on_select, **kwargs):
        super().__init__(**kwargs)
        self.title = '选择文件'
        self.size_hint = (0.9, 0.9)
        self.on_select = on_select
        layout = BoxLayout(orientation='vertical', padding=10, spacing=5)
        self.path_label = Label(text='/sdcard/', size_hint_y=0.05, font_name='ChineseFont', color=[0, 0, 0, 1])
        layout.add_widget(self.path_label)
        self.file_list = ScrollView(size_hint_y=0.8)
        self.file_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self.file_layout.bind(minimum_height=self.file_layout.setter('height'))
        self.file_list.add_widget(self.file_layout)
        layout.add_widget(self.file_list)
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=10)
        cancel_btn = Button(text='取消', font_name='ChineseFont', on_press=lambda x: self.dismiss())
        btn_layout.add_widget(cancel_btn)
        layout.add_widget(btn_layout)
        self.content = layout
        self.current_path = '/sdcard/'
        self._load_files()

    def _load_files(self):
        self.file_layout.clear_widgets()
        try:
            self.path_label.text = self.current_path
            files = os.listdir(self.current_path)
            files.sort()
            if self.current_path != '/':
                up_btn = Button(text='📁 .. (上级目录)', size_hint_y=None, height=40, font_name='ChineseFont', halign='left', on_press=lambda x: self._go_up())
                self.file_layout.add_widget(up_btn)
            for f in files:
                full_path = os.path.join(self.current_path, f)
                if os.path.isdir(full_path):
                    btn = Button(text=f'📁 {f}', size_hint_y=None, height=40, font_name='ChineseFont', halign='left', on_press=lambda x, p=full_path: self._enter_dir(p))
                    self.file_layout.add_widget(btn)
                elif f.endswith(('.csv', '.xlsx', '.xls', '.jpg', '.jpeg', '.png')):
                    btn = Button(text=f'📄 {f}', size_hint_y=None, height=40, font_name='ChineseFont', halign='left', background_color=[0.8, 0.9, 1, 1], on_press=lambda x, p=full_path: self._select_file(p))
                    self.file_layout.add_widget(btn)
        except Exception as e:
            self.file_layout.add_widget(Label(text=f'读取失败: {e}', font_name='ChineseFont'))

    def _go_up(self):
        self.current_path = os.path.dirname(self.current_path.rstrip('/'))
        if not self.current_path:
            self.current_path = '/'
        self._load_files()

    def _enter_dir(self, path):
        self.current_path = path
        self._load_files()

    def _select_file(self, path):
        self.dismiss()
        if self.on_select:
            self.on_select(path)


class CropWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crop_rect = [0.1, 0.15, 0.8, 0.7]
        self.dragging = None
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, *args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 0.8)
            x = self.x + self.crop_rect[0] * self.width
            y = self.y + self.crop_rect[1] * self.height
            w = self.crop_rect[2] * self.width
            h = self.crop_rect[3] * self.height
            Line(rectangle=(x, y, w, h), width=2)
            Color(0.2, 0.6, 1, 1)
            corner_size = 20
            for cx, cy in [(x, y), (x+w, y), (x, y+h), (x+w, y+h)]:
                Rectangle(pos=(cx-corner_size/2, cy-corner_size/2), size=(corner_size, corner_size))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            x = self.x + self.crop_rect[0] * self.width
            y = self.y + self.crop_rect[1] * self.height
            w = self.crop_rect[2] * self.width
            h = self.crop_rect[3] * self.height
            corner_size = 40
            corners = [('tl', x, y+h), ('tr', x+w, y+h), ('bl', x, y), ('br', x+w, y)]
            for name, cx, cy in corners:
                if abs(touch.x - cx) < corner_size and abs(touch.y - cy) < corner_size:
                    self.dragging = name
                    return True
            if x <= touch.x <= x+w and y <= touch.y <= y+h:
                self.dragging = 'move'
                self.drag_start = (touch.x, touch.y)
                self.rect_start = self.crop_rect[:]
                return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.dragging:
            rel_x = (touch.x - self.x) / self.width
            rel_y = (touch.y - self.y) / self.height
            if self.dragging == 'move':
                dx = (touch.x - self.drag_start[0]) / self.width
                dy = (touch.y - self.drag_start[1]) / self.height
                self.crop_rect[0] = max(0, min(1 - self.crop_rect[2], self.rect_start[0] + dx))
                self.crop_rect[1] = max(0, min(1 - self.crop_rect[3], self.rect_start[1] + dy))
            elif self.dragging == 'br':
                self.crop_rect[2] = max(0.1, min(1 - self.crop_rect[0], rel_x - self.crop_rect[0]))
                self.crop_rect[3] = max(0.1, min(1 - self.crop_rect[1], rel_y - self.crop_rect[1]))
            elif self.dragging == 'tr':
                self.crop_rect[2] = max(0.1, min(1 - self.crop_rect[0], rel_x - self.crop_rect[0]))
                new_h = max(0.1, self.crop_rect[1] + self.crop_rect[3] - rel_y)
                self.crop_rect[1] = min(rel_y, self.crop_rect[1] + self.crop_rect[3] - 0.1)
                self.crop_rect[3] = new_h
            elif self.dragging == 'bl':
                new_w = max(0.1, self.crop_rect[0] + self.crop_rect[2] - rel_x)
                self.crop_rect[0] = min(rel_x, self.crop_rect[0] + self.crop_rect[2] - 0.1)
                self.crop_rect[2] = new_w
                self.crop_rect[3] = max(0.1, min(1 - self.crop_rect[1], rel_y - self.crop_rect[1]))
            elif self.dragging == 'tl':
                new_w = max(0.1, self.crop_rect[0] + self.crop_rect[2] - rel_x)
                new_h = max(0.1, self.crop_rect[1] + self.crop_rect[3] - rel_y)
                self.crop_rect[0] = min(rel_x, self.crop_rect[0] + self.crop_rect[2] - 0.1)
                self.crop_rect[1] = min(rel_y, self.crop_rect[1] + self.crop_rect[3] - 0.1)
                self.crop_rect[2] = new_w
                self.crop_rect[3] = new_h
            self._update_rect()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self.dragging = None
        return super().on_touch_up(touch)

    def get_crop_coords(self):
        x = self.crop_rect[0] * self.width
        y = self.crop_rect[1] * self.height
        w = self.crop_rect[2] * self.width
        h = self.crop_rect[3] * self.height
        return int(x), int(y), int(w), int(h)


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'main'
        self.question_bank = None
        self.search_engine = None
        self.importer = None
        self._initialized = False
        self._build_ui()
        Clock.schedule_once(self._init_background, 0.5)

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        title = Label(text='离线搜题宝', font_size='28sp', size_hint_y=0.08, font_name='ChineseFont', color=[0.1, 0.3, 0.6, 1])
        layout.add_widget(title)
        self.status_label = Label(text='正在初始化...', font_size='14sp', size_hint_y=0.04, font_name='ChineseFont', color=[0.4, 0.4, 0.4, 1])
        layout.add_widget(self.status_label)
        self.stats_label = Label(text='题库: 0道题', font_size='16sp', size_hint_y=0.04, font_name='ChineseFont', color=[0.2, 0.5, 0.2, 1])
        layout.add_widget(self.stats_label)
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=0.15, spacing=15)
        self.camera_btn = Button(text='拍照搜题', font_size='18sp', background_color=[0.2, 0.5, 0.9, 1], background_normal='', font_name='ChineseFont')
        self.camera_btn.bind(on_press=self.on_camera_click)
        btn_layout.add_widget(self.camera_btn)
        self.import_btn = Button(text='导入题库', font_size='18sp', background_color=[0.9, 0.6, 0.2, 1], background_normal='', font_name='ChineseFont')
        self.import_btn.bind(on_press=self.on_import_click)
        btn_layout.add_widget(self.import_btn)
        layout.add_widget(btn_layout)
        layout.add_widget(Label(text='或手动输入题目文字：', size_hint_y=0.04, font_name='ChineseFont', color=[0.3, 0.3, 0.3, 1]))
        self.question_input = TextInput(hint_text='在此输入题目文字...', font_size='14sp', size_hint_y=0.1, font_name='ChineseFont', multiline=False)
        layout.add_widget(self.question_input)
        self.search_btn = Button(text='搜索', font_size='18sp', size_hint_y=0.07, background_color=[0.2, 0.6, 0.8, 1], background_normal='', font_name='ChineseFont')
        self.search_btn.bind(on_press=self.on_search_click)
        layout.add_widget(self.search_btn)
        self.result_scroll = ScrollView(size_hint_y=0.4)
        self.result_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10, padding=10)
        self.result_layout.bind(minimum_height=self.result_layout.setter('height'))
        self.result_label = Label(text='搜索结果将在这里显示...\n\n欢迎使用离线搜题宝！', font_size='14sp', size_hint_y=None, height=100, halign='left', valign='top', text_size=(Window.width - 40, None), color=[0, 0, 0, 1], font_name='ChineseFont')
        self.result_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1] + 20))
        self.result_layout.add_widget(self.result_label)
        self.result_scroll.add_widget(self.result_layout)
        layout.add_widget(self.result_scroll)
        self.add_widget(layout)

    def _init_background(self, dt):
        def init_thread():
            try:
                self._set_status('正在初始化题库...')
                try:
                    from question_bank import get_question_bank
                    self.question_bank = get_question_bank()
                except Exception as e:
                    print(f'题库初始化失败: {e}')
                try:
                    from search_engine import get_search_engine
                    self.search_engine = get_search_engine()
                except Exception as e:
                    print(f'搜题引擎初始化失败: {e}')
                if self.question_bank and self.importer is None:
                    try:
                        from importer import get_importer
                        self.importer = get_importer()
                    except Exception as e:
                        print(f'导入器初始化失败: {e}')
                try:
                    if self.question_bank and self.importer:
                        stats = self.question_bank.get_statistics()
                        if stats['total'] == 0:
                            self._set_status('正在导入内置题库...')
                            script_dir = os.path.dirname(os.path.abspath(__file__))
                            cwd = os.getcwd()
                            search_dirs = []
                            if os.path.exists(os.path.join(cwd, 'assets')):
                                search_dirs = [os.path.join(cwd, 'assets')]
                            elif os.path.exists(os.path.join(script_dir, 'assets')):
                                search_dirs = [os.path.join(script_dir, 'assets')]
                            for search_dir in search_dirs:
                                if os.path.exists(search_dir):
                                    files = os.listdir(search_dir)
                                    csv_files = [f for f in files if f.endswith('.csv')]
                                    for filename in csv_files:
                                        file_path = os.path.join(search_dir, filename)
                                        try:
                                            self.importer.import_file(file_path)
                                        except Exception as e:
                                            print(f'导入{filename}失败: {e}')
                except Exception as e:
                    print(f'内置题库导入失败: {e}')
                    traceback.print_exc()
                if self.question_bank and self.search_engine:
                    try:
                        stats = self.question_bank.get_statistics()
                        if stats['total'] > 0:
                            self._set_status('正在构建搜索索引...')
                            self.search_engine.build_index()
                    except Exception as e:
                        print(f'索引构建失败: {e}')
                Clock.schedule_once(lambda dt: self._update_stats(), 0)
                self._set_status('准备就绪')
                self._initialized = True
            except Exception as e:
                print(f'初始化线程异常: {e}')
                traceback.print_exc()
        threading.Thread(target=init_thread, daemon=True).start()

    def _set_status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', text), 0)

    def _update_stats(self):
        if self.question_bank:
            try:
                stats = self.question_bank.get_statistics()
                self.stats_label.text = f'题库: {stats["total"]}道题'
            except Exception as e:
                print(f'获取统计失败: {e}')

    def on_camera_click(self, instance):
        self.manager.current = 'camera'

    def on_import_click(self, instance):
        if not self.importer:
            self.result_label.text = '导入器未初始化，请稍后再试'
            return
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        except:
            pass
        popup = FileChooserPopup(on_select=self._on_file_selected)
        popup.open()

    def _on_file_selected(self, file_path):
        if isinstance(file_path, bytes):
            file_path = file_path.decode('utf-8')
        if not os.path.exists(file_path):
            self._show_error(f'文件不存在: {file_path}')
            return
        self.status_label.text = '正在导入题库...'
        self.import_btn.disabled = True

        def import_thread():
            try:
                success, fail, error = self.importer.import_file(file_path)
                if error:
                    Clock.schedule_once(lambda dt: self._show_error(f'导入失败: {error}'), 0)
                else:
                    Clock.schedule_once(lambda dt: self._update_stats(), 0)
                    msg = f'导入完成！成功 {success} 道题，失败 {fail} 道题'
                    self._set_status(msg)
                    self.result_label.text = f'✅ {msg}\n\n题库已更新，可以开始搜题了！'
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)), 0)
            finally:
                self.import_btn.disabled = False
        threading.Thread(target=import_thread, daemon=True).start()

    def on_search_click(self, instance):
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
                results = self.search_engine.search(query_text, top_k=5)
                Clock.schedule_once(lambda dt: self._show_results(query_text, results), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)), 0)
        threading.Thread(target=search_thread, daemon=True).start()

    def _show_results(self, query_text, results):
        self.search_btn.disabled = False
        if not results:
            self.result_label.text = (
                f'未找到匹配的题目\n\n'
                f'搜索关键词：{query_text[:50]}...\n\n'
                f'请尝试：\n'
                f'1. 输入更多题目关键词\n'
                f'2. 检查是否已导入题库\n'
                f'3. 重新拍照识别'
            )
            self.status_label.text = '未找到匹配题目'
            return
        result_text = f'🔍 搜索到 {len(results)} 个结果：\n\n'
        for i, (question, similarity) in enumerate(results, 1):
            score = similarity * 100
            result_text += f'━━━━━━━━━━━━━━━━━━━━\n'
            result_text += f'【结果 {i}】匹配度：{score:.1f}%\n\n'
            q_type = question.get('question_type', '未知题型')
            result_text += f'题型：{q_type}\n\n'
            q_text = question.get('question_text', '')
            result_text += f'题目：{q_text}\n\n'
            options = question.get('options', '')
            if options:
                result_text += f'选项：\n{options}\n\n'
            answer = question.get('answer', '')
            result_text += f'✅ 答案：{answer}\n\n'
            analysis = question.get('analysis', '')
            if analysis:
                result_text += f'📝 解析：{analysis}\n\n'
        result_text += '━━━━━━━━━━━━━━━━━━━━'
        self.result_label.text = result_text
        self.status_label.text = f'找到 {len(results)} 个匹配结果'

    def _show_error(self, error_msg):
        self.search_btn.disabled = False
        self.camera_btn.disabled = False
        self.result_label.text = f'错误：{error_msg}'
        self.status_label.text = '操作失败'


class CameraScreen(Screen):
    """拍照界面 - 使用WebView + HTML5相机API"""

    def __init__(self, **kwargs):
        super(CameraScreen, self).__init__(**kwargs)
        self._webview = None
        self._photo_data = None
        self._checking = False
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=0, spacing=0)
        with layout.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda *a: setattr(self.bg_rect, 'pos', layout.pos),
                    size=lambda *a: setattr(self.bg_rect, 'size', layout.size))

        # 顶部标题栏
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=0.08, padding=10)
        title = Label(text='拍照搜题', font_size='18sp', font_name='ChineseFont', color=[1, 1, 1, 1])
        top_bar.add_widget(title)
        layout.add_widget(top_bar)

        # 状态提示
        self.status_label = Label(text='正在启动相机...', font_size='16sp',
                                  font_name='ChineseFont', color=[1, 1, 1, 1],
                                  size_hint_y=0.05)
        layout.add_widget(self.status_label)

        # WebView容器（占位）
        self.webview_placeholder = BoxLayout(size_hint_y=0.77)
        layout.add_widget(self.webview_placeholder)

        # 底部按钮区域
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1, padding=20, spacing=20)

        close_btn = Button(text='返回', font_size='16sp', background_color=[0.5, 0.5, 0.5, 1],
                          background_normal='', font_name='ChineseFont')
        close_btn.bind(on_press=self._on_close)
        btn_layout.add_widget(close_btn)

        album_btn = Button(text='相册', font_size='16sp', background_color=[0.6, 0.5, 0.3, 1],
                          background_normal='', font_name='ChineseFont')
        album_btn.bind(on_press=self._on_album)
        btn_layout.add_widget(album_btn)

        layout.add_widget(btn_layout)
        self.add_widget(layout)

    def on_enter(self):
        """进入页面时创建WebView"""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.CAMERA])
        except Exception as e:
            print(f'权限请求跳过: {e}')
        Clock.schedule_once(self._create_webview, 0.5)

    def _create_webview(self, dt=None):
        """创建Android WebView并加载相机页面 - 所有操作都在UI线程"""
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread
            print('步骤1: 导入jnius成功')

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            print(f'步骤2: 获取Activity成功: {activity}')

            # 所有WebView操作都在UI线程中执行
            @run_on_ui_thread
            def create_webview_on_ui_thread():
                try:
                    print('步骤3: 开始在UI线程创建WebView')
                    WebView = autoclass('android.webkit.WebView')
                    self._webview = WebView(activity)
                    print('步骤4: WebView创建成功')

                    # 配置WebView设置
                    settings = self._webview.getSettings()
                    settings.setJavaScriptEnabled(True)
                    settings.setDomStorageEnabled(True)
                    settings.setAllowFileAccess(True)
                    settings.setAllowContentAccess(True)
                    settings.setMediaPlaybackRequiresUserGesture(False)
                    print('步骤5: WebView设置配置成功')

                    # 设置WebViewClient
                    WebViewClient = autoclass('android.webkit.WebViewClient')
                    self._webview.setWebViewClient(WebViewClient())
                    print('步骤6: WebViewClient设置成功')

                    # 添加WebView到Activity
                    LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
                    params = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
                    activity.addContentView(self._webview, params)
                    print('步骤7: WebView已添加到Activity')

                    # 加载相机HTML页面
                    html_content = self._get_camera_html()
                    self._webview.loadDataWithBaseURL(None, html_content, 'text/html', 'UTF-8', None)
                    print('步骤8: WebView加载相机页面成功')

                    # 开始检查是否有拍照数据
                    self._checking = True
                    Clock.schedule_interval(self._check_photo_data, 1)
                    print('步骤9: 开始检查拍照数据')

                    self.status_label.text = '相机已启动，请对准题目后点击拍照'

                except Exception as inner_e:
                    print(f'UI线程中创建WebView失败: {inner_e}')
                    traceback.print_exc()
                    self.status_label.text = 'UI线程失败: ' + str(inner_e)[:60]

            create_webview_on_ui_thread()
            print('步骤10: 已调用UI线程创建WebView')

        except Exception as e:
            print(f'创建WebView失败: {e}')
            traceback.print_exc()
            self.status_label.text = 'WebView失败: ' + str(e)[:60]

    def _get_camera_html(self):
        """返回HTML相机页面"""
        return """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#000; color:#fff; font-family:sans-serif; height:100vh; display:flex; flex-direction:column; overflow:hidden; }
#container { flex:1; position:relative; background:#000; }
#video { width:100%; height:100%; object-fit:contain; }
#canvas { display:none; }
#frame { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:85%; height:65%; border:3px solid #00d4ff; border-radius:10px; pointer-events:none; }
#controls { padding:15px; background:#16213e; display:flex; justify-content:center; }
#captureBtn { width:70px; height:70px; border-radius:50%; background:#00d4ff; border:4px solid #fff; font-size:14px; color:#000; cursor:pointer; }
#status { position:absolute; top:10px; left:50%; transform:translateX(-50%); background:rgba(0,0,0,0.7); padding:8px 16px; border-radius:20px; font-size:14px; }
#error { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); text-align:center; padding:20px; display:none; }
</style>
</head>
<body>
<div id="container">
<video id="video" autoplay playsinline></video>
<canvas id="canvas"></canvas>
<div id="frame"></div>
<div id="status">正在启动相机...</div>
<div id="error"></div>
</div>
<div id="controls">
<button id="captureBtn">拍照</button>
</div>
<script>
let video = document.getElementById('video');
let canvas = document.getElementById('canvas');
let status = document.getElementById('status');
let errorDiv = document.getElementById('error');
let stream = null;

async function startCamera() {
    try {
        status.style.display = 'block';
        status.textContent = '正在启动相机...';
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
            audio: false
        });
        video.srcObject = stream;
        await video.play();
        status.style.display = 'none';
        console.log('相机启动成功');
    } catch (err) {
        console.error('相机启动失败:', err);
        status.style.display = 'none';
        errorDiv.style.display = 'block';
        errorDiv.innerHTML = '相机启动失败: ' + err.message + '<br><br>请确保已授予相机权限';
    }
}

function capture() {
    if (!stream) { alert('相机未启动'); return; }
    try {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        let ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        let dataUrl = canvas.toDataURL('image/jpeg', 0.9);
        // 保存到localStorage供Python读取
        localStorage.setItem('photo_data', dataUrl);
        localStorage.setItem('photo_time', Date.now().toString());
        status.style.display = 'block';
        status.textContent = '拍照成功，正在处理...';
        console.log('拍照成功，数据长度:', dataUrl.length);
    } catch (err) {
        console.error('拍照失败:', err);
        alert('拍照失败: ' + err.message);
    }
}

document.getElementById('captureBtn').addEventListener('click', capture);
startCamera();
</script>
</body>
</html>"""

    def _check_photo_data(self, dt):
        """检查WebView中是否有拍照数据"""
        if not self._webview or not self._checking:
            return

        try:
            from jnius import autoclass
            ValueCallback = autoclass('android.webkit.ValueCallback')

            # 创建回调
            class PhotoCallback:
                def __init__(self, screen):
                    self.screen = screen
                def onReceiveValue(self, value):
                    if value and value != 'null':
                        # 去掉引号
                        data = value.strip('"')
                        if data and len(data) > 100:
                            print(f'获取到拍照数据，长度: {len(data)}')
                            self.screen._handle_photo_data(data)

            callback = PhotoCallback(self)
            self._webview.evaluateJavascript("localStorage.getItem('photo_data')", callback)

        except Exception as e:
            print(f'检查拍照数据失败: {e}')

    def _handle_photo_data(self, data_url):
        """处理拍照数据"""
        try:
            self._checking = False

            # 解码base64数据
            import base64
            if data_url.startswith('data:image/jpeg;base64,'):
                base64_data = data_url[len('data:image/jpeg;base64,'):]
            else:
                base64_data = data_url

            photo_bytes = base64.b64decode(base64_data)
            print(f'解码照片数据成功，大小: {len(photo_bytes)} 字节')

            # 保存到APP私有目录
            photo_dir = os.path.join(BASE_DIR, 'photos')
            if not os.path.exists(photo_dir):
                os.makedirs(photo_dir)
            self.photo_path = os.path.join(photo_dir, f'photo_{int(time.time())}.jpg')

            with open(self.photo_path, 'wb') as f:
                f.write(photo_bytes)

            print(f'照片已保存: {self.photo_path}')

            # 清除WebView中的数据
            try:
                self._webview.evaluateJavascript("localStorage.removeItem('photo_data')", None)
            except:
                pass

            # 进入裁剪界面
            crop_screen = self.manager.get_screen('crop')
            crop_screen.set_image(self.photo_path)
            self.manager.current = 'crop'

        except Exception as e:
            print(f'处理拍照数据失败: {e}')
            traceback.print_exc()
            self.status_label.text = '处理照片失败: ' + str(e)[:50]

    def _on_capture(self, instance=None):
        """回退方案：使用系统相机"""
        try:
            from jnius import autoclass
            from android.permissions import request_permissions, Permission
            try:
                request_permissions([Permission.CAMERA, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            except:
                pass

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            MediaStore = autoclass('android.provider.MediaStore')
            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            PythonActivity.mActivity.startActivityForResult(intent, 1001)
            self._capture_time = time.time()
            self._check_count = 0
            Clock.schedule_once(self._check_captured_photo, 5)
        except Exception as e:
            print(f'启动系统相机失败: {e}')
            self._show_error(f'启动相机失败: {str(e)[:60]}')

    def _check_captured_photo(self, dt):
        """系统相机回退方案：检查照片"""
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Uri = autoclass('android.net.Uri')
            ContentUris = autoclass('android.content.ContentUris')
            base_uri = Uri.parse("content://media/external/images/media")
            content_resolver = PythonActivity.mActivity.getContentResolver()
            cursor = content_resolver.query(base_uri, ["_id"], None, None, "date_added DESC LIMIT 1")
            if cursor and cursor.moveToFirst():
                p_id = cursor.getLong(0)
                cursor.close()
                photo_uri = ContentUris.withAppendedId(base_uri, p_id)
                input_stream = content_resolver.openInputStream(photo_uri)
                if input_stream:
                    BufferedInputStream = autoclass('java.io.BufferedInputStream')
                    ByteArrayOutputStream = autoclass('java.io.ByteArrayOutputStream')
                    buffered_stream = BufferedInputStream(input_stream)
                    byte_array_stream = ByteArrayOutputStream()
                    buffer = [0] * 8192
                    while True:
                        read = buffered_stream.read(buffer)
                        if read == -1:
                            break
                        byte_array_stream.write(buffer, 0, read)
                    photo_bytes = byte_array_stream.toByteArray()
                    buffered_stream.close()
                    input_stream.close()
                    byte_array_stream.close()
                    if len(photo_bytes) > 1000:
                        photo_dir = os.path.join(BASE_DIR, 'photos')
                        if not os.path.exists(photo_dir):
                            os.makedirs(photo_dir)
                        self.photo_path = os.path.join(photo_dir, f'photo_{int(time.time())}.jpg')
                        with open(self.photo_path, 'wb') as f:
                            f.write(photo_bytes)
                        crop_screen = self.manager.get_screen('crop')
                        crop_screen.set_image(self.photo_path)
                        self.manager.current = 'crop'
                        return
        except Exception as e:
            print(f'检查照片失败: {e}')

        if not hasattr(self, '_check_count'):
            self._check_count = 0
        self._check_count += 1
        if self._check_count < 20:
            Clock.schedule_once(self._check_captured_photo, 2)
        else:
            self._show_error('未找到拍摄的照片\n请使用相册选择图片')

    def _on_album(self, instance):
        """从相册选择"""
        self._show_error('相册功能开发中\n请使用拍照功能')

    def _on_close(self, instance=None):
        """返回主界面"""
        self._checking = False
        if self._webview:
            try:
                from android.runnable import run_on_ui_thread
                @run_on_ui_thread
                def destroy():
                    self._webview.destroy()
                destroy()
            except:
                pass
            self._webview = None
        self.manager.current = 'main'

    def _show_error(self, message):
        """显示错误"""
        self.status_label.text = message

class CropScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'crop'
        self.image_path = None
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=0, spacing=0)
        with layout.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda *a: setattr(self.bg_rect, 'pos', layout.pos), size=lambda *a: setattr(self.bg_rect, 'size', layout.size))
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=0.08, padding=10)
        title = Label(text='裁剪题目区域', font_size='18sp', font_name='ChineseFont', color=[1, 1, 1, 1])
        top_bar.add_widget(title)
        layout.add_widget(top_bar)
        self.image_container = BoxLayout(size_hint_y=0.75)
        self.image = Image(allow_stretch=True, keep_ratio=True)
        self.image_container.add_widget(self.image)
        self.crop_widget = CropWidget()
        self.image_container.add_widget(self.crop_widget)
        layout.add_widget(self.image_container)
        hint = Label(text='拖动四角调整裁剪框，框选题目区域', font_size='14sp', size_hint_y=0.05, font_name='ChineseFont', color=[0.9, 0.9, 0.9, 1])
        layout.add_widget(hint)
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=0.12, padding=20, spacing=20)
        retake_btn = Button(text='重拍', font_size='18sp', background_color=[0.8, 0.3, 0.3, 1], background_normal='', font_name='ChineseFont')
        retake_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'camera'))
        btn_layout.add_widget(retake_btn)
        confirm_btn = Button(text='确认识别', font_size='18sp', background_color=[0.2, 0.7, 0.3, 1], background_normal='', font_name='ChineseFont')
        confirm_btn.bind(on_press=self._on_confirm)
        btn_layout.add_widget(confirm_btn)
        layout.add_widget(btn_layout)
        self.add_widget(layout)

    def set_image(self, path):
        self.image_path = path
        self.image.source = path
        self.image.reload()

    def _on_confirm(self, instance):
        if not self.image_path:
            return
        try:
            from PIL import Image as PILImage
            img = PILImage.open(self.image_path)
            iw, ih = img.size
            cw, ch = self.crop_widget.size
            cx, cy, cw_rect, ch_rect = self.crop_widget.get_crop_coords()
            display_ratio = min(cw / iw, ch / ih)
            display_w = iw * display_ratio
            display_h = ih * display_ratio
            offset_x = (cw - display_w) / 2
            offset_y = (ch - display_h) / 2
            img_x = max(0, int((cx - offset_x) / display_ratio))
            img_y = max(0, int((cy - offset_y) / display_ratio))
            img_w = max(1, int(cw_rect / display_ratio))
            img_h = max(1, int(ch_rect / display_ratio))
            img_x = min(iw - 1, img_x)
            img_y = min(ih - 1, img_y)
            img_w = min(iw - img_x, img_w)
            img_h = min(ih - img_y, img_h)
            cropped = img.crop((img_x, img_y, img_x + img_w, img_y + img_h))
            cropped_path = self.image_path + '_cropped.jpg'
            cropped.save(cropped_path)
            result_screen = self.manager.get_screen('result')
            result_screen.process_image(cropped_path)
            self.manager.current = 'result'
        except Exception as e:
            print(f'裁剪失败: {e}')
            traceback.print_exc()


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'result'
        self.ocr_engine = None
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=0.07)
        back_btn = Button(text='← 返回', font_size='14sp', size_hint_x=0.2, background_color=[0.5, 0.5, 0.5, 1], background_normal='', font_name='ChineseFont')
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'main'))
        top_bar.add_widget(back_btn)
        title = Label(text='识别结果', font_size='18sp', font_name='ChineseFont', color=[0.1, 0.3, 0.6, 1])
        top_bar.add_widget(title)
        layout.add_widget(top_bar)
        self.status_label = Label(text='正在识别...', font_size='14sp', size_hint_y=0.05, font_name='ChineseFont', color=[0.4, 0.4, 0.4, 1])
        layout.add_widget(self.status_label)
        layout.add_widget(Label(text='识别的题目文字（可编辑）：', font_size='14sp', size_hint_y=0.04, font_name='ChineseFont', color=[0.3, 0.3, 0.3, 1], halign='left'))
        self.question_input = TextInput(hint_text='识别结果将显示在这里，可手动编辑...', font_size='14sp', size_hint_y=0.15, font_name='ChineseFont', multiline=True)
        layout.add_widget(self.question_input)
        self.search_btn = Button(text='搜索答案', font_size='16sp', size_hint_y=0.07, background_color=[0.2, 0.6, 0.8, 1], background_normal='', font_name='ChineseFont')
        self.search_btn.bind(on_press=self._on_search)
        layout.add_widget(self.search_btn)
        self.result_scroll = ScrollView(size_hint_y=0.5)
        self.result_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10, padding=10)
        self.result_layout.bind(minimum_height=self.result_layout.setter('height'))
        self.result_label = Label(text='等待识别...', font_size='14sp', size_hint_y=None, height=100, halign='left', valign='top', text_size=(Window.width - 50, None), color=[0, 0, 0, 1], font_name='ChineseFont')
        self.result_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1] + 20))
        self.result_layout.add_widget(self.result_label)
        self.result_scroll.add_widget(self.result_layout)
        layout.add_widget(self.result_scroll)
        bottom_btn = Button(text='再搜一题', font_size='16sp', size_hint_y=0.07, background_color=[0.9, 0.6, 0.2, 1], background_normal='', font_name='ChineseFont')
        bottom_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'camera'))
        layout.add_widget(bottom_btn)
        self.add_widget(layout)

    def process_image(self, image_path):
        self.status_label.text = '正在识别...'
        self.result_label.text = '正在识别图片中的文字...'
        def process_thread():
            try:
                if not self.ocr_engine:
                    from ocr_engine_python import get_ocr_engine
                    self.ocr_engine = get_ocr_engine()
                text = self.ocr_engine.recognize(image_path)
                question_text = self.ocr_engine.extract_question_text(text)
                Clock.schedule_once(lambda dt: self._on_ocr_complete(question_text), 0)
            except Exception as e:
                error_msg = f'识别失败: {e}'
                Clock.schedule_once(lambda dt: self._on_ocr_error(error_msg), 0)
                print(f'OCR处理失败: {e}')
                traceback.print_exc()
        threading.Thread(target=process_thread, daemon=True).start()

    def _on_ocr_complete(self, question_text):
        self.status_label.text = '识别完成，请核对题目文字'
        if question_text:
            self.question_input.text = question_text
        else:
            self.question_input.text = ''
            self.result_label.text = (
                '⚠️ 纯Python OCR识别能力有限\n\n'
                '请手动输入题目文字，然后点击"搜索答案"\n\n'
                '提示：\n'
                '1. 确保裁剪区域包含完整题目\n'
                '2. 输入题目中的关键词即可搜索\n'
                '3. 题目越完整，搜索结果越准确'
            )

    def _on_ocr_error(self, error_msg):
        self.status_label.text = '识别失败'
        self.result_label.text = f'{error_msg}\n\n请手动输入题目文字后搜索'

    def _on_search(self, instance):
        query_text = self.question_input.text.strip()
        if not query_text:
            self.result_label.text = '请输入题目文字后再搜索'
            return
        main_screen = self.manager.get_screen('main')
        if not main_screen.search_engine:
            self.result_label.text = '搜题引擎未初始化，请稍后再试'
            return
        self.status_label.text = '正在搜索...'
        self.search_btn.disabled = True
        def search_thread():
            try:
                results = main_screen.search_engine.search(query_text, top_k=5)
                Clock.schedule_once(lambda dt: self._show_results(query_text, results), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)), 0)
        threading.Thread(target=search_thread, daemon=True).start()

    def _show_results(self, query_text, results):
        self.search_btn.disabled = False
        if not results:
            self.result_label.text = (
                f'未找到匹配的题目\n\n'
                f'搜索关键词：{query_text[:50]}...\n\n'
                f'请尝试：\n'
                f'1. 输入更多题目关键词\n'
                f'2. 检查是否已导入题库\n'
                f'3. 重新拍照裁剪'
            )
            self.status_label.text = '未找到匹配题目'
            return
        result_text = f'🔍 搜索到 {len(results)} 个结果：\n\n'
        for i, (question, similarity) in enumerate(results, 1):
            score = similarity * 100
            result_text += f'━━━━━━━━━━━━━━━━━━━━\n'
            result_text += f'【结果 {i}】匹配度：{score:.1f}%\n\n'
            q_type = question.get('question_type', '未知题型')
            result_text += f'题型：{q_type}\n\n'
            q_text = question.get('question_text', '')
            result_text += f'题目：{q_text}\n\n'
            options = question.get('options', '')
            if options:
                result_text += f'选项：\n{options}\n\n'
            answer = question.get('answer', '')
            result_text += f'✅ 答案：{answer}\n\n'
            analysis = question.get('analysis', '')
            if analysis:
                result_text += f'📝 解析：{analysis}\n\n'
        result_text += '━━━━━━━━━━━━━━━━━━━━'
        self.result_label.text = result_text
        self.status_label.text = f'找到 {len(results)} 个匹配结果'

    def _show_error(self, error_msg):
        self.search_btn.disabled = False
        self.result_label.text = f'错误：{error_msg}'
        self.status_label.text = '操作失败'


class OfflineQAApp(App):
    def build(self):
        try:
            Window.clearcolor = UI['bg_color']
            sm = ScreenManager()
            try:
                sm.add_widget(MainScreen(name='main'))
            except Exception as e:
                print(f'MainScreen创建失败: {e}')
                traceback.print_exc()
                sm.add_widget(self._create_error_screen('主界面初始化失败', str(e)))
            try:
                sm.add_widget(CameraScreen(name='camera'))
            except Exception as e:
                print(f'CameraScreen创建失败: {e}')
                traceback.print_exc()
            try:
                sm.add_widget(CropScreen(name='crop'))
            except Exception as e:
                print(f'CropScreen创建失败: {e}')
                traceback.print_exc()
            try:
                sm.add_widget(ResultScreen(name='result'))
            except Exception as e:
                print(f'ResultScreen创建失败: {e}')
                traceback.print_exc()
            return sm
        except Exception as e:
            print(f'APP构建失败: {e}')
            traceback.print_exc()
            return self._create_error_screen('APP启动失败', str(e))

    def _create_error_screen(self, title, message):
        screen = Screen(name='error')
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text=title, font_size='20sp', color=[1, 0, 0, 1]))
        layout.add_widget(Label(text=message, font_size='14sp', color=[0.5, 0.5, 0.5, 1]))
        layout.add_widget(Label(text='请检查错误日志', font_size='12sp', color=[0.5, 0.5, 0.5, 1]))
        screen.add_widget(layout)
        return screen


if __name__ == '__main__':
    try:
        OfflineQAApp().run()
    except Exception as e:
        print(f'APP运行错误: {e}')
        traceback.print_exc()
        try:
            log_path = os.path.join(BASE_DIR, "fatal_error.log")
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f'Fatal Error: {e}\n')
                f.write(traceback.format_exc())
        except:
            pass
