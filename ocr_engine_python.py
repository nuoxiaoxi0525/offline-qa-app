# -*- coding: utf-8 -*-
"""
纯Python OCR引擎 - 使用Pillow进行图像预处理和简单文字提取
适用于Android离线环境，不依赖原生库
"""
import os
import re
from PIL import Image, ImageEnhance, ImageFilter


class PythonOCREngine:
    """纯Python OCR引擎，基于图像处理"""
    
    def __init__(self):
        self._initialized = True
    
    def _initialize(self):
        """初始化（纯Python无需额外初始化）"""
        pass
    
    def preprocess_image(self, image_path):
        """
        图像预处理：
        1. 转为灰度图
        2. 增强对比度
        3. 二值化
        4. 去噪
        返回预处理后的图片路径
        """
        try:
            # 打开图片
            img = Image.open(image_path)
            
            # 转为灰度图
            img = img.convert('L')
            
            # 增强对比度
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # 增强锐度
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)
            
            # 二值化（自适应阈值）
            threshold = 127
            img = img.point(lambda x: 0 if x < threshold else 255, '1')
            
            # 保存预处理后的图片
            preprocessed_path = image_path + '_processed.png'
            img.save(preprocessed_path)
            
            return preprocessed_path
            
        except Exception as e:
            print(f"图像预处理失败: {e}")
            return image_path
    
    def detect_text_regions(self, image_path):
        """
        简单的文字区域检测（基于投影法）
        返回文字行的坐标列表
        """
        try:
            img = Image.open(image_path)
            if img.mode != 'L':
                img = img.convert('L')
            
            width, height = img.size
            pixels = img.load()
            
            # 水平投影：检测文字行
            row_counts = []
            for y in range(height):
                count = 0
                for x in range(width):
                    if pixels[x, y] < 128:  # 黑色像素
                        count += 1
                row_counts.append(count)
            
            # 找到文字行（黑色像素较多的行）
            text_rows = []
            in_text = False
            start_row = 0
            threshold = width * 0.05  # 黑色像素超过5%认为是文字行
            
            for y, count in enumerate(row_counts):
                if count > threshold and not in_text:
                    start_row = y
                    in_text = True
                elif count <= threshold and in_text:
                    if y - start_row > 5:  # 至少5像素高
                        text_rows.append((start_row, y))
                    in_text = False
            
            return text_rows
            
        except Exception as e:
            print(f"文字区域检测失败: {e}")
            return []
    
    def recognize(self, image_path):
        """
        识别图片中的文字
        由于纯Python OCR准确率有限，这里返回预处理后的信息
        用户可以在界面上手动编辑识别结果
        """
        try:
            # 图像预处理
            processed_path = self.preprocess_image(image_path)
            
            # 检测文字区域
            text_rows = self.detect_text_regions(processed_path)
            
            # 构建识别结果提示
            result = f"[纯Python OCR识别结果]\n"
            result += f"检测到 {len(text_rows)} 行文字区域\n"
            result += f"图片已预处理，请手动核对并输入题目文字\n"
            result += f"\n提示：\n"
            result += f"1. 请核对裁剪区域是否包含完整题目\n"
            result += f"2. 在下方输入框中输入或修改题目文字\n"
            result += f"3. 点击搜索按钮查找答案\n"
            
            # 清理临时文件
            try:
                if processed_path != image_path and os.path.exists(processed_path):
                    os.remove(processed_path)
            except:
                pass
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"OCR识别失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return f"识别失败: {e}"
    
    def extract_question_text(self, ocr_text):
        """从OCR结果中提取题目文本"""
        if not ocr_text:
            return ""
        
        # 如果是纯Python OCR的提示信息，返回空字符串，让用户手动输入
        if "[纯Python OCR识别结果]" in ocr_text:
            return ""
        
        # 去除多余空白
        text = re.sub(r'\s+', ' ', ocr_text).strip()
        
        # 如果文本太长，取前500个字符
        if len(text) > 500:
            text = text[:500]
        
        return text
    
    def __del__(self):
        """释放资源"""
        pass


# 全局单例
_engine_instance = None

def get_ocr_engine():
    """获取OCR引擎单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PythonOCREngine()
    return _engine_instance
