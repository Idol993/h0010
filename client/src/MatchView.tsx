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
}

interface CompareItem {
  resume_id?: number;
  name: string;
  jobs: CompareJob[];
}

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

  const loadMatch = async (targetPage?: number) => {
    if (!selectedJob) return;
    const p = targetPage ?? page;
    setLoading(true);
    try {
      const { data } = await axios.get(`/api/match/${selectedJob}`, {
        params: { page: p, page_size: pageSize },
      });
      setData(data);
      if (targetPage !== undefined) {
        setPage(targetPage);
      }
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
    return (
      <div key={r.id} className="candidate-card" onClick={() => setExpanded(open ? null : (r.id ?? null))}>
        <div className="row">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className={`rank ${result.rank <= 3 ? "top-3" : ""}`}>{result.rank}</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>{r.name || r.filename}</div>
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
              onChange={(e) => setSelectedJob(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">-- 请选择岗位 --</option>
              {activeJobs.map((j) => (
                <option key={j.id} value={j.id}>{j.title}</option>
              ))}
            </select>
            <button className="btn" onClick={loadMatch} disabled={!selectedJob || loading}>开始匹配</button>
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
          </div>
          {loading && <div className="empty">对比计算中...</div>}
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
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
          {!loading && compareData && compareData.length === 0 && (
            <div className="empty">请选择岗位并点击「开始对比」</div>
          )}
        </>
      )}
    </div>
  );
}
