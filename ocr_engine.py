# -*- coding: utf-8 -*-
"""
OCR文字识别引擎 - RapidOCR (PP-OCRv4)
对应刷刷题的"文本检测+OCR识别层"
中文识别率97%+，完全离线运行
"""
import os
import re
import cv2
import numpy as np
from config import OCR_CONFIG, MODEL_DIR, TEMP_DIR


class OCREngine:
    """RapidOCR离线文字识别引擎"""

    def __init__(self, config=None):
        self.config = config or OCR_CONFIG
        self._ocr = None
        self._initialized = False

    def _initialize(self):
        """延迟初始化RapidOCR"""
        if self._initialized:
            return

        try:
            from rapidocr_onnxruntime import RapidOCR

            # 检查是否有自定义模型路径
            model_path = os.path.join(MODEL_DIR, "rapidocr")
            if os.path.exists(model_path):
                # 使用打包进APK的本地模型
                self._ocr = RapidOCR(
                    det_model_path=os.path.join(model_path, "ch_PP-OCRv4_det.onnx"),
                    rec_model_path=os.path.join(model_path, "ch_PP-OCRv4_rec.onnx"),
                    cls_model_path=os.path.join(model_path, "ch_ppocr_mobile_v2.0_cls.onnx"),
                )
            else:
                # 使用rapidocr内置模型（首次运行会自动下载）
                self._ocr = RapidOCR()

            self._initialized = True
        except ImportError:
            raise RuntimeError(
                "rapidocr-onnxruntime未安装，请执行: pip install rapidocr-onnxruntime"
            )
        except Exception as e:
            raise RuntimeError(f"RapidOCR初始化失败: {e}")

    def recognize(self, image):
        """
        对图像进行OCR识别
        :param image: 预处理后的图像（numpy数组或图像路径）
        :return: 识别出的文本
        """
        self._initialize()

        # 如果传入的是路径，读取图像
        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                raise ValueError(f"无法读取图像: {image}")
        else:
            img = image

        # 执行OCR识别
        try:
            result, elapse = self._ocr(img)
        except Exception as e:
            # 降级：尝试用默认参数
            result, elapse = self._ocr(img)

        # 解析识别结果
        if result is None or len(result) == 0:
            return ""

        # 按文本框位置排序（从上到下，从左到右）
        sorted_results = self._sort_results(result)

        # 合并文本
        lines = []
        for item in sorted_results:
            # item格式: [bbox, text, confidence]
            if len(item) >= 2:
                text = item[1]
                if text and text.strip():
                    lines.append(text.strip())

        return '\n'.join(lines)

    def recognize_with_boxes(self, image):
        """
        OCR识别并返回文本框坐标
        :return: (文本, 文本框列表)
        """
        self._initialize()

        if isinstance(image, str):
            img = cv2.imread(image)
        else:
            img = image

        result, elapse = self._ocr(img)

        if result is None:
            return "", []

        sorted_results = self._sort_results(result)

        boxes = []
        lines = []
        for item in sorted_results:
            if len(item) >= 3:
                bbox = item[0]  # 四个角点坐标
                text = item[1]
                confidence = item[2]
                if text and text.strip():
                    lines.append(text.strip())
                    boxes.append({
                        'text': text.strip(),
                        'confidence': float(confidence),
                        'bbox': bbox,
                    })

        full_text = '\n'.join(lines)
        return full_text, boxes

    def _sort_results(self, results):
        """
        按文本框位置排序（从上到下，从左到右）
        PP-OCR返回的结果已经大致有序，但做一次精确排序
        """
        def get_sort_key(item):
            if len(item) >= 1 and item[0] is not None:
                bbox = item[0]
                # 取左上角点的y坐标作为行排序依据
                y_coords = [point[1] for point in bbox]
                x_coords = [point[0] for point in bbox]
                avg_y = sum(y_coords) / len(y_coords)
                avg_x = sum(x_coords) / len(x_coords)
                # 先按y排序（行），同一行内按x排序（列）
                return (int(avg_y // 30), avg_x)
            return (0, 0)

        return sorted(results, key=get_sort_key)

    def post_process(self, text):
        """
        OCR结果后处理（NLP语义纠错层）
        """
        if not text:
            return ""

        # 去除行首尾空白
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        text = '\n'.join(lines)

        # 修正常见OCR错误
        corrections = {
            '（': '(', '）': ')', '，': ',', '。': '.',
            '：': ':', '；': ';', '？': '?', '！': '!',
        }
        for old, new in corrections.items():
            text = text.replace(old, new)

        # 规范化选项格式
        text = re.sub(r'([A-D])[、\s]+', r'\1.', text)
        text = re.sub(r'([A-D])\.\n', r'\1.', text)

        return text

    def extract_question_text(self, full_text):
        """从OCR全文中提取题目核心文本"""
        if not full_text:
            return ""

        lines = full_text.split('\n')
        question_lines = []

        for line in lines:
            if re.match(r'^[A-D][\.、]', line.strip()):
                continue
            if any(kw in line for kw in ['答案', '解析', '正确答案', '参考答案']):
                continue
            if re.match(r'^\d+[\.、]?$', line.strip()):
                continue
            question_lines.append(line.strip())

        return ' '.join(question_lines).strip()


# 单例模式
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine()
    return _ocr_engine
