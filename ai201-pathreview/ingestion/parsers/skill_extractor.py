import re
from dataclasses import dataclass


@dataclass
class SkillDetection:
    """Result of detecting a skill."""

    name: str
    category: str
    confidence: float
    evidence: list[str]


class SkillExtractor:
    """Extract skills from source code and documentation."""

    PYTHON_KEYWORDS = {
        "import",
        "from",
        "def",
        "class",
        "async",
        "await",
        "yield",
        "lambda",
        "with",
    }

    JS_TS_KEYWORDS = {
        "import",
        "export",
        "require",
        "const",
        "let",
        "var",
        "function",
        "async",
        "await",
        "class",
    }

    REACT_INDICATORS = {
        "import React",
        "useState",
        "useEffect",
        "useContext",
        "useReducer",
        "useCallback",
        "useMemo",
        "useRef",
        "createContext",
        "ReactDOM.render",
        ".jsx",
        ".tsx",
    }

    # Syntax that only appears in TypeScript, paired with the evidence string
    # reported to callers.
    TYPESCRIPT_INDICATORS = (
        (r"\binterface\s+\w+\s*\{", "TypeScript interface declaration"),
        (r"\btype\s+\w+\s*=", "TypeScript type alias"),
        (r"\benum\s+\w+\s*\{", "TypeScript enum declaration"),
        (r":\s*(?:string|number|boolean|any|void|unknown)\b", "TypeScript type annotations"),
        (r"\bPromise\s*<", "TypeScript generic Promise"),
        (r"\bimplements\s+\w+", "TypeScript implements clause"),
    )

    JS_INDICATORS = (
        (r"\brequire\s*\(", "CommonJS require() call"),
        (r"\b(?:import|export)\s+", "ES module import/export"),
        (r"\b(?:const|let)\s+\w+\s*=", "const/let declaration"),
        (r"\bconsole\.log\s*\(", "console.log call"),
        (r"\bmodule\.exports\b", "module.exports assignment"),
    )

    # Client libraries that imply a database without naming it.
    DATABASE_ALIASES = {
        "psycopg2": "postgresql",
        "asyncpg": "postgresql",
        "pymongo": "mongodb",
        "pymysql": "mysql",
        "mysqlclient": "mysql",
    }

    FRAMEWORKS = {
        "django": ("Python", 0.95),
        "flask": ("Python", 0.95),
        "fastapi": ("Python", 0.95),
        "sqlalchemy": ("Python", 0.85),
        "numpy": ("Python", 0.85),
        "pandas": ("Python", 0.85),
        "scikit-learn": ("Python", 0.85),
        "tensorflow": ("Python", 0.85),
        "pytorch": ("Python", 0.85),
        "express": ("JavaScript", 0.95),
        "next.js": ("JavaScript", 0.95),
        "react": ("JavaScript", 0.95),
        "vue": ("JavaScript", 0.95),
        "angular": ("JavaScript", 0.95),
        "svelte": ("JavaScript", 0.85),
        "webpack": ("JavaScript", 0.85),
        "vite": ("JavaScript", 0.85),
        "rollup": ("JavaScript", 0.85),
        "jest": ("JavaScript", 0.80),
        "mocha": ("JavaScript", 0.80),
    }

    DATABASES = {
        "postgresql": 0.95,
        "mysql": 0.95,
        "mongodb": 0.95,
        "redis": 0.90,
        "elasticsearch": 0.90,
        "dynamodb": 0.90,
        "firebase": 0.85,
        "cassandra": 0.85,
        "oracle": 0.85,
    }

    TOOLS = {
        "docker": 0.95,
        "kubernetes": 0.95,
        "git": 0.90,
        "github": 0.90,
        "gitlab": 0.90,
        "aws": 0.90,
        "gcp": 0.90,
        "azure": 0.90,
        "ci/cd": 0.85,
        "jenkins": 0.85,
        "terraform": 0.85,
        "ansible": 0.85,
    }

    def extract_skills(self, text: str, filename: str | None = None) -> list[SkillDetection]:
        """
        Extract skills from source code or documentation text.

        Args:
            text: The source text to analyze
            filename: Optional filename for extension-based detection

        Returns:
            List of detected skills with confidence scores
        """
        detected_skills: dict[str, SkillDetection] = {}

        # Detect languages first
        self._detect_languages(text, filename, detected_skills)

        # Detect frameworks and libraries
        self._detect_frameworks(text, detected_skills)

        # Detect React specifically
        self._detect_react(text, detected_skills)

        # Detect databases
        self._detect_databases(text, detected_skills)

        # Detect tools
        self._detect_tools(text, detected_skills)

        # Sort by confidence
        return sorted(
            detected_skills.values(),
            key=lambda x: x.confidence,
            reverse=True,
        )

    def _detect_languages(
        self,
        text: str,
        filename: str | None,
        skills_dict: dict,
    ) -> None:
        """Detect programming languages."""
        text_lower = text.lower()
        filename_lower = str(filename or "").lower()

        # Python detection
        python_evidence = []
        if ".py" in filename_lower:
            python_evidence.append("Python file extension (.py)")
        if re.search(r"\bimport\s+\w+", text):
            python_evidence.append("Python import statements")
        if re.search(r"\bdef\s+\w+\s*\(", text):
            python_evidence.append("Python function definitions")
        # Word-bounded so a TypeScript ": string" is not read as Python's "str"
        if re.search(r":\s*(int|str|float|bool|list|dict)\b", text):
            python_evidence.append("Python type annotations")
        if "requirements.txt" in text_lower:
            python_evidence.append("requirements.txt found")

        if python_evidence:
            skills_dict["Python"] = SkillDetection(
                name="Python",
                category="Language",
                confidence=min(0.95, 0.6 + len(python_evidence) * 0.1),
                evidence=python_evidence,
            )

        # JavaScript/TypeScript detection
        js_evidence = []
        if ".js" in filename_lower:
            js_evidence.append("JavaScript file extension (.js)")
        for pattern, description in self.JS_INDICATORS:
            if re.search(pattern, text):
                js_evidence.append(description)
        if "package.json" in text_lower:
            js_evidence.append("package.json found")

        # TypeScript is a superset, so its markers decide which of the two the
        # source is reported as.
        ts_evidence = []
        if ".ts" in filename_lower:
            ts_evidence.append("TypeScript file extension (.ts)")
        for pattern, description in self.TYPESCRIPT_INDICATORS:
            if re.search(pattern, text):
                ts_evidence.append(description)

        if js_evidence or ts_evidence:
            evidence = js_evidence + ts_evidence
            lang = "TypeScript" if ts_evidence else "JavaScript"
            skills_dict[lang] = SkillDetection(
                name=lang,
                category="Language",
                confidence=min(0.95, 0.6 + len(evidence) * 0.1),
                evidence=evidence,
            )

        # Other languages by extension
        extension_langs = {
            ".ipynb": ("Jupyter", 0.95),
            ".java": ("Java", 0.95),
            ".cpp": ("C++", 0.95),
            ".cs": ("C#", 0.95),
            ".go": ("Go", 0.95),
            ".rs": ("Rust", 0.95),
            ".rb": ("Ruby", 0.95),
            ".php": ("PHP", 0.95),
            ".swift": ("Swift", 0.95),
        }

        for ext, (lang, confidence) in extension_langs.items():
            if ext in filename_lower:
                skills_dict[lang] = SkillDetection(
                    name=lang,
                    category="Language",
                    confidence=confidence,
                    evidence=[f"{lang} file extension"],
                )

    def _detect_frameworks(self, text: str, skills_dict: dict) -> None:
        """Detect frameworks and libraries."""
        text_lower = text.lower()

        for framework, (category, confidence) in self.FRAMEWORKS.items():
            if framework in text_lower:
                display_name = framework.title()
                if display_name not in skills_dict:
                    skills_dict[display_name] = SkillDetection(
                        name=display_name,
                        category=category,
                        confidence=confidence,
                        evidence=[f"Found '{framework}' in content"],
                    )

    def _detect_react(self, text: str, skills_dict: dict) -> None:
        """Detect React specifically."""
        text_lower = text.lower()
        react_evidence = []

        for indicator in self.REACT_INDICATORS:
            if indicator.lower() in text_lower:
                react_evidence.append(indicator)

        if react_evidence:
            skills_dict["React"] = SkillDetection(
                name="React",
                category="Framework",
                confidence=min(0.99, 0.7 + len(react_evidence) * 0.05),
                evidence=react_evidence,
            )

    def _detect_databases(self, text: str, skills_dict: dict) -> None:
        """Detect databases."""
        text_lower = text.lower()

        for db, confidence in self.DATABASES.items():
            if db in text_lower:
                display_name = db.upper() if db in ["sql", "nosql"] else db.title()
                if display_name not in skills_dict:
                    skills_dict[display_name] = SkillDetection(
                        name=display_name,
                        category="Database",
                        confidence=confidence,
                        evidence=[f"Found '{db}' reference in content"],
                    )

        # Client libraries name the driver, not the database.
        for alias, db in self.DATABASE_ALIASES.items():
            if alias in text_lower:
                display_name = db.title()
                if display_name not in skills_dict:
                    skills_dict[display_name] = SkillDetection(
                        name=display_name,
                        category="Database",
                        confidence=self.DATABASES.get(db, 0.85),
                        evidence=[f"Found '{alias}' client library in content"],
                    )

    def _detect_tools(self, text: str, skills_dict: dict) -> None:
        """Detect tools and DevOps technologies."""
        text_lower = text.lower()

        for tool, confidence in self.TOOLS.items():
            if tool in text_lower:
                display_name = tool.upper() if tool in ["ci/cd"] else tool.title()
                if display_name not in skills_dict:
                    skills_dict[display_name] = SkillDetection(
                        name=display_name,
                        category="Tool",
                        confidence=confidence,
                        evidence=[f"Found '{tool}' reference in content"],
                    )

        if "Docker" not in skills_dict:
            docker_evidence = self._detect_docker_by_structure(text)
            if docker_evidence:
                skills_dict["Docker"] = SkillDetection(
                    name="Docker",
                    category="Tool",
                    confidence=0.85,
                    evidence=docker_evidence,
                )

    @classmethod
    def _detect_docker_by_structure(cls, text: str) -> list[str]:
        """Recognise Dockerfiles and Compose files, which rarely say "Docker"."""
        evidence = []

        if re.search(r"^[ \t]*FROM\s+\S+", text, re.MULTILINE) and re.search(
            r"^[ \t]*(?:RUN|EXPOSE|CMD|ENTRYPOINT|COPY|ADD|WORKDIR|ENV)\s",
            text,
            re.MULTILINE,
        ):
            evidence.append("Dockerfile directives")

        if re.search(r"^[ \t]*services\s*:", text, re.MULTILINE) and re.search(
            r"^[ \t]*(?:version|build|ports|image)\s*:", text, re.MULTILINE
        ):
            evidence.append("Docker Compose service definitions")

        return evidence
