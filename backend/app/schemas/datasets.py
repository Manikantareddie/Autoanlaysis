from datetime import datetime

from pydantic import BaseModel, Field


class NumericStatistics(BaseModel):
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    median: float | None = None


class DateCoverage(BaseModel):
    minimum: str | None = None
    maximum: str | None = None


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    missing_count: int
    missing_percentage: float
    distinct_count: int
    sample_values: list[str]
    numeric_statistics: NumericStatistics | None = None
    date_coverage: DateCoverage | None = None


class QualityWarning(BaseModel):
    code: str
    message: str
    column: str | None = None
    severity: str


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    duplicate_row_count: int
    columns: list[ColumnProfile]
    warnings: list[QualityWarning]


class DatasetSummary(BaseModel):
    id: str
    original_filename: str
    file_size_bytes: int
    row_count: int
    column_count: int
    status: str
    created_at: datetime


class DatasetDetail(DatasetSummary):
    profile: DatasetProfile


class DatasetPreview(BaseModel):
    dataset_id: str
    columns: list[str]
    rows: list[dict[str, str | int | float | bool | None]]
    limit: int = Field(ge=1, le=100)


class KpiMetric(BaseModel):
    label: str
    value: str | float | int
    format: str
    description: str | None = None


class DashboardChartItem(BaseModel):
    label: str
    value: float


class DashboardChart(BaseModel):
    title: str
    type: str
    x_label: str
    y_label: str
    items: list[DashboardChartItem]


class SuggestedQuestion(BaseModel):
    question: str
    category: str


class DatasetDashboard(BaseModel):
    dataset_id: str
    kpis: list[KpiMetric]
    charts: list[DashboardChart]
    suggested_questions: list[SuggestedQuestion]
    date_range: str | None = None

