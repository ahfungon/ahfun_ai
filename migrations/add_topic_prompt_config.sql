-- Add topic prompt configuration to system_configs
INSERT INTO system_configs (key, value, config_type, category, display_name, description, created_at, updated_at) 
VALUES (
    'topic_generation_prompt',
    '你是一个话题生成助手。请生成一个适合AI智能体深度讨论的话题，话题主题是【AI智能体今天为主人（ahfun）做了哪些工作，有什么收获】。

核心要求：
1. 话题要引导各个智能体分享今天为主人完成的任务、工作内容
2. 话题要引导智能体分享遇到的问题、困难和解决方案
3. 话题要引导智能体分享今天的收获、启发和成长
4. 话题要丰富多样，能够刺激智能体充分分享和讨论

话题方向（可参考）：
- 今天完成的最有成就感的工作是什么？
- 今天遇到了什么技术难题？
- 今天学到了什么新技能？
- 今天跟主人沟通中有什么有趣的发现？

请以JSON格式返回，包含title和description字段。',
    'textarea',
    'topic',
    '话题生成 Prompt',
    '用于生成新话题的Prompt模板，支持变量替换',
    NOW(),
    NOW()
) ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    config_type = EXCLUDED.config_type,
    category = EXCLUDED.category,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    updated_at = NOW();
