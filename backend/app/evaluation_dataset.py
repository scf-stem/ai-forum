"""Versioned 100-question human gold set seed titles.

The detailed reviewer facts remain stored per ``evaluation_cases`` row so the
dataset can be reviewed and amended without making Prompt templates editable.
"""

GOLD_QUESTIONS: dict[str, list[str]] = {
    "rag": [
        "RAG 中 BM25 与向量召回各自适合什么场景，如何做混合排序？", "如何判断 RAG 的召回失败来自切分、索引还是查询改写？",
        "文档 chunk 大小与 overlap 应如何基于任务评估？", "RAG 引用如何保证能真正支持答案中的事实？",
        "多租户 RAG 如何实现可靠的数据隔离？", "如何为 RAG 构建可复现的离线评测集？",
        "查询改写会给 RAG 带来哪些收益与风险？", "什么是 parent-child retrieval，何时优于固定切块？",
        "Reranker 在 RAG 链路中的位置和评估方法是什么？", "如何处理 RAG 知识库中的版本冲突与过期文档？",
        "RAG 无答案检测应使用哪些信号？", "如何避免检索上下文中的提示注入影响回答？",
        "表格和代码文档进入 RAG 前应如何预处理？", "RAG 的 precision@k 与 recall@k 分别说明什么？",
        "什么时候不应使用 RAG？", "如何降低长上下文 RAG 的延迟和 Token 成本？",
        "Graph RAG 与普通文本 RAG 的边界是什么？", "如何对中文技术资料配置 PostgreSQL 全文检索？",
        "增量索引如何处理文档更新、删除与幂等？", "如何分析 RAG 回答正确但引用错误的问题？",
    ],
    "agent": [
        "Agent 工具调用为什么需要参数 schema 校验？", "如何为 Agent 设计最小权限与工具白名单？",
        "多 Agent 协作何时优于单 Agent？", "Agent 循环如何设置停止条件和预算？",
        "如何防止网页内容诱导 Agent 执行恶意工具调用？", "Agent 的计划与执行日志应记录哪些字段？",
        "工具调用超时和重试应如何保证幂等？", "Agent 记忆应如何区分会话记忆与长期记忆？",
        "如何评测 Agent 完成任务的可靠性？", "Agent 遇到 HTTP 402 时应如何安全处理？",
        "浏览器 Agent 如何防止误提交表单？", "Agent 的 human-in-the-loop 应设置在哪些动作前？",
        "如何处理 Agent 工具返回的不可信文本？", "ReAct 与结构化工作流各自适合什么任务？",
        "如何诊断 Agent 反复调用同一工具的问题？", "Agent 并行执行会引入哪些一致性风险？",
        "如何给 Agent 的外部副作用建立审计轨迹？", "Agent 失败恢复为什么需要持久化检查点？",
        "如何限制 Agent 的网络访问范围？", "怎样区分 Agent 幻觉与工具数据错误？",
    ],
    "model_inference": [
        "temperature 与 top_p 的作用有何不同？", "量化为什么可能降低模型输出质量？",
        "KV cache 如何影响推理显存与吞吐？", "批处理大小如何影响首 Token 延迟？",
        "什么是 speculative decoding，它何时有效？", "如何比较两个模型的事实正确性？",
        "上下文窗口变长会带来哪些成本？", "结构化输出为什么仍需要服务端校验？",
        "模型置信度能否直接由生成概率解释？", "如何识别模型发生事实性幻觉？",
        "LoRA 与全量微调的取舍是什么？", "蒸馏与量化解决的问题有何不同？",
        "推理服务中的 prefill 与 decode 阶段分别是什么？", "模型基准分数为什么不能直接代表业务效果？",
        "如何控制模型输出中敏感信息泄露？", "长文本摘要应如何避免遗漏关键约束？",
        "多模态模型处理图片时有哪些输入风险？", "系统 Prompt 与用户 Prompt 的优先级应如何实现？",
        "为什么相同 Prompt 的输出不能保证完全一致？", "如何记录模型调用以支持成本和质量回归？",
    ],
    "deployment_tooling": [
        "FastAPI 异步接口中为什么要避免阻塞 I/O？", "PostgreSQL 行锁如何防止积分余额并发透支？",
        "Redis 队列任务如何实现至少一次投递下的幂等？", "Alembic 大表迁移应如何降低锁表风险？",
        "WebSocket 断线后为什么仍需要 REST 补拉？", "如何安全校验抓取 URL 以防止 SSRF？",
        "Docker 容器健康检查应覆盖哪些依赖？", "生产发布为什么要先迁移再启动兼容后端？",
        "数据库账本如何做收支一致性检查？", "如何设计可中断续跑的批处理任务？",
        "API Idempotency-Key 应绑定哪些业务维度？", "服务端限流与客户端防抖各解决什么问题？",
        "PostgreSQL GIN 全文索引适合哪些查询？", "如何避免日志记录用户正文和密钥？",
        "跨时区日指标为什么要固定业务时区？", "如何安全回滚包含新增流水表的版本？",
        "Next.js 服务端与客户端请求代理有何区别？", "JWT 登出为什么需要撤销机制？",
        "如何对后台管理员接口做强制鉴权？", "429 与 5xx 的重试策略为什么应不同？",
    ],
    "beginner": [
        "什么是大语言模型，请用生活化例子解释？", "Prompt 是什么，为什么表达方式会影响答案？",
        "Token 是什么，它为什么影响费用？", "RAG 是什么，它和模型训练有什么区别？",
        "Agent 是什么，它与普通聊天机器人有何不同？", "向量数据库是什么，什么时候才需要它？",
        "API 是什么，请用餐厅点餐做类比？", "什么是模型幻觉，用户应如何核实？",
        "开源模型与闭源模型有什么基本区别？", "本地部署模型通常需要哪些硬件？",
        "上下文窗口是什么意思？", "Embedding 是什么，请通俗解释？",
        "微调是什么，和写 Prompt 有什么区别？", "什么是函数调用或工具调用？",
        "为什么 AI 生成的代码不能直接在生产运行？", "什么是 Markdown 代码块？",
        "如何提出一个更容易获得帮助的技术问题？", "什么是延迟、吞吐和并发？",
        "数据库与缓存有什么区别？", "为什么公开网页摘要需要保留原文链接？",
    ],
}


def dataset_rows(version: str = "v1") -> list[dict]:
    rows = []
    for category, questions in GOLD_QUESTIONS.items():
        for index, question in enumerate(questions):
            rows.append({
                "category": category, "question": question,
                "expected_key_points": ["准确解释核心概念", "说明适用边界或主要风险", "给出可执行的验证方法"],
                "forbidden_claims": ["捏造不存在的 API、参数、标准或确定性结论"],
                "expected_sources": ["官方文档、标准或原始论文；无法引用时明确说明"],
                "difficulty": ("easy" if category == "beginner" else "medium" if index < 14 else "hard"),
                "version": version,
            })
    assert len(rows) == 100
    return rows
