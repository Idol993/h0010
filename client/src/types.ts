export interface SkillItem { name: string; confidence: number; }
export interface Experience { company: string; position?: string; duration?: string; }
export interface Resume {
  id?: number;
  filename: string;
  name?: string;
  phone?: string;
  email?: string;
  education?: string;
  years_of_experience: number;
  skills: SkillItem[];
  recent_companies: Experience[];
  raw_text: string;
  confidence: number;
  parse_error?: string;
  created_at?: string;
}
export interface JobSkillRequirement { skill: string; weight: number; required: boolean; }
export interface JobDescription {
  id?: number;
  title: string;
  department?: string;
  description: string;
  required_education?: string;
  min_years_experience: number;
  skills: JobSkillRequirement[];
  is_active: boolean;
}
export interface ScoreBreakdown {
  semantic_similarity: number;
  experience_bonus: number;
  education_bonus: number;
  famous_company_bonus: number;
  total: number;
}
export interface MatchResult {
  resume: Resume;
  score: number;
  rank: number;
  score_breakdown: ScoreBreakdown;
  top_skills: SkillItem[];
  highlighted_snippets: string[];
}
export interface MatchResponse {
  job_id: number;
  job_title: string;
  total_candidates: number;
  page: number;
  page_size: number;
  results: MatchResult[];
}
