# -*- coding: utf-8 -*-
"""
摄像头处理模块 - 使用plyer调用安卓原生相机
支持后置/广角摄像头，高分辨率拍照
"""
import os
import time
from config import CAMERA_CONFIG, PHOTO_DIR


class CameraHandler:
    """摄像头处理器"""

    def __init__(self, config=None):
        self.config = config or CAMERA_CONFIG
        self._camera = None
        self._platform = self._detect_platform()

    def _detect_platform(self):
        """检测运行平台"""
        try:
            from android.permissions import Permission
            return 'android'
        except ImportError:
            return 'desktop'

    def take_photo(self, filename=None):
        """
        拍照
        :param filename: 保存的文件名（可选）
        :return: 照片文件路径
        """
        if filename is None:
            filename = f"photo_{int(time.time())}.jpg"

        filepath = os.path.join(PHOTO_DIR, filename)

        if self._platform == 'android':
            return self._take_photo_android(filepath)
        else:
            return self._take_photo_desktop(filepath)

    def _take_photo_android(self, filepath):
        """安卓平台拍照（使用plyer）"""
        try:
            from plyer import camera

            # 请求相机权限
            self._request_camera_permission()

            # 调用系统相机拍照
            camera.take_picture(filename=filepath, on_complete=self._on_photo_complete)

            # 等待拍照完成（plyer的take_picture是异步的）
            # 实际使用中需要通过回调处理，这里简化处理
            time.sleep(2)

            if os.path.exists(filepath):
                return filepath
            else:
                # 如果文件不存在，尝试使用Kivy的相机
                return self._take_photo_kivy(filepath)

        except ImportError:
            # plyer不可用，使用Kivy相机
            return self._take_photo_kivy(filepath)
        except Exception as e:
            print(f"plyer拍照失败: {e}")
            return self._take_photo_kivy(filepath)

    def _take_photo_kivy(self, filepath):
        """使用Kivy内置相机拍照"""
        try:
            from kivy.core.camera import Camera
            from kivy.graphics.texture import Texture
            import cv2
            import numpy as np

            # 创建相机实例
            self._camera = Camera(
                index=0,  # 0=后置，1=前置
                resolution=self.config['resolution'],
                size=self.config['resolution']
            )
            self._camera.play = True

            # 等待相机启动
            time.sleep(1)

            # 捕获当前帧
            texture = self._camera.texture
            if texture:
                # 将texture转换为numpy数组
                buf = texture.pixels
                w, h = texture.size
                arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
                # RGBA -> BGR
                img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
                # 垂直翻转（Kivy的texture是上下颠倒的）
                img = cv2.flip(img, 0)
                # 保存
                cv2.imwrite(filepath, img)

            # 停止相机
            self._camera.play = False
            self._camera = None

            return filepath if os.path.exists(filepath) else None

        except Exception as e:
            print(f"Kivy相机拍照失败: {e}")
            return None

    def _take_photo_desktop(self, filepath):
        """桌面平台拍照（用于开发测试）"""
        try:
            import cv2

            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("无法打开摄像头")
                return None

            # 等待摄像头启动
            time.sleep(1)

            # 读取一帧
            ret, frame = cap.read()
            cap.release()

            if ret:
                cv2.imwrite(filepath, frame)
                return filepath
            return None

        except Exception as e:
            print(f"桌面摄像头拍照失败: {e}")
            return None

    def _request_camera_permission(self):
        """请求安卓相机权限"""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
            ])
        except ImportError:
            pass

    def _on_photo_complete(self, filepath):
        """拍照完成回调"""
        print(f"拍照完成: {filepath}")

    def get_camera_info(self):
        """获取摄像头信息"""
        info = {
            'platform': self._platform,
            'preferred_facing': self.config['preferred_facing'],
            'resolution': self.config['resolution'],
            'wide_angle': self.config['enable_wide_angle'],
        }
        return info

    def release(self):
        """释放摄像头资源"""
        if self._camera:
            try:
                self._camera.play = False
            except Exception:
                pass
            self._camera = None


# 单例模式
_camera_handler = None

def get_camera_handler():
    global _camera_handler
    if _camera_handler is None:
        _camera_handler = CameraHandler()
    return _camera_handler
