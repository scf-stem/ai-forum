"""Resumable AI gold-set evaluation execution and gate summaries."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ops import EvaluationCase, EvaluationResult, EvaluationRun
from app.services.ai_service import generate_answer
from app.services.retrieval_service import RetrievalService


async def execute_evaluation(db: AsyncSession, run: EvaluationRun, progress=None) -> int:
    cases = (await db.execute(select(EvaluationCase).where(
        EvaluationCase.active.is_(True), EvaluationCase.version == run.dataset_version)
        .order_by(EvaluationCase.category, EvaluationCase.id))).scalars().all()
    run.status = "running"; await db.commit()
    for index, case in enumerate(cases):
        await db.refresh(run)
        if run.status == "cancelled":
            return index
        exists = (await db.execute(select(EvaluationResult.id).where(
            EvaluationResult.run_id == run.id, EvaluationResult.case_id == case.id))).scalar_one_or_none()
        if exists:
            continue
        sources, _ = await RetrievalService.retrieve(case.question)
        answer, usage = await generate_answer(case.question, case.question, sources, run.prompt_version)
        db.add(EvaluationResult(run_id=run.id, case_id=case.id, answer=answer, sources=sources,
            token_usage=usage, confidence_level="high" if len(sources) >= 2 else "low"))
        await db.commit()
        if progress: await progress(int((index + 1) / max(1, len(cases)) * 95))
    run.status = "awaiting_review"; await db.commit()
    return len(cases)


async def summarize_evaluation(db: AsyncSession, run: EvaluationRun) -> dict:
    rows = (await db.execute(select(EvaluationResult, EvaluationCase).join(
        EvaluationCase, EvaluationResult.case_id == EvaluationCase.id).where(EvaluationResult.run_id == run.id))).all()
    reviewed = [(r, c) for r, c in rows if r.correctness is not None]
    total = len(reviewed)
    if total == 0:
        return {"reviewed": 0, "passed": False, "reason": "尚无人工评分"}
    correct = sum(1 for r, _ in reviewed if r.correctness >= 3)
    citations = sum(1 for r, _ in reviewed if r.citation_validity >= 3)
    hallucinations = sum(1 for r, _ in reviewed if r.hallucination)
    by_category: dict[str, list[bool]] = {}
    for result, case in reviewed:
        by_category.setdefault(case.category, []).append(result.correctness >= 3)
    category_accuracy = {key: sum(vals) / len(vals) for key, vals in by_category.items()}
    high_confidence = [r for r, _ in reviewed if r.confidence_level == "high"]
    high_confidence_accuracy = (sum(1 for r in high_confidence if r.correctness >= 3) /
                                len(high_confidence)) if high_confidence else 0
    summary = {"reviewed": total, "accuracy": correct / total,
               "citation_validity": citations / total, "hallucination_rate": hallucinations / total,
               "high_confidence_accuracy": high_confidence_accuracy,
               "category_accuracy": category_accuracy}
    summary["passed"] = (total >= 100 and summary["accuracy"] >= .85 and
        summary["high_confidence_accuracy"] >= .90 and
        summary["citation_validity"] >= .90 and summary["hallucination_rate"] <= .05 and
        all(value >= .75 for value in category_accuracy.values()))
    if run.baseline_run_id:
        baseline = (await db.execute(select(EvaluationRun).where(
            EvaluationRun.id == run.baseline_run_id))).scalar_one_or_none()
        if baseline and baseline.summary:
            regressions = {
                "accuracy": baseline.summary.get("accuracy", 0) - summary["accuracy"],
                "citation_validity": baseline.summary.get("citation_validity", 0) - summary["citation_validity"],
                "hallucination_rate": summary["hallucination_rate"] - baseline.summary.get("hallucination_rate", 1),
            }
            summary["regressions"] = regressions
            summary["passed"] = summary["passed"] and all(value <= .03 for value in regressions.values())
    run.summary = summary
    if total >= 100: run.status = "passed" if summary["passed"] else "failed"
    run.finished_at = datetime.now(timezone.utc) if total >= 100 else None
    await db.commit()
    return summary
