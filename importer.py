# -*- coding: utf-8 -*-
"""
题库导入模块 - 支持Excel/CSV格式导入
兼容刷刷题APP的导入格式：题型、题目、选项、答案、解析
使用openpyxl读取Excel（不依赖pandas）
"""
import os
import re
import csv
from config import IMPORT, EXPORT_DIR
from question_bank import get_question_bank
from search_engine import get_search_engine


class QuestionImporter:
    """题库导入器"""

    def __init__(self):
        self.bank = get_question_bank()
        self.search_engine = get_search_engine()

    def import_file(self, file_path, subject='', source=''):
        """
        导入题库文件
        :param file_path: 文件路径（.xlsx/.xls/.csv）
        :param subject: 科目名称
        :param source: 来源标记
        :return: (成功数量, 失败数量, 错误信息)
        """
        if not os.path.exists(file_path):
            return 0, 0, f"文件不存在: {file_path}"

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in IMPORT["supported_formats"]:
            return 0, 0, f"不支持的文件格式: {ext}"

        try:
            if ext in ['.xlsx', '.xls']:
                questions = self._parse_excel(file_path)
            elif ext == '.csv':
                questions = self._parse_csv(file_path)
            else:
                return 0, 0, f"不支持的文件格式: {ext}"
        except Exception as e:
            return 0, 0, f"解析文件失败: {e}"

        if not questions:
            return 0, 0, "未解析到有效题目"

        # 添加科目和来源
        for q in questions:
            if subject:
                q['subject'] = subject
            if source:
                q['source'] = source

        # 批量导入
        success_count = self.bank.add_questions_batch(questions)
        fail_count = len(questions) - success_count

        # 重建搜索索引
        if success_count > 0:
            self.search_engine.rebuild_index()

        return success_count, fail_count, ""

    def _parse_excel(self, file_path):
        """解析Excel文件（使用openpyxl，不依赖pandas）"""
        from openpyxl import load_workbook

        wb = load_workbook(filename=file_path, read_only=True)
        ws = wb.active

        # 读取所有行
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []

        # 第一行是表头
        headers = [str(h).strip() if h else '' for h in rows[0]]
        data_rows = rows[1:]

        # 列名映射（支持中英文）
        column_mapping = {
            '题型': 'question_type',
            'type': 'question_type',
            '题目': 'question_text',
            '题干': 'question_text',
            'question': 'question_text',
            '选项': 'options',
            'options': 'options',
            '答案': 'answer',
            'answer': 'answer',
            '解析': 'analysis',
            'analysis': 'analysis',
            '科目': 'subject',
            'subject': 'subject',
            '年份': 'year',
            'year': 'year',
            '来源': 'source',
            'source': 'source',
        }

        # 建立列索引映射
        col_index = {}
        for idx, header in enumerate(headers):
            for col_name, field_name in column_mapping.items():
                if header == col_name:
                    col_index[field_name] = idx
                    break

        questions = []
        for row in data_rows:
            q = {}
            for field_name, idx in col_index.items():
                if idx < len(row):
                    value = row[idx]
                    if value is not None and str(value).strip():
                        q[field_name] = str(value).strip()

            # 验证必填字段
            if 'question_text' not in q or not q['question_text']:
                continue
            if 'answer' not in q or not q['answer']:
                continue

            # 清理答案（只保留A-D字母）
            q['answer'] = self._clean_answer(q['answer'])

            # 默认题型
            if 'question_type' not in q or not q['question_type']:
                q['question_type'] = '单选题' if len(q['answer']) == 1 else '多选题'

            questions.append(q)

        wb.close()
        return questions

    def _parse_csv(self, file_path):
        """解析CSV文件"""
        # 尝试多种编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
            try:
                questions = self._parse_csv_with_encoding(file_path, encoding)
                if questions:
                    return questions
            except UnicodeDecodeError:
                continue
        else:
            raise RuntimeError("无法识别CSV文件编码")

    def _parse_csv_with_encoding(self, file_path, encoding):
        """用指定编码解析CSV"""
        questions = []

        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)

            # 列名映射
            column_mapping = {
                '题型': 'question_type',
                'type': 'question_type',
                '题目': 'question_text',
                '题干': 'question_text',
                'question': 'question_text',
                '选项': 'options',
                'options': 'options',
                '答案': 'answer',
                'answer': 'answer',
                '解析': 'analysis',
                'analysis': 'analysis',
                '科目': 'subject',
                'subject': 'subject',
                '年份': 'year',
                'year': 'year',
                '来源': 'source',
                'source': 'source',
            }

            for row in reader:
                q = {}
                for col_name, field_name in column_mapping.items():
                    if col_name in row and row[col_name]:
                        q[field_name] = str(row[col_name]).strip()

                # 验证必填字段
                if 'question_text' not in q or not q['question_text']:
                    continue
                if 'answer' not in q or not q['answer']:
                    continue

                # 清理答案
                q['answer'] = self._clean_answer(q['answer'])

                # 默认题型
                if 'question_type' not in q or not q['question_type']:
                    q['question_type'] = '单选题' if len(q['answer']) == 1 else '多选题'

                questions.append(q)

        return questions

    def _clean_answer(self, answer):
        """清理答案，只保留A-D字母"""
        if not answer:
            return ''
        letters = re.findall(r'[A-D]', answer.upper())
        return ''.join(sorted(set(letters)))

    def export_template(self, output_path=None):
        """
        导出题库导入模板
        """
        from openpyxl import Workbook

        if output_path is None:
            output_path = os.path.join(EXPORT_DIR, "题库导入模板.xlsx")

        # 创建工作簿
        wb = Workbook()
        ws = wb.active
        ws.title = "题库模板"

        # 写入表头
        headers = ['题型', '题目', '选项', '答案', '解析']
        ws.append(headers)

        # 写入示例数据
        ws.append([
            '单选题',
            '根据《安全生产法》，生产经营单位的主要负责人对本单位安全生产工作负有的职责不包括（）',
            'A.建立健全并落实本单位全员安全生产责任制|B.组织制定并实施本单位安全生产规章制度和操作规程|C.组织制定并实施本单位安全生产教育和培训计划|D.直接负责本单位的日常安全检查工作',
            'D',
            '根据《安全生产法》第二十一条，主要负责人职责包括ABC选项，D选项属于安全生产管理人员职责。',
        ])

        ws.append([
            '多选题',
            '下列属于从业人员安全生产权利的有（）',
            'A.知情权|B.建议权|C.批评检举控告权|D.拒绝违章指挥权',
            'ABCD',
            '根据《安全生产法》，从业人员享有知情权、建议权、批评检举控告权、拒绝违章指挥权、紧急避险权等。',
        ])

        # 保存
        wb.save(output_path)
        wb.close()
        return output_path


# 单例模式
_importer = None

def get_importer():
    global _importer
    if _importer is None:
        _importer = QuestionImporter()
    return _importer
