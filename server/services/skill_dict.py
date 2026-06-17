import json
import os
from typing import Dict, List, Set, Optional
from pathlib import Path
import difflib

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SKILL_DICT_FILE = DATA_DIR / "skill_dict.json"
CANDIDATE_FILE = DATA_DIR / "skill_candidates.json"


FAMOUS_COMPANIES: Set[str] = {
    "google", "alibaba", "tencent", "baidu", "bytedance", "microsoft", "amazon",
    "meta", "apple", "netflix", "tesla", "nvidia", "oracle", "ibm", "salesforce",
    "adobe", "cisco", "intel", "huawei", "xiaomi", "meituan", "jd", "netease",
    "didi", "ant", "蚂蚁", "阿里", "腾讯", "百度", "字节", "华为", "小米",
    "美团", "京东", "网易", "滴滴"
}

EDUCATION_LEVELS: Dict[str, int] = {
    "博士": 5, "phd": 5, "doctorate": 5,
    "硕士": 4, "master": 4, "研究生": 4,
    "本科": 3, "bachelor": 3, "学士": 3,
    "大专": 2, "associate": 2, "专科": 2,
    "高中": 1, "high school": 1,
}

DEFAULT_SKILL_SYNONYMS: Dict[str, List[str]] = {
    "Python": ["python3", "py", "python 2", "python 3", "cpython"],
    "Java": ["j2se", "j2ee", "javase", "javaee", "openjdk", "jdk"],
    "JavaScript": ["js", "ecmascript", "es6", "es5", "vanilla js"],
    "TypeScript": ["ts", "tsx", "typescript2", "typescript3"],
    "React": ["reactjs", "react.js", "react js", "react hooks", "react-native", "react native"],
    "Vue.js": ["vue", "vuejs", "vue3", "vue2", "nuxt", "nuxt.js"],
    "Angular": ["angularjs", "angular.js", "angular 2", "angular 4", "angular 6", "angular 8", "angular 10", "angular 12"],
    "Node.js": ["node", "nodejs", "node js", "express", "koa", "nestjs", "nest.js"],
    "Django": ["django rest", "django-rest-framework", "drf"],
    "Flask": ["flask restful", "flask-restful"],
    "FastAPI": ["fast api"],
    "Spring Boot": ["springboot", "spring boot 2", "spring boot 3", "spring mvc", "springmvc"],
    "Spring": ["spring framework", "spring core", "spring aop", "spring ioc"],
    "MySQL": ["mysql 5", "mysql 8", "mariadb", "mysql server"],
    "PostgreSQL": ["postgres", "postgresql 12", "postgresql 14", "pg"],
    "MongoDB": ["mongo", "nosql mongo"],
    "Redis": ["redis cluster", "redis sentinel", "redis cache"],
    "Docker": ["docker-compose", "docker compose", "dockerfile", "containerization"],
    "Kubernetes": ["k8s", "k8's", "kubernets"],
    "AWS": ["amazon web services", "aws cloud", "ec2", "s3", "lambda", "aws lambda"],
    "GCP": ["google cloud", "google cloud platform", "gcp cloud"],
    "Azure": ["microsoft azure", "azure cloud"],
    "Git": ["gitflow", "git flow", "github", "gitlab", "bitbucket"],
    "CI/CD": ["cicd", "ci cd", "continuous integration", "continuous deployment", "jenkins", "github actions", "gitlab ci"],
    "Linux": ["unix", "ubuntu", "centos", "debian", "redhat", "rhel", "shell", "bash"],
    "Machine Learning": ["ml", "machinelearning", "statistical learning"],
    "Deep Learning": ["dl", "deeplearning", "neural networks", "nn"],
    "PyTorch": ["pytorch 2", "torch", "pytorch lightning", "lightning"],
    "TensorFlow": ["tf", "tensorflow 2", "keras", "tf 2"],
    "NLP": ["natural language processing", "nlp processing", "text mining"],
    "Computer Vision": ["cv", "computer vision", "image processing", "image recognition"],
    "SQL": ["sql server", "t-sql", "transact sql", "plsql", "pl/sql", "ansi sql"],
    "GraphQL": ["graph ql", "gql"],
    "REST API": ["rest", "restful", "rest api", "restful api", "http api"],
    "gRPC": ["grpc", "google rpc"],
    "Microservices": ["microservice", "micro service", "micro services", "soa"],
    "Kafka": ["apache kafka", "kafka streams"],
    "RabbitMQ": ["rabbit mq", "amqp"],
    "Elasticsearch": ["es", "elastic search", "elk", "elasticsearch 7", "elasticsearch 8"],
    "HTML": ["html5", "html 5", "xhtml"],
    "CSS": ["css3", "css 3", "scss", "sass", "less", "tailwind", "tailwindcss", "bootstrap"],
    "Webpack": ["webpack 4", "webpack 5", "module bundler"],
    "Vite": ["vitejs", "vite.js"],
    "Next.js": ["next", "nextjs", "next 13", "next 14"],
    "Selenium": ["selenium webdriver", "webdriver"],
    "Pandas": ["pandas dataframe", "pd"],
    "NumPy": ["numpy array", "np"],
    "Scikit-learn": ["sklearn", "scikit learn", "scikitlearn"],
    "Go": ["golang", "go lang", "go language"],
    "Rust": ["rustlang", "rust lang"],
    "C++": ["cpp", "cplusplus", "c plus plus"],
    "C#": ["csharp", "c sharp", ".net", "dotnet", "asp.net", "aspnet"],
    "PHP": ["php 7", "php 8", "laravel", "symfony"],
    "Swift": ["swiftui", "swift ui", "ios swift"],
    "Kotlin": ["kotlin android", "android kotlin"],
    "Android": ["android sdk", "android development", "android studio"],
    "iOS": ["ios development", "ios sdk", "xcode", "objective-c", "objectivec"],
    "Flutter": ["flutter dart", "dart flutter"],
    "Dart": ["dartlang", "dart language"],
    "React Native": ["rn", "reactnative", "mobile react"],
    "Jest": ["jest testing", "jestjs"],
    "Mocha": ["mocha js", "mocha testing"],
    "Cypress": ["cypress io", "e2e testing"],
    "Postman": ["postman api", "api testing"],
    "Figma": ["figma design", "ui design"],
    "Agile": ["scrum", "agile methodology", "sprint"],
    "DevOps": ["dev ops", "sre", "site reliability"],
    "Blockchain": ["block chain", "smart contract", "solidity", "web3", "web3.js"],
    "Data Analysis": ["data analytics", "data analyst", "analytics"],
    "Big Data": ["bigdata", "hadoop", "spark", "apache spark"],
    "Tableau": ["tableau desktop", "tableau server"],
    "Power BI": ["powerbi", "ms power bi", "business intelligence"],
    "JIRA": ["jira atlassian", "confluence"],
    "Terraform": ["terraform iac", "infrastructure as code"],
    "Ansible": ["ansible automation"],
    "Prometheus": ["prometheus monitoring", "grafana"],
    "Nginx": ["nginx server", "nginx reverse proxy"],
    "Apache": ["apache httpd", "apache server", "httpd"],
    "TCP/IP": ["tcp", "ip", "networking", "network protocol"],
    "OAuth": ["oauth2", "oauth 2.0", "openid", "openid connect", "sso"],
    "JWT": ["json web token", "jwt token"],
    "WebSocket": ["ws", "socket.io", "socketio", "realtime"],
}


class SkillDictionary:
    def __init__(self):
        self._canonical_to_synonyms: Dict[str, List[str]] = {}
        self._synonym_to_canonical: Dict[str, str] = {}
        self._candidates: List[Dict] = []
        self._load()

    def _load(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._canonical_to_synonyms = dict(DEFAULT_SKILL_SYNONYMS)
        if SKILL_DICT_FILE.exists():
            with open(SKILL_DICT_FILE, "r", encoding="utf-8") as f:
                extra = json.load(f)
                for k, v in extra.items():
                    self._canonical_to_synonyms[k] = self._canonical_to_synonyms.get(k, []) + v
        self._rebuild_index()
        self._load_candidates()

    def _rebuild_index(self):
        self._synonym_to_canonical = {}
        for canonical, syns in self._canonical_to_synonyms.items():
            self._synonym_to_canonical[canonical.lower()] = canonical
            for s in syns:
                self._synonym_to_canonical[s.lower()] = canonical

    def _load_candidates(self):
        if CANDIDATE_FILE.exists():
            with open(CANDIDATE_FILE, "r", encoding="utf-8") as f:
                self._candidates = json.load(f)
        else:
            self._candidates = []

    def _save_candidates(self):
        with open(CANDIDATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._candidates, f, ensure_ascii=False, indent=2)

    def _save_skills(self):
        to_save = {k: v for k, v in self._canonical_to_synonyms.items()
                   if k not in DEFAULT_SKILL_SYNONYMS or v != DEFAULT_SKILL_SYNONYMS[k]}
        with open(SKILL_DICT_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)

    def all_canonical(self) -> List[str]:
        return list(self._canonical_to_synonyms.keys())

    def normalize(self, term: str) -> Optional[str]:
        if not term:
            return None
        t = term.strip().lower()
        if t in self._synonym_to_canonical:
            return self._synonym_to_canonical[t]
        matches = difflib.get_close_matches(t, list(self._synonym_to_canonical.keys()), n=1, cutoff=0.85)
        if matches:
            return self._synonym_to_canonical[matches[0]]
        return None

    def record_candidate(self, term: str, resume_id: Optional[int] = None):
        t = term.strip().lower()
        if not t or len(t) < 2 or self.normalize(t):
            return
        for c in self._candidates:
            if c["term"].lower() == t:
                c["frequency"] = c.get("frequency", 1) + 1
                self._save_candidates()
                return
        self._candidates.append({
            "term": term.strip(),
            "source_resume_id": resume_id,
            "frequency": 1,
            "first_seen": str(__import__("datetime").datetime.now()),
        })
        self._save_candidates()

    def list_candidates(self) -> List[Dict]:
        return sorted(self._candidates, key=lambda c: -c.get("frequency", 0))

    def approve_candidate(self, term: str, canonical: Optional[str] = None):
        t = term.strip()
        canon = canonical or t
        self._candidates = [c for c in self._candidates if c["term"].strip().lower() != t.lower()]
        self._save_candidates()
        if canon not in self._canonical_to_synonyms:
            self._canonical_to_synonyms[canon] = []
        if t != canon and t.lower() not in [s.lower() for s in self._canonical_to_synonyms[canon]]:
            self._canonical_to_synonyms[canon].append(t)
        self._save_skills()
        self._rebuild_index()

    def add_skill(self, canonical: str, synonyms: Optional[List[str]] = None):
        if canonical not in self._canonical_to_synonyms:
            self._canonical_to_synonyms[canonical] = []
        if synonyms:
            for s in synonyms:
                if s.lower() not in [x.lower() for x in self._canonical_to_synonyms[canonical]]:
                    self._canonical_to_synonyms[canonical].append(s)
        self._save_skills()
        self._rebuild_index()


skill_dict = SkillDictionary()
