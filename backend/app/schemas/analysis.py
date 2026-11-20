from typing import Literal
from pydantic import BaseModel, Field

class PlanStep(BaseModel):
    step_id: int = Field(ge=1, le=4)
    description: str = Field(min_length=1, max_length=500)
    tool: Literal["sql", "python"] = "sql"
    expected_output: str = Field(min_length=1, max_length=200)

class AnalysisPlan(BaseModel):
    objective: str = Field(min_length=1, max_length=500)
    required_columns: list[str] = Field(max_length=20)
    steps: list[PlanStep] = Field(min_length=1, max_length=4)

class AnalysisRequest(BaseModel):
    dataset_id: str
    question: str = Field(min_length=2, max_length=2000)
    previous_analysis_id: str | None = None

class SqlProposal(BaseModel):
    sql: str = Field(min_length=1, max_length=10000)
    explanation: str = Field(min_length=1, max_length=1000)

class BusinessReport(BaseModel):
    executive_summary: str = Field(min_length=1, max_length=2000)
    key_findings: list[str] = Field(default_factory=list, max_length=10)
    business_recommendations: list[str] = Field(default_factory=list, max_length=10)
    data_caveats: list[str] = Field(default_factory=list, max_length=10)

class AnalysisResult(BaseModel):
    analysis_id: str
    plan: AnalysisPlan
    sql: str
    columns: list[str]
    rows: list[list[object]]
    row_count: int
    report: BusinessReport | None = None

