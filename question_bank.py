# -*- coding: utf-8 -*-
"""
题库管理模块 - SQLite数据库存储
支持题目增删改查、分类管理、导入导出
"""
import sqlite3
import os
import json
import re
from config import DB_PATH


class QuestionBank:
    """题库管理器"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # 题目表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT DEFAULT '',
                year TEXT DEFAULT '',
                source TEXT DEFAULT '',
                question_type TEXT DEFAULT '单选题',
                question_text TEXT NOT NULL,
                options TEXT DEFAULT '',
                answer TEXT NOT NULL,
                analysis TEXT DEFAULT '',
                difficulty INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 科目表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                question_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_year ON questions(year)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(question_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_text ON questions(question_text)')

        conn.commit()
        conn.close()

    def add_question(self, question_text, answer, question_type='单选题',
                     options='', analysis='', subject='', year='', source=''):
        """
        添加单道题目
        :return: 题目ID
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO questions (subject, year, source, question_type,
                                   question_text, options, answer, analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (subject, year, source, question_type,
              question_text, options, answer, analysis))

        question_id = cursor.lastrowid

        # 更新科目题目计数
        if subject:
            cursor.execute('''
                INSERT OR IGNORE INTO subjects (name, question_count) VALUES (?, 0)
            ''', (subject,))
            cursor.execute('''
                UPDATE subjects SET question_count = question_count + 1 WHERE name = ?
            ''', (subject,))

        conn.commit()
        conn.close()
        return question_id

    def add_questions_batch(self, questions):
        """
        批量添加题目
        :param questions: 题目字典列表
        :return: 成功添加的数量
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        count = 0

        for q in questions:
            try:
                cursor.execute('''
                    INSERT INTO questions (subject, year, source, question_type,
                                           question_text, options, answer, analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    q.get('subject', ''),
                    q.get('year', ''),
                    q.get('source', ''),
                    q.get('question_type', q.get('题型', '单选题')),
                    q.get('question_text', q.get('题目', '')),
                    q.get('options', q.get('选项', '')),
                    q.get('answer', q.get('答案', '')),
                    q.get('analysis', q.get('解析', '')),
                ))
                count += 1

                # 更新科目计数
                subject = q.get('subject', '')
                if subject:
                    cursor.execute('''
                        INSERT OR IGNORE INTO subjects (name, question_count) VALUES (?, 0)
                    ''', (subject,))
                    cursor.execute('''
                        UPDATE subjects SET question_count = question_count + 1 WHERE name = ?
                    ''', (subject,))
            except Exception as e:
                print(f"添加题目失败: {e}")
                continue

        conn.commit()
        conn.close()
        return count

    def get_question(self, question_id):
        """根据ID获取题目"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM questions WHERE id = ?', (question_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def search_questions(self, keyword, subject=None, year=None,
                         question_type=None, limit=100, offset=0):
        """
        关键词搜索题目
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        query = 'SELECT * FROM questions WHERE question_text LIKE ?'
        params = [f'%{keyword}%']

        if subject:
            query += ' AND subject = ?'
            params.append(subject)
        if year:
            query += ' AND year = ?'
            params.append(year)
        if question_type:
            query += ' AND question_type = ?'
            params.append(question_type)

        query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_questions(self, subject=None, limit=None):
        """获取所有题目（用于构建搜索索引）"""
        conn = self._get_conn()
        cursor = conn.cursor()

        if subject:
            cursor.execute('SELECT * FROM questions WHERE subject = ? ORDER BY id', (subject,))
        else:
            cursor.execute('SELECT * FROM questions ORDER BY id')

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_subjects(self):
        """获取所有科目及题目数量"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subjects ORDER BY name')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_statistics(self):
        """获取题库统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as total FROM questions')
        total = cursor.fetchone()['total']

        cursor.execute('''
            SELECT question_type, COUNT(*) as count
            FROM questions GROUP BY question_type
        ''')
        type_stats = {row['question_type']: row['count'] for row in cursor.fetchall()}

        cursor.execute('''
            SELECT subject, COUNT(*) as count
            FROM questions GROUP BY subject ORDER BY count DESC
        ''')
        subject_stats = {row['subject']: row['count'] for row in cursor.fetchall()}

        conn.close()
        return {
            'total': total,
            'by_type': type_stats,
            'by_subject': subject_stats,
        }

    def delete_question(self, question_id):
        """删除题目"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def clear_subject(self, subject):
        """清空指定科目的所有题目"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM questions WHERE subject = ?', (subject,))
        cursor.execute('DELETE FROM subjects WHERE name = ?', (subject,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        return deleted

    def export_to_json(self, subject=None):
        """导出题库为JSON"""
        questions = self.get_all_questions(subject)
        return json.dumps(questions, ensure_ascii=False, indent=2)


# 单例模式
_question_bank = None

def get_question_bank():
    global _question_bank
    if _question_bank is None:
        _question_bank = QuestionBank()
    return _question_bank
