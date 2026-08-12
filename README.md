# tianpeng-demo · Monorepo

本仓库采用 Monorepo 结构，包含两个完全独立的子项目：**AI 辅助开发者论坛** 与 **个人作品集**。

---

## 仓库总览

```
tianpeng-demo/
├── AGENTS.md                      # AI Agent 协作规范（仓库级）
├── README.md                      # 本文件（Monorepo 导航）
├── .gitignore                     # 仓库级忽略规则
│
├── ai-forum/                      # ===== AI 辅助开发者论坛 =====
│   ├── README.md                  #   论坛专属 README（快速开始 · API · 文档）
│   ├── docker-compose.yml         #   PostgreSQL + Redis 一键启动
│   ├── docs/
│   │   ├── prd/                   #   产品需求文档（HTML + Mermaid + ECharts）
│   │   ├── requirements/          #   需求汇总文档
│   │   └── information-architecture.md
│   ├── prototype/                 #   高保真原型（9 个页面）
│   ├── backend/                   #   FastAPI (Python 3.11)
│   ├── database/                  #   PostgreSQL 初始化脚本 + 种子数据
│   ├── frontend/                  #   Next.js 14 + TypeScript
│   └── static/
│       └── forum-home.html        #   论坛首页静态原型
│
└── personal-portfolio/            # ===== 个人作品集 =====
    ├── site/                      #   Vite + React 作品集站点
    │   ├── public/                #   Vite 静态资源（3 个独立 HTML demo）
    │   │   ├── weather-app.html   #     天气应用
    │   │   ├── snake-game.html    #     贪吃蛇游戏（赛博朋克风格）
    │   │   ├── accounting-tool.html #   记账工具
    │   │   └── xiaoxin.jpeg       #     头像
    │   └── src/
    │       ├── components/        #   Hero / Nav / WorksGrid / ProjectCard 等
    │       └── components/previews/ # 项目缩略预览组件
    └── tools/
        └── weather-proxy/
            └── server.js          #   和风天气 API 代理服务器（绕过 CORS）
```

---

## 子项目导航

### 🧠 AI 辅助开发者论坛 → [`ai-forum/`](./ai-forum/)

面向 AI / 大模型领域开发者与兴趣用户的垂直技术社区，以「**AI 先答 + 社区补全**」为核心范式。

- **技术栈**：Next.js 14 + FastAPI + PostgreSQL 15 + Redis 7 + Alembic
- **核心特性**：双路检索 AI 问答、流式实时推送、入门/深度分区、声望徽章体系、AI 辅助写作
- **开发进度**：Phase 0（基础骨架已完成，前后端可运行）
- **详细文档**：参见 [`ai-forum/README.md`](./ai-forum/README.md)

### 🎨 个人作品集 → [`personal-portfolio/site/`](./personal-portfolio/site/)

资深产品设计师的个人作品集，采用 React 19 + Vite + Tailwind CSS v4 构建。

- **独立演示项目**（位于 `personal-portfolio/site/public/`）：
  - 🌤 天气应用 `weather-app.html` — 配合 `tools/weather-proxy/server.js` 使用
  - 🐍 贪吃蛇游戏 `snake-game.html` — 赛博朋克霓虹风格，四难度 + 穿墙模式
  - 📒 记账工具 `accounting-tool.html`

---

## 快速开始

### AI Forum

```bash
# 1. 启动数据库
cd ai-forum && docker compose up -d

# 2. 启动后端
cd ai-forum/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. 启动前端
cd ai-forum/frontend
npm install && npm run dev
```

### Personal Portfolio

```bash
# 启动作品集站点
cd personal-portfolio/site
npm install && npm run dev

# 启动天气应用代理（如需要独立访问天气 demo）
node personal-portfolio/tools/weather-proxy/server.js
# → http://localhost:8765
```

---

## 协作规范

本仓库的 AI Agent 协作规范定义于 [`AGENTS.md`](./AGENTS.md)，主要规则：

- 默认分支：`main`
- 自动推送：完成功能 / 修复 / 重构后自动提交并推送至 `origin main`
- Commit 风格：Conventional Commits（`feat:` / `fix:` / `refactor:` / `docs:` / `chore:`）
- 安全约束：禁止提交 `.env`、密钥；禁止 `--force` 推送

---

## 许可

本项目仅供学习与内部使用。
