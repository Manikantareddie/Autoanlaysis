import time
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.agents.graph import analysis_graph
from app.agents.planner import create_report
from app.agents.recovery import correct_sql
from app.db.base import Base
from app.db.session import engine, get_session
from app.models.analysis import Analysis, AnalysisStep, Execution
from app.models.dataset import Dataset
from app.schemas.analysis import AnalysisRequest, AnalysisResult
from app.schemas.history import AnalysisHistory, AnalysisSummary, ExecutionTrace
from app.tools.sql_executor import execute_read_only

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])
MAX_CORRECTION_ATTEMPTS = 2

@router.post("/run", response_model=AnalysisResult)
def run_analysis(request: AnalysisRequest, session: Session = Depends(get_session)) -> AnalysisResult:
    dataset = session.get(Dataset, request.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    Base.metadata.create_all(bind=engine)
    analysis = Analysis(dataset_id=dataset.id, question=request.question, status="running")
    session.add(analysis); session.commit(); session.refresh(analysis)
    context = None
    if request.previous_analysis_id:
        prev = session.get(Analysis, request.previous_analysis_id)
        if prev:
            context = {
                "previous_question": prev.question,
                "previous_summary": prev.report_json.get("executive_summary") if prev.report_json else None,
                "previous_sql": prev.plan_json.get("sql") if prev.plan_json else None,
            }
    try:
        state = analysis_graph.invoke(
            {"question": request.question, "profile": dataset.profile_json, "context": context},
            {"recursion_limit": 4}
        )
        plan, proposal = state["plan"], state["proposal"]
        analysis.plan_json = plan.model_dump()
        step = AnalysisStep(analysis_id=analysis.id, step_number=1, description=plan.steps[0].description, tool_type="sql", status="running")
        session.add(step); session.commit(); session.refresh(step)
        for attempt in range(1, MAX_CORRECTION_ATTEMPTS + 2):
            started = time.perf_counter()
            try:
                sql, columns, rows = execute_read_only(Path(dataset.duckdb_path), proposal.sql)
                session.add(Execution(analysis_step_id=step.id, attempt_number=attempt, generated_code=sql, execution_status="succeeded", duration_ms=int((time.perf_counter()-started)*1000), result_reference={"row_count": len(rows), "columns": columns}))
                step.status, step.retry_count = "succeeded", attempt - 1
                analysis.status, analysis.completed_at = "succeeded", datetime.now(timezone.utc)
                report = None
                try:
                    report = create_report(request.question, plan, sql, columns, rows)
                    analysis.report_json = report.model_dump()
                except Exception as rep_err:
                    logger.warning("Report generation warning: %s", rep_err)
                session.commit()
                return AnalysisResult(analysis_id=analysis.id, plan=plan, sql=sql, columns=columns, rows=rows, row_count=len(rows), report=report)
            except HTTPException as error:
                session.add(Execution(analysis_step_id=step.id, attempt_number=attempt, generated_code=proposal.sql, execution_status="failed", error_message=str(error.detail)[:500], duration_ms=int((time.perf_counter()-started)*1000)))
                if attempt > MAX_CORRECTION_ATTEMPTS:
                    step.status, step.retry_count = "failed", attempt - 1
                    analysis.status, analysis.completed_at = "failed", datetime.now(timezone.utc)
                    session.commit()
                    raise
                proposal = correct_sql(request.question, dataset.profile_json, proposal.sql, str(error.detail)[:500])
                step.retry_count = attempt
                session.commit()
    except HTTPException:
        raise
    except Exception as error:
        analysis.status, analysis.completed_at = "failed", datetime.now(timezone.utc)
        session.commit()
        raise HTTPException(status_code=502, detail="Analysis planning failed.") from error

@router.get("", response_model=list[AnalysisSummary])
def list_analyses(dataset_id: str | None = None, session: Session = Depends(get_session)) -> list[AnalysisSummary]:
    query = select(Analysis).order_by(Analysis.created_at.desc())
    if dataset_id:
        query = query.where(Analysis.dataset_id == dataset_id)
    analyses = session.scalars(query).all()
    return [
        AnalysisSummary(
            id=a.id,
            dataset_id=a.dataset_id,
            question=a.question,
            status=a.status,
            created_at=a.created_at,
            completed_at=a.completed_at,
        )
        for a in analyses
    ]

@router.get("/{analysis_id}", response_model=AnalysisHistory)
def get_analysis(analysis_id: str, session: Session = Depends(get_session)) -> AnalysisHistory:
    analysis = session.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    steps = session.scalars(select(AnalysisStep).where(AnalysisStep.analysis_id == analysis.id)).all()
    traces = []
    for step in steps:
        traces.extend(session.scalars(select(Execution).where(Execution.analysis_step_id == step.id).order_by(Execution.attempt_number)).all())
    return AnalysisHistory(id=analysis.id, dataset_id=analysis.dataset_id, question=analysis.question, status=analysis.status, plan=analysis.plan_json, report=analysis.report_json, created_at=analysis.created_at, completed_at=analysis.completed_at, executions=[ExecutionTrace(attempt_number=trace.attempt_number, generated_code=trace.generated_code, execution_status=trace.execution_status, error_message=trace.error_message, duration_ms=trace.duration_ms) for trace in traces])

