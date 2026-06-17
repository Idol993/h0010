import os
import re
import time
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from functools import lru_cache

import numpy as np

from server.models import (
    Resume, JobDescription, MatchResult, ScoreBreakdown, SkillItem
)
from server.services.skill_dict import skill_dict, FAMOUS_COMPANIES, EDUCATION_LEVELS

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class MatcherEngine:
    def __init__(self):
        self._model = None
        self._cache: Dict[str, np.ndarray] = {}

    def _get_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
            MODELS_DIR.mkdir(exist_ok=True)
            os.environ.setdefault("HF_HOME", str(MODELS_DIR))
            os.environ.setdefault("TRANSFORMERS_CACHE", str(MODELS_DIR))
            self._model = SentenceTransformer(MODEL_NAME, cache_folder=str(MODELS_DIR))
        except Exception as e:
            print(f"Warning: sentence-transformers load failed: {e}. Using fallback TF-IDF matcher.")
            self._model = None
        return self._model

    def _encode(self, texts: List[str]) -> np.ndarray:
        model = self._get_model()
        if model is not None:
            return model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return self._encode_fallback(texts)

    def _encode_fallback(self, texts: List[str]) -> np.ndarray:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(lowercase=True, max_features=1000, stop_words="english")
        if not texts:
            return np.zeros((0, 1))
        try:
            vecs = vectorizer.fit_transform(texts).toarray()
            return vecs
        except Exception:
            return np.zeros((len(texts), 1))

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        if a.size == 0 or b.size == 0:
            return 0.0
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    @staticmethod
    def _resume_text(r: Resume) -> str:
        parts: List[str] = []
        if r.skills:
            parts.append(" ".join(s.name for s in r.skills))
        if r.education:
            parts.append(r.education)
        if r.recent_companies:
            parts.append(" ".join(e.company for e in r.recent_companies))
        parts.append(r.raw_text[:3000] if r.raw_text else "")
        return " | ".join(parts)

    @staticmethod
    def _job_text(jd: JobDescription) -> str:
        parts: List[str] = [jd.title, jd.description]
        if jd.skills:
            for s in jd.skills:
                for _ in range(max(1, int(round(s.weight * 3)))):
                    parts.append(s.skill)
        if jd.required_education:
            parts.append(jd.required_education)
        return " | ".join(parts)

    def _semantic_score(self, r: Resume, jd: JobDescription) -> float:
        r_text = self._resume_text(r)
        j_text = self._job_text(jd)
        r_vec = self._encode([r_text])[0]
        j_vec = self._encode([j_text])[0]
        sim = self._cosine(r_vec, j_vec)
        return max(0.0, min(1.0, (sim + 1.0) / 2.0))

    @staticmethod
    def _education_match(r_edu: Optional[str], j_edu: Optional[str]) -> bool:
        if not j_edu:
            return False
        rlvl = EDUCATION_LEVELS.get((r_edu or "").lower(), 0)
        jlvl = EDUCATION_LEVELS.get((j_edu or "").lower(), 0)
        return rlvl >= jlvl > 0

    @staticmethod
    def _has_famous_company(r: Resume) -> bool:
        for exp in r.recent_companies:
            low = exp.company.lower()
            for fc in FAMOUS_COMPANIES:
                if fc in low:
                    return True
        return False

    @staticmethod
    def _top_matching_skills(r: Resume, jd: JobDescription, top_n: int = 5) -> List[SkillItem]:
        job_skill_names = {s.skill.lower() for s in jd.skills}
        jd_norm = {}
        for s in jd.skills:
            canon = skill_dict.normalize(s.skill)
            if canon:
                jd_norm[canon.lower()] = s.weight
        matched: List[SkillItem] = []
        for rs in r.skills:
            canon = skill_dict.normalize(rs.name) or rs.name
            weight = jd_norm.get(canon.lower(), 0.0)
            if weight > 0 or canon.lower() in job_skill_names:
                matched.append(SkillItem(name=canon, confidence=max(weight, rs.confidence)))
        matched.sort(key=lambda x: -x.confidence)
        return matched[:top_n]

    @staticmethod
    def _highlight_snippets(r: Resume, jd: JobDescription, top_n: int = 3) -> List[str]:
        if not r.raw_text:
            return []
        highlight_words = set()
        for s in jd.skills:
            highlight_words.add(s.skill.lower())
            canon = skill_dict.normalize(s.skill)
            if canon:
                highlight_words.add(canon.lower())
        for rs in r.skills:
            highlight_words.add(rs.name.lower())
        if not highlight_words:
            return []
        sentences = re.split(r"[。.!?！？\n]+", r.raw_text)
        scored: List[Tuple[int, str]] = []
        for idx, sent in enumerate(sentences):
            s = sent.strip()
            if len(s) < 10 or len(s) > 300:
                continue
            hits = sum(1 for w in highlight_words if w and w in s.lower())
            if hits > 0:
                scored.append((hits, s))
        scored.sort(key=lambda x: -x[0])
        return [s for _, s in scored[:top_n]]

    def match_one(self, r: Resume, jd: JobDescription, rank: int = 0,
                  weights: Optional[Dict] = None) -> MatchResult:
        weights = weights or {}
        w_sem = weights.get("semantic", 60)
        w_exp = weights.get("experience", 15)
        w_edu = weights.get("education", 15)
        w_company = weights.get("company", 10)
        w_sum = w_sem + w_exp + w_edu + w_company or 1

        base = self._semantic_score(r, jd)
        extra_years = max(0, r.years_of_experience - jd.min_years_experience)
        exp_points = min(extra_years * 2, 100)
        edu_match = self._education_match(r.education, jd.required_education)
        edu_points = 100 if edu_match else 0
        famous = self._has_famous_company(r)
        company_points = 100 if famous else 0

        total_raw = (
            base * w_sem
            + (exp_points / 100) * w_exp
            + (edu_points / 100) * w_edu
            + (company_points / 100) * w_company
        ) / w_sum
        total = round(max(0.0, min(100.0, total_raw * 100)), 2)

        breakdown = ScoreBreakdown(
            semantic_similarity=round(base * 100, 2),
            experience_bonus=round(min(extra_years * 2, 20), 2),
            education_bonus=5.0 if edu_match else 0.0,
            famous_company_bonus=3.0 if famous else 0.0,
            total=total,
        )
        return MatchResult(
            resume=r,
            score=total,
            rank=rank,
            score_breakdown=breakdown,
            top_skills=self._top_matching_skills(r, jd),
            highlighted_snippets=self._highlight_snippets(r, jd),
        )

    def match_all(self, resumes: List[Resume], jd: JobDescription,
                  weights: Optional[Dict] = None) -> List[MatchResult]:
        results = [self.match_one(r, jd, 0, weights) for r in resumes]
        results.sort(key=lambda m: -m.score)
        for i, m in enumerate(results, 1):
            m.rank = i
        return results


matcher = MatcherEngine()
