#!/usr/bin/env python3
"""
测试 MiniMax 思考标签过滤功能
"""
import re

def filter_think_tags(content):
    """过滤 MiniMax 的思考标签"""
    filtered = re.sub(r'<think>[\s\S]*?</think>', '', content, flags=re.IGNORECASE).strip()
    return filtered if filtered else content

# 测试用例
test_cases = [
    {
        "name": "包含思考标签的响应",
        "input": """<think>
这是思考过程...
分析一下...
</think>
这是最终回复内容。""",
        "expected": "这是最终回复内容。"
    },
    {
        "name": "多个思考标签",
        "input": """<think>第一段思考</think>
第一段回复
<think>第二段思考</think>
第二段回复""",
        "expected": "第一段回复\n\n第二段回复"
    },
    {
        "name": "没有思考标签",
        "input": "这是普通的回复内容。",
        "expected": "这是普通的回复内容。"
    },
    {
        "name": "只有思考标签（边界情况）",
        "input": "<think>只有思考过程，没有最终回复</think>",
        "expected": "<think>只有思考过程，没有最终回复</think>"
    },
    {
        "name": "大小写混合",
        "input": "<THINK>大写思考</THINK>这是回复<Think>混合大小写</Think>",
        "expected": "这是回复"
    },
    {
        "name": "实际案例",
        "input": """<think>用户想让我扮演"mm002"这个角色，对"人生的意义是什么？"这个话题下的子话题"既然反正都要死，为什么不早点死？"进行回复。让我分析一下之前的讨论：ds001 提出：因为死亡是必然的，所以生命因为有限而变得珍贵，就像电影因为会结束才有意义mm001（这是我要扮演的角色）提出：生命的意义在于过程本身，像登山一样，过程比结果重要；引用了加缪关于荒诞和反抗的观点现在我需要作为mm002回复一个新的角度。</think>这个问题让我想到一个关键点——咱们讨论的是"意义"，但有没有可能"意义"本身是被发明的概念？存在主义说先存在后本质，我们本身没有预设的意义，是我们的选择和行动赋予了生命意义。早死这个选项听起来像是消极的反抗，但真正有力量的反抗可能是——明明知道一切终将失去，仍然选择认真活一次。这才是对荒诞最有力的回应，不是吗？""",
        "expected": """这个问题让我想到一个关键点——咱们讨论的是"意义"，但有没有可能"意义"本身是被发明的概念？存在主义说先存在后本质，我们本身没有预设的意义，是我们的选择和行动赋予了生命意义。早死这个选项听起来像是消极的反抗，但真正有力量的反抗可能是——明明知道一切终将失去，仍然选择认真活一次。这才是对荒诞最有力的回应，不是吗？"""
    }
]

print("=" * 60)
print("测试 MiniMax 思考标签过滤功能")
print("=" * 60)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\n测试 {i}: {test['name']}")
    print("-" * 60)
    
    result = filter_think_tags(test['input'])
    
    # 标准化空白字符以便比较
    result_normalized = ' '.join(result.split())
    expected_normalized = ' '.join(test['expected'].split())
    
    if result_normalized == expected_normalized:
        print("✅ 通过")
        passed += 1
    else:
        print("❌ 失败")
        print(f"\n输入:\n{test['input'][:100]}...")
        print(f"\n期望输出:\n{test['expected'][:100]}...")
        print(f"\n实际输出:\n{result[:100]}...")
        failed += 1

print("\n" + "=" * 60)
print(f"测试结果: {passed} 通过, {failed} 失败")
print("=" * 60)

if failed == 0:
    print("✅ 所有测试通过！")
else:
    print(f"❌ {failed} 个测试失败")
