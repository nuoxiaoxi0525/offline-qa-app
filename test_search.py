# -*- coding: utf-8 -*-
"""
测试搜题功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from question_bank import QuestionBank
from search_engine import SearchEngine
from importer import QuestionImporter


def test_search():
    print("=" * 60)
    print("测试搜题功能")
    print("=" * 60)

    # 1. 初始化题库
    print("\n【1】初始化题库...")
    bank = QuestionBank(db_path="test_question_bank.db")
    print(f"题库路径: {bank.db_path}")

    # 2. 导入测试题库（使用已有的注安题库Excel）
    print("\n【2】导入题库...")
    importer = QuestionImporter()
    importer.bank = bank
    importer.search_engine = SearchEngine()

    # 查找工作目录中的Excel文件
    work_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_files = [
        os.path.join(work_dir, "中级注安_安全生产法律法规_历年真题汇总.xlsx"),
        os.path.join(work_dir, "中级注安_安全生产管理_历年真题汇总.xlsx"),
        os.path.join(work_dir, "中级注安_安全生产技术基础_历年真题汇总.xlsx"),
        os.path.join(work_dir, "中级注安_建筑施工安全实务_历年真题汇总.xlsx"),
    ]

    total_imported = 0
    for excel_file in excel_files:
        if os.path.exists(excel_file):
            subject = os.path.basename(excel_file).replace("中级注安_", "").replace("_历年真题汇总.xlsx", "")
            print(f"  导入: {subject}...")
            success, fail, error = importer.import_file(excel_file, subject=subject)
            print(f"    成功: {success}道, 失败: {fail}道, 错误: {error}")
            total_imported += success
        else:
            print(f"  文件不存在: {excel_file}")

    print(f"  总计导入: {total_imported}道题")

    # 3. 构建搜索索引
    print("\n【3】构建搜索索引...")
    search_engine = SearchEngine()
    search_engine._index_path = "test_search_index.pkl"
    questions = bank.get_all_questions()
    print(f"  题库题目数: {len(questions)}")
    search_engine.build_index(questions)
    print(f"  词汇表大小: {len(search_engine.vocabulary)}")
    print(f"  索引构建完成")

    # 4. 测试搜索
    print("\n【4】测试搜索...")

    test_cases = [
        # 原题测试（应该能精确匹配）
        {
            "name": "原题测试-法规",
            "query": "根据《安全生产法》，生产经营单位的主要负责人对本单位安全生产工作负有的职责",
            "expect": "应匹配到安全生产法相关题目"
        },
        {
            "name": "原题测试-管理",
            "query": "某企业因产能扩大，在原危险化学品库房中间设置一道防火墙",
            "expect": "应匹配到重大危险源辨识题目"
        },
        {
            "name": "原题测试-技术",
            "query": "正确操作对锅炉的安全运行至关重要，尤其是在启动和点火升压阶段",
            "expect": "应匹配到锅炉启动安全要求题目"
        },
        # 变种测试（题干改写）
        {
            "name": "变种测试-题干改写",
            "query": "安全生产法规定生产经营单位主要负责人职责不包括哪项",
            "expect": "应能匹配到主要负责人职责题目"
        },
        # 关键词测试
        {
            "name": "关键词测试",
            "query": "劳动防护用品 未提供 罚款",
            "expect": "应匹配到劳动防护用品相关题目"
        },
        # 建筑实务测试
        {
            "name": "建筑实务测试",
            "query": "装配式建筑混凝土预制构件安装施工 现场安全管理",
            "expect": "应匹配到预制构件安装题目"
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n  测试{i}: {test['name']}")
        print(f"    查询: {test['query'][:50]}...")
        print(f"    期望: {test['expect']}")

        results = search_engine.search(test['query'], top_k=3)

        if results:
            print(f"    匹配结果（Top{len(results)}）:")
            for j, (q, sim) in enumerate(results, 1):
                q_text = q.get('question_text', '')[:60]
                answer = q.get('answer', '')
                subject = q.get('subject', '')
                print(f"      {j}. 相似度:{sim*100:.1f}% | 科目:{subject} | 答案:{answer}")
                print(f"         题目: {q_text}...")
        else:
            print(f"    未找到匹配结果")

    # 5. 统计信息
    print("\n【5】题库统计...")
    stats = bank.get_statistics()
    print(f"  总题数: {stats['total']}")
    print(f"  按题型: {stats['by_type']}")
    print(f"  按科目: {stats['by_subject']}")

    # 6. 清理测试文件
    print("\n【6】清理测试文件...")
    try:
        os.remove("test_question_bank.db")
        os.remove("test_search_index.pkl")
        print("  测试文件已清理")
    except Exception as e:
        print(f"  清理失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    test_search()
