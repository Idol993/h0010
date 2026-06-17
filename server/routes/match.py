from typing import List, Optional, Dict, Any
import io
import csv
import re

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.models import MatchResponse, MatchResult, HRReview
from server.services.matcher import matcher
from server import db

router = APIRouter(prefix="/api/match", tags=["match"])

STATUS_LABEL = {"pass": "通过", "pending": "待定", "reject": "淘汰"}


class CompareRequest(BaseModel):
    job_ids: List[int]
    resume_id: Optional[int] = None


class ReviewSaveRequest(BaseModel):
    job_id: int
    resume_id: int
    status: str = "pending"
    note: str = ""
    interview_advice: str = ""


def _paginate(items, page: int, page_size: int):
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total


def _strip_html(snippets: List[str]) -> List[str]:
    clean = []
    for s in snippets:
        clean.append(re.sub(r"<[^>]+>", "", s))
    return clean


def _match_for_job(job_id: int, weights: Optional[Dict] = None) -> List[MatchResult]:
    jd = db.get_job(job_id)
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")
    if not jd.is_active:
        raise HTTPException(status_code=400, detail="岗位已停用")
    all_resumes = db.list_resumes()
    matched = matcher.match_all(all_resumes, jd, weights=weights)
    reviews_map = db.list_reviews_by_job(job_id)
    for m in matched:
        m.review = reviews_map.get(m.resume.id)
    return matched, jd


def _build_weights(
    w_semantic: Optional[float],
    w_experience: Optional[float],
    w_education: Optional[float],
    w_company: Optional[float],
):
    weights = {}
    if w_semantic is not None:
        weights["semantic"] = w_semantic
    if w_experience is not None:
        weights["experience"] = w_experience
    if w_education is not None:
        weights["education"] = w_education
    if w_company is not None:
        weights["company"] = w_company
    return weights or None


def _write_match_csv(rows: List[MatchResult], jd_title: str,
                     include_review: bool = True) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    header = [
        "排名", "姓名", "邮箱", "手机", "学历", "工作年限(年)",
        "总分", "语义相似度", "经验加分", "学历加分", "名企加分",
        "TOP5命中技能", "命中片段", "推荐理由",
    ]
    if include_review:
        header += ["评审状态", "备注", "面试建议"]
    writer.writerow(header)
    for m in rows:
        r = m.resume
        row = [
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
            m.recommend_reason,
        ]
        if include_review:
            if m.review:
                row += [
                    STATUS_LABEL.get(m.review.status, m.review.status),
                    m.review.note,
                    m.review.interview_advice,
                ]
            else:
                row += ["未评审", "", ""]
        writer.writerow(row)
    content = buf.getvalue()
    return content.encode("utf-8-sig")


@router.get("/{job_id}", response_model=MatchResponse)
def match_job(
    job_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    review_status: Optional[str] = Query(None, description="按评审状态筛选 pass/pending/reject"),
    w_semantic: Optional[float] = Query(None, ge=0),
    w_experience: Optional[float] = Query(None, ge=0),
    w_education: Optional[float] = Query(None, ge=0),
    w_company: Optional[float] = Query(None, ge=0),
):
    weights = _build_weights(w_semantic, w_experience, w_education, w_company)
    matched, jd = _match_for_job(job_id, weights)
    if review_status:
        matched = [m for m in matched if (m.review and m.review.status == review_status) or
                   (not m.review and review_status == "pending")]
    page_items, total = _paginate(matched, page, page_size)
    return MatchResponse(
        job_id=jd.id,
        job_title=jd.title,
        total_candidates=total,
        page=page,
        page_size=page_size,
        results=page_items,
    )


@router.get("/{job_id}/export.csv")
def export_match_csv(
    job_id: int,
    resume_id: Optional[int] = Query(None, description="指定单个简历ID导出单人报告；不填导出全量"),
    w_semantic: Optional[float] = Query(None, ge=0),
    w_experience: Optional[float] = Query(None, ge=0),
    w_education: Optional[float] = Query(None, ge=0),
    w_company: Optional[float] = Query(None, ge=0),
):
    weights = _build_weights(w_semantic, w_experience, w_education, w_company)
    matched, jd = _match_for_job(job_id, weights)
    if resume_id:
        matched = [m for m in matched if m.resume.id == resume_id]
        if not matched:
            raise HTTPException(status_code=404, detail="未找到该简历的匹配结果")
    payload = _write_match_csv(matched, jd.title)
    filename = f"match_{jd.title}_{job_id}{('_r'+str(resume_id)) if resume_id else ''}.csv"
    return StreamingResponse(
        iter([payload]),
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
            f"[{jd.title}] 命中片段",
            f"[{jd.title}] 推荐理由",
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
                " | ".join(_strip_html(m.highlighted_snippets)),
                m.recommend_reason,
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
            per_job.append({
                "job_id": jd.id,
                "job_title": jd.title,
                "score": m.score,
                "top_skills": m.top_skills,
                "breakdown": m.score_breakdown,
                "highlighted_snippets": m.highlighted_snippets,
                "recommend_reason": m.recommend_reason,
            })
        result.append({"resume_id": r.id, "name": r.name or r.filename, "jobs": per_job})
    return {"jobs": [{"id": j.id, "title": j.title} for j in jobs], "comparisons": result}


@router.post("/review")
def save_review(req: ReviewSaveRequest):
    if req.status not in ("pass", "pending", "reject"):
        raise HTTPException(status_code=400, detail="status 必须是 pass/pending/reject")
    jd = db.get_job(req.job_id)
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")
    r = db.get_resume(req.resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="简历不存在")
    rev = HRReview(
        job_id=req.job_id,
        resume_id=req.resume_id,
        status=req.status,
        note=req.note or "",
        interview_advice=req.interview_advice or "",
    )
    saved = db.save_review(rev)
    return {"ok": True, "review": saved}


@router.get("/review/{job_id}/{resume_id}")
def get_review(job_id: int, resume_id: int):
    rev = db.get_review(job_id, resume_id)
    return {"review": rev}
