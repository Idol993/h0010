import { useMemo, useState } from "react";
import axios from "axios";
import { JobDescription, MatchResponse, Resume, MatchResult, SkillItem, ScoreBreakdown } from "./types";

interface Props {
  mode: "match" | "compare";
  jobs: JobDescription[];
  resumes: Resume[];
  onJobChanged?: () => void;
}

interface CompareJob {
  job_id: number;
  job_title: string;
  score: number;
  top_skills: SkillItem[];
  breakdown: ScoreBreakdown;
  highlighted_snippets?: string[];
  recommend_reason?: string;
}

interface CompareItem {
  resume_id?: number;
  name: string;
  jobs: CompareJob[];
}

interface ReviewForm {
  resume_id: number;
  status: "pass" | "pending" | "reject";
  note: string;
  interview_advice: string;
}

const STATUS_OPTIONS = [
  { value: "", label: "全部状态" },
  { value: "pending", label: "待评审" },
  { value: "pass", label: "通过" },
  { value: "reject", label: "淘汰" },
];

const STATUS_LABEL: Record<string, string> = {
  pass: "通过",
  pending: "待定",
  reject: "淘汰",
};

const STATUS_COLOR: Record<string, string> = {
  pass: "#10b981",
  pending: "#f59e0b",
  reject: "#ef4444",
};

export default function MatchView({ mode, jobs, resumes }: Props) {
  const [selectedJob, setSelectedJob] = useState<number | "">("");
  const [selectedCompare, setSelectedCompare] = useState<number[]>([]);
  const [selectedResume, setSelectedResume] = useState<number | "">("");
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [data, setData] = useState<MatchResponse | null>(null);
  const [compareData, setCompareData] = useState<CompareItem[] | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [reviewStatus, setReviewStatus] = useState<string>("");
  const [singleExport, setSingleExport] = useState<number | null>(null);
  const [reviewOpen, setReviewOpen] = useState<ReviewForm | null>(null);

  const loadMatch = async (targetPage?: number) => {
    if (!selectedJob) return;
    const p = targetPage ?? page;
    setLoading(true);
    try {
      const { data } = await axios.get(`/api/match/${selectedJob}`, {
        params: {
          page: p,
          page_size: pageSize,
          review_status: reviewStatus || undefined,
        },
      });
      setData(data);
      if (targetPage !== undefined) setPage(targetPage);
    } finally {
      setLoading(false);
    }
  };

  const loadCompare = async () => {
    if (selectedCompare.length < 2) return;
    setLoading(true);
    try {
      const { data } = await axios.post("/api/match/compare", {
        job_ids: selectedCompare,
        resume_id: selectedResume || null,
      });
      setCompareData(data.comparisons || []);
    } finally {
      setLoading(false);
    }
  };

  const exportAllCSV = () => {
    if (!selectedJob) return;
    const params = new URLSearchParams();
    if (reviewStatus) params.append("review_status", reviewStatus);
    const qs = params.toString();
    window.open(`/api/match/${selectedJob}/export.csv${qs ? "?" + qs : ""}`, "_blank");
  };

  const exportSingleCSV = (resumeId: number) => {
    if (!selectedJob) return;
    window.open(`/api/match/${selectedJob}/export.csv?resume_id=${resumeId}`, "_blank");
  };

  const exportCompareCSV = async () => {
    try {
      const resp = await axios.post("/api/match/compare/export.csv", {
        job_ids: selectedCompare,
        resume_id: selectedResume || null,
      }, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `compare_${selectedCompare.join("_")}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      alert("导出失败: " + (e?.response?.data?.detail || e.message));
    }
  };

  const openReview = (res: MatchResult) => {
    const r = res.review;
    setReviewOpen({
      resume_id: res.resume.id!,
      status: (r?.status as any) || "pending",
      note: r?.note || "",
      interview_advice: r?.interview_advice || "",
    });
  };

  const saveReview = async () => {
    if (!reviewOpen || !selectedJob) return;
    try {
      await axios.post("/api/match/review", {
        job_id: selectedJob,
        resume_id: reviewOpen.resume_id,
        status: reviewOpen.status,
        note: reviewOpen.note,
        interview_advice: reviewOpen.interview_advice,
      });
      setReviewOpen(null);
      await loadMatch();
    } catch (e: any) {
      alert("保存失败: " + (e?.response?.data?.detail || e.message));
    }
  };

  const activeJobs = jobs.filter((j) => j.is_active);

  const totalPages = useMemo(() => {
    if (!data) return 1;
    return Math.max(1, Math.ceil(data.total_candidates / pageSize));
  }, [data, pageSize]);

  const toggleCompareJob = (id: number) => {
    if (selectedCompare.includes(id)) {
      setSelectedCompare(selectedCompare.filter((x) => x !== id));
    } else if (selectedCompare.length < 3) {
      setSelectedCompare([...selectedCompare, id]);
    }
  };

  const renderCard = (result: MatchResult) => {
    const r = result.resume;
    const open = expanded === r.id;
    const rev = result.review;
    return (
      <div key={r.id} className="candidate-card">
        <div className="row" onClick={() => setExpanded(open ? null : (r.id ?? null))} style={{ cursor: "pointer" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className={`rank ${result.rank <= 3 ? "top-3" : ""}`}>{result.rank}</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>
                {r.name || r.filename}
                {rev && (
                  <span style={{
                    marginLeft: 8, fontSize: 11, padding: "1px 6px",
                    borderRadius: 10, color: "#fff", background: STATUS_COLOR[rev.status] || "#aaa",
                  }}>
                    {STATUS_LABEL[rev.status] || "待定"}
                  </span>
                )}
              </div>
              <div className="meta">{r.email || "-"}</div>
            </div>
          </div>
          <span className="badge-score">{result.score.toFixed(1)}</span>
        </div>
        <div style={{ marginBottom: 6 }}>
          {result.top_skills.map((s, i) => (
            <span key={i} className="skill-tag">{s.name}</span>
          ))}
        </div>
        <div className="meta">
          {r.education || "学历未知"} · {r.years_of_experience} 年经验 · 置信度 {Math.round(r.confidence * 100)}%
        </div>
        <div className="breakdown">
          <div>语义相似度: <span className="val">{result.score_breakdown.semantic_similarity.toFixed(1)}</span></div>
          <div>经验加分: <span className="val">+{result.score_breakdown.experience_bonus.toFixed(1)}</span></div>
          <div>学历匹配: <span className="val">+{result.score_breakdown.education_bonus.toFixed(1)}</span></div>
          <div>名企经历: <span className="val">+{result.score_breakdown.famous_company_bonus.toFixed(1)}</span></div>
        </div>
        {result.recommend_reason && (
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            💡 {result.recommend_reason}
          </div>
        )}
        <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button
            className="btn"
            style={{ padding: "4px 10px", fontSize: 12 }}
            onClick={(e) => { e.stopPropagation(); openReview(result); }}
          >
            {rev ? "编辑评审" : "标记评审"}
          </button>
          <button
            className="btn secondary"
            style={{ padding: "4px 10px", fontSize: 12 }}
            onClick={(e) => { e.stopPropagation(); exportSingleCSV(r.id!); }}
          >
            单人导出
          </button>
          <button
            className="btn secondary"
            style={{ padding: "4px 10px", fontSize: 12 }}
            onClick={(e) => { e.stopPropagation(); setExpanded(open ? null : (r.id ?? null)); }}
          >
            {open ? "收起" : "展开详情"}
          </button>
        </div>
        {rev && (rev.note || rev.interview_advice) && (
          <div style={{
            marginTop: 8, fontSize: 12, padding: 8,
            background: "#f8fafc", border: "1px solid var(--border)", borderRadius: 6,
          }}>
            {rev.note && <div><b>备注：</b>{rev.note}</div>}
            {rev.interview_advice && <div style={{ marginTop: 4 }}><b>面试建议：</b>{rev.interview_advice}</div>}
          </div>
        )}
        {open && (
          <div className="expand-detail" onClick={(e) => e.stopPropagation()}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>命中片段：</div>
            {result.highlighted_snippets.length > 0 ? (
              result.highlighted_snippets.map((s, i) => (
                <div key={i} className="snippet" dangerouslySetInnerHTML={{ __html: s }} />
              ))
            ) : (
              <div style={{ color: "var(--text-muted)" }}>无</div>
            )}
            <div style={{ fontWeight: 600, marginTop: 10, marginBottom: 6 }}>简历原文（前2000字）：</div>
            <div style={{ whiteSpace: "pre-wrap", maxHeight: 300, overflow: "auto", fontSize: 12 }}>
              {r.raw_text.slice(0, 2000)}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="panel">
      {mode === "match" && (
        <>
          <div className="filter-bar">
            <label>选择岗位：</label>
            <select
              className="input"
              value={selectedJob}
              onChange={(e) => { setSelectedJob(e.target.value ? Number(e.target.value) : ""); setPage(1); setData(null); }}
            >
              <option value="">-- 请选择岗位 --</option>
              {activeJobs.map((j) => (
                <option key={j.id} value={j.id}>{j.title}</option>
              ))}
            </select>
            <label>评审状态：</label>
            <select
              className="input"
              value={reviewStatus}
              onChange={(e) => { setReviewStatus(e.target.value); setPage(1); }}
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
            <button className="btn" onClick={() => loadMatch(1)} disabled={!selectedJob || loading}>开始匹配</button>
            {data && (
              <>
                <button className="btn secondary" onClick={exportAllCSV}>导出全量 CSV</button>
              </>
            )}
          </div>

          {loading && <div className="empty">匹配中...</div>}

          {!loading && data && (
            <>
              <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 12 }}>
                岗位「{data.job_title}」共匹配 {data.total_candidates} 位候选人
              </div>
              {data.results.length === 0 ? (
                <div className="empty">暂无匹配结果</div>
              ) : (
                <div className="candidate-grid">
                  {data.results.map((r) => renderCard(r))}
                </div>
              )}
              {totalPages > 1 && (
                <div className="pagination">
                  {Array.from({ length: totalPages }).map((_, i) => (
                    <button
                      key={i}
                      className={data?.page === i + 1 ? "active" : ""}
                      onClick={() => loadMatch(i + 1)}
                    >
                      {i + 1}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}

      {mode === "compare" && (
        <>
          <div className="filter-bar">
            <label>选择 2-3 个岗位：</label>
            {activeJobs.map((j) => (
              <button
                key={j.id}
                className={`tab ${selectedCompare.includes(j.id) ? "active" : ""}`}
                onClick={() => toggleCompareJob(j.id)}
              >
                {j.title}
              </button>
            ))}
          </div>
          <div className="filter-bar">
            <label>简历筛选：</label>
            <select
              className="input"
              value={selectedResume}
              onChange={(e) => setSelectedResume(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">全部简历</option>
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>{r.name || r.filename}</option>
              ))}
            </select>
            <button
              className="btn"
              onClick={loadCompare}
              disabled={selectedCompare.length < 2 || loading}
            >
              开始对比
            </button>
            {compareData && compareData.length > 0 && (
              <button className="btn secondary" onClick={exportCompareCSV}>导出 CSV</button>
            )}
          </div>

          {loading && <div className="empty">对比中...</div>}

          {!loading && compareData && compareData.length > 0 && (
            <div className="candidate-grid">
              {compareData.map((c) => (
                <div key={c.resume_id} className="candidate-card">
                  <div style={{ fontWeight: 600, marginBottom: 12 }}>{c.name}</div>
                  {c.jobs.map((j) => (
                    <div key={j.job_id} style={{ marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid var(--border)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 14 }}>
                        <span style={{ fontWeight: 500 }}>{j.job_title}</span>
                        <span className="badge-score">{j.score.toFixed(1)}</span>
                      </div>
                      <div style={{ marginBottom: 6 }}>
                        {j.top_skills && j.top_skills.length > 0 ? (
                          j.top_skills.map((s, i) => (
                            <span key={i} className="skill-tag">{s.name}</span>
                          ))
                        ) : (
                          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>无命中技能</span>
                        )}
                      </div>
                      <div className="breakdown" style={{ fontSize: 11, marginTop: 4, paddingTop: 4, borderTop: "1px dashed var(--border)" }}>
                        <div>语义相似度: <span className="val">{j.breakdown.semantic_similarity.toFixed(1)}</span></div>
                        <div>经验加分: <span className="val">+{j.breakdown.experience_bonus.toFixed(1)}</span></div>
                        <div>学历匹配: <span className="val">+{j.breakdown.education_bonus.toFixed(1)}</span></div>
                        <div>名企经历: <span className="val">+{j.breakdown.famous_company_bonus.toFixed(1)}</span></div>
                      </div>
                      {j.recommend_reason && (
                        <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                          💡 {j.recommend_reason}
                        </div>
                      )}
                      {j.highlighted_snippets && j.highlighted_snippets.length > 0 && (
                        <div style={{ marginTop: 6 }}>
                          {j.highlighted_snippets.slice(0, 2).map((s, i) => (
                            <div key={i} className="snippet" style={{ fontSize: 11 }} dangerouslySetInnerHTML={{ __html: s }} />
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {reviewOpen && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999,
        }} onClick={() => setReviewOpen(null)}>
          <div style={{
            background: "#fff", padding: 24, borderRadius: 10, minWidth: 460,
            boxShadow: "0 10px 30px rgba(0,0,0,0.15)",
          }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0 }}>HR 评审</h3>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13 }}>评审状态</label>
              <select
                className="input"
                value={reviewOpen.status}
                onChange={(e) => setReviewOpen({ ...reviewOpen, status: e.target.value as any })}
              >
                <option value="pending">待定</option>
                <option value="pass">通过</option>
                <option value="reject">淘汰</option>
              </select>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13 }}>备注</label>
              <textarea
                className="input"
                rows={3}
                value={reviewOpen.note}
                onChange={(e) => setReviewOpen({ ...reviewOpen, note: e.target.value })}
                placeholder="备注候选人特点..."
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13 }}>面试建议</label>
              <textarea
                className="input"
                rows={3}
                value={reviewOpen.interview_advice}
                onChange={(e) => setReviewOpen({ ...reviewOpen, interview_advice: e.target.value })}
                placeholder="面试重点考察方向..."
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button className="btn secondary" onClick={() => setReviewOpen(null)}>取消</button>
              <button className="btn" onClick={saveReview}>保存</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
