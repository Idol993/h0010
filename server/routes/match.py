from typing import List, Optional, Dict, Any
import io
import csv
import html

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.models import MatchResponse, MatchResult
from server.services.matcher import matcher
from server import db

router = APIRouter(prefix="/api/match", tags=["match"])


class CompareRequest(BaseModel):
    job_ids: List[int]
    resume_id: Optional[int] = None


def _paginate(items, page: int, page_size: int):
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total


def _recommend_reason(m: MatchResult, jd_title: str = "") -> str:
    reasons = []
    if m.score >= 85:
        reasons.append("整体匹配度极高，强烈推荐")
    elif m.score >= 70:
        reasons.append("整体匹配度较好，建议进入面试")
    elif m.score >= 50:
        reasons.append("有一定匹配度，可进一步评估")
    else:
        reasons.append("匹配度偏低，建议参考后决定")
    top = [s.name for s in m.top_skills[:3]]
    if top:
        reasons.append(f"核心技能匹配：{'、'.join(top)}")
    if m.score_breakdown.education_bonus > 0:
        reasons.append("学历符合要求")
    if m.score_breakdown.experience_bonus > 0:
        reasons.append(f"工作经验达标且有 {round(m.score_breakdown.experience_bonus / 2)} 年加分空间")
    if m.score_breakdown.famous_company_bonus > 0:
        reasons.append("有名企工作经历")
    return "；".join(reasons)


def _strip_html(snippets: List[str]) -> List[str]:
    clean = []
    for s in snippets:
        import re
        t = re.sub(r"<[^>]+>", "", s)
        clean.append(t)
    return clean


@router.get("/{job_id}/export.csv")
def export_match_csv(job_id: int):
    jd = db.get_job(job_id)
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")
    all_resumes = db.list_resumes()
    matched = matcher.match_all(all_resumes, jd)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "排名", "姓名", "邮箱", "手机", "学历", "工作年限(年)",
        "总分", "语义相似度", "经验加分", "学历加分", "名企加分",
        "TOP5命中技能", "命中片段", "推荐理由",
    ])
    for m in matched:
        r = m.resume
        writer.writerow([
            m.rank,
            r.name or r.filename,
            r.email or "",
            r.phone or "",
            r.education or "",
            r.years_of_experience,
            round(m.score, 2),
            round(m.score_breakdown.semantic_similarity, 2),
            round(m.score_breakdown.experience_bonus, 2),
            round(m.score_breakdown.education_bonus, 2),
            round(m.score_breakdown.famous_company_bonus, 2),
            "、".join(s.name for s in m.top_skills),
            " | ".join(_strip_html(m.highlighted_snippets)),
            _recommend_reason(m, jd.title),
        ])
    content = buf.getvalue()
    buf_io = io.BytesIO(content.encode("utf-8-sig"))
    filename = f"match_{jd.title}_{job_id}.csv"
    return StreamingResponse(
        iter([buf_io.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/compare/export.csv")
def export_compare_csv(req: CompareRequest):
    job_ids = req.job_ids
    resume_id = req.resume_id
    if len(job_ids) < 2 or len(job_ids) > 3:
        raise HTTPException(status_code=400, detail="必须同时选择2-3个岗位")
    jobs = []
    for jid in job_ids:
        jd = db.get_job(jid)
        if not jd:
            raise HTTPException(status_code=404, detail=f"岗位 {jid} 不存在")
        jobs.append(jd)
    if resume_id:
        r = db.get_resume(resume_id)
        if not r:
            raise HTTPException(status_code=404, detail="简历不存在")
        resumes = [r]
    else:
        resumes = db.list_resumes()
    buf = io.StringIO()
    writer = csv.writer(buf)
    header = ["姓名", "邮箱", "手机", "学历", "工作年限(年)"]
    for jd in jobs:
        header += [
            f"[{jd.title}] 总分",
            f"[{jd.title}] 语义相似度",
            f"[{jd.title}] 经验加分",
            f"[{jd.title}] 学历加分",
            f"[{jd.title}] 名企加分",
            f"[{jd.title}] 命中技能",
        ]
    writer.writerow(header)
    for r in resumes:
        row = [r.name or r.filename, r.email or "", r.phone or "", r.education or "", r.years_of_experience]
        for jd in jobs:
            m = matcher.match_one(r, jd)
            row += [
                round(m.score, 2),
                round(m.score_breakdown.semantic_similarity, 2),
                round(m.score_breakdown.experience_bonus, 2),
                round(m.score_breakdown.education_bonus, 2),
                round(m.score_breakdown.famous_company_bonus, 2),
                "、".join(s.name for s in m.top_skills),
            ]
        writer.writerow(row)
    content = buf.getvalue()
    buf_io = io.BytesIO(content.encode("utf-8-sig"))
    filename = f"compare_{'_'.join(j.title for j in jobs)}.csv"
    return StreamingResponse(
        iter([buf_io.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{job_id}", response_model=MatchResponse)
def match_job(
    job_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    w_semantic: Optional[float] = Query(None, ge=0),
    w_experience: Optional[float] = Query(None, ge=0),
    w_education: Optional[float] = Query(None, ge=0),
    w_company: Optional[float] = Query(None, ge=0),
):
    jd = db.get_job(job_id)
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")
    if not jd.is_active:
        raise HTTPException(status_code=400, detail="岗位已停用")
    all_resumes = db.list_resumes()
    weights = {}
    if w_semantic is not None:
        weights["semantic"] = w_semantic
    if w_experience is not None:
        weights["experience"] = w_experience
    if w_education is not None:
        weights["education"] = w_education
    if w_company is not None:
        weights["company"] = w_company
    matched = matcher.match_all(all_resumes, jd, weights=weights or None)
    page_items, total = _paginate(matched, page, page_size)
    return MatchResponse(
        job_id=jd.id,
        job_title=jd.title,
        total_candidates=total,
        page=page,
        page_size=page_size,
        results=page_items,
    )


@router.post("/compare")
def compare_jobs(req: CompareRequest):
    job_ids = req.job_ids
    resume_id = req.resume_id
    if len(job_ids) < 2 or len(job_ids) > 3:
        raise HTTPException(status_code=400, detail="必须同时选择2-3个岗位")
    jobs = []
    for jid in job_ids:
        jd = db.get_job(jid)
        if not jd:
            raise HTTPException(status_code=404, detail=f"岗位 {jid} 不存在")
        jobs.append(jd)
    if resume_id:
        r = db.get_resume(resume_id)
        if not r:
            raise HTTPException(status_code=404, detail="简历不存在")
        resumes = [r]
    else:
        resumes = db.list_resumes()
    result = []
    for r in resumes:
        per_job = []
        for jd in jobs:
            m = matcher.match_one(r, jd)
            per_job.append({"job_id": jd.id, "job_title": jd.title, "score": m.score,
                            "top_skills": m.top_skills, "breakdown": m.score_breakdown})
        result.append({"resume_id": r.id, "name": r.name or r.filename, "jobs": per_job})
    return {"jobs": [{"id": j.id, "title": j.title} for j in jobs], "comparisons": result}
