# -*- coding: utf-8 -*-
"""
离线搜题宝 - 完整功能版本
支持：拍照OCR识别 + 本地题库导入 + 离线语义搜题
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
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase

from config import UI, BASE_DIR, TEMP_DIR


# 全局错误处理
def excepthook(exc_type, exc_value, exc_traceback):
    """全局异常处理，防止闪退"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"未捕获异常: {error_msg}")
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
        print(f"当前工作目录: {os.getcwd()}")
        print(f"__file__: {__file__}")

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
            print(f"检查字体: {font_path} -> {os.path.exists(font_path)}")
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
    """简单的文件选择器弹窗"""
    def __init__(self, on_select, **kwargs):
        super().__init__(**kwargs)
        self.title = '选择Excel文件导入'
        self.size_hint = (0.9, 0.9)
        self.on_select = on_select

        layout = BoxLayout(orientation='vertical', padding=10, spacing=5)

        # 当前路径
        self.path_label = Label(
            text='/sdcard/',
            size_hint_y=0.05,
            font_name='ChineseFont'
        )
        layout.add_widget(self.path_label)

        # 文件列表
        scroll = ScrollView(size_hint_y=0.8)
        self.file_list = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=2
        )
        self.file_list.bind(minimum_height=self.file_list.setter('height'))
        scroll.add_widget(self.file_list)
        layout.add_widget(scroll)

        # 按钮
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=5)

        up_btn = Button(
            text='上级目录',
            font_name='ChineseFont',
            background_color=[0.5, 0.5, 0.5, 1],
            background_normal='',
        )
        up_btn.bind(on_press=self.go_up)
        btn_layout.add_widget(up_btn)

        cancel_btn = Button(
            text='取消',
            font_name='ChineseFont',
            background_color=[0.8, 0.3, 0.3, 1],
            background_normal='',
        )
        cancel_btn.bind(on_press=self.dismiss)
        btn_layout.add_widget(cancel_btn)

        layout.add_widget(btn_layout)
        self.content = layout

        # 请求存储权限
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.MANAGE_EXTERNAL_STORAGE
            ])
        except:
            pass

        # 默认从根目录开始，让用户手动浏览
        default_paths = [
            '/storage/emulated/0/',
            '/sdcard/',
            '/',
        ]
        
        self.current_path = '/'
        for p in default_paths:
            print(f"检查路径: {p} -> {os.path.exists(p)}")
            if os.path.exists(p):
                self.current_path = p
                break
        
        print(f"使用路径: {self.current_path}")
        self.load_dir(self.current_path)

    def load_dir(self, path):
        """加载目录内容"""
        self.current_path = path
        self.path_label.text = path
        self.file_list.clear_widgets()

        print(f"加载目录: {path}")
        print(f"目录存在: {os.path.exists(path)}")
        print(f"是否是目录: {os.path.isdir(path)}")

        try:
            items = os.listdir(path)
            print(f"目录内容数量: {len(items)}")
            print(f"目录内容: {items[:10]}")  # 只打印前10个
        except PermissionError as e:
            print(f"权限错误: {e}")
            # 显示错误信息
            error_label = Label(
                text=f'权限不足，无法访问此目录\n请点击"上级目录"返回上一级',
                font_size='14sp',
                size_hint_y=None,
                height=60,
                font_name='ChineseFont',
                color=[0.8, 0.3, 0.3, 1]
            )
            self.file_list.add_widget(error_label)
            return
        except Exception as e:
            print(f"读取目录失败: {e}")
            items = []

        # 目录
        dirs = []
        files = []
        for item in items:
            full_path = os.path.join(path, item)
            try:
                if os.path.isdir(full_path):
                    dirs.append(item)
                else:
                    files.append(item)
            except:
                pass

        print(f"目录数: {len(dirs)}, 文件数: {len(files)}")

        # 如果没有内容，显示提示
        if not dirs and not files:
            empty_label = Label(
                text='此目录为空',
                font_size='14sp',
                size_hint_y=None,
                height=40,
                font_name='ChineseFont',
                color=[0.5, 0.5, 0.5, 1]
            )
            self.file_list.add_widget(empty_label)

        # 添加目录
        for d in sorted(dirs):
            btn = Button(
                text=f'📁 {d}',
                size_hint_y=None,
                height=40,
                halign='left',
                font_name='ChineseFont',
                background_color=[0.8, 0.85, 0.9, 1],
                background_normal='',
            )
            btn.bind(on_press=lambda x, p=os.path.join(path, d): self.load_dir(p))
            self.file_list.add_widget(btn)

        # 添加文件（显示所有文件，不只是Excel）
        for f in sorted(files):
            # 根据文件类型显示不同图标
            ext = os.path.splitext(f)[1].lower()
            if ext in ['.xlsx', '.xls', '.csv']:
                icon = '📊'
                bg_color = [0.9, 0.95, 0.9, 1]
            elif ext in ['.pdf']:
                icon = '📕'
                bg_color = [0.95, 0.9, 0.9, 1]
            elif ext in ['.txt', '.doc', '.docx']:
                icon = '📄'
                bg_color = [0.95, 0.95, 0.9, 1]
            else:
                icon = '📄'
                bg_color = [0.9, 0.9, 0.9, 1]
            
            btn = Button(
                text=f'{icon} {f}',
                size_hint_y=None,
                height=40,
                halign='left',
                font_name='ChineseFont',
                background_color=bg_color,
                background_normal='',
            )
            btn.bind(on_press=lambda x, p=os.path.join(path, f): self.select_file(p))
            self.file_list.add_widget(btn)

    def go_up(self, instance):
        """返回上级目录"""
        parent = os.path.dirname(self.current_path.rstrip('/'))
        if parent:
            self.load_dir(parent + '/')
        else:
            self.load_dir('/')

    def select_file(self, file_path):
        """选择文件"""
        self.dismiss()
        self.on_select(file_path)


class OfflineQALayout(BoxLayout):
    """主界面布局"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10

        self.question_bank = None
        self.search_engine = None
        self.importer = None
        self.ocr_engine = None
        self._initialized = False

        self._build_ui()
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
            color=[0, 0, 0, 1],
            font_name='ChineseFont'
        )
        self.add_widget(self.stats_label)

        # 调试信息（显示当前目录）
        self.debug_label = Label(
            text='调试信息加载中...',
            font_size='10sp',
            size_hint_y=0.08,
            color=[0.3, 0.3, 0.3, 1],
            halign='left',
            valign='top',
            text_size=(Window.width - 20, None),
            font_name='ChineseFont'
        )
        self.add_widget(self.debug_label)

        # 主按钮区域
        btn_layout = BoxLayout(size_hint_y=0.25, spacing=10, padding=5)

        self.camera_btn = Button(
            text='拍照搜题',
            font_size='20sp',
            background_color=UI['theme_color'],
            background_normal='',
            font_name='ChineseFont'
        )
        self.camera_btn.bind(on_press=self.on_camera_click)
        btn_layout.add_widget(self.camera_btn)

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
            color=[0, 0, 0, 1],
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

        # 结果显示区域
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
            color=[0, 0, 0, 1],
            font_name='ChineseFont'
        )
        self.result_layout.add_widget(self.result_label)
        self.result_scroll.add_widget(self.result_layout)
        self.add_widget(self.result_scroll)

    def _init_background(self, dt):
        """异步初始化后台组件"""
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

                # 自动导入内置题库
                if self.question_bank and self.importer is None:
                    try:
                        from importer import get_importer
                        self.importer = get_importer()
                    except Exception as e:
                        print(f'导入器初始化失败: {e}')

                # 检查题库是否为空，如果为空则自动导入内置题库
                debug_import = '导入调试: '
                
                try:
                    if not self.question_bank:
                        debug_import += '\n错误: question_bank为空'
                    elif not self.importer:
                        debug_import += '\n错误: importer为空'
                    else:
                        stats = self.question_bank.get_statistics()
                        debug_import += f'\n当前题库: {stats["total"]}题'
                        
                        if stats['total'] == 0:
                            self._set_status('正在导入内置题库...')
                            print('题库为空，自动导入内置题库...')

                            script_dir = os.path.dirname(os.path.abspath(__file__))
                            cwd = os.getcwd()

                            # 只在assets目录查找CSV文件（避免重复导入）
                            search_dirs = [
                                os.path.join(cwd, 'assets'),
                                os.path.join(script_dir, 'assets'),
                            ]

                            imported_count = 0

                            for search_dir in search_dirs:
                                debug_import += f'\n搜索: {search_dir[-15:]}'
                                
                                if os.path.exists(search_dir):
                                    files = os.listdir(search_dir)
                                    # 优先导入CSV文件（不需要openpyxl）
                                    csv_files = [f for f in files if f.endswith('.csv')]
                                    debug_import += f' 找到{len(csv_files)}个csv'

                                    for filename in csv_files:
                                        file_path = os.path.join(search_dir, filename)
                                        debug_import += f'\n  {filename}'

                                        try:
                                            success, fail, error = self.importer.import_file(file_path)
                                            if error:
                                                debug_import += f' 错误: {str(error)[:15]}'
                                            else:
                                                debug_import += f' 成功: {success}题'
                                                imported_count += success
                                        except Exception as e:
                                            debug_import += f' 异常: {str(e)[:15]}'
                                            traceback.print_exc()

                            debug_import += f'\n总计导入: {imported_count}题'
                except Exception as e:
                    debug_import += f'\n整体错误: {str(e)[:20]}'
                    traceback.print_exc()
                
                # 把导入调试信息显示在结果标签上（不会被覆盖）
                Clock.schedule_once(lambda dt: setattr(self.result_label, 'text', debug_import), 0)

                # 构建搜索索引
                if self.question_bank and self.search_engine:
                    try:
                        stats = self.question_bank.get_statistics()
                        if stats['total'] > 0:
                            self._set_status('正在构建搜索索引...')
                            self.search_engine.build_index()
                    except Exception as e:
                        print(f'统计或索引构建失败: {e}')

                Clock.schedule_once(lambda dt: self._update_stats(), 0)
                Clock.schedule_once(lambda dt: self._update_debug(), 0)
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

    def _update_debug(self):
        """更新调试信息，显示当前目录和文件列表"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cwd = os.getcwd()

            debug_text = f'调试信息:\n'
            debug_text += f'cwd: {cwd}\n'

            try:
                files = os.listdir(cwd)
                debug_text += f'根目录: {str(files[:10])}\n'
            except:
                debug_text += '根目录: 无法读取\n'

            # 显示assets目录内容
            assets_dir = os.path.join(cwd, 'assets')
            if os.path.exists(assets_dir):
                try:
                    assets_files = os.listdir(assets_dir)
                    debug_text += f'assets目录: {str(assets_files[:10])}'
                except:
                    debug_text += 'assets目录: 无法读取'
            else:
                debug_text += 'assets目录: 不存在'

            self.debug_label.text = debug_text
        except Exception as e:
            self.debug_label.text = f'调试信息错误: {e}'

    def on_camera_click(self, instance):
        """拍照搜题按钮点击"""
        try:
            from kivy.uix.camera import Camera
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.button import Button
            from kivy.graphics.texture import Texture
            import numpy as np
            from PIL import Image
            import time

            self.result_label.text = '正在打开相机...'

            # 请求相机权限
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.CAMERA])
            except:
                pass

            # 创建相机弹窗
            camera_popup = Popup(
                title='拍照搜题',
                size_hint=(0.95, 0.95),
            )

            layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

            # 相机预览
            camera = Camera(
                index=0,  # 后置摄像头
                resolution=(640, 480),
                play=True
            )
            layout.add_widget(camera)

            # 拍照按钮
            def take_photo(btn):
                try:
                    # 捕获当前帧
                    texture = camera.texture
                    if texture:
                        # 将texture转换为PIL Image
                        buf = texture.pixels
                        w, h = texture.size
                        arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
                        # RGBA -> RGB
                        img = Image.fromarray(arr[:, :, :3])
                        # 垂直翻转 + 旋转90度（修正竖屏显示）
                        img = img.transpose(Image.FLIP_TOP_BOTTOM)
                        img = img.rotate(90, expand=True)

                        # 保存照片
                        photo_path = f'/sdcard/photo_{int(time.time())}.jpg'
                        img.save(photo_path)

                        camera.play = False
                        camera_popup.dismiss()

                        # 处理照片
                        self._process_photo(photo_path)

                except Exception as e:
                    self.result_label.text = f'拍照失败: {str(e)[:50]}'
                    camera_popup.dismiss()

            capture_btn = Button(
                text='拍照识别',
                size_hint_y=0.15,
                background_color=[0.2, 0.6, 0.8, 1],
                background_normal='',
                font_name='ChineseFont'
            )
            capture_btn.bind(on_press=take_photo)
            layout.add_widget(capture_btn)

            camera_popup.content = layout
            camera_popup.open()

        except Exception as e:
            self.result_label.text = f'相机打开失败: {str(e)[:50]}\n\n请使用手动输入搜题功能。'
            import traceback
            traceback.print_exc()

    def _on_photo_taken(self, path):
        """拍照完成回调"""
        print(f'拍照完成: {path}')

    def _process_photo(self, photo_path):
        """处理拍照：OCR识别 + 自动搜题"""
        def process_thread():
            try:
                debug_msg = f'处理照片: {photo_path}\n'
                debug_msg += f'文件存在: {os.path.exists(photo_path)}\n'

                # 初始化OCR引擎
                if not self.ocr_engine:
                    self._set_status('正在加载OCR模型...')
                    try:
                        from ocr_engine import get_ocr_engine
                        self.ocr_engine = get_ocr_engine()
                        debug_msg += 'OCR引擎加载成功\n'
                    except Exception as e:
                        debug_msg += f'OCR引擎加载失败: {str(e)[:30]}\n'
                        raise

                # OCR识别
                self._set_status('正在识别题目文字...')
                debug_msg += '开始OCR识别...\n'
                text = self.ocr_engine.recognize(photo_path)
                debug_msg += f'识别结果长度: {len(text) if text else 0}\n'

                if not text or len(text.strip()) < 5:
                    debug_msg += '识别失败：结果太短\n'
                    Clock.schedule_once(lambda dt: setattr(self.result_label, 'text', debug_msg), 0)
                    self.camera_btn.disabled = False
                    return

                # 提取题目文本
                question_text = self.ocr_engine.extract_question_text(text)
                debug_msg += f'题目文本: {question_text[:30]}...\n'
                self.question_input.text = question_text

                # 自动搜索
                self._set_status('正在搜索题库...')
                debug_msg += '开始搜索题库...\n'
                results = self.search_engine.search(question_text, top_k=5)
                debug_msg += f'找到{len(results)}个结果\n'

                # 显示调试信息和结果
                Clock.schedule_once(lambda dt: self._show_results(question_text, results, debug_msg), 0)

            except Exception as e:
                error_msg = f'识别失败: {str(e)[:50]}'
                debug_msg += f'错误: {error_msg}\n'
                Clock.schedule_once(lambda dt: setattr(self.result_label, 'text', debug_msg), 0)
                print(f'OCR处理失败: {e}')
                traceback.print_exc()
            finally:
                self.camera_btn.disabled = False

        threading.Thread(target=process_thread, daemon=True).start()

    def on_import_click(self, instance):
        """题库导入按钮点击"""
        if not self.importer:
            self.result_label.text = '导入器未初始化，请稍后再试'
            return

        # 请求存储权限
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        except:
            pass

        # 使用自定义文件选择器
        popup = FileChooserPopup(on_select=self._on_file_selected)
        popup.open()

    def _on_file_selected_plyer(self, selection):
        """plyer文件选择回调"""
        if not selection:
            print("没有选择文件")
            return

        # 处理不同类型的返回值
        if isinstance(selection, list):
            if len(selection) == 0:
                return
            file_path = selection[0]
        elif isinstance(selection, str):
            file_path = selection
        else:
            file_path = str(selection)

        # 确保路径是字符串
        if isinstance(file_path, bytes):
            file_path = file_path.decode('utf-8')

        print(f"选择的文件: {file_path}")
        print(f"文件类型: {type(file_path)}")
        print(f"文件存在: {os.path.exists(file_path)}")

        self._on_file_selected(file_path)

    def _on_file_selected(self, file_path):
        """选择文件后导入"""
        # 确保路径是字符串
        if isinstance(file_path, bytes):
            file_path = file_path.decode('utf-8')

        print(f"导入文件: {file_path}")
        print(f"文件存在: {os.path.exists(file_path)}")

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
                error_msg = f'导入失败: {str(e)[:50]}'
                Clock.schedule_once(lambda dt: self._show_error(error_msg), 0)
                print(f'导入失败: {e}')
                traceback.print_exc()
            finally:
                self.import_btn.disabled = False

        threading.Thread(target=import_thread, daemon=True).start()

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
                results = self.search_engine.search(query_text, top_k=5)
                Clock.schedule_once(lambda dt: self._show_results(query_text, results), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)), 0)

        threading.Thread(target=search_thread, daemon=True).start()

    def _show_results(self, query_text, results, debug_info=''):
        """显示搜索结果"""
        self.search_btn.disabled = False

        if not results:
            self.result_label.text = (
                f'未找到匹配的题目\n\n'
                f'搜索关键词：{query_text[:50]}...\n\n'
                f'{debug_info}\n\n'
                f'请尝试：\n'
                f'1. 输入更多题目关键词\n'
                f'2. 检查是否已导入题库\n'
                f'3. 重新拍照识别'
            )
            self.status_label.text = '未找到匹配题目'
            return

        result_text = f'🔍 搜索到 {len(results)} 个结果：\n\n'
        if debug_info:
            result_text += f'调试信息：{debug_info}\n\n'

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


class OfflineQAApp(App):
    """离线搜题宝应用"""

    def build(self):
        Window.clearcolor = UI['bg_color']
        return OfflineQALayout()


if __name__ == '__main__':
    try:
        OfflineQAApp().run()
    except Exception as e:
        print(f'APP运行错误: {e}')
        traceback.print_exc()

