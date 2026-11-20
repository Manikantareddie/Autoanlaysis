import { type ChangeEvent, useEffect, useState, useRef } from "react";
import axios from "axios";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import {
  Sparkles,
  Database,
  Clock,
  ArrowUpRight,
  BarChart3,
  FileSpreadsheet,
  TrendingUp,
  Search,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Download,
  Calendar,
  Layers,
  ArrowRight,
  Code2,
  RefreshCw,
  X,
} from "lucide-react";

import {
  getDatasetPreview,
  getDataset,
  getDatasetDashboard,
  getHealth,
  listDatasets,
  uploadDataset,
  runAnalysis,
  listAnalyses,
  getAnalysis,
  type DatasetDetail,
  type DatasetPreview,
  type DatasetSummary,
  type DatasetDashboard,
  type AnalysisResult,
  type AnalysisSummary,
  type AnalysisHistory,
} from "./services/api";

type ViewMode = "workspace" | "datasets" | "history";

interface ConversationTurn {
  id: string;
  question: string;
  timestamp: Date;
  result: AnalysisResult;
}

function friendlyError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return typeof error.response?.data?.detail === "string"
      ? error.response.data.detail
      : "The request could not be completed. Please check your data or try again.";
  }
  return "An unexpected error occurred.";
}

function formatNumber(val: unknown, format?: string): string {
  if (typeof val === "number") {
    if (format === "percentage") {
      return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(val) + "%";
    }
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(val);
  }
  return String(val ?? "");
}

// Custom tooltip for clean, soft styling
function CustomChartTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; name?: string }[]; label?: string }) {
  if (active && payload && payload.length > 0) {
    return (
      <div className="custom-chart-tooltip">
        <span className="tooltip-label">{label}</span>
        <span className="tooltip-value">{formatNumber(payload[0].value)}</span>
      </div>
    );
  }
  return null;
}

export default function App() {
  const [view, setView] = useState<ViewMode>("workspace");
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selected, setSelected] = useState<DatasetDetail | null>(null);
  const [dashboard, setDashboard] = useState<DatasetDashboard | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSchemaModal, setShowSchemaModal] = useState(false);

  // Analysis state
  const [question, setQuestion] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState<"planning" | "executing" | "synthesizing">("planning");
  const [conversation, setConversation] = useState<ConversationTurn[]>([]);
  const [openMethodologyTurnId, setOpenMethodologyTurnId] = useState<string | null>(null);
  const [showSqlAuditId, setShowSqlAuditId] = useState<string | null>(null);

  // History state
  const [historyList, setHistoryList] = useState<AnalysisSummary[]>([]);
  const [activeHistoryItem, setActiveHistoryItem] = useState<AnalysisHistory | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const questionInputRef = useRef<HTMLInputElement>(null);
  const conversationEndRef = useRef<HTMLDivElement>(null);

  async function loadInitial() {
    try {
      await getHealth();
      const list = await listDatasets();
      setDatasets(list);
      const hist = await listAnalyses();
      setHistoryList(hist);
    } catch {
      // Backend may be starting
    }
  }

  useEffect(() => {
    void loadInitial();
  }, []);

  useEffect(() => {
    if (conversation.length > 0) {
      conversationEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [conversation, analyzing]);

  async function handleSelectDataset(id: string) {
    setError(null);
    setConversation([]);
    try {
      const detail = await getDataset(id);
      setSelected(detail);
      const [dash, prev] = await Promise.all([
        getDatasetDashboard(id).catch(() => null),
        getDatasetPreview(id).catch(() => null),
      ]);
      setDashboard(dash);
      setPreview(prev);
      setView("workspace");
    } catch (err) {
      setError(friendlyError(err));
    }
  }

  async function handleFileUpload(file: File) {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a standard CSV file (.csv).");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const created = await uploadDataset(file);
      const list = await listDatasets();
      setDatasets(list);
      await handleSelectDataset(created.id);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setUploading(false);
    }
  }

  function onFileInputChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (f) void handleFileUpload(f);
  }

  async function submitQuestion(q: string, previousAnalysisId?: string) {
    if (!selected) {
      setError("Please select or upload a dataset first.");
      return;
    }
    if (!q.trim()) return;

    setAnalyzing(true);
    setAnalysisStep("planning");
    setError(null);

    const stepTimer = setTimeout(() => {
      setAnalysisStep("executing");
      setTimeout(() => setAnalysisStep("synthesizing"), 1500);
    }, 1200);

    try {
      const result = await runAnalysis(selected.id, q, previousAnalysisId);
      clearTimeout(stepTimer);

      const turn: ConversationTurn = {
        id: result.analysis_id,
        question: q,
        timestamp: new Date(),
        result,
      };

      setConversation((prev) => [...prev, turn]);
      setQuestion("");
      void listAnalyses(selected.id).then(setHistoryList).catch(() => {});
    } catch (err) {
      clearTimeout(stepTimer);
      setError(friendlyError(err));
    } finally {
      setAnalyzing(false);
    }
  }

  async function openHistoryDetail(id: string) {
    setLoadingHistory(true);
    try {
      const detail = await getAnalysis(id);
      setActiveHistoryItem(detail);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setLoadingHistory(false);
    }
  }

  function loadHistoryIntoWorkspace(item: AnalysisHistory) {
    if (!selected || selected.id !== item.dataset_id) {
      void handleSelectDataset(item.dataset_id).then(() => {
        if (item.plan && item.executions.length > 0) {
          const fakeResult: AnalysisResult = {
            analysis_id: item.id,
            plan: item.plan,
            sql: item.executions[0].generated_code,
            columns: [],
            rows: [],
            row_count: 0,
            report: item.report,
          };
          setConversation([
            {
              id: item.id,
              question: item.question,
              timestamp: new Date(item.created_at),
              result: fakeResult,
            },
          ]);
        }
        setView("workspace");
      });
    } else {
      if (item.plan && item.executions.length > 0) {
        const fakeResult: AnalysisResult = {
          analysis_id: item.id,
          plan: item.plan,
          sql: item.executions[0].generated_code,
          columns: [],
          rows: [],
          row_count: 0,
          report: item.report,
        };
        setConversation((prev) => [
          ...prev,
          {
            id: item.id,
            question: item.question,
            timestamp: new Date(item.created_at),
            result: fakeResult,
          },
        ]);
      }
      setView("workspace");
    }
  }

  // Determine chart rendering for an analysis turn
  function getTurnChartData(result: AnalysisResult) {
    if (!result || result.rows.length === 0 || result.columns.length < 2) return null;

    const firstCol = result.columns[0];
    const secondCol = result.columns[1];
    const valid = result.rows
      .filter((r) => r[0] != null && typeof r[1] === "number" && !isNaN(r[1]))
      .slice(0, 15)
      .map((r) => ({
        label: String(r[0]),
        value: r[1] as number,
      }));

    if (valid.length < 2) return null;

    const isTimeSeries =
      firstCol.toLowerCase().includes("month") ||
      firstCol.toLowerCase().includes("date") ||
      firstCol.toLowerCase().includes("year") ||
      firstCol.toLowerCase().includes("period") ||
      /^\d{4}-\d{2}/.test(valid[0].label);

    return {
      type: isTimeSeries ? ("line" as const) : ("bar" as const),
      xKey: firstCol,
      yKey: secondCol,
      data: valid,
    };
  }

  function downloadReport(turn: ConversationTurn) {
    const lines = [
      `# InsightPilot AI — Analysis Report`,
      `**Question:** ${turn.question}`,
      `**Dataset:** ${selected?.original_filename || "Dataset"}`,
      `**Date:** ${turn.timestamp.toLocaleString()}`,
      `\n## Executive Summary`,
      turn.result.report?.executive_summary || "No executive summary available.",
      `\n## Key Findings`,
      ...(turn.result.report?.key_findings.map((f) => `- ${f}`) || ["- Data verified in DuckDB."]),
    ];

    if (turn.result.report?.business_recommendations?.length) {
      lines.push(`\n## Business Recommendations`);
      lines.push(...turn.result.report.business_recommendations.map((r) => `- ${r}`));
    }

    if (turn.result.report?.data_caveats?.length) {
      lines.push(`\n## Data Caveats`);
      lines.push(...turn.result.report.data_caveats.map((c) => `- ${c}`));
    }

    lines.push(`\n## Calculation Trace (SQL)`);
    lines.push(`\`\`\`sql\n${turn.result.sql}\n\`\`\``);

    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `InsightPilot_Analysis_${turn.id.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="saas-shell">
      {/* 1. TOP APPLICATION NAVIGATION */}
      <header className="saas-header">
        <div className="saas-header-inner">
          <div className="brand-group">
            <div className="brand-badge-icon">
              <Sparkles size={16} strokeWidth={2.5} />
            </div>
            <div>
              <span className="brand-title">InsightPilot</span>
              <span className="brand-badge">AI Analyst</span>
            </div>
          </div>

          <nav className="nav-tabs-group">
            <button
              type="button"
              className={`nav-tab-item ${view === "workspace" ? "active" : ""}`}
              onClick={() => setView("workspace")}
            >
              <BarChart3 size={15} />
              <span>Workspace</span>
            </button>
            <button
              type="button"
              className={`nav-tab-item ${view === "datasets" ? "active" : ""}`}
              onClick={() => {
                setView("datasets");
                void listDatasets().then(setDatasets).catch(() => {});
              }}
            >
              <Database size={15} />
              <span>Datasets {datasets.length > 0 && `(${datasets.length})`}</span>
            </button>
            <button
              type="button"
              className={`nav-tab-item ${view === "history" ? "active" : ""}`}
              onClick={() => {
                setView("history");
                void listAnalyses(selected?.id).then(setHistoryList).catch(() => {});
              }}
            >
              <Clock size={15} />
              <span>History {historyList.length > 0 && `(${historyList.length})`}</span>
            </button>
          </nav>

          <div className="header-actions">
            {selected && (
              <div className="active-pill-badge" title="Active dataset in DuckDB">
                <span className="dot-indicator" />
                <span className="pill-name">{selected.original_filename}</span>
                <span className="pill-count">({selected.row_count.toLocaleString()} rows)</span>
              </div>
            )}
            <button
              type="button"
              className="btn-upload-nav"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              <FileSpreadsheet size={14} />
              <span>{uploading ? "Ingesting…" : "Upload CSV"}</span>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              style={{ display: "none" }}
              onChange={onFileInputChange}
            />
          </div>
        </div>
      </header>

      {/* 2. MAIN APPLICATION CONTENT AREA */}
      <main className="saas-main">
        {error && (
          <div className="banner-alert" role="alert">
            <AlertCircle size={16} className="alert-icon" />
            <span className="alert-message">{error}</span>
            <button type="button" className="alert-close" onClick={() => setError(null)}>
              <X size={14} />
            </button>
          </div>
        )}

        {/* ========================================================
            VIEW 1: WORKSPACE (Main Experience: Upload -> Explore -> Ask)
            ======================================================== */}
        {view === "workspace" && (
          <>
            {/* STATE A: NO DATASET SELECTED -> UPLOAD-FIRST LANDING */}
            {!selected && (
              <div className="landing-upload-card">
                <div className="landing-copy">
                  <div className="product-chip">
                    <Sparkles size={12} />
                    <span>Autonomous Business Intelligence</span>
                  </div>
                  <h1 className="landing-headline">Turn raw CSV data into verified answers.</h1>
                  <p className="landing-subtitle">
                    Upload any CSV file. InsightPilot automatically generates an intelligent executive dashboard,
                    profiles quality, and answers your natural-language questions with verified SQL calculations.
                  </p>
                </div>

                {/* Drag and Drop Upload Card */}
                <div
                  className={`saas-dropzone ${isDragging ? "active-drag" : ""}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setIsDragging(false);
                    const file = e.dataTransfer.files?.[0];
                    if (file) void handleFileUpload(file);
                  }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="dropzone-inner-content">
                    <div className="dropzone-icon-box">
                      <FileSpreadsheet size={28} strokeWidth={1.75} />
                    </div>
                    <div className="dropzone-text-group">
                      <strong className="dropzone-title">
                        {uploading ? "Ingesting & profiling dataset in DuckDB…" : "Drop your CSV here, or browse files"}
                      </strong>
                      <span className="dropzone-desc">
                        Supports standard CSV files up to 25 MB and 100,000 rows. No sensitive data leaves your server.
                      </span>
                    </div>
                    <button type="button" className="btn-browse-action" disabled={uploading}>
                      Choose File
                    </button>
                  </div>
                </div>

                {/* Recent Datasets Quick Select */}
                {datasets.length > 0 && (
                  <div className="recent-datasets-tray">
                    <span className="recent-tray-label">Or resume with a previous dataset:</span>
                    <div className="recent-pills-row">
                      {datasets.slice(0, 4).map((d) => (
                        <button
                          key={d.id}
                          type="button"
                          className="recent-dataset-pill"
                          onClick={() => void handleSelectDataset(d.id)}
                        >
                          <Database size={13} />
                          <span className="filename">{d.original_filename}</span>
                          <span className="rowcount">{d.row_count.toLocaleString()} rows</span>
                          <ArrowRight size={12} className="arrow" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* STATE B: DATASET SELECTED -> INTELLIGENT DASHBOARD & AI ANALYST */}
            {selected && (
              <div className="workspace-flow">
                {/* Active Dataset Overview Bar */}
                <div className="dataset-overview-strip">
                  <div className="strip-left">
                    <div className="file-avatar">
                      <FileSpreadsheet size={18} />
                    </div>
                    <div>
                      <div className="file-name-row">
                        <h2 className="file-name">{selected.original_filename}</h2>
                        <span className="badge-meta">
                          {selected.row_count.toLocaleString()} rows · {selected.column_count} columns
                        </span>
                        {dashboard?.date_range && (
                          <span className="badge-date">
                            <Calendar size={12} />
                            <span>{dashboard.date_range}</span>
                          </span>
                        )}
                      </div>
                      <div className="data-policy-notice">
                        <CheckCircle2 size={12} className="check-icon" />
                        <span>All rows verified in read-only DuckDB boundary. Calculations adhere to strict data policies.</span>
                      </div>
                    </div>
                  </div>

                  <div className="strip-actions">
                    <button
                      type="button"
                      className="btn-subtle"
                      onClick={() => setShowSchemaModal(true)}
                    >
                      <Layers size={14} />
                      <span>Data Schema</span>
                    </button>
                    <button
                      type="button"
                      className="btn-subtle"
                      onClick={() => {
                        setSelected(null);
                        setDashboard(null);
                        setPreview(null);
                        setConversation([]);
                      }}
                    >
                      <span>Switch File</span>
                    </button>
                  </div>
                </div>

                {/* 1. Intelligent Executive KPI Cards */}
                {dashboard && dashboard.kpis.length > 0 && (
                  <section className="executive-kpi-grid">
                    {dashboard.kpis.map((kpi, idx) => (
                      <div key={idx} className="kpi-metric-card">
                        <span className="kpi-label">{kpi.label}</span>
                        <div className="kpi-value-row">
                          <span className="kpi-value">{formatNumber(kpi.value, kpi.format)}</span>
                        </div>
                        {kpi.description && <span className="kpi-caption">{kpi.description}</span>}
                      </div>
                    ))}
                  </section>
                )}

                {/* 2. Automatic Visual Intelligence Overview Charts (Recharts) */}
                {dashboard && dashboard.charts.length > 0 && (
                  <section className="dashboard-visuals-grid">
                    {dashboard.charts.map((ch, idx) => {
                      const isTrend = ch.type === "trend" || ch.title.toLowerCase().includes("trend");

                      return (
                        <div key={idx} className="visual-chart-card">
                          <div className="chart-card-header">
                            <div>
                              <h3 className="chart-card-title">{ch.title}</h3>
                              <span className="chart-card-sub">
                                {ch.y_label} across {ch.x_label}
                              </span>
                            </div>
                            {isTrend ? (
                              <TrendingUp size={15} className="chart-type-icon" />
                            ) : (
                              <BarChart3 size={15} className="chart-type-icon" />
                            )}
                          </div>

                          <div className="chart-render-wrap">
                            <ResponsiveContainer width="100%" height={220}>
                              {isTrend ? (
                                <LineChart data={ch.items} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                  <XAxis
                                    dataKey="label"
                                    tick={{ fontSize: 11, fill: "#64748b" }}
                                    axisLine={{ stroke: "#e2e8f0" }}
                                    tickLine={false}
                                  />
                                  <YAxis
                                    tick={{ fontSize: 11, fill: "#64748b" }}
                                    axisLine={false}
                                    tickLine={false}
                                    tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))}
                                  />
                                  <Tooltip content={<CustomChartTooltip />} />
                                  <Line
                                    type="monotone"
                                    dataKey="value"
                                    stroke="#0f172a"
                                    strokeWidth={2.2}
                                    dot={{ fill: "#0f172a", r: 3 }}
                                    activeDot={{ r: 5, fill: "#0f172a" }}
                                  />
                                </LineChart>
                              ) : (
                                <BarChart data={ch.items} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                  <XAxis
                                    dataKey="label"
                                    tick={{ fontSize: 11, fill: "#64748b" }}
                                    axisLine={{ stroke: "#e2e8f0" }}
                                    tickLine={false}
                                  />
                                  <YAxis
                                    tick={{ fontSize: 11, fill: "#64748b" }}
                                    axisLine={false}
                                    tickLine={false}
                                    tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))}
                                  />
                                  <Tooltip content={<CustomChartTooltip />} />
                                  <Bar dataKey="value" fill="#334155" radius={[4, 4, 0, 0]} />
                                </BarChart>
                              )}
                            </ResponsiveContainer>
                          </div>
                        </div>
                      );
                    })}
                  </section>
                )}

                {/* 3. AI Question & Conversation Thread */}
                <section className="qa-conversation-stream">
                  {conversation.map((turn, ti) => {
                    const chartData = getTurnChartData(turn.result);
                    const isMethodologyOpen = openMethodologyTurnId === turn.id;
                    const isSqlAuditOpen = showSqlAuditId === turn.id;
                    const isSimpleFact =
                      turn.result.rows.length <= 1 &&
                      turn.result.columns.length <= 2 &&
                      (!turn.result.report?.business_recommendations?.length || turn.result.report.business_recommendations.length === 0);

                    return (
                      <article key={turn.id} className="qa-turn-card">
                        {/* User Question Bubble */}
                        <div className="user-question-row">
                          <div className="user-avatar">Q</div>
                          <div className="user-question-text">
                            <h4>{turn.question}</h4>
                            <span className="question-time">
                              {turn.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </span>
                          </div>
                          <div className="turn-actions">
                            <button
                              type="button"
                              className="btn-download-icon"
                              title="Download Markdown Report"
                              onClick={() => downloadReport(turn)}
                            >
                              <Download size={14} />
                            </button>
                          </div>
                        </div>

                        {/* AI Executive Answer */}
                        <div className="ai-response-body">
                          {/* Direct Executive Summary */}
                          {turn.result.report && (
                            <div className="ai-executive-summary">
                              <div className="summary-chip-row">
                                <div className="summary-chip">
                                  <Sparkles size={13} />
                                  <span>Verified Answer</span>
                                </div>
                                {turn.result.routing_path && (
                                  <span className={`route-badge ${turn.result.routing_path}`}>
                                    {turn.result.routing_path === "semantic_rag"
                                      ? "🔍 Semantic Search"
                                      : turn.result.routing_path === "hybrid"
                                      ? "⚡🔍 Hybrid RAG"
                                      : "⚡ SQL Analytics"}
                                  </span>
                                )}
                              </div>
                              <p className="summary-prose">{turn.result.report.executive_summary}</p>
                            </div>
                          )}

                          {/* Adaptive Presentation: Single Metric Highlight for Simple Count/Fact Questions */}
                          {isSimpleFact && turn.result.rows.length === 1 && (
                            <div className="single-fact-callout">
                              <span className="fact-label">{turn.result.columns[turn.result.columns.length - 1].replace(/_/g, " ").toUpperCase()}</span>
                              <span className="fact-value">{formatNumber(turn.result.rows[0][turn.result.rows[0].length - 1])}</span>
                            </div>
                          )}

                          {/* Key Findings Grid (When comparison or strategic) */}
                          {turn.result.report && turn.result.report.key_findings.length > 0 && !isSimpleFact && (
                            <div className="findings-section">
                              <h5 className="section-small-title">Key Observations</h5>
                              <ul className="findings-bullet-list">
                                {turn.result.report.key_findings.map((f, fi) => (
                                  <li key={fi}>
                                    <span className="bullet-point" />
                                    <span>{f}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Strategic Recommendations (Only when applicable) */}
                          {turn.result.report?.business_recommendations && turn.result.report.business_recommendations.length > 0 && (
                            <div className="recommendations-box">
                              <h5 className="section-small-title">Strategic Next Steps</h5>
                              <ul className="recommendations-list">
                                {turn.result.report.business_recommendations.map((rec, ri) => (
                                  <li key={ri}>
                                    <ArrowUpRight size={14} className="rec-icon" />
                                    <span>{rec}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Data Caveats (Only when quality exceptions or returns detected) */}
                          {turn.result.report?.data_caveats && turn.result.report.data_caveats.length > 0 && (
                            <div className="caveats-note">
                              <AlertCircle size={14} />
                              <span>{turn.result.report.data_caveats.join(" ")}</span>
                            </div>
                          )}

                          {/* Interactive Chart for Multi-row Answers */}
                          {chartData && (
                            <div className="answer-chart-container">
                              <div className="answer-chart-header">
                                <span className="answer-chart-title">
                                  {chartData.yKey.replace(/_/g, " ")} by {chartData.xKey.replace(/_/g, " ")}
                                </span>
                              </div>
                              <ResponsiveContainer width="100%" height={240}>
                                {chartData.type === "line" ? (
                                  <LineChart data={chartData.data} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={{ stroke: "#e2e8f0" }} tickLine={false} />
                                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))} />
                                    <Tooltip content={<CustomChartTooltip />} />
                                    <Line type="monotone" dataKey="value" stroke="#0f172a" strokeWidth={2.4} dot={{ fill: "#0f172a", r: 3 }} activeDot={{ r: 5 }} />
                                  </LineChart>
                                ) : (
                                  <BarChart data={chartData.data} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={{ stroke: "#e2e8f0" }} tickLine={false} />
                                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))} />
                                    <Tooltip content={<CustomChartTooltip />} />
                                    <Bar dataKey="value" fill="#0f172a" radius={[4, 4, 0, 0]} />
                                  </BarChart>
                                )}
                              </ResponsiveContainer>
                            </div>
                          )}

                          {/* RAG Retrieved Evidence & Citations */}
                          {turn.result.rag_evidence && turn.result.rag_evidence.length > 0 && (
                            <div className="rag-evidence-card">
                              <div className="evidence-header">
                                <Search size={13} className="evidence-icon" />
                                <span className="evidence-title">
                                  Retrieved Evidence ({turn.result.rag_evidence.length} sources matched in vector index)
                                </span>
                              </div>
                              <div className="evidence-grid">
                                {turn.result.rag_evidence.slice(0, 6).map((ev, ei) => (
                                  <div key={ei} className="evidence-item">
                                    <div className="evidence-meta">
                                      <span className="evidence-ref">
                                        {ev.row_id ? `Record #${ev.row_id}` : ev.column_name ? `Col: ${ev.column_name}` : "Schema context"}
                                      </span>
                                      <span className="evidence-score">
                                        {(ev.score * 100).toFixed(0)}% match
                                      </span>
                                    </div>
                                    <p className="evidence-text">{ev.text}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* How This Was Calculated (Plain English Methodology) */}
                          <div className="methodology-accordion">
                            <button
                              type="button"
                              className="methodology-trigger"
                              onClick={() => setOpenMethodologyTurnId(isMethodologyOpen ? null : turn.id)}
                            >
                              <span>How this was calculated</span>
                              {isMethodologyOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            </button>

                            {isMethodologyOpen && (
                              <div className="methodology-content">
                                <p className="methodology-objective">
                                  <strong>Plan Objective:</strong> {turn.result.plan.objective}
                                </p>
                                <p className="methodology-steps">
                                  Calculated over <strong>{turn.result.row_count} verified rows</strong> in DuckDB.
                                  Targeted dataset columns: {turn.result.columns.join(", ")}.
                                </p>

                                {/* Optional Technical View for Developers / Auditing */}
                                <div className="technical-audit-toggle-row">
                                  <button
                                    type="button"
                                    className="btn-technical-toggle"
                                    onClick={() => setShowSqlAuditId(isSqlAuditOpen ? null : turn.id)}
                                  >
                                    <Code2 size={13} />
                                    <span>{isSqlAuditOpen ? "Hide SQL Statement" : "View SQL Statement & Raw Rows"}</span>
                                  </button>
                                </div>

                                {isSqlAuditOpen && (
                                  <div className="technical-code-box">
                                    <pre className="sql-code-block">{turn.result.sql}</pre>
                                    <div className="raw-table-scroll">
                                      <table className="clean-audit-table">
                                        <thead>
                                          <tr>{turn.result.columns.map((c) => <th key={c}>{c}</th>)}</tr>
                                        </thead>
                                        <tbody>
                                          {turn.result.rows.slice(0, 20).map((row, ri) => (
                                            <tr key={ri}>
                                              {row.map((cell, ci) => <td key={ci}>{formatNumber(cell)}</td>)}
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>

                          {/* Follow-up Question Suggestions on Latest Answer */}
                          {ti === conversation.length - 1 && (
                            <div className="follow-up-suggestions-bar">
                              <span className="follow-up-hint">Suggested follow-ups:</span>
                              <div className="follow-up-pills">
                                <button
                                  type="button"
                                  className="pill-suggest-btn"
                                  onClick={() => void submitQuestion("Compare this with the top performing category", turn.id)}
                                  disabled={analyzing}
                                >
                                  Compare with top performing category
                                </button>
                                <button
                                  type="button"
                                  className="pill-suggest-btn"
                                  onClick={() => void submitQuestion("Show the month-over-month trend for these figures", turn.id)}
                                  disabled={analyzing}
                                >
                                  Show monthly trend for this
                                </button>
                                <button
                                  type="button"
                                  className="pill-suggest-btn"
                                  onClick={() => void submitQuestion("Are there any returns or anomalies affecting this metric?", turn.id)}
                                  disabled={analyzing}
                                >
                                  Check for returns or anomalies
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      </article>
                    );
                  })}

                  {/* Multi-step Analysis Progress Indicator */}
                  {analyzing && (
                    <div className="analysis-progress-card">
                      <div className="progress-spinner-ring" />
                      <div className="progress-text-stack">
                        <strong className="progress-current-title">
                          {analysisStep === "planning" && "Understanding business question & building plan…"}
                          {analysisStep === "executing" && "Executing verified calculations in DuckDB…"}
                          {analysisStep === "synthesizing" && "Synthesizing executive findings & charts…"}
                        </strong>
                        <span className="progress-sub">Treating dataset as untrusted data · Read-only AST boundary</span>
                      </div>
                    </div>
                  )}

                  <div ref={conversationEndRef} />
                </section>

                {/* 4. Question Input Composer (Persistent at bottom of Workspace) */}
                <div className="sticky-composer-container">
                  <div className="composer-input-wrapper">
                    <Search size={18} className="search-icon" />
                    <input
                      ref={questionInputRef}
                      type="text"
                      className="composer-text-input"
                      placeholder="Ask any business question in plain English (e.g. 'What are the top 3 categories by revenue?')"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !analyzing && question.trim()) {
                          const lastId = conversation.length > 0 ? conversation[conversation.length - 1].id : undefined;
                          void submitQuestion(question, lastId);
                        }
                      }}
                      disabled={analyzing}
                    />
                    <button
                      type="button"
                      className="btn-submit-question"
                      disabled={analyzing || !question.trim()}
                      onClick={() => {
                        const lastId = conversation.length > 0 ? conversation[conversation.length - 1].id : undefined;
                        void submitQuestion(question, lastId);
                      }}
                    >
                      {analyzing ? <RefreshCw size={14} className="spin-icon" /> : "Ask AI"}
                    </button>
                  </div>

                  {/* Schema-aware Suggested Questions */}
                  {dashboard && dashboard.suggested_questions.length > 0 && (
                    <div className="composer-suggestions-row">
                      <span className="suggestions-label">Suggestions:</span>
                      <div className="suggestions-scroll">
                        {dashboard.suggested_questions.map((sq, i) => (
                          <button
                            key={i}
                            type="button"
                            className="suggestion-chip"
                            onClick={() => {
                              setQuestion(sq.question);
                              const lastId = conversation.length > 0 ? conversation[conversation.length - 1].id : undefined;
                              void submitQuestion(sq.question, lastId);
                            }}
                            disabled={analyzing}
                          >
                            <span>{sq.question}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* ========================================================
            VIEW 2: DATASETS (Catalog of Uploaded Files)
            ======================================================== */}
        {view === "datasets" && (
          <div className="datasets-view-container">
            <div className="view-header-row">
              <div>
                <h2 className="view-title">Uploaded Datasets</h2>
                <p className="view-subtitle">Select any dataset to launch into the analysis workspace.</p>
              </div>
              <button
                type="button"
                className="btn-upload-primary"
                onClick={() => fileInputRef.current?.click()}
              >
                <FileSpreadsheet size={15} />
                <span>Upload New CSV</span>
              </button>
            </div>

            {datasets.length === 0 ? (
              <div className="empty-state-box">
                <Database size={32} strokeWidth={1.5} />
                <p>No datasets uploaded yet.</p>
                <button type="button" className="btn-browse-action" onClick={() => fileInputRef.current?.click()}>
                  Upload Your First CSV
                </button>
              </div>
            ) : (
              <div className="datasets-grid">
                {datasets.map((d) => (
                  <div key={d.id} className="dataset-catalog-card">
                    <div className="card-top">
                      <div className="dataset-avatar">
                        <FileSpreadsheet size={20} />
                      </div>
                      <div className="dataset-info">
                        <h4 className="dataset-name">{d.original_filename}</h4>
                        <span className="dataset-meta-line">
                          {d.row_count.toLocaleString()} rows · {d.column_count} columns · {(d.file_size_bytes / 1024).toFixed(1)} KB
                        </span>
                      </div>
                    </div>

                    <div className="card-footer">
                      <span className="card-date">{new Date(d.created_at).toLocaleDateString()}</span>
                      <button
                        type="button"
                        className="btn-open-dataset"
                        onClick={() => void handleSelectDataset(d.id)}
                      >
                        <span>Open Workspace</span>
                        <ArrowRight size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ========================================================
            VIEW 3: HISTORY (Past Analysis Conversations)
            ======================================================== */}
        {view === "history" && (
          <div className="history-view-container">
            <div className="view-header-row">
              <div>
                <h2 className="view-title">Analysis History</h2>
                <p className="view-subtitle">Review previous AI business answers and calculations.</p>
              </div>
            </div>

            <div className="history-master-detail">
              {/* Left Column: List of Analyses */}
              <div className="history-list-pane">
                {historyList.length === 0 ? (
                  <p className="empty-history-text">No past analyses recorded.</p>
                ) : (
                  <div className="history-items-stack">
                    {historyList.map((h) => (
                      <div
                        key={h.id}
                        className={`history-item-entry ${activeHistoryItem?.id === h.id ? "active" : ""}`}
                        onClick={() => void openHistoryDetail(h.id)}
                      >
                        <strong className="history-item-question">{h.question}</strong>
                        <div className="history-item-meta">
                          <span>{new Date(h.created_at).toLocaleDateString([], { month: "short", day: "numeric" })} at {new Date(h.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                          <span className={`status-pill ${h.status}`}>{h.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right Column: Detailed View */}
              <div className="history-detail-pane">
                {loadingHistory && <p className="loading-state-text">Loading analysis…</p>}
                {!loadingHistory && !activeHistoryItem && (
                  <div className="history-placeholder">
                    <Clock size={36} strokeWidth={1.5} />
                    <p>Select any analysis from the left to view the verified results.</p>
                  </div>
                )}
                {!loadingHistory && activeHistoryItem && (
                  <div className="history-record-view">
                    <div className="record-header">
                      <h3>{activeHistoryItem.question}</h3>
                      <button
                        type="button"
                        className="btn-restore-workspace"
                        onClick={() => loadHistoryIntoWorkspace(activeHistoryItem)}
                      >
                        <span>Reopen in Workspace</span>
                        <ArrowUpRight size={13} />
                      </button>
                    </div>

                    {activeHistoryItem.report && (
                      <div className="history-executive-box">
                        <strong>Executive Summary</strong>
                        <p>{activeHistoryItem.report.executive_summary}</p>
                      </div>
                    )}

                    {activeHistoryItem.report?.key_findings && (
                      <div className="history-findings-box">
                        <h5>Key Observations</h5>
                        <ul>
                          {activeHistoryItem.report.key_findings.map((f, i) => (
                            <li key={i}>{f}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {activeHistoryItem.executions.length > 0 && (
                      <div className="history-code-trace">
                        <h5>Executed SQL</h5>
                        <pre className="sql-code-block">{activeHistoryItem.executions[0].generated_code}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* 3. SCHEMA DETAILS MODAL */}
      {showSchemaModal && selected && (
        <div className="modal-backdrop" onClick={() => setShowSchemaModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 className="modal-title">Dataset Profiling & Schema</h3>
                <span className="modal-sub">
                  {selected.original_filename} · {selected.profile.duplicate_row_count} duplicates detected
                </span>
              </div>
              <button type="button" className="btn-close-modal" onClick={() => setShowSchemaModal(false)}>
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              <div className="clean-table-scroll-container">
                <table className="schema-table">
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>Type</th>
                      <th>Missing</th>
                      <th>Distinct</th>
                      <th>Sample Values</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selected.profile.columns.map((c) => (
                      <tr key={c.name}>
                        <td><strong>{c.name}</strong></td>
                        <td><span className="type-chip">{c.inferred_type}</span></td>
                        <td>{c.missing_count} ({c.missing_percentage}%)</td>
                        <td>{c.distinct_count}</td>
                        <td className="sample-cell">{c.sample_values.join(", ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {preview && (
                <div className="preview-table-section">
                  <h4 className="preview-title">First 20 Ingested Records</h4>
                  <div className="clean-table-scroll-container">
                    <table className="schema-table">
                      <thead>
                        <tr>{preview.columns.map((col) => <th key={col}>{col}</th>)}</tr>
                      </thead>
                      <tbody>
                        {preview.rows.map((row, ri) => (
                          <tr key={ri}>
                            {preview.columns.map((col) => <td key={col}>{formatNumber(row[col])}</td>)}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
