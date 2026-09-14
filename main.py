"""
离线搜题宝 - 最小测试版本
用于验证Buildozer打包是否正常工作
"""
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class TestLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 10

        self.add_widget(Label(
            text='离线搜题宝 - 测试版本',
            font_size='24sp',
            size_hint_y=0.3
        ))

        self.status_label = Label(
            text='点击按钮测试功能',
            font_size='16sp',
            size_hint_y=0.3
        )
        self.add_widget(self.status_label)

        test_btn = Button(
            text='测试按钮',
            font_size='18sp',
            size_hint_y=0.2
        )
        test_btn.bind(on_press=self.on_test_click)
        self.add_widget(test_btn)

    def on_test_click(self, instance):
        self.status_label.text = '测试成功！APP运行正常！'


class OfflineQAApp(App):
    def build(self):
        return TestLayout()


if __name__ == '__main__':
    OfflineQAApp().run()
