import { useEffect, useMemo, useState } from "react";
import axios from "axios";

interface DictItem { canonical: string; synonyms: string[]; }
interface Candidate { term: string; frequency: number; first_seen?: string; source_resume_id?: number; }

type SortKey = "freq_desc" | "freq_asc" | "time_desc" | "time_asc";

export default function SkillDictPanel() {
  const [tab, setTab] = useState<"dict" | "candidates">("dict");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [items, setItems] = useState<DictItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalCanonical, setTotalCanonical] = useState(0);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [mergeTarget, setMergeTarget] = useState<string>("");
  const [mergeDropdownOpen, setMergeDropdownOpen] = useState(false);
  const [mergeSearch, setMergeSearch] = useState("");
  const [candidateSort, setCandidateSort] = useState<SortKey>("freq_desc");

  const loadDict = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get("/api/jobs/skills/dict", {
        params: { search, page, page_size: pageSize, include_synonyms: true },
      });
      setItems(data.items || []);
      setTotal(data.total || 0);
      setTotalCanonical(data.total_canonical || 0);
    } finally {
      setLoading(false);
    }
  };

  const loadCandidates = async () => {
    try {
      const { data } = await axios.get("/api/jobs/skills/candidates");
      setCandidates(data.candidates || []);
    } catch (e) {
      setCandidates([]);
    }
  };

  useEffect(() => {
    if (tab === "dict") loadDict();
    else loadCandidates();
  }, [tab, search, page]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const allCanonicalNames = useMemo(() => {
    // fetch all canonical names once for merge dropdown search
    // we'll derive from current loaded items, but also allow the user to type
    // for an accurate list, fetch without search limit on mount
    return items.map(it => it.canonical);
  }, [items]);

  const loadAllCanonicalForMerge = async () => {
    try {
      const { data } = await axios.get("/api/jobs/skills/dict", {
        params: { page: 1, page_size: 1000, include_synonyms: false },
      });
      return (data.items || []).map((i: any) => i.canonical as string);
    } catch (e) { return []; }
  };

  const onApproveNew = async (term: string) => {
    if (!confirm(`将「${term}」作为新技能加入词典？`)) return;
    try {
      await axios.post("/api/jobs/skills/candidates/approve", null, { params: { term, canonical: term } });
      await Promise.all([loadCandidates(), loadDict()]);
    } catch (e: any) {
      alert("审核失败: " + (e?.response?.data?.detail || e.message));
    }
  };

  const onMerge = async (term: string, target: string) => {
    if (!target) { alert("请选择或输入要合并到的技能名"); return; }
    if (!confirm(`将「${term}」合并为「${target}」的同义词？`)) return;
    try {
      await axios.post("/api/jobs/skills/candidates/approve", null, { params: { term, canonical: target } });
      setMergeTarget("");
      setMergeSearch("");
      setMergeDropdownOpen(false);
      await Promise.all([loadCandidates(), loadDict()]);
    } catch (e: any) {
      alert("合并失败: " + (e?.response?.data?.detail || e.message));
    }
  };

  const onAddSkill = async () => {
    const name = prompt("输入技能名称：");
    if (!name) return;
    const synsRaw = prompt("输入同义词（逗号分隔，可为空）：", "");
    const syns = synsRaw ? synsRaw.split(/[,，]/).map(s => s.trim()).filter(Boolean) : [];
    try {
      await axios.post("/api/jobs/skills/dict", null, { params: { canonical: name, synonyms: syns } });
      await loadDict();
    } catch (e: any) {
      alert("新增失败: " + (e?.response?.data?.detail || e.message));
    }
  };

  const sortedCandidates = useMemo(() => {
    const arr = [...candidates];
    switch (candidateSort) {
      case "freq_desc":
        arr.sort((a, b) => b.frequency - a.frequency);
        break;
      case "freq_asc":
        arr.sort((a, b) => a.frequency - b.frequency);
        break;
      case "time_desc":
        arr.sort((a, b) => (b.first_seen || "").localeCompare(a.first_seen || ""));
        break;
      case "time_asc":
        arr.sort((a, b) => (a.first_seen || "").localeCompare(b.first_seen || ""));
        break;
    }
    return arr;
  }, [candidates, candidateSort]);

  // dropdown options
  const [mergeOptions, setMergeOptions] = useState<string[]>([]);
  const openMergeDropdown = async () => {
    const list = await loadAllCanonicalForMerge();
    setMergeOptions(list);
    setMergeDropdownOpen(true);
  };
  const filteredMergeOptions = useMemo(() => {
    if (!mergeSearch) return mergeOptions.slice(0, 50);
    const kw = mergeSearch.toLowerCase();
    return mergeOptions.filter(n => n.toLowerCase().includes(kw)).slice(0, 50);
  }, [mergeOptions, mergeSearch]);

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>技能词典管理</h3>
        <button className="btn secondary" onClick={onAddSkill}>+ 新增技能</button>
      </div>
      <div className="tabs" style={{ marginBottom: 16 }}>
        <button className={`tab ${tab === "dict" ? "active" : ""}`} onClick={() => setTab("dict")}>
          词典 ({totalCanonical})
        </button>
        <button className={`tab ${tab === "candidates" ? "active" : ""}`} onClick={() => setTab("candidates")}>
          候选词 ({candidates.length})
        </button>
      </div>

      {tab === "dict" && (
        <>
          <div className="filter-bar">
            <input
              className="input"
              placeholder="搜索技能或同义词..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              style={{ minWidth: 240 }}
            />
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>共 {total} 条匹配（词典总数 {totalCanonical}）</span>
          </div>
          {loading ? (
            <div className="empty">加载中...</div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10 }}>
              {items.map((it, i) => (
                <div key={i} style={{ padding: 12, border: "1px solid var(--border)", borderRadius: 8, background: "var(--bg)" }}>
                  <div style={{ fontWeight: 600, color: "var(--primary)", marginBottom: 4 }}>{it.canonical}</div>
                  {it.synonyms && it.synonyms.length > 0 ? (
                    <div style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.7 }}>
                      同义词：{it.synonyms.join("、")}
                    </div>
                  ) : (
                    <div style={{ fontSize: 12, color: "var(--text-muted)" }}>暂无同义词</div>
                  )}
                </div>
              ))}
            </div>
          )}
          {totalPages > 1 && (
            <div className="pagination" style={{ marginTop: 16 }}>
              {Array.from({ length: totalPages }).map((_, i) => (
                <button key={i} className={page === i + 1 ? "active" : ""} onClick={() => setPage(i + 1)}>
                  {i + 1}
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "candidates" && (
        <>
          <div className="filter-bar" style={{ marginBottom: 12 }}>
            <label>排序：</label>
            <select
              className="input"
              value={candidateSort}
              onChange={(e) => setCandidateSort(e.target.value as SortKey)}
            >
              <option value="freq_desc">频次从高到低</option>
              <option value="freq_asc">频次从低到高</option>
              <option value="time_desc">最新出现</option>
              <option value="time_asc">最早出现</option>
            </select>
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>共 {candidates.length} 条候选词</span>
          </div>
          {candidates.length === 0 ? (
            <div className="empty">暂无候选词</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {sortedCandidates.map((c, i) => (
                <div key={i} style={{
                  padding: 12, border: "1px solid var(--border)", borderRadius: 8,
                  background: "var(--bg)", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap",
                }}>
                  <div style={{ flex: 1, minWidth: 180 }}>
                    <div style={{ fontWeight: 600 }}>{c.term}</div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                      出现 {c.frequency} 次 · 来源：简历 #{c.source_resume_id || "未知"} · {c.first_seen || ""}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, position: "relative" }}>
                    <input
                      className="input"
                      placeholder="搜索合并目标..."
                      value={mergeSearch}
                      onChange={(e) => setMergeSearch(e.target.value)}
                      onFocus={openMergeDropdown}
                      style={{ width: 180, fontSize: 13 }}
                    />
                    {mergeDropdownOpen && (
                      <div style={{
                        position: "absolute", top: "100%", left: 0, right: 0, marginTop: 2,
                        background: "#fff", border: "1px solid var(--border)", borderRadius: 6,
                        maxHeight: 240, overflow: "auto", zIndex: 50,
                      }}>
                        {filteredMergeOptions.length === 0 ? (
                          <div style={{ padding: 8, fontSize: 12, color: "var(--text-muted)" }}>无匹配，可直接输入自定义词</div>
                        ) : (
                          filteredMergeOptions.map((opt, k) => (
                            <div
                              key={k}
                              onClick={() => { setMergeSearch(opt); setMergeTarget(opt); setMergeDropdownOpen(false); }}
                              style={{ padding: "6px 10px", fontSize: 13, cursor: "pointer" }}
                              onMouseOver={(e) => (e.currentTarget.style.background = "#eff6ff")}
                              onMouseOut={(e) => (e.currentTarget.style.background = "transparent")}
                            >{opt}</div>
                          ))
                        )}
                      </div>
                    )}
                    <button className="btn secondary" onClick={() => onMerge(c.term, mergeSearch || mergeTarget)}>合并</button>
                    <button className="btn" onClick={() => onApproveNew(c.term)}>转正</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
