# UI/UX Pro Max 技能 - 快速使用指南

✅ **状态**: 已激活并可用

## 环境信息
- Python 版本: 3.9.6
- 技能位置: `.kiro/steering/ui-ux-pro-max/`
- 数据库: 11 个 CSV 文件，包含 67 种样式、96 个调色板、57 个字体配对等

## 核心命令

### 1. 生成完整设计系统（最常用）

```bash
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "产品类型 行业 关键词" --design-system -p "项目名称"
```

**示例**:
```bash
# SaaS 仪表板
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "saas dashboard analytics" --design-system -p "我的项目"

# 电商网站
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "ecommerce fashion modern" --design-system -p "时尚商城"

# 美容服务
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "beauty spa wellness elegant" --design-system -p "美容院"
```

### 2. 保存设计系统（持久化）

```bash
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "查询" --design-system --persist -p "项目名称"
```

这会创建:
- `design-system/MASTER.md` - 全局设计规则
- `design-system/pages/` - 页面特定覆盖

### 3. 按领域搜索

```bash
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "关键词" --domain <领域> -n <结果数>
```

**可用领域**:
- `style` - UI 样式（玻璃态、极简等）
- `color` - 调色板
- `typography` - 字体配对
- `landing` - 落地页结构
- `chart` - 图表类型
- `ux` - UX 最佳实践

**示例**:
```bash
# 搜索玻璃态样式
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "glassmorphism dark" --domain style -n 3

# 搜索优雅字体
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "elegant luxury" --domain typography -n 5

# 搜索 UX 指南
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "animation accessibility" --domain ux
```

### 4. 技术栈指南

```bash
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "关键词" --stack <技术栈>
```

**可用技术栈**:
- `html-tailwind` (默认)
- `react`
- `nextjs`
- `vue`
- `svelte`
- `swiftui`
- `react-native`
- `flutter`
- `shadcn`
- `jetpack-compose`

## 典型工作流程

### 场景：创建新的 UI 页面

1. **生成设计系统**
```bash
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "你的产品描述" --design-system -p "项目名"
```

2. **获取详细 UX 指南**（可选）
```bash
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "animation hover" --domain ux
```

3. **获取技术栈最佳实践**
```bash
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "responsive layout" --stack html-tailwind
```

4. **实现设计** - 根据生成的设计系统编码

## 输出格式

```bash
# ASCII 框（默认，适合终端）
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "query" --design-system

# Markdown（适合文档）
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "query" --design-system -f markdown
```

## 专业 UI 检查清单

在交付前验证：

### 视觉质量
- [ ] 不使用 emoji 作为图标（使用 SVG）
- [ ] 所有图标来自一致的图标集（Heroicons/Lucide）
- [ ] 品牌 logo 正确
- [ ] hover 状态不会导致布局偏移

### 交互
- [ ] 所有可点击元素有 `cursor-pointer`
- [ ] hover 状态提供清晰的视觉反馈
- [ ] 过渡动画流畅（150-300ms）

### 明暗模式
- [ ] 浅色模式文本对比度充足（4.5:1 最小）
- [ ] 玻璃/透明元素在浅色模式下可见
- [ ] 边框在两种模式下都可见

### 布局
- [ ] 浮动元素与边缘有适当间距
- [ ] 内容不会被固定导航栏遮挡
- [ ] 响应式：375px、768px、1024px、1440px

### 无障碍
- [ ] 所有图片有 alt 文本
- [ ] 表单输入有标签
- [ ] 颜色不是唯一指示器
- [ ] 尊重 `prefers-reduced-motion`

## 快速测试

验证技能是否正常工作：
```bash
python3 .kiro/steering/ui-ux-pro-max/scripts/search.py "test" --domain style -n 1
```

## 需要帮助？

直接告诉我你要做什么，例如：
- "创建一个 SaaS 仪表板的设计系统"
- "我需要一个优雅的美容院网站设计"
- "帮我找适合金融科技的配色方案"

我会自动使用这个技能为你生成专业的设计建议！
