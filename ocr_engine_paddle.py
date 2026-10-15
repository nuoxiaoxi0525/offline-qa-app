# -*- coding: utf-8 -*-
"""
PaddleOCR-Lite 离线OCR引擎
使用onnxruntime运行PaddleOCR-Lite模型
"""

import os
import sys
import numpy as np
from PIL import Image, ImageOps, ImageFilter

# 导入配置
try:
    from config import BASE_DIR, OCR_CONFIG
except ImportError:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OCR_CONFIG = {}


class PaddleOCREngine:
    """PaddleOCR-Lite离线OCR引擎"""
    
    def __init__(self):
        self.name = "PaddleOCR-Lite"
        self.model_dir = os.path.join(BASE_DIR, "models")
        self.det_model_path = os.path.join(self.model_dir, "ch_PP-OCRv4_det_infer.onnx")
        self.rec_model_path = os.path.join(self.model_dir, "ch_PP-OCRv4_rec_infer.onnx")
        self.use_gpu = False
        self.session_det = None
        self.session_rec = None
        self.character_dict = None
        self.is_available = False
        
        # 初始化
        self._init_engine()
    
    def _init_engine(self):
        """初始化OCR引擎"""
        try:
            # 检查模型文件是否存在
            if not os.path.exists(self.det_model_path) or not os.path.exists(self.rec_model_path):
                print(f"[PaddleOCR] 模型文件不存在，使用纯Python OCR后备方案")
                self.is_available = False
                return
            
            # 尝试导入onnxruntime
            try:
                import onnxruntime as ort
                print(f"[PaddleOCR] onnxruntime版本: {ort.__version__}")
            except ImportError as e:
                print(f"[PaddleOCR] onnxruntime导入失败: {e}")
                self.is_available = False
                return
            
            # 创建推理会话
            providers = ['CPUExecutionProvider']
            self.session_det = ort.InferenceSession(self.det_model_path, providers=providers)
            self.session_rec = ort.InferenceSession(self.rec_model_path, providers=providers)
            print(f"[PaddleOCR] 模型加载成功")
            
            # 加载字符字典
            self._load_character_dict()
            
            self.is_available = True
            print(f"[PaddleOCR] 引擎初始化完成")
            
        except Exception as e:
            print(f"[PaddleOCR] 引擎初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self.is_available = False
    
    def _load_character_dict(self):
        """加载字符字典"""
        try:
            dict_path = os.path.join(self.model_dir, "ppocr_keys_v1.txt")
            if os.path.exists(dict_path):
                with open(dict_path, 'r', encoding='utf-8') as f:
                    self.character_dict = [line.strip() for line in f.readlines()]
                # 添加CTC blank token
                self.character_dict = ['blank'] + self.character_dict
                print(f"[PaddleOCR] 字符字典加载成功，共{len(self.character_dict)}个字符")
            else:
                # 使用默认的中文字符字典（简化版）
                self.character_dict = ['blank'] + list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ，。、；：？！""''（）《》【】")
                print(f"[PaddleOCR] 使用默认字符字典")
        except Exception as e:
            print(f"[PaddleOCR] 加载字符字典失败: {e}")
            self.character_dict = ['blank'] + list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    
    def preprocess_image(self, image_path):
        """预处理图像"""
        try:
            # 打开图像
            img = Image.open(image_path).convert('RGB')
            
            # 调整大小（保持比例）
            max_size = 960
            w, h = img.size
            if max(w, h) > max_size:
                ratio = max_size / max(w, h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                img = img.resize((new_w, new_h), Image.LANCZOS)
            
            # 灰度化
            img_gray = img.convert('L')
            
            # 增强对比度
            img_gray = ImageOps.autocontrast(img_gray)
            
            # 降噪
            img_gray = img_gray.filter(ImageFilter.MedianFilter(size=3))
            
            return img, img_gray
            
        except Exception as e:
            print(f"[PaddleOCR] 图像预处理失败: {e}")
            return None, None
    
    def detect_text_regions(self, img):
        """检测文本区域（简化版）"""
        try:
            # 简化版：返回整个图像作为一个文本区域
            # 实际PaddleOCR会使用检测模型找到文本框
            w, h = img.size
            boxes = [[0, 0, w, h]]
            return boxes
        except Exception as e:
            print(f"[PaddleOCR] 文本区域检测失败: {e}")
            return []
    
    def recognize_text(self, img, box):
        """识别单个文本区域的文字"""
        try:
            # 裁剪文本区域
            x1, y1, x2, y2 = box
            text_img = img.crop((x1, y1, x2, y2))
            
            # 调整到模型输入大小（32高度，宽度按比例）
            target_h = 32
            w, h = text_img.size
            ratio = target_h / h
            target_w = int(w * ratio)
            text_img = text_img.resize((target_w, target_h), Image.LANCZOS)
            
            # 转换为numpy数组
            img_array = np.array(text_img).astype(np.float32)
            
            # 归一化
            img_array = img_array / 255.0
            img_array = (img_array - 0.5) / 0.5
            
            # 转换为CHW格式
            if len(img_array.shape) == 2:
                img_array = np.stack([img_array, img_array, img_array], axis=0)
            else:
                img_array = img_array.transpose(2, 0, 1)
            
            # 添加batch维度
            input_tensor = np.expand_dims(img_array, axis=0)
            
            if self.session_rec is None:
                return ""
            
            # 推理
            input_name = self.session_rec.get_inputs()[0].name
            outputs = self.session_rec.run(None, {input_name: input_tensor})
            
            # 后处理（CTC解码）
            pred = outputs[0][0]  # (seq_len, num_classes)
            pred_labels = np.argmax(pred, axis=1)
            
            # CTC解码（合并重复字符，去除blank）
            result = []
            prev = -1
            for label in pred_labels:
                if label != prev and label != 0:  # 0是blank
                    if label < len(self.character_dict):
                        result.append(self.character_dict[label])
                prev = label
            
            text = ''.join(result)
            return text
            
        except Exception as e:
            print(f"[PaddleOCR] 文字识别失败: {e}")
            return ""
    
    def recognize(self, image_path):
        """识别图像中的文字"""
        if not self.is_available:
            return {
                'success': False,
                'text': '',
                'error': 'PaddleOCR引擎不可用',
                'engine': self.name
            }
        
        try:
            print(f"[PaddleOCR] 开始识别: {image_path}")
            
            # 预处理图像
            img, img_gray = self.preprocess_image(image_path)
            if img is None:
                return {'success': False, 'text': '', 'error': '图像预处理失败', 'engine': self.name}
            
            # 检测文本区域
            boxes = self.detect_text_regions(img)
            if not boxes:
                return {'success': False, 'text': '', 'error': '未检测到文本区域', 'engine': self.name}
            
            # 识别每个文本区域
            all_text = []
            for box in boxes:
                text = self.recognize_text(img, box)
                if text.strip():
                    all_text.append(text.strip())
            
            result_text = '\n'.join(all_text)
            
            print(f"[PaddleOCR] 识别完成，结果长度: {len(result_text)}")
            
            return {
                'success': True,
                'text': result_text,
                'error': None,
                'engine': self.name
            }
            
        except Exception as e:
            print(f"[PaddleOCR] 识别失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'text': '',
                'error': str(e),
                'engine': self.name
            }


# 全局实例
_engine = None

def get_ocr_engine():
    """获取OCR引擎单例"""
    global _engine
    if _engine is None:
        _engine = PaddleOCREngine()
    return _engine


if __name__ == "__main__":
    # 测试
    engine = get_ocr_engine()
    print(f"引擎状态: {engine.is_available}")
