from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class SkillItem(BaseModel):
    name: str
    confidence: float = 1.0


class Experience(BaseModel):
    company: str
    position: Optional[str] = None
    duration: Optional[str] = None


class Resume(BaseModel):
    id: Optional[int] = None
    filename: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    education: Optional[str] = None
    years_of_experience: int = 0
    skills: List[SkillItem] = []
    recent_companies: List[Experience] = []
    raw_text: str = ""
    confidence: float = 0.0
    parse_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ResumeParseResponse(BaseModel):
    success: bool
    resume: Optional[Resume] = None
    error: Optional[str] = None
    parse_time_ms: float = 0.0


class JobSkillRequirement(BaseModel):
    skill: str
    weight: float = 1.0
    required: bool = True


class JobDescription(BaseModel):
    id: Optional[int] = None
    title: str
    department: Optional[str] = None
    description: str = ""
    required_education: Optional[str] = None
    min_years_experience: int = 0
    skills: List[JobSkillRequirement] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ScoreBreakdown(BaseModel):
    semantic_similarity: float = 0.0
    experience_bonus: float = 0.0
    education_bonus: float = 0.0
    famous_company_bonus: float = 0.0
    total: float = 0.0


class MatchResult(BaseModel):
    resume: Resume
    score: float
    rank: int
    score_breakdown: ScoreBreakdown
    top_skills: List[SkillItem] = []
    highlighted_snippets: List[str] = []


class MatchResponse(BaseModel):
    job_id: int
    job_title: str
    total_candidates: int
    page: int
    page_size: int
    results: List[MatchResult] = []


class SkillDictEntry(BaseModel):
    canonical: str
    synonyms: List[str] = []


class SkillCandidate(BaseModel):
    term: str
    source_resume_id: Optional[int] = None
    frequency: int = 1
    first_seen: datetime = Field(default_factory=datetime.now)


class PaginatedParams(BaseModel):
    page: int = 1
    page_size: int = 20


class HRReview(BaseModel):
    id: Optional[int] = None
    job_id: int
    resume_id: int
    status: str = "pending"
    note: str = ""
    interview_advice: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MatchResult(BaseModel):
    resume: Resume
    score: float
    rank: int
    score_breakdown: ScoreBreakdown
    top_skills: List[SkillItem] = []
    highlighted_snippets: List[str] = []
    recommend_reason: str = ""
    review: Optional[HRReview] = None
