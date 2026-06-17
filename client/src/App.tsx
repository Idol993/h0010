import { useEffect, useState } from "react";
import axios from "axios";
import UploadPanel from "./UploadPanel";
import MatchView from "./MatchView";
import { Resume, JobDescription } from "./types";

type Tab = "upload" | "resumes" | "match" | "compare";

export default function App() {
  const [tab, setTab] = useState<Tab>("upload");
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [jobs, setJobs] = useState<JobDescription[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [r, j] = await Promise.all([
        axios.get("/api/upload/resumes").catch(() => ({ data: { resumes: [] } })),
        axios.get("/api/jobs?active_only=false").catch(() => ({ data: [] })),
      ]);
      setResumes((r.data as any).resumes || []);
      setJobs(j.data || []);
    } finally {
      setLoading(false);
    }
  };

  const onUploaded = () => loadAll();

  return (
    <div>
      <div className="header">
        <h1>智能简历解析与岗位匹配系统</h1>
      </div>
      <div className="container">
        <div className="tabs">
          <button className={`tab ${tab === "upload" ? "active" : ""}`} onClick={() => setTab("upload")}>简历上传</button>
          <button className={`tab ${tab === "resumes" ? "active" : ""}`} onClick={() => setTab("resumes")}>简历库 ({resumes.length})</button>
          <button className={`tab ${tab === "match" ? "active" : ""}`} onClick={() => setTab("match")}>岗位匹配</button>
          <button className={`tab ${tab === "compare" ? "active" : ""}`} onClick={() => setTab("compare")}>岗位对比</button>
        </div>

        {tab === "upload" && <UploadPanel onUploaded={onUploaded} />}

        {tab === "resumes" && (
          <div className="panel">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>已解析简历</h3>
              <button className="btn secondary" onClick={loadAll}>刷新</button>
            </div>
            {resumes.length === 0 ? (
              <div className="empty">暂无简历，请到"简历上传"标签上传</div>
            ) : (
              <div className="resume-list">
                {resumes.map((r) => (
                  <div key={r.id} className="resume-row">
                    <div>#{r.id}</div>
                    <div>
                      <div style={{ fontWeight: 600 }}>{r.name || r.filename}</div>
                      <div className="confidence">{r.email || "-"} | {r.phone || "-"} | {r.education || "-"}</div>
                    </div>
                    <div>{r.years_of_experience} 年经验</div>
                    <div className="confidence">置信度 {Math.round(r.confidence * 100)}%</div>
                    <div style={{ textAlign: "right" }}>
                      {r.skills.slice(0, 3).map((s, i) => (
                        <span key={i} className="skill-tag">{s.name}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "match" && (
          <MatchView mode="match" jobs={jobs} resumes={resumes} onJobChanged={loadAll} />
        )}

        {tab === "compare" && (
          <MatchView mode="compare" jobs={jobs} resumes={resumes} onJobChanged={loadAll} />
        )}
      </div>
    </div>
  );
}
