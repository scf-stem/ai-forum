"""版块种子数据脚本。

使用 asyncio + asyncpg 直接执行 SQL 插入预置版块数据，不依赖 ORM。
幂等设计：基于 name + tier 冲突时更新描述与排序。

使用方式：
    python seed_boards.py
    # 或自定义连接串
    DATABASE_URL=postgresql://forum:forum@localhost:5432/forum python seed_boards.py

注意：需先执行 alembic upgrade head 创建表结构。
"""
import asyncio
import os
import sys

import asyncpg

# 默认连接串，可通过环境变量 DATABASE_URL 覆盖
DEFAULT_DSN = "postgresql://forum:forum@localhost:5432/forum"

# 预置版块数据：分为入门区与深度区两档
BOARDS = [
    # 入门区：面向 AI 开发新手
    {
        "name": "AI 概念科普",
        "tier": "entry",
        "description": "用通俗的语言讲解 AI 基础概念，帮助新手快速建立认知框架。",
        "sort_order": 1,
    },
    {
        "name": "上手教程",
        "tier": "entry",
        "description": "从零开始的实战教程，跟着步骤完成第一个 AI 应用。",
        "sort_order": 2,
    },
    {
        "name": "工具推荐",
        "tier": "entry",
        "description": "分享好用的 AI 开发工具、插件与效率利器。",
        "sort_order": 3,
    },
    # 深度区：面向有经验的开发者
    {
        "name": "大模型",
        "tier": "deep",
        "description": "大语言模型的训练、微调、推理与评测等深度话题。",
        "sort_order": 1,
    },
    {
        "name": "RAG",
        "tier": "deep",
        "description": "检索增强生成的架构设计、向量数据库与效果优化实践。",
        "sort_order": 2,
    },
    {
        "name": "Agent",
        "tier": "deep",
        "description": "智能体编排、工具调用、多 Agent 协作与工作流设计。",
        "sort_order": 3,
    },
    {
        "name": "部署优化",
        "tier": "deep",
        "description": "模型部署、推理加速、成本控制与生产环境最佳实践。",
        "sort_order": 4,
    },
]

# 幂等插入：基于 name + tier 冲突时更新描述与排序
UPSERT_BOARD_SQL = """
INSERT INTO boards (name, tier, description, sort_order, post_count, follower_count)
VALUES ($1, $2, $3, $4, 0, 0)
ON CONFLICT (name, tier) DO UPDATE
SET description = EXCLUDED.description,
    sort_order = EXCLUDED.sort_order
RETURNING id, name;
"""


async def seed_boards(dsn: str) -> None:
    """连接数据库并写入预置版块数据。"""
    conn = await asyncpg.connect(dsn)
    try:
        print("开始写入版块种子数据...")
        for board in BOARDS:
            row = await conn.fetchrow(
                UPSERT_BOARD_SQL,
                board["name"],
                board["tier"],
                board["description"],
                board["sort_order"],
            )
            print(f"  ✓ [{board['tier']}] {board['name']} (id={row['id']})")

        print(f"\n完成：共处理 {len(BOARDS)} 个版块。")
    finally:
        await conn.close()


def main() -> None:
    """脚本入口：从环境变量读取连接串并执行种子写入。"""
    dsn = os.getenv("DATABASE_URL", DEFAULT_DSN)
    # asyncpg 需要 postgresql:// 前缀，兼容 +asyncpg 形式的连接串
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    try:
        asyncio.run(seed_boards(dsn))
    except Exception as exc:  # noqa: BLE001
        print(f"种子数据写入失败：{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
