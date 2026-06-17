from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query

from server.models import MatchResponse
from server.services.matcher import matcher
from server import db

router = APIRouter(prefix="/api/match", tags=["match"])


def _paginate(items, page: int, page_size: int):
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total


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
def compare_jobs(
    job_ids: List[int] = Query(...),
    resume_id: Optional[int] = Query(None),
):
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
