from datetime import datetime
from pydantic import BaseModel

class ExecutionTrace(BaseModel):
    attempt_number: int
    generated_code: str
    execution_status: str
    error_message: str | None
    duration_ms: int | None

class AnalysisSummary(BaseModel):
    id: str
    dataset_id: str
    question: str
    status: str
    created_at: datetime
    completed_at: datetime | None

class AnalysisHistory(BaseModel):
    id: str
    dataset_id: str
    question: str
    status: str
    plan: dict | None
    report: dict | None = None
    created_at: datetime
    completed_at: datetime | None
    executions: list[ExecutionTrace]

