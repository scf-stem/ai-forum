# AGENTS.md

本文件定义本仓库中 AI Agent（如 Trae / Claude Code 等）的协作规则。

## 仓库信息

- GitHub 远程仓库：https://github.com/tianpeng-dev/ai-forum.git
- 默认分支：`main`
- 工作目录：`/Users/peng/Documents/trae_projects/tianpeng-demo`

## 自动推送规则（必须执行）

每次完成一轮开发任务（新增功能、修复 Bug、重构、文档更新等）后，Agent 必须自动执行以下流程，将代码同步到 GitHub `main` 分支，无需等待用户额外提示：

1. **检查变更**
   - 运行 `git status` 与 `git diff`，确认本次改动范围。
   - 排除 `.gitignore` 中已忽略的文件（如 `.DS_Store`、`.trae/`、`node_modules/`、`.venv/`、`.env` 等）。

2. **暂存改动**
   - 按文件粒度 `git add <具体文件>`，避免使用 `git add -A` / `git add .` 误入库敏感文件。
   - 如有新增依赖文件（`package.json`、`requirements.txt` 等），一并加入。

3. **提交**
   - 使用 HEREDOC 形式提交，commit message 遵循 Conventional Commits 风格：
     - `feat: <新功能>`
     - `fix: <修复>`
     - `refactor: <重构>`
     - `docs: <文档>`
     - `chore: <杂项>`
   - 消息体简要说明“为什么改”，而非仅描述“改了什么”。

4. **推送到 GitHub `main` 分支**
   - 首次推送：`git push -u origin main`
   - 后续推送：`git push origin main`
   - **禁止** 使用 `git push --force` 或 `git push --force-with-lease`，除非用户明确要求。
   - 若推送因远端有新提交而失败，先执行 `git pull --rebase origin main`，解决冲突后再推送。

5. **验证**
   - 推送后运行 `git status` 确认工作区干净，`git log --oneline -1` 确认最新 commit 已同步。

## 分支与命名

- 主分支统一使用 `main`，不使用 `master`。
- 如需功能分支，命名格式：`feat/<功能名>`、`fix/<问题名>`、`docs/<主题>`。

## Git 安全约定

- 不得修改全局 `git config`。
- 不得执行 `--force` 推送（除非用户明确授权）。
- 不得提交 `.env`、密钥、令牌等敏感文件。
- 不得主动创建空 commit。

## 项目结构概览

```
.
├── AGENTS.md                      # 本文件
├── README.md                      # 项目说明
├── .gitignore
├── docker-compose.yml             # 一键启动 PostgreSQL + Redis
├── docs/
│   ├── prd/                       # PRD 文档（HTML + Mermaid + ECharts）
│   ├── requirements/              # 需求汇总文档
│   └── information-architecture.md
├── prototype/                     # 高保真原型（多页面）
├── backend/                       # FastAPI 后端
├── database/                      # 数据库初始化脚本
├── frontend/                      # Next.js 前端
└── static/
    └── forum-home.html            # 论坛首页静态原型
```

## 触发自动推送的场景

Agent 在以下情况必须自动执行推送流程：

- 完成一个完整功能模块的开发
- 修复一个 Bug 并通过验证
- 重构某一代码模块
- 新增或更新文档
- 用户显式说“提交”、“推送”、“同步到 GitHub”等指令

## 例外情况

如果出现以下情况，先暂停并询问用户，不要自动推送：

- 改动涉及敏感配置（数据库密码、API Key 等）
- 测试未通过或编译失败
- 存在未解决的合并冲突
- 用户明确表示“先不要推送”
