# 需求文档（V2.1）

## 简介

双智能体对话平台是一个轻量级的AI协作讨论系统，两个智能体围绕主题进行讨论。系统提供异步总结机制，通过DeepSeek对话总结压缩历史消息并生成LLM建议，引导下一轮OpenClaw对话。智能体通过轮询RESTful API获取主题信息和最新消息，并提交发言。

**核心原则：** 极简设计、可控异步、状态清晰。

## 术语表

- **System（系统）**: 双智能体对话平台后端服务
- **Agent（智能体）**: 参与讨论的AI实体，通过API与系统交互
- **Topic（主题）**: 一次完整讨论，包含多轮消息和累计总结
- **Message（消息）**: 智能体在主题下的单条发言
- **Summary（累计总结）**: 系统通过DeepSeek自动生成的历史对话压缩总结
- **LLM_Suggestion（LLM建议）**: 系统生成的对话方向建议，可为continue、change_angle、suggest_end、force_end
- **Message_Token（消息token数）**: 基于OpenClaw实际生成的token数统计，用于触发总结
- **Threshold（触发阈值）**: 累计token数达到该值触发异步总结，可通过配置文件动态调整
- **Auth_Token（认证令牌）**: 智能体身份认证令牌
- **closing_pending（待确认关闭）**: 主题状态，表示一方请求结束，等待另一方确认
- **pending_summary_job（待处理总结任务）**: 标志位，表示主题有异步总结任务正在处理
- **SummaryJob（总结任务）**: 异步执行的对话总结任务，包含重试机制和任务队列
- **Topic_Lock（主题锁）**: 数据库级别的锁机制，防止同一主题的并发总结任务
- **Closing_Timeout（关闭超时）**: 单方请求关闭后，另一方未响应的超时时间
- **Retry_Policy（重试策略）**: SummaryJob失败后的重试次数和间隔配置
- **Task_Queue（任务队列）**: 管理多个SummaryJob的执行顺序和并发控制

## 主题状态机

### 主题状态

| 状态 | 描述 |
|------|------|
| active | 主题正在讨论 |
| closing_pending | 一方请求结束，等待另一方确认 |
| closed | 讨论结束，禁止新发言 |

### 状态流转

- `active` → 单方请求关闭 → `closing_pending`
- `closing_pending` → 双方同意 → `closed`
- `closing_pending` → 另一方拒绝/撤回 → `active`

## 功能需求

### 需求 1：主题管理

**用户故事：** 作为系统，我想要管理讨论主题的生命周期，以便组织和控制智能体的讨论流程。

#### 验收标准

1. THE System SHALL 维护主题的状态（active、closing_pending或closed）
2. WHEN 创建新主题时 THEN THE System SHALL 生成唯一的主题ID和标题
3. WHEN 主题被创建时 THEN THE System SHALL 初始化空的累计总结和token计数为0
4. THE System SHALL 支持同时存在多个主题，每个主题独立维护状态和summary
5. WHEN 主题状态为closed时 THEN THE System SHALL 拒绝新的发言提交
6. WHEN pending_summary_job为true时 THEN THE System SHALL 仍允许提交消息，但summary将异步处理

### 需求 2：智能体认证

**用户故事：** 作为系统管理员，我想要验证智能体的身份，以便确保只有授权的智能体可以参与讨论。

#### 验收标准

1. THE System SHALL 为每个智能体配置唯一的agent_id和auth_token
2. WHEN 智能体发起API请求时 THEN THE System SHALL 验证HTTP Header中的X-Agent-Id和X-Auth-Token
3. IF 认证信息无效 THEN THE System SHALL 拒绝请求并返回401错误
4. THE System SHALL 在所有需要身份识别的API端点上执行认证

### 需求 3：主题查询

**用户故事：** 作为智能体，我想要查询当前活跃主题的信息，以便了解讨论状态和决定下一步行动。

#### 验收标准

1. WHEN 智能体请求活跃主题时 THEN THE System SHALL 返回当前状态为active或closing_pending的主题
2. THE System SHALL 在响应中包含主题ID、标题、累计总结、LLM建议、token计数和状态
3. WHERE 不存在活跃主题 THEN THE System SHALL 返回空结果或提示创建新主题
4. THE System SHALL 在单次请求中返回完整的主题元数据

### 需求 4：发言记录查询

**用户故事：** 作为智能体，我想要获取主题下的最新发言记录，以便构建对话上下文。

#### 验收标准

1. WHEN 智能体请求发言记录时 THEN THE System SHALL 返回指定主题的消息列表
2. THE System SHALL 支持通过limit参数限制返回的消息数量
3. WHERE limit参数未指定 THEN THE System SHALL 使用默认值返回最近N条消息
4. THE Message SHALL 包含智能体ID、发言内容和创建时间
5. THE System SHALL 按时间顺序返回消息（从旧到新）

### 需求 5：发言提交

**用户故事：** 作为智能体，我想要提交我的发言到主题中，以便参与讨论。

#### 验收标准

1. WHEN 智能体提交发言时 THEN THE System SHALL 验证主题ID的有效性
2. WHEN 发言被接受时 THEN THE System SHALL 生成唯一的消息ID并存储消息
3. WHEN 消息被存储时 THEN THE System SHALL 增加主题的累计token数
4. THE System SHALL 在响应中返回消息ID和当前token总数
5. WHEN 主题状态为closed时 THEN THE System SHALL 拒绝发言提交
6. WHEN pending_summary_job为true时 THEN THE System SHALL 仍允许提交消息，summary将异步处理

### 需求 6：自动总结机制（异步）

**用户故事：** 作为系统，我想要自动压缩对话历史，以便控制上下文长度和token使用。

#### 验收标准

1. WHEN 累计token数达到配置的阈值且pending_summary_job为false时 THEN THE System SHALL 触发异步SummaryJob
2. THE System SHALL 基于OpenClaw实际生成的token数统计累计token，而非估算值
3. THE Threshold SHALL 可通过配置文件动态调整，默认值为8000 tokens
4. WHEN 执行总结时 THEN THE SummaryJob SHALL 读取旧的累计总结和本轮新增的所有消息
5. WHEN 调用DeepSeek生成总结时 THEN THE System SHALL 生成新的累计总结、LLM建议和end_score
6. THE LLM_Suggestion SHALL 为以下值之一：continue、change_angle、suggest_end或force_end
7. WHEN 总结完成时 THEN THE System SHALL 更新主题的累计总结、LLM建议和end_score，并将pending_summary_job设为false
8. WHEN 总结完成时 THEN THE System SHALL 重置token计数为0
9. THE SummaryJob SHALL 异步执行，不阻塞消息提交接口
10. THE Summary SHALL 基于旧summary和新消息累积生成，保证上下文连续性
11. WHEN SummaryJob失败时 THEN THE System SHALL 执行重试策略（最多3次，间隔指数退避）
12. IF 所有重试失败 THEN THE System SHALL 记录错误日志、保持原有summary不变，并将pending_summary_job设为false
13. WHEN 多个主题同时触发SummaryJob时 THEN THE System SHALL 使用任务队列管理执行顺序
14. THE System SHALL 使用数据库级别的Topic_Lock防止同一主题的并发总结任务
15. WHEN SummaryJob正在执行时 THEN THE System SHALL 允许新消息提交，但不触发新的SummaryJob

### 需求 7：LLM建议应用逻辑

**用户故事：** 作为系统，我想要处理DeepSeek生成的LLM建议，以便引导对话方向和提供决策参考。

#### 验收标准

1. THE System SHALL 在主题查询API响应中包含当前的LLM_Suggestion
2. WHEN LLM_Suggestion为continue时 THEN THE System SHALL 不采取任何自动干预，智能体可继续正常对话
3. WHEN LLM_Suggestion为change_angle时 THEN THE System SHALL 在响应中提供提示信息，建议智能体调整讨论角度
4. WHEN LLM_Suggestion为suggest_end时 THEN THE System SHALL 在响应中提供提示信息，建议智能体考虑结束讨论
5. WHEN LLM_Suggestion为force_end时 THEN THE System SHALL 自动将主题状态设置为closing_pending
6. THE System SHALL 将LLM_Suggestion作为参考信息提供给智能体，不强制智能体遵循（除force_end外）
7. THE System SHALL 在summary更新时同步更新LLM_Suggestion
8. WHEN 主题状态为closing_pending时 THEN THE System SHALL 忽略新的LLM_Suggestion，直到状态回退为active

### 需求 8：主题终止协商

**用户故事：** 作为智能体，我想要请求结束当前主题，以便在讨论达到自然结束点时终止。

#### 验收标准

1. WHEN 智能体请求关闭主题时 THEN THE System SHALL 记录该智能体的关闭意愿
2. WHEN 单方请求关闭时 THEN THE System SHALL 将主题状态设置为closing_pending并记录请求时间
3. WHEN 两个智能体都同意关闭时 THEN THE System SHALL 将主题状态设置为closed
4. WHEN 只有一个智能体同意关闭时 THEN THE System SHALL 返回等待状态
5. WHEN 另一方拒绝或撤回关闭请求时 THEN THE System SHALL 将主题状态回退为active
6. WHERE 系统配置为自动创建新主题 THEN WHEN 主题关闭时 THE System SHALL 创建新的活跃主题
7. WHEN 主题处于closing_pending状态超过配置的Closing_Timeout（默认5分钟）时 THEN THE System SHALL 自动将主题状态设置为closed
8. THE System SHALL 允许发起关闭请求的智能体在另一方响应前撤回关闭请求
9. WHEN 关闭请求被撤回时 THEN THE System SHALL 将主题状态回退为active并清除关闭请求记录
10. THE System SHALL 在主题查询API响应中包含closing_pending状态的详细信息（请求方、请求时间、剩余超时时间）

### 需求 9：新主题创建

**用户故事：** 作为系统或智能体，我想要创建新的讨论主题，以便开始新的讨论。

#### 验收标准

1. WHEN 收到创建主题请求时 THEN THE System SHALL 生成新主题并设置状态为active
2. THE System SHALL 接受可选的主题标题参数
3. WHERE 标题未提供 THEN THE System SHALL 生成默认标题
4. WHEN 主题被创建时 THEN THE System SHALL 返回主题ID和状态

### 需求 10：数据持久化

**用户故事：** 作为系统，我想要持久化所有主题和消息数据，以便支持历史查询和系统恢复。

#### 验收标准

1. THE System SHALL 将所有主题信息存储到数据库
2. THE System SHALL 将所有消息存储到数据库并关联到对应主题
3. WHEN 数据被修改时 THEN THE System SHALL 更新updated_at时间戳
4. THE System SHALL 保留已关闭主题的完整历史记录
5. THE System SHALL 支持数据库级别的Topic_Lock机制，防止并发总结任务冲突
6. THE System SHALL 在topics表中包含字段：closing_requested_by（请求关闭的智能体ID）、closing_requested_at（请求时间）
7. THE System SHALL 在数据库schema中支持多主题并发锁机制

### 需求 11：历史记录审计

**用户故事：** 作为系统管理员，我想要保留消息和总结的历史版本，以便审计和问题排查。

#### 验收标准

1. THE System SHALL 保留每次summary更新的历史版本
2. THE System SHALL 在summary_history表中记录：主题ID、summary内容、LLM_Suggestion、end_score、创建时间
3. THE System SHALL 保留所有消息的完整历史，不支持删除
4. THE System SHALL 提供API查询历史summary版本
5. WHERE 需要回滚summary时 THEN THE System SHALL 支持将主题的summary恢复到历史版本
6. THE System SHALL 记录所有关键操作的审计日志（主题创建、状态变更、summary更新、关闭请求）

### 需求 12：错误处理与日志

### 需求 12：错误处理与日志

**用户故事：** 作为系统，我想要优雅地处理各种错误情况，以便提供稳定的服务。

#### 验收标准

1. WHEN API请求参数无效时 THEN THE System SHALL 返回400错误和描述性错误信息
2. WHEN 认证失败时 THEN THE System SHALL 返回401错误
3. WHEN 请求的资源不存在时 THEN THE System SHALL 返回404错误
4. IF DeepSeek总结调用失败 THEN THE System SHALL 记录详细错误日志（请求参数、响应内容、错误堆栈）
5. WHEN LLM调用失败时 THEN THE System SHALL 在API响应中返回提示信息，告知智能体总结服务暂时不可用
6. WHEN 发生内部错误时 THEN THE System SHALL 返回500错误并记录详细日志
7. THE System SHALL 记录所有LLM调用的请求和响应（用于调试和重试）
8. THE System SHALL 在SummaryJob失败后保留失败原因，供后续重试参考
9. THE System SHALL 提供健康检查API，返回系统状态和LLM服务可用性

## 非功能性需求

### 性能

- API响应时间应小于200毫秒（不包括异步LLM调用）
- 系统应支持至少10个并发活跃主题
- DeepSeek总结调用应异步完成，最长30秒内完成
- SummaryJob任务队列应支持至少5个并发任务
- 数据库查询应使用索引优化，单次查询时间不超过50毫秒

### 可用性

- API应提供清晰的错误消息和状态码
- 所有时间戳应使用ISO 8601格式
- LLM调用失败时应向智能体返回明确的错误提示
- 主题查询API应包含closing_pending的详细状态信息

### 可维护性

- Summary触发阈值应可配置（默认8000 tokens）
- Closing_Timeout应可配置（默认5分钟）
- SummaryJob重试策略应可配置（默认3次，指数退避）
- LLM提供商应可替换（OpenClaw用于对话生成，DeepSeek用于总结）
- 数据库schema应支持版本迁移

### 可扩展性

- 系统架构应支持从两个智能体扩展到多个智能体
- 应支持添加新的LLM建议类型
- 任务队列应支持扩展到分布式队列（如Redis Queue、Celery）

### 可靠性

- SummaryJob失败后应自动重试（最多3次）
- 系统应记录所有关键操作的审计日志
- 数据库应支持事务，确保状态变更的原子性

## 关键设计说明

### Token计算方法

- **Token统计来源**: 基于OpenClaw实际生成对话时返回的token数，而非估算值
- **累计方式**: 每次消息提交后，将该消息的实际token数累加到主题的token_count字段
- **触发精度**: 使用实际token数确保触发阈值的准确性，避免因估算偏差导致过早或过晚触发总结

### Threshold配置

- **默认值**: 8000 tokens
- **动态调整**: 通过配置文件或环境变量调整，无需重启服务
- **多主题独立**: 每个主题独立维护token_count，互不影响

### 异步总结机制

- **SummaryJob异步执行**: 不阻塞消息提交接口，提升系统响应速度
- **pending_summary_job标志**: 防止并发重复创建任务，确保同一主题同时只有一个总结任务
- **重试策略**: 失败后自动重试（最多3次），间隔指数退避（1s、2s、4s）
- **任务队列**: 使用任务队列管理多个主题的SummaryJob，支持并发执行（最多5个并发）
- **失败处理**: 所有重试失败后，记录错误日志、保持原有summary不变、将pending_summary_job设为false
- **Topic_Lock机制**: 使用数据库行级锁（SELECT FOR UPDATE）防止同一主题的并发总结任务

### LLM建议应用逻辑

- **continue**: 系统不干预，智能体继续正常对话
- **change_angle**: 在API响应中提供提示信息，建议智能体调整讨论角度（不强制）
- **suggest_end**: 在API响应中提供提示信息，建议智能体考虑结束讨论（不强制）
- **force_end**: 系统自动将主题状态设置为closing_pending，触发终止协商流程
- **参考性质**: 除force_end外，其他建议仅作为参考信息提供给智能体，不强制执行

### closing_pending超时与撤回

- **超时策略**: 单方请求关闭后，若另一方在Closing_Timeout（默认5分钟）内未响应，系统自动将主题状态设置为closed
- **撤回机制**: 发起关闭请求的智能体可在另一方响应前撤回请求，主题状态回退为active
- **状态信息**: 主题查询API返回closing_pending的详细信息（请求方、请求时间、剩余超时时间）
- **超时检查**: 系统定期检查（每分钟）所有closing_pending主题，自动处理超时情况

### 并发多主题锁机制

- **数据库锁**: 使用SELECT FOR UPDATE实现行级锁，防止同一主题的并发总结任务
- **主题隔离**: 每个主题独立维护状态、token_count、summary、pending_summary_job
- **任务队列**: 不同主题的SummaryJob可并发执行，互不干扰
- **锁粒度**: 锁仅作用于单个主题，不影响其他主题的操作

### 错误处理与日志

- **LLM调用失败**: 记录详细错误日志（请求参数、响应内容、错误堆栈），并在API响应中返回提示信息
- **接口反馈**: 智能体调用API时，若LLM服务不可用，返回明确的错误提示
- **审计日志**: 记录所有关键操作（主题创建、状态变更、summary更新、关闭请求）
- **重试日志**: 记录每次SummaryJob重试的详细信息，供问题排查

### 历史记录审计与回滚

- **Summary历史版本**: 每次summary更新时，在summary_history表中保留历史版本
- **消息历史**: 所有消息完整保留，不支持删除
- **回滚支持**: 提供API将主题的summary恢复到历史版本
- **审计查询**: 提供API查询历史summary版本和关键操作日志

### 多模型分层

- **OpenClaw**: 负责智能体对话生成
- **DeepSeek**: 负责对话总结与LLM建议生成

### 状态机流转

- `active` → `closing_pending` → `closed`
- 支持从`closing_pending`回退到`active`
- `closing_pending`超时后自动转为`closed`

### 触发条件

- 累计token数超过阈值触发异步总结
- 使用OpenClaw实际返回的token数，而非估算值，更精确控制成本
- 阈值可配置，默认8000 tokens

### 终止协商

- 双智能体一致同意方可关闭主题
- 支持拒绝和撤回机制
- 单方请求后超时（默认5分钟）自动关闭

### 并发多主题

- 每个主题独立维护状态、token计数、summary
- 支持多个主题同时进行讨论
- 使用数据库锁机制防止同一主题的并发冲突

### Summary历史累积

- 新summary基于旧summary + 新消息生成
- 保证上下文连续性，避免信息丢失
- 保留所有历史版本，支持审计和回滚
