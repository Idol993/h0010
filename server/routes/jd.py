from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from server.models import JobDescription, JobSkillRequirement
from server.services.skill_dict import skill_dict
from server import db

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=List[JobDescription])
def list_jobs(active_only: bool = Query(False)):
    return db.list_jobs(active_only=active_only)


@router.get("/{job_id}", response_model=JobDescription)
def get_job(job_id: int):
    jd = db.get_job(job_id)
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return jd


@router.post("", response_model=JobDescription)
def create_job(jd: JobDescription):
    jd.id = None
    return db.save_job(jd)


@router.put("/{job_id}", response_model=JobDescription)
def update_job(job_id: int, update: JobDescription):
    existing = db.get_job(job_id)
    if not existing:
        raise HTTPException(status_code=404, detail="岗位不存在")
    update.id = job_id
    return db.save_job(update)


@router.patch("/{job_id}/skills")
def update_job_skills(job_id: int, skills: List[JobSkillRequirement]):
    jd = db.get_job(job_id)
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")
    jd.skills = skills
    return db.save_job(jd)


@router.post("/{job_id}/toggle")
def toggle_job(job_id: int):
    jd = db.get_job(job_id)
    if not jd:
        raise HTTPException(status_code=404, detail="岗位不存在")
    jd.is_active = not jd.is_active
    return db.save_job(jd)


@router.delete("/{job_id}")
def delete_job(job_id: int):
    if not db.delete_job(job_id):
        raise HTTPException(status_code=404, detail="岗位不存在")
    return {"ok": True}


@router.get("/skills/dict")
def get_skill_dict():
    return {
        "total_canonical": len(skill_dict.all_canonical()),
        "canonical": skill_dict.all_canonical()[:200],
    }


@router.post("/skills/dict")
def add_skill_entry(canonical: str, synonyms: Optional[List[str]] = None):
    if not canonical or not canonical.strip():
        raise HTTPException(status_code=400, detail="技能名称不能为空")
    skill_dict.add_skill(canonical.strip(), synonyms or [])
    return {"ok": True, "canonical": canonical.strip()}


@router.get("/skills/candidates")
def list_skill_candidates():
    return {"candidates": skill_dict.list_candidates()}


@router.post("/skills/candidates/approve")
def approve_candidate(term: str, canonical: Optional[str] = None):
    skill_dict.approve_candidate(term, canonical)
    return {"ok": True}
