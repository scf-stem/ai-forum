# Phase 2–4 数据与运营手册

## 1. 数据字典

| 域 | 关键表 | 不变量 |
|---|---|---|
| 声望 | `reputation_logs`, `user_badges` | `event_key` 唯一；撤销以反向流水记录，不改写历史 |
| 搜索 | `search_documents` | `(source_type, source_id)` 唯一；只检索 `is_active=true` |
| 通知 | `notifications`, `notification_preferences` | 先持久化再 WebSocket 推送；REST 是重连后的事实来源 |
| 积分 | `point_ledger`, `content_rewards` | 余额行加锁；收支双流水；成功打赏不退款 |
| 推荐 | `analytics_events`, `post_similarities` | 客户端 UUID 去重；关闭个性化后不保存画像目标 `post_id` |
| 抓取 | `crawl_sources`, `crawl_items`, `background_jobs` | 只保存原创摘要、元数据与来源链接，不保存网页原文 |
| 指标 | `daily_metrics` | Asia/Shanghai 自然日；比例使用 basis points（10000=100%） |
| AI 评测 | `evaluation_cases`, `evaluation_runs`, `evaluation_results`, `evaluation_reviews` | 两人独立评分；冲突由第三人裁决；逐题持久化 |

等级阈值为 0/50/150/300/600/1200/3000/6000/10000/20000。积分没有现金价值，不支持购买、提现、退款或站外转移。

## 2. 指标口径

`daily_metrics.metric_name` 的核心值如下：

- `dau`：当天产生有效会话、打开、发帖、回复、投票、采纳、打赏或追问的非管理员、非系统登录用户数。
- `organic_posts` / `seed_posts`：自然原创帖子与官方摘要分别统计。
- `organic_content_share_bp`：自然用户帖子和回复占全部帖子和回复的比例。
- `human_reply_24h_bp`：问题在 24 小时内获得非管理员、非系统人工回复的比例。
- `ai_helpful_rate_bp` / `high_confidence_helpful_rate_bp`：满七天答案获得提问者 helpful 的比例。
- `low_confidence_verified_24h_bp`：低置信度答案 24 小时内获提问者或 Lv3+ 反馈，或采纳纠错的比例。
- `human_reply_acceptance_bp`：满七天且有有效人工回复的问题中存在采纳的比例。
- `search_documents`：有效 accepted reply 与 high-confidence AI 搜索文档数。
- `retention_d1_bp` / `retention_d7_bp`：注册当天有有效行为的用户在第 1/7 自然日回访比例。
- `recommendation_ctr_{cold_start|cooccurrence|hot|latest}_bp`：同策略客户端打开事件除以曝光事件。

第六个月目标为日均 DAU 3,000、月自然发帖 10,000；连续四周自然内容占比至少 80% 且 24 小时人工回复率至少 50% 才判定社区自运转。

## 3. 抓取运营 SOP

1. 在 `/ops` 录入同域 HTTPS 入口、速率、最大页数和站点条款 URL，并确认已完成条款/著作权/个人信息核对。
2. worker 校验公共 IP、重定向、`robots.txt`、HTML 类型和 2 MB 上限；单域串行，默认间隔 2 秒，429/5xx 指数退避 3 次。
3. 页面正文只在内存中进入无工具权限的摘要 Prompt；数据库只保存摘要、标签、canonical URL 和内容哈希。
4. 运营在待审核区编辑并批准；内容以不可登录的 `seed_bot` 发布，并带原文链接。
5. 投诉、授权变化或来源失效时停用来源；关联种子帖归档并同步失效 SearchIndex。

`robots.txt` 只表达自动访问规则，不等于转载授权。运营仍需按站点条款、著作权和个人信息最小化要求审核。

## 4. AI 评测 SOP

1. 金标集固定 100 条，RAG、Agent、模型/推理、部署/工具链、入门概念各 20 条；每条维护关键事实、禁止错误、期望来源、难度和版本。
2. 候选 Prompt 与生产基线必须使用同一数据集版本和模型配置；Prompt 在代码中版本化，答案持久化 `prompt_version`。
3. 两名评审独立提交正确性、完整性、引用有效性和幻觉评分；不一致时第三名评审结果为裁决值。
4. 任务逐题提交，可在中断后继续；保留来源、模型、Prompt、Token 和答案。
5. 发布门槛：全量正确率 ≥85%，高置信度正确率 ≥90%，任一领域 ≥75%，引用有效率 ≥90%，幻觉率 ≤5%，且相对生产基线任一核心指标下降不超过 3 个百分点。
6. LLM Judge 与规则检查只做排序和预警，不能单独批准上线。

## 5. 整包上线与回滚

1. 备份生产库；在副本执行 `alembic upgrade head` 并核对回填数量。
2. 迁移会为既有用户补 100 积分、按既有赞回填声望，并回填帖子、高置信度 AI 答案及采纳回复 SearchIndex；不伪造历史分析事件。
3. 依次启动 `python -m app.worker`、后端、新前端。先用 `python -m app.cli set-admin <email>` 授权首位管理员。
4. 执行健康检查、管理员鉴权、账本收支、通知补拉、推荐、抓取 dry-run、评测门槛和关键 E2E。
5. 硬门槛失败立即停止上线。严重故障先停 worker，再回滚应用版本；新增表和流水不删除，以向前修复为主。

本地真实依赖测试：

```bash
docker compose -f docker-compose.test.yml up -d
cd backend
TEST_DATABASE_URL=postgresql+asyncpg://forum_test:forum_test@localhost:55432/forum_test \
TEST_REDIS_URL=redis://localhost:56379/1 pytest -m integration
```
