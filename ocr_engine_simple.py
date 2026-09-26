# -*- coding: utf-8 -*-
"""
简化版OCR引擎 - 直接使用onnxruntime运行PP-OCRv3模型
不依赖opencv，使用Pillow和numpy进行图像处理
"""
import os
import re
import numpy as np
from PIL import Image

try:
    import onnxruntime as ort
except ImportError:
    ort = None

from config import MODEL_DIR


# PP-OCRv3 中文字典（简化版，包含常用字符）
# 完整字典有6623个字符，这里使用一个简化版
CHAR_DICT = list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ")
# 添加常用中文标点和符号
CHAR_DICT += list("，。！？、；：""''（）【】《》—…·")
# 添加常用汉字（这里只添加一部分，实际使用时需要完整字典）
COMMON_CHARS = "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严龙飞"
CHAR_DICT += list(COMMON_CHARS)
# 去重
CHAR_DICT = list(dict.fromkeys(CHAR_DICT))
# 添加blank标记（CTC解码用）
CHAR_DICT = ['blank'] + CHAR_DICT

CHAR_TO_IDX = {char: idx for idx, char in enumerate(CHAR_DICT)}
IDX_TO_CHAR = {idx: char for idx, char in enumerate(CHAR_DICT)}


class SimpleOCREngine:
    """简化版OCR引擎，直接使用onnxruntime"""
    
    def __init__(self):
        self.det_session = None
        self.rec_session = None
        self.cls_session = None
        self._initialized = False
    
    def _initialize(self):
        """延迟初始化模型"""
        if self._initialized:
            return
        
        if ort is None:
            raise RuntimeError("onnxruntime未安装")
        
        # 查找模型文件
        det_model = None
        rec_model = None
        cls_model = None
        
        for f in os.listdir(MODEL_DIR):
            if 'det' in f.lower() and f.endswith('.onnx'):
                det_model = os.path.join(MODEL_DIR, f)
            elif 'rec' in f.lower() and f.endswith('.onnx'):
                rec_model = os.path.join(MODEL_DIR, f)
            elif 'cls' in f.lower() and f.endswith('.onnx'):
                cls_model = os.path.join(MODEL_DIR, f)
        
        if not det_model or not rec_model:
            raise RuntimeError(f"模型文件未找到: det={det_model}, rec={rec_model}")
        
        # 创建推理会话
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        self.det_session = ort.InferenceSession(det_model, so)
        self.rec_session = ort.InferenceSession(rec_model, so)
        if cls_model:
            self.cls_session = ort.InferenceSession(cls_model, so)
        
        self._initialized = True
        print(f"OCR模型初始化成功: det={det_model}, rec={rec_model}")
    
    def _preprocess_image(self, image, target_height=640):
        """图像预处理：resize和归一化"""
        # 计算缩放比例
        h, w = image.shape[:2]
        ratio = target_height / h
        new_h = target_height
        new_w = int(w * ratio)
        # 确保宽度是32的倍数
        new_w = max(32, (new_w // 32) * 32)
        
        # 使用Pillow resize
        pil_img = Image.fromarray(image)
        pil_img = pil_img.resize((new_w, new_h), Image.BILINEAR)
        resized = np.array(pil_img)
        
        # 归一化 (RGB)
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        normalized = (resized.astype(np.float32) / 255.0 - mean) / std
        
        # HWC -> CHW
        chw = normalized.transpose(2, 0, 1)
        # 增加batch维度
        input_data = np.expand_dims(chw, axis=0).astype(np.float32)
        
        return input_data, ratio
    
    def _detect_text_boxes(self, image):
        """文本检测：使用DBNet模型检测文本框"""
        input_data, ratio = self._preprocess_image(image)
        
        # 推理
        input_name = self.det_session.get_inputs()[0].name
        output_name = self.det_session.get_outputs()[0].name
        result = self.det_session.run([output_name], {input_name: input_data})[0]
        
        # 后处理：简化版，从概率图提取文本框
        prob_map = result[0, 0]  # [H, W]
        
        # 二值化
        binary = (prob_map > 0.3).astype(np.uint8)
        
        # 简单的连通区域分析（简化版）
        # 实际应该使用更复杂的DB后处理算法
        boxes = []
        h, w = binary.shape
        
        # 使用投影法检测文本行
        # 水平投影
        row_sum = np.sum(binary, axis=1)
        rows_with_text = row_sum > (w * 0.05)  # 超过5%的像素有文本
        
        # 找到连续的文本行
        in_row = False
        row_start = 0
        for i in range(h):
            if rows_with_text[i] and not in_row:
                row_start = i
                in_row = True
            elif not rows_with_text[i] and in_row:
                # 找到一行文本
                row_end = i
                if row_end - row_start > 5:  # 最小高度
                    # 找到这一行的左右边界
                    row_region = binary[row_start:row_end, :]
                    col_sum = np.sum(row_region, axis=0)
                    cols_with_text = col_sum > 0
                    
                    # 找到左边界
                    left = 0
                    for j in range(w):
                        if cols_with_text[j]:
                            left = j
                            break
                    
                    # 找到右边界
                    right = w - 1
                    for j in range(w-1, -1, -1):
                        if cols_with_text[j]:
                            right = j
                            break
                    
                    if right - left > 10:  # 最小宽度
                        # 转换回原图坐标
                        boxes.append({
                            'bbox': [[left/ratio, row_start/ratio], 
                                    [right/ratio, row_start/ratio],
                                    [right/ratio, row_end/ratio],
                                    [left/ratio, row_end/ratio]],
                            'text': ''
                        })
                in_row = False
        
        return boxes
    
    def _recognize_text(self, image, boxes):
        """文本识别：对每个文本框进行识别"""
        results = []
        
        for box in boxes:
            bbox = box['bbox']
            # 裁剪文本区域
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            x1, y1 = int(min(x_coords)), int(min(y_coords))
            x2, y2 = int(max(x_coords)), int(max(y_coords))
            
            # 确保坐标在图像范围内
            h, w = image.shape[:2]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # 裁剪
            crop_img = image[y1:y2, x1:x2]
            
            # 预处理：高度固定48，宽度按比例缩放
            crop_h, crop_w = crop_img.shape[:2]
            target_h = 48
            ratio = target_h / crop_h
            target_w = int(crop_w * ratio)
            target_w = max(8, min(320, target_w))
            # 确保宽度是8的倍数
            target_w = (target_w // 8) * 8
            
            pil_crop = Image.fromarray(crop_img)
            pil_crop = pil_crop.resize((target_w, target_h), Image.BILINEAR)
            crop_resized = np.array(pil_crop)
            
            # 归一化
            mean = np.array([0.5, 0.5, 0.5])
            std = np.array([0.5, 0.5, 0.5])
            normalized = (crop_resized.astype(np.float32) / 255.0 - mean) / std
            
            # HWC -> CHW，增加batch维度
            chw = normalized.transpose(2, 0, 1)
            input_data = np.expand_dims(chw, axis=0).astype(np.float32)
            
            # 推理
            input_name = self.rec_session.get_inputs()[0].name
            output_name = self.rec_session.get_outputs()[0].name
            result = self.rec_session.run([output_name], {input_name: input_data})[0]
            
            # CTC解码（简化版）
            text = self._ctc_decode(result[0])
            
            if text.strip():
                results.append({
                    'bbox': bbox,
                    'text': text.strip(),
                    'confidence': 0.8  # 简化版，固定置信度
                })
        
        return results
    
    def _ctc_decode(self, output):
        """CTC解码（简化版贪心解码）"""
        # output shape: [T, num_classes]
        indices = np.argmax(output, axis=1)
        
        # 去重和去blank
        text = []
        prev_idx = -1
        for idx in indices:
            if idx != prev_idx and idx != 0:  # 0是blank
                if idx < len(IDX_TO_CHAR):
                    text.append(IDX_TO_CHAR[idx])
            prev_idx = idx
        
        return ''.join(text)
    
    def recognize(self, image_path):
        """
        对图像进行OCR识别
        :param image_path: 图像路径或numpy数组
        :return: 识别出的文本
        """
        self._initialize()
        
        # 读取图像
        if isinstance(image_path, str):
            pil_img = Image.open(image_path).convert('RGB')
            image = np.array(pil_img)
        else:
            image = image_path
        
        # 文本检测
        boxes = self._detect_text_boxes(image)
        
        if not boxes:
            return ""
        
        # 文本识别
        results = self._recognize_text(image, boxes)
        
        # 按位置排序（从上到下，从左到右）
        def sort_key(item):
            bbox = item['bbox']
            y_coords = [p[1] for p in bbox]
            x_coords = [p[0] for p in bbox]
            avg_y = sum(y_coords) / len(y_coords)
            avg_x = sum(x_coords) / len(x_coords)
            return (int(avg_y // 30), avg_x)
        
        results.sort(key=sort_key)
        
        # 合并文本
        lines = [r['text'] for r in results if r['text']]
        return '\n'.join(lines)
    
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
        _ocr_engine = SimpleOCREngine()
    return _ocr_engine
