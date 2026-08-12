# AI 辅助开发者论坛

> **提问即答案 · AI 先答，社区补全**
>
> 面向 AI / 大模型领域开发者与零基础兴趣用户的垂直技术社区。以「AI 先答 + 社区补全」为核心范式，把「提问到获得可用答案」的链路从小时级压缩到秒级，让答案随社区补充持续沉淀为可检索的知识资产。

---

## 目录

- [产品简介](#产品简介)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [后端 API 概览](#后端-api-概览)
- [前端页面概览](#前端页面概览)
- [开发路线图](#开发路线图)
- [文档与原型](#文档与原型)
- [协作规范](#协作规范)

---

## 产品简介

当前 AI 应用开发者遇到的问题（RAG 召回失效、Agent 工具调用失败、推理成本失控……）高度依赖即时、准确、可追溯的答案。但传统社区仍是「人等人」模式——提问后等待人工回复，平均响应时间数小时到数天，且答案散落各处难以聚合。

本项目的范式改变：

```
传统社区：  提问 → 等待人回复 → 数小时~数天 → 答案碎片化
本产品：    提问 → AI 秒答（双路检索 + 来源标注）→ 社区补全 → 知识沉淀
```

- **AI 先答**：提问后 AI 秒级聚合论坛已有内容与实时联网检索，生成带来源标注的结构化答案。
- **社区补全**：社区成员补充实战经验与纠错，补充内容回流为可检索知识资产。
- **知识沉淀**：采纳的补充与高置信度 AI 答案写入检索索引，后续同类提问可直接命中。

---

## 核心特性

- **双路检索 AI 问答**：论坛向量匹配 + 实时联网搜索并行调度，结构化答案带来源标注与置信度。
- **流式实时推送**：FastAPI WebSocket 支撑答案逐字生成与补充/纠错实时推送。
- **入门 / 深度分区**：版块分层，入门区服务零基础用户（术语降维辅助），深度区服务开发者。
- **社区自治机制**：点赞 / 踩 / 举报 / 折叠，低质 AI 答案可被社区纠错降权。
- **声望与徽章体系**：回答被采纳、纠错验证、入门带新等行为驱动声望结算与等级提升。
- **内容打赏**：用户对创作者的内容激励，培育内容生态。
- **AI 辅助写作**：发帖时润色、代码格式化、摘要生成、标签推荐。
- **SEO 友好**：Next.js SSR 渲染未登录可浏览页面，提升冷启动获客。

---

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| **前端** | Next.js 14 · React 18 · TypeScript · Tailwind CSS | SSR 渲染 + WebSocket 实时接收 |
| **后端** | FastAPI · Python 3 | 原生 async/await 支撑双路检索并行调度 |
| **数据库** | PostgreSQL 15 | User / Post / Reply / Reputation / Bounty 等核心结构化数据 |
| **缓存** | Redis 7 | 会话、热点缓存、通知队列 |
| **ORM / 迁移** | SQLAlchemy 2 (async) · Alembic | 异步 ORM + 数据库版本迁移 |
| **鉴权** | JWT (python-jose + passlib) | Access Token + Refresh Token |
| **AI 服务** | 大模型 API · 联网搜索 API · Embedding 服务 | 双路检索 + 流式生成 + 向量化沉淀 |
| **检索（规划）** | 向量数据库 · Elasticsearch | 内容语义检索 + 全文搜索 |
| **基础设施** | Docker Compose | 一键启动 PostgreSQL + Redis |

---

## 项目结构

```
ai-forum/
├── frontend/                     # Next.js 前端
│   └── src/
│       ├── app/                  # App Router 页面（首页/版块/帖子/发帖/个人主页/...）
│       ├── components/           # Header、PostCard、MarkdownEditor 等组件
│       └── lib/                  # api 封装、auth-context、types、utils
├── backend/                      # FastAPI 后端
│   ├── app/
│   │   ├── main.py               # 应用入口（CORS + 路由挂载）
│   │   ├── config.py             # pydantic-settings 配置管理
│   │   ├── database.py           # 异步数据库引擎
│   │   ├── models/               # SQLAlchemy 模型（User/Post/Reply/Vote/...）
│   │   ├── schemas/              # Pydantic 请求/响应模型
│   │   ├── routers/              # API 路由（auth/users/boards/posts/replies/votes/reports）
│   │   ├── services/             # 业务逻辑（auth_service 等）
│   │   └── middleware/           # JWT 鉴权中间件
│   ├── alembic/                  # 数据库迁移脚本
│   ├── requirements.txt
│   └── .env.example              # 环境变量示例
├── database/                     # 数据库初始化
│   ├── init.sql                  # PostgreSQL 初始化脚本
│   └── seed_boards.py            # 版块种子数据
├── docs/
│   ├── prd/                      # 产品需求文档（PRD，HTML + Mermaid 图表）
│   ├── requirements/             # 需求汇总文档
│   └── information-architecture.md
├── prototype/                    # 高保真原型（9 个页面）
├── static/
│   └── forum-home.html           # 论坛首页静态原型
├── docker-compose.yml            # 一键启动 PostgreSQL + Redis
└── README.md                     # 本文件
```

---

## 快速开始

### 前置要求

- [Docker](https://www.docker.com/) & Docker Compose（启动数据库）
- [Node.js](https://nodejs.org/) >= 18（前端）
- [Python](https://www.python.org/) >= 3.11（后端）

### 1. 启动数据库与缓存

在 `ai-forum/` 目录下执行：

```bash
docker compose up -d
```

启动 PostgreSQL（`localhost:5432`）与 Redis（`localhost:6379`），数据库 `forum` 自动初始化。

### 2. 启动后端

```bash
cd ai-forum/backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env             # 按需修改 JWT_SECRET 等

# 执行数据库迁移
alembic upgrade head

# 启动开发服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端启动后访问：

- API 服务：`http://localhost:8000`
- Swagger 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/health`

### 3. 启动前端

```bash
cd ai-forum/frontend

# 安装依赖
npm install

# 启动开发服务
npm run dev
```

前端启动后访问 `http://localhost:3000`。

### 4.（可选）初始化版块种子数据

```bash
cd ai-forum/database
python seed_boards.py
```

---

## 后端 API 概览

所有接口前缀为 `/api`，Swagger 文档位于 `/docs`。

| 模块 | 前缀 | 说明 |
|---|---|---|
| 认证 | `/api/auth` | 注册、登录、刷新 Token |
| 用户 | `/api/users` | 用户资料、声望、徽章 |
| 版块 | `/api/boards` | 版块列表、入门/深度分区 |
| 帖子 | `/api/posts` | 发帖、列表、详情、排序 |
| 回复 | `/api/posts/{id}/replies`、`/api/replies/{id}` | 回复、补充、纠错 |
| 投票 | `/api` | 点赞 / 踩 |
| 举报 | `/api` | 内容举报 |
| 健康 | `/api/health` | 容器探针 |

---

## 前端页面概览

| 页面 | 路由 | 核心职责 |
|---|---|---|
| 首页 | `/` | 个性化推荐 Feed 与全站入口 |
| 版块详情 | `/boards/[boardId]` | 帖子列表、入门/深度分区切换 |
| 帖子详情 | `/posts/[postId]` | 正文、AI 答案区、社区补充区 |
| 发帖 / 提问 | `/ask` | 富文本编辑 + AI 辅助写作 |
| 个人主页 | `/users/[username]` | 资料、声望徽章、内容历史 |
| 登录 / 注册 | `/auth` | 账号注册登录 |
| 设置 | `/settings` | 账号、通知偏好、隐私 |

---

## 开发路线图

| 阶段 | 目标 | 关键交付 |
|---|---|---|
| **Phase 0** 基础骨架 | 搭建可运行的社区底座（不含 AI） | 账号体系、版块、发帖回帖、点赞举报、未登录浏览 |
| **Phase 1** AI 问答核心 | 核心差异化能力落地 | 双路检索、AI 答案生成、流式推送、低置信度降级 |
| **Phase 2** 社区机制与沉淀 | 答案随补充变好并沉淀 | 声望体系、纠错折叠、采纳回流 SearchIndex、通知系统 |
| **Phase 3** 推荐与打赏 | 提升留存与创作者激励 | 个性化推荐、内容打赏、AI 辅助写作、术语降维 |
| **Phase 4** 冷启动运营与验证 | 种子内容与数据验证 | 种子用户、指标埋点、AI 准确率评估 |

> 当前进度：**Phase 0**（基础骨架已完成，前后端可运行）

---

## 文档与原型

| 文档 | 路径 | 说明 |
|---|---|---|
| 产品需求文档 (PRD) | [`docs/prd/`](./docs/prd/) | 完整 PRD（HTML + Mermaid 图表 + ECharts） |
| 高保真原型 | [`prototype/`](./prototype/) | 9 个页面原型 |
| 需求汇总 | [`docs/requirements/`](./docs/requirements/) | 需求总结文档 |
| 信息架构 | [`docs/information-architecture.md`](./docs/information-architecture.md) | 页面清单与跳转关系 |

---

## 协作规范

本仓库的 AI Agent 协作规范定义于仓库根目录的 `AGENTS.md`，核心规则：

- 默认分支为 `main`
- 每次开发完成后自动提交并推送到 GitHub `main` 分支
- Commit message 遵循 Conventional Commits（`feat:` / `fix:` / `docs:` / `refactor:` / `chore:`）
- 禁止提交 `.env`、密钥等敏感文件
- 禁止 `--force` 推送（除非用户明确授权）

---

## 许可

本项目仅供学习与内部使用。
