# -*- coding: utf-8 -*-
"""
题库导入模块 - 支持Excel/CSV格式导入
兼容刷刷题APP的导入格式：题型、题目、选项、答案、解析
"""
import os
import re
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
        """解析Excel文件"""
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("需要安装pandas和openpyxl: pip install pandas openpyxl")

        df = pd.read_excel(file_path)
        return self._parse_dataframe(df)

    def _parse_csv(self, file_path):
        """解析CSV文件"""
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("需要安装pandas: pip install pandas")

        # 尝试多种编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise RuntimeError("无法识别CSV文件编码")

        return self._parse_dataframe(df)

    def _parse_dataframe(self, df):
        """将DataFrame解析为题目列表"""
        import pandas as pd
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

        # 标准化列名
        df.columns = [str(col).strip() for col in df.columns]

        questions = []
        for _, row in df.iterrows():
            q = {}
            for col_name, field_name in column_mapping.items():
                if col_name in df.columns:
                    value = row[col_name]
                    if pd.notna(value):
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
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("需要安装pandas和openpyxl")

        if output_path is None:
            output_path = os.path.join(EXPORT_DIR, "题库导入模板.xlsx")

        # 模板数据
        template_data = [
            {
                '题型': '单选题',
                '题目': '根据《安全生产法》，生产经营单位的主要负责人对本单位安全生产工作负有的职责不包括（）',
                '选项': 'A.建立健全并落实本单位全员安全生产责任制|B.组织制定并实施本单位安全生产规章制度和操作规程|C.组织制定并实施本单位安全生产教育和培训计划|D.直接负责本单位的日常安全检查工作',
                '答案': 'D',
                '解析': '根据《安全生产法》第二十一条，主要负责人职责包括ABC选项，D选项属于安全生产管理人员职责。',
            },
            {
                '题型': '多选题',
                '题目': '下列属于从业人员安全生产权利的有（）',
                '选项': 'A.知情权|B.建议权|C.批评检举控告权|D.拒绝违章指挥权',
                '答案': 'ABCD',
                '解析': '根据《安全生产法》，从业人员享有知情权、建议权、批评检举控告权、拒绝违章指挥权、紧急避险权等。',
            },
        ]

        df = pd.DataFrame(template_data, columns=['题型', '题目', '选项', '答案', '解析'])
        df.to_excel(output_path, index=False)
        return output_path


# 单例模式
_importer = None

def get_importer():
    global _importer
    if _importer is None:
        _importer = QuestionImporter()
    return _importer
