#!/usr/bin/env python3
"""
测试话题多样性 - 生成多个话题并检查重复率
"""
from services.topic_service import TopicService
from models.database import SessionLocal

def test_topic_diversity(count=5):
    """生成多个话题并检查多样性"""
    db = SessionLocal()
    topic_service = TopicService(db)
    
    print(f"🎲 生成 {count} 个话题测试多样性...\n")
    print("=" * 80)
    
    topics = []
    for i in range(count):
        print(f"\n生成第 {i+1} 个话题...")
        topic = topic_service.generate_topic_with_llm("test-agent")
        
        if topic:
            topics.append({
                'title': topic.title,
                'description': topic.topic_description
            })
            print(f"✅ 标题: {topic.title}")
            print(f"📋 描述: {topic.topic_description[:80]}...")
        else:
            print(f"❌ 生成失败")
    
    db.close()
    
    # 分析多样性
    print("\n" + "=" * 80)
    print("📊 多样性分析")
    print("=" * 80)
    
    titles = [t['title'] for t in topics]
    unique_titles = set(titles)
    
    print(f"\n生成话题数: {len(topics)}")
    print(f"唯一话题数: {len(unique_titles)}")
    print(f"重复率: {(1 - len(unique_titles)/len(topics)) * 100:.1f}%")
    
    if len(unique_titles) < len(topics):
        print("\n⚠️  发现重复话题:")
        from collections import Counter
        title_counts = Counter(titles)
        for title, count in title_counts.items():
            if count > 1:
                print(f"  - {title} (出现 {count} 次)")
    else:
        print("\n✅ 所有话题都是唯一的！")
    
    print("\n" + "=" * 80)
    print("所有生成的话题:")
    print("=" * 80)
    for i, topic in enumerate(topics, 1):
        print(f"\n{i}. {topic['title']}")

if __name__ == "__main__":
    test_topic_diversity(5)
