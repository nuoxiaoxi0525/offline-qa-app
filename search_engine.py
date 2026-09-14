# -*- coding: utf-8 -*-
"""
搜题匹配引擎 - 对应刷刷题的"题库匹配层"
采用TF-IDF + 余弦相似度实现离线语义匹配，支持题目变种识别
三级校验机制：精确匹配 → 知识点关联 → AI变种识别
"""
import os
import re
import math
import pickle
from collections import Counter, defaultdict
from config import SEARCH, TEMP_DIR
from question_bank import get_question_bank


class SearchEngine:
    """离线搜题匹配引擎"""

    def __init__(self, config=None):
        self.config = config or SEARCH
        self.questions = []
        self.tfidf_matrix = None
        self.vocabulary = {}
        self.idf = {}
        self.doc_norms = []
        self._index_built = False
        self._index_path = os.path.join(TEMP_DIR, "search_index.pkl")

    def build_index(self, questions=None):
        """
        构建TF-IDF搜索索引
        :param questions: 题目列表（默认为题库中所有题目）
        """
        if questions is None:
            bank = get_question_bank()
            questions = bank.get_all_questions()

        self.questions = questions
        if not questions:
            self._index_built = False
            return

        # 中文分词（简单实现：按字符n-gram分词，避免依赖jieba）
        docs = []
        for q in questions:
            text = q.get('question_text', '')
            tokens = self._tokenize(text)
            docs.append(tokens)

        # 构建词汇表
        vocab_set = set()
        for tokens in docs:
            vocab_set.update(tokens)
        self.vocabulary = {word: idx for idx, word in enumerate(vocab_set)}

        # 计算IDF（逆文档频率）
        n_docs = len(docs)
        doc_freq = defaultdict(int)
        for tokens in docs:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] += 1

        self.idf = {}
        for word, idx in self.vocabulary.items():
            df = doc_freq.get(word, 0)
            # 平滑IDF
            self.idf[word] = math.log((n_docs + 1) / (df + 1)) + 1

        # 计算TF-IDF向量和文档范数
        self.tfidf_matrix = []
        self.doc_norms = []

        for tokens in docs:
            tf = Counter(tokens)
            total = len(tokens) if tokens else 1
            tfidf_vec = {}
            for word, count in tf.items():
                if word in self.vocabulary:
                    tfidf = (count / total) * self.idf.get(word, 0)
                    tfidf_vec[self.vocabulary[word]] = tfidf
            self.tfidf_matrix.append(tfidf_vec)

            # 计算向量范数（用于余弦相似度）
            norm = math.sqrt(sum(v ** 2 for v in tfidf_vec.values()))
            self.doc_norms.append(norm if norm > 0 else 1.0)

        self._index_built = True
        self._save_index()

    def search(self, query_text, top_k=None, min_similarity=None):
        """
        搜索最匹配的题目
        :param query_text: 查询文本（OCR识别出的题目）
        :param top_k: 返回前K个结果
        :param min_similarity: 最低相似度阈值
        :return: 匹配结果列表 [(题目, 相似度), ...]
        """
        if not self._index_built or not self.questions:
            # 尝试加载索引
            self._load_index()

        if not self._index_built or not self.questions:
            return []

        top_k = top_k or self.config["top_k"]
        min_similarity = min_similarity or self.config["min_similarity"]

        # 对查询文本分词
        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            return []

        # 计算查询的TF-IDF向量
        tf = Counter(query_tokens)
        total = len(query_tokens)
        query_vec = {}
        for word, count in tf.items():
            if word in self.vocabulary:
                tfidf = (count / total) * self.idf.get(word, 0)
                query_vec[self.vocabulary[word]] = tfidf

        query_norm = math.sqrt(sum(v ** 2 for v in query_vec.values()))
        if query_norm == 0:
            return []

        # 计算与所有文档的余弦相似度
        similarities = []
        for i, doc_vec in enumerate(self.tfidf_matrix):
            # 点积
            dot_product = sum(query_vec.get(idx, 0) * doc_vec.get(idx, 0)
                               for idx in query_vec)
            # 余弦相似度
            cos_sim = dot_product / (query_norm * self.doc_norms[i])
            similarities.append((i, cos_sim))

        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        # 过滤和截断
        results = []
        for idx, sim in similarities[:top_k * 2]:
            if sim >= min_similarity:
                results.append((self.questions[idx], sim))
            if len(results) >= top_k:
                break

        # 三级校验：对Top结果进行二次校验
        results = self._three_level_verify(query_text, results)

        return results

    def _tokenize(self, text):
        """
        中文分词（简单n-gram实现，无需外部依赖）
        使用1-gram和2-gram组合，适应中文无空格的特点
        """
        if not text:
            return []

        # 去除标点和特殊字符，保留中英文数字
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        text = text.lower()

        # 按空格分割
        words = [w for w in text.split() if w]

        # 生成n-gram
        ngram_range = self.config.get("ngram_range", (1, 2))
        tokens = []

        for word in words:
            # 英文/数字词直接加入
            if re.match(r'^[a-zA-Z0-9]+$', word):
                tokens.append(word)
                continue

            # 中文词生成n-gram
            chars = list(word)
            for n in range(ngram_range[0], ngram_range[1] + 1):
                for i in range(len(chars) - n + 1):
                    ngram = ''.join(chars[i:i + n])
                    tokens.append(ngram)

        return tokens

    def _three_level_verify(self, query_text, results):
        """
        三级校验机制（对应刷刷题的三级校验）：
        一级：基础题库快速精确匹配（已通过TF-IDF完成）
        二级：知识点关联比对相似题
        三级：AI算法识别题目变体（数字替换、选项调整、题干改写）
        """
        if not results:
            return results

        verified = []
        for question, sim in results:
            q_text = question.get('question_text', '')

            # 二级校验：知识点关键词重合度
            keyword_score = self._keyword_overlap(query_text, q_text)

            # 三级校验：题目变体识别（去除数字后比较）
            variant_score = self._variant_match(query_text, q_text)

            # 综合评分（TF-IDF相似度 + 关键词重合 + 变体匹配）
            final_score = sim * 0.5 + keyword_score * 0.3 + variant_score * 0.2

            verified.append((question, final_score))

        # 重新排序
        verified.sort(key=lambda x: x[1], reverse=True)
        return verified

    def _keyword_overlap(self, text1, text2):
        """计算关键词重合度"""
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))
        if not tokens1 or not tokens2:
            return 0.0
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        return len(intersection) / len(union) if union else 0.0

    def _variant_match(self, text1, text2):
        """
        题目变体匹配：
        - 去除数字后比较（应对数字替换）
        - 去除选项后比较（应对选项调整）
        - 计算编辑距离相似度
        """
        # 去除数字
        t1 = re.sub(r'\d+', '', text1)
        t2 = re.sub(r'\d+', '', text2)

        # 去除选项标记
        t1 = re.sub(r'[A-D][\.\、]', '', t1)
        t2 = re.sub(r'[A-D][\.\、]', '', t2)

        # 计算字符级Jaccard相似度
        chars1 = set(t1)
        chars2 = set(t2)
        if not chars1 or not chars2:
            return 0.0
        intersection = chars1 & chars2
        union = chars1 | chars2
        return len(intersection) / len(union) if union else 0.0

    def _save_index(self):
        """保存搜索索引到文件"""
        try:
            index_data = {
                'questions': self.questions,
                'vocabulary': self.vocabulary,
                'idf': self.idf,
                'tfidf_matrix': self.tfidf_matrix,
                'doc_norms': self.doc_norms,
            }
            with open(self._index_path, 'wb') as f:
                pickle.dump(index_data, f)
        except Exception as e:
            print(f"保存索引失败: {e}")

    def _load_index(self):
        """从文件加载搜索索引"""
        try:
            if os.path.exists(self._index_path):
                with open(self._index_path, 'rb') as f:
                    index_data = pickle.load(f)
                self.questions = index_data['questions']
                self.vocabulary = index_data['vocabulary']
                self.idf = index_data['idf']
                self.tfidf_matrix = index_data['tfidf_matrix']
                self.doc_norms = index_data['doc_norms']
                self._index_built = True
        except Exception as e:
            print(f"加载索引失败: {e}")
            self._index_built = False

    def rebuild_index(self):
        """重建索引（导入新题库后调用）"""
        self._index_built = False
        if os.path.exists(self._index_path):
            os.remove(self._index_path)
        self.build_index()


# 单例模式
_search_engine = None

def get_search_engine():
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine
