# -*- coding: utf-8 -*-
"""
图像预处理模块 - 对应刷刷题的"图像预处理层"
功能：亮度/对比度调整、倾斜矫正、二值化、去噪增强
"""
import cv2
import numpy as np
import os
from config import PREPROCESS, TEMP_DIR


class ImageProcessor:
    """图像预处理器"""

    def __init__(self, config=None):
        self.config = config or PREPROCESS

    def process(self, image_path, save_debug=False):
        """
        完整预处理流程
        :param image_path: 输入图像路径
        :param save_debug: 是否保存调试中间图
        :return: 预处理后的图像（numpy数组）
        """
        # 1. 读取图像
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图像: {image_path}")

        # 2. 缩放（限制最大宽度，加速处理）
        img = self._resize(img)

        if save_debug:
            self._save_debug(img, "01_original")

        # 3. 倾斜矫正
        img = self._deskew(img)
        if save_debug:
            self._save_debug(img, "02_deskewed")

        # 4. 亮度/对比度自适应调整
        img = self._adjust_brightness_contrast(img)
        if save_debug:
            self._save_debug(img, "03_brightness")

        # 5. 灰度化
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 6. 去噪增强（非局部均值去噪）
        denoised = self._denoise(gray)
        if save_debug:
            self._save_debug(denoised, "04_denoised")

        # 7. 二值化（OTSU自动阈值）
        binary = self._binarize(denoised)
        if save_debug:
            self._save_debug(binary, "05_binary")

        # 8. 形态学操作（去除小噪点，连接断裂字符）
        processed = self._morphology(binary)
        if save_debug:
            self._save_debug(processed, "06_final")

        return processed

    def _resize(self, img):
        """限制图像最大宽度"""
        h, w = img.shape[:2]
        max_w = self.config["max_width"]
        if w > max_w:
            ratio = max_w / w
            new_h = int(h * ratio)
            img = cv2.resize(img, (max_w, new_h), interpolation=cv2.INTER_AREA)
        return img

    def _deskew(self, img):
        """
        倾斜矫正：自动检测并校正倾斜角度
        支持30度以内的倾斜矫正
        """
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # 反转颜色（文字变白色，背景变黑色）
            gray = cv2.bitwise_not(gray)
            # 二值化
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

            # 获取所有非零像素坐标
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 10:
                return img

            # 计算最小外接矩形的旋转角度
            angle = cv2.minAreaRect(coords)[-1]

            # 修正角度方向
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            # 只矫正30度以内的倾斜
            if abs(angle) > self.config["max_skew_angle"]:
                return img
            if abs(angle) < 0.5:  # 角度太小无需矫正
                return img

            # 执行旋转矫正
            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(img, M, (w, h),
                                      flags=cv2.INTER_CUBIC,
                                      borderMode=cv2.BORDER_REPLICATE)
            return rotated
        except Exception:
            return img

    def _adjust_brightness_contrast(self, img):
        """
        亮度/对比度自适应调整
        使用CLAHE（限制对比度自适应直方图均衡化）
        """
        # 转换到LAB色彩空间
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # 对L通道（亮度）应用CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)

        # 合并通道
        limg = cv2.merge((cl, a, b))
        result = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # 额外的对比度/亮度调整
        alpha = self.config["contrast_alpha"]
        beta = self.config["brightness_beta"]
        result = cv2.convertScaleAbs(result, alpha=alpha, beta=beta)

        return result

    def _denoise(self, gray):
        """
        非局部均值去噪（对应刷刷题的CNN去噪增强）
        去除干扰线条，增强字符轮廓
        """
        denoised = cv2.fastNlMeansDenoising(
            gray,
            None,
            h=self.config["denoise_h"],
            templateWindowSize=self.config["denoise_templateWindowSize"],
            searchWindowSize=self.config["denoise_searchWindowSize"]
        )
        return denoised

    def _binarize(self, gray):
        """
        二值化处理
        使用自适应阈值+OTSU，适应不均匀光照
        """
        # 自适应高斯阈值（处理光照不均）
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31, 10
        )
        return binary

    def _morphology(self, binary):
        """
        形态学操作：
        - 开运算：去除小噪点
        - 轻微闭运算：连接断裂字符
        """
        # 定义核
        kernel_small = np.ones((2, 2), np.uint8)

        # 开运算（先腐蚀后膨胀）：去除小白噪点
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small)

        return opened

    def _save_debug(self, img, name):
        """保存调试图像"""
        path = os.path.join(TEMP_DIR, f"debug_{name}.png")
        cv2.imwrite(path, img)
        return path

    def to_bytes(self, img):
        """将图像转为PNG字节流（用于OCR或显示）"""
        _, buffer = cv2.imencode('.png', img)
        return buffer.tobytes()


# 单例模式
_processor = None

def get_processor():
    global _processor
    if _processor is None:
        _processor = ImageProcessor()
    return _processor
