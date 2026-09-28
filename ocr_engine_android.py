# -*- coding: utf-8 -*-
"""
Android原生OCR引擎 - 使用Google Play Services TextRecognizer API
通过jnius调用Android原生API，离线运行，准确率高
"""
import os
import re

# 尝试导入jnius（仅在Android上可用）
try:
    from jnius import autoclass
    from jnius import cast
    _JNIUS_AVAILABLE = True
except ImportError:
    _JNIUS_AVAILABLE = False

from config import MODEL_DIR


class AndroidOCREngine:
    """Android原生OCR引擎，使用Google Play Services TextRecognizer"""
    
    def __init__(self):
        self.text_recognizer = None
        self._initialized = False
        self._error = None
    
    def _initialize(self):
        """延迟初始化TextRecognizer"""
        if self._initialized:
            return
        
        if not _JNIUS_AVAILABLE:
            raise RuntimeError("jnius不可用，只能在Android设备上使用此OCR引擎")
        
        error_details = []
        
        try:
            # 获取Android Context
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            
            # 先检查Google Play Services是否可用
            try:
                GoogleApiAvailability = autoclass('com.google.android.gms.common.GoogleApiAvailability')
                gaa = GoogleApiAvailability.getInstance()
                result_code = gaa.isGooglePlayServicesAvailable(context)
                # SUCCESS = 0
                if result_code != 0:
                    error_string = gaa.getErrorString(result_code)
                    error_details.append(f"Google Play Services不可用: {error_string} (code={result_code})")
                    raise RuntimeError(f"Google Play Services不可用: {error_string}")
                else:
                    error_details.append("Google Play Services可用")
            except RuntimeError:
                raise
            except Exception as e:
                error_details.append(f"检查Google Play Services异常: {str(e)}")
            
            # 创建TextRecognizer
            try:
                TextRecognizerBuilder = autoclass('com.google.android.gms.vision.text.TextRecognizer$Builder')
                builder = TextRecognizerBuilder(context)
                self.text_recognizer = builder.build()
                error_details.append("TextRecognizer创建成功")
            except Exception as e:
                error_details.append(f"TextRecognizer创建失败: {str(e)}")
                raise
            
            # 检查是否可用
            if not self.text_recognizer.isOperational():
                error_details.append("TextRecognizer.isOperational()返回False")
                raise RuntimeError("TextRecognizer不可用，可能需要下载语言包或Google Play Services")
            
            self._initialized = True
            print("Android OCR引擎初始化成功")
            
        except Exception as e:
            import traceback
            error_detail = "\n".join(error_details)
            error_detail += f"\n异常: {str(e)}"
            # 尝试获取更详细的Java异常信息
            try:
                if hasattr(e, 'java_exception'):
                    java_exc = e.java_exception
                    error_detail += f"\nJava异常详情: {java_exc.toString()}"
            except:
                pass
            self._error = f"{error_detail}\n{traceback.format_exc()}"
            raise RuntimeError(f"Android OCR引擎初始化失败:\n{self._error}")
    
    def recognize(self, image_path):
        """识别图片中的文字"""
        self._initialize()
        
        try:
            # 加载图片为Bitmap
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            bitmap = BitmapFactory.decodeFile(image_path)
            
            if bitmap is None:
                raise RuntimeError(f"无法加载图片: {image_path}")
            
            # 创建Frame
            FrameBuilder = autoclass('com.google.android.gms.vision.Frame$Builder')
            frame_builder = FrameBuilder()
            frame_builder.setBitmap(bitmap)
            frame = frame_builder.build()
            
            # 识别文字
            sparse_array = self.text_recognizer.detect(frame)
            
            # 提取文字
            text_lines = []
            size = sparse_array.size()
            
            for i in range(size):
                key = sparse_array.keyAt(i)
                text_block = sparse_array.get(key)
                # TextBlock包含多个Line
                lines = text_block.getComponents()
                for j in range(lines.size()):
                    line = lines.valueAt(j)
                    text_lines.append(line.getValue())
            
            # 合并所有行
            result_text = '\n'.join(text_lines)
            
            # 回收Bitmap
            bitmap.recycle()
            
            return result_text
            
        except Exception as e:
            import traceback
            error_msg = f"OCR识别失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise RuntimeError(error_msg)
    
    def extract_question_text(self, ocr_text):
        """从OCR结果中提取题目文本"""
        if not ocr_text:
            return ""
        
        # 去除多余空白
        text = re.sub(r'\s+', ' ', ocr_text).strip()
        
        # 如果文本太长，取前500个字符
        if len(text) > 500:
            text = text[:500]
        
        return text


# 全局单例
_engine_instance = None

def get_ocr_engine():
    """获取OCR引擎单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AndroidOCREngine()
    return _engine_instance
