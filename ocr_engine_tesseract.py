# -*- coding: utf-8 -*-
"""
Tesseract OCR引擎 - 使用Tesseract Android库
通过jnius调用Tesseract API，完全离线运行，兼容性好
"""
import os
import re

# 尝试导入jnius（仅在Android上可用）
try:
    from jnius import autoclass
    _JNIUS_AVAILABLE = True
except ImportError:
    _JNIUS_AVAILABLE = False

from config import MODEL_DIR


class TesseractOCREngine:
    """Tesseract OCR引擎，完全离线运行"""
    
    def __init__(self):
        self.base_api = None
        self._initialized = False
        self._tessdata_path = None
    
    def _initialize(self):
        """延迟初始化Tesseract"""
        if self._initialized:
            return
        
        if not _JNIUS_AVAILABLE:
            raise RuntimeError("jnius不可用，只能在Android设备上使用此OCR引擎")
        
        error_details = []
        
        try:
            # 获取Android Context
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            
            # 获取APP私有目录
            files_dir = context.getFilesDir().getAbsolutePath()
            self._tessdata_path = os.path.join(files_dir, 'tessdata')
            
            # 创建tessdata目录
            if not os.path.exists(self._tessdata_path):
                os.makedirs(self._tessdata_path, exist_ok=True)
            
            error_details.append(f"tessdata目录: {self._tessdata_path}")
            
            # 列出assets目录中的所有文件（调试用）
            try:
                asset_manager = context.getAssets()
                asset_files = list(asset_manager.list(''))
                error_details.append(f"assets根目录文件({len(asset_files)}): {asset_files[:30]}")
                
                # 尝试列出tessdata子目录
                try:
                    tessdata_files = list(asset_manager.list('tessdata'))
                    error_details.append(f"assets/tessdata文件: {tessdata_files}")
                except Exception as e:
                    error_details.append(f"列出assets/tessdata失败: {e}")
            except Exception as e:
                error_details.append(f"列出assets失败: {e}")
            
            # 检查语言包是否存在，如果不存在则从assets复制
            lang_file = os.path.join(self._tessdata_path, 'chi_sim.traineddata')
            if not os.path.exists(lang_file):
                error_details.append("语言包不存在，尝试从assets复制")
                self._copy_language_data(context, error_details)
            else:
                file_size = os.path.getsize(lang_file)
                error_details.append(f"语言包已存在，大小: {file_size} 字节")
            
            # 初始化Tesseract - 尝试多个可能的包名
            tess_class = None
            package_names = [
                'com.googlecode.tesseract.android.TessBaseAPI',
                'cz.adaptech.tesseract4android.TessBaseAPI',
                'com.google.tesseract.android.TessBaseAPI',
            ]
            
            for pkg in package_names:
                try:
                    tess_class = autoclass(pkg)
                    error_details.append(f"成功加载Tesseract类: {pkg}")
                    break
                except Exception as e:
                    error_details.append(f"加载类失败 {pkg}: {str(e)[:100]}")
            
            if tess_class is None:
                raise RuntimeError("无法加载任何Tesseract类")
            
            self.base_api = tess_class()
            error_details.append("TessBaseAPI实例创建成功")
            
            # 初始化
            success = self.base_api.init(files_dir, 'chi_sim')
            error_details.append(f"init返回值: {success}")
            
            if not success:
                error_details.append("Tesseract初始化失败，init返回False")
                raise RuntimeError("\n".join(error_details))
            
            # 设置Page Segmentation Mode（自动检测段落）
            self.base_api.setPageSegMode(3)  # PSM_AUTO
            
            self._initialized = True
            error_details.append("Tesseract初始化成功")
            print("\n".join(error_details))
            
        except Exception as e:
            import traceback
            error_detail = "\n".join(error_details)
            error_detail += f"\n异常: {str(e)}"
            error_detail += f"\n{traceback.format_exc()}"
            # 把错误信息写入文件
            try:
                log_path = os.path.join(files_dir, 'ocr_error.log')
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(error_detail)
                error_detail += f"\n错误日志已保存到: {log_path}"
            except:
                pass
            raise RuntimeError(f"Tesseract OCR引擎初始化失败:\n{error_detail}")
    
    def _copy_language_data(self, context, error_details):
        """从assets目录复制语言包到私有目录"""
        try:
            asset_manager = context.getAssets()
            
            # 查找语言包文件 - 优先从fonts目录查找（已确认能被打包）
            lang_file_name = None
            search_paths = ['fonts', '', 'tessdata', 'assets', 'data']
            
            for path in search_paths:
                try:
                    files = list(asset_manager.list(path))
                    error_details.append(f"assets/{path}文件列表: {files[:20]}")
                    for f in files:
                        if f.endswith('.traineddata'):
                            if path:
                                lang_file_name = os.path.join(path, f)
                            else:
                                lang_file_name = f
                            error_details.append(f"在assets/{path}找到语言包: {f}")
                            break
                    if lang_file_name:
                        break
                except Exception as e:
                    error_details.append(f"搜索assets/{path}失败: {e}")
            
            if lang_file_name is None:
                # 列出所有assets文件帮助调试
                all_files = []
                try:
                    all_files = list(asset_manager.list(''))
                except:
                    pass
                raise RuntimeError(f"在assets中未找到语言包文件(.traineddata)。assets文件: {all_files}")
            
            # 复制文件
            input_stream = asset_manager.open(lang_file_name)
            output_path = os.path.join(self._tessdata_path, 'chi_sim.traineddata')
            
            total_bytes = 0
            with open(output_path, 'wb') as output:
                buffer = bytearray(8192)
                while True:
                    read = input_stream.read(buffer)
                    if read == -1:
                        break
                    output.write(buffer[:read])
                    total_bytes += read
            
            input_stream.close()
            error_details.append(f"语言包复制完成，大小: {total_bytes} 字节")
            
            # 验证文件大小
            if total_bytes < 1000000:
                raise RuntimeError(f"语言包文件太小: {total_bytes} 字节")
            
        except Exception as e:
            raise RuntimeError(f"复制语言包失败: {e}")
    
    def recognize(self, image_path):
        """识别图片中的文字"""
        self._initialize()
        
        try:
            # 加载图片为Bitmap
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            bitmap = BitmapFactory.decodeFile(image_path)
            
            if bitmap is None:
                raise RuntimeError(f"无法加载图片: {image_path}")
            
            # 设置图片
            self.base_api.setImage(bitmap)
            
            # 获取识别结果
            result_text = self.base_api.getUTF8Text()
            
            # 回收
            self.base_api.clear()
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
    
    def __del__(self):
        """释放资源"""
        if self.base_api is not None:
            try:
                self.base_api.end()
            except:
                pass


# 全局单例
_engine_instance = None

def get_ocr_engine():
    """获取OCR引擎单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TesseractOCREngine()
    return _engine_instance
