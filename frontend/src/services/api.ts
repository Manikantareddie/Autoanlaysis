import axios from "axios";

export type QualityWarning = {
  code: string;
  message: string;
  column: string | null;
  severity: "warning" | "error" | "info";
};

export type ColumnProfile = {
  name: string;
  inferred_type: string;
  missing_count: number;
  missing_percentage: number;
  distinct_count: number;
  sample_values: string[];
  numeric_statistics?: { minimum: number | null; maximum: number | null; mean: number | null; median: number | null };
  date_coverage?: { minimum: string | null; maximum: string | null };
};

export type DatasetProfile = {
  row_count: number;
  column_count: number;
  duplicate_row_count: number;
  columns: ColumnProfile[];
  warnings: QualityWarning[];
};

export type DatasetSummary = {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  row_count: number;
  column_count: number;
  status: string;
  created_at: string;
};

export type DatasetDetail = DatasetSummary & { profile: DatasetProfile };

export type DatasetPreview = {
  dataset_id: string;
  columns: string[];
  rows: Record<string, string | number | boolean | null>[];
  limit: number;
};

export type HealthResponse = {
  status: string;
  service: string;
  environment: string;
};

export type PlanStep = {
  step_id: number;
  description: string;
  tool: string;
  expected_output: string;
};

export type AnalysisPlan = {
  objective: string;
  required_columns: string[];
  steps: PlanStep[];
};

export type BusinessReport = {
  executive_summary: string;
  key_findings: string[];
  business_recommendations: string[];
  data_caveats: string[];
};

export type RagEvidenceItem = {
  chunk_id: string;
  chunk_type: string;
  score: number;
  text: string;
  row_id?: number | null;
  column_name?: string | null;
};

export type AnalysisResult = {
  analysis_id: string;
  plan: AnalysisPlan;
  sql: string;
  columns: string[];
  rows: (string | number | boolean | null)[][];
  row_count: number;
  report?: BusinessReport | null;
  routing_path?: "structured_analytics" | "semantic_rag" | "hybrid" | string;
  rag_evidence?: RagEvidenceItem[];
};

export type ExecutionTrace = {
  attempt_number: number;
  generated_code: string;
  execution_status: string;
  error_message: string | null;
  duration_ms: number | null;
};

export type AnalysisSummary = {
  id: string;
  dataset_id: string;
  question: string;
  status: string;
  created_at: string;
  completed_at: string | null;
};

export type AnalysisHistory = {
  id: string;
  dataset_id: string;
  question: string;
  status: string;
  plan: AnalysisPlan | null;
  report?: BusinessReport | null;
  created_at: string;
  completed_at: string | null;
  executions: ExecutionTrace[];
};

export type KpiMetric = {
  label: string;
  value: string | number;
  format: "currency" | "number" | "percentage" | "text";
  description?: string | null;
};

export type DashboardChartItem = {
  label: string;
  value: number;
};

export type DashboardChart = {
  title: string;
  type: "trend" | "category" | "distribution";
  x_label: string;
  y_label: string;
  items: DashboardChartItem[];
};

export type SuggestedQuestion = {
  question: string;
  category: string;
};

export type DatasetDashboard = {
  dataset_id: string;
  kpis: KpiMetric[];
  charts: DashboardChart[];
  suggested_questions: SuggestedQuestion[];
  date_range?: string | null;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45_000,
});

export async function getHealth(): Promise<HealthResponse> {
  return (await api.get<HealthResponse>("/health")).data;
}

export async function listDatasets(): Promise<DatasetSummary[]> {
  return (await api.get<DatasetSummary[]>("/api/v1/datasets")).data;
}

export async function uploadDataset(file: File): Promise<DatasetDetail> {
  const form = new FormData();
  form.append("file", file);
  return (await api.post<DatasetDetail>("/api/v1/datasets", form)).data;
}

export async function getDataset(datasetId: string): Promise<DatasetDetail> {
  return (await api.get<DatasetDetail>("/api/v1/datasets/" + datasetId)).data;
}

export async function getDatasetPreview(datasetId: string): Promise<DatasetPreview> {
  return (await api.get<DatasetPreview>("/api/v1/datasets/" + datasetId + "/preview")).data;
}

export async function getDatasetDashboard(datasetId: string): Promise<DatasetDashboard> {
  return (await api.get<DatasetDashboard>("/api/v1/datasets/" + datasetId + "/dashboard")).data;
}

export async function runAnalysis(
  datasetId: string,
  question: string,
  previousAnalysisId?: string
): Promise<AnalysisResult> {
  return (
    await api.post<AnalysisResult>("/api/v1/analyses/run", {
      dataset_id: datasetId,
      question,
      previous_analysis_id: previousAnalysisId,
    })
  ).data;
}

export async function listAnalyses(datasetId?: string): Promise<AnalysisSummary[]> {
  const params = datasetId ? { dataset_id: datasetId } : {};
  return (await api.get<AnalysisSummary[]>("/api/v1/analyses", { params })).data;
}

export async function getAnalysis(analysisId: string): Promise<AnalysisHistory> {
  return (await api.get<AnalysisHistory>("/api/v1/analyses/" + analysisId)).data;
}

