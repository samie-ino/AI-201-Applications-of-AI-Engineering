"""Technology stack detector tool."""

from collections import Counter

import structlog

from .base import BaseTool, ToolResult

logger = structlog.get_logger()


class TechDetector(BaseTool):
    """Detect technology stack from repository files."""

    name = "tech_detector"
    description = "Detect technology stack from repository files"

    # File extension to language mapping
    EXT_TO_LANG = {
        ".py": "Python",
        ".ipynb": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".kt": "Kotlin",
        ".cs": "C#",
        ".cpp": "C++",
        ".c": "C",
        ".h": "C",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".scala": "Scala",
        ".r": "R",
        ".m": "Objective-C",
        ".groovy": "Groovy",
    }

    # Some config indicators describe a category rather than a language; these
    # must never be counted as (or become the primary) language.
    NON_LANGUAGE_CATEGORIES = {"Infrastructure", "Build", "CI/CD"}

    # Config file to language/framework mapping
    CONFIG_INDICATORS = {
        "package.json": ("Node.js", "JavaScript"),
        "package-lock.json": ("Node.js", "JavaScript"),
        "yarn.lock": ("Node.js", "JavaScript"),
        "requirements.txt": ("Python", "Python"),
        "setup.py": ("Python", "Python"),
        "Pipfile": ("Python", "Python"),
        "Gemfile": ("Ruby", "Ruby"),
        "Cargo.toml": ("Rust", "Rust"),
        "pom.xml": ("Java", "Java"),
        "build.gradle": ("Java", "Java"),
        "Dockerfile": ("Docker", "Infrastructure"),
        "docker-compose.yml": ("Docker", "Infrastructure"),
        ".github/workflows": ("GitHub Actions", "CI/CD"),
        "Makefile": ("Make", "Build"),
        "cmake": ("CMake", "Build"),
    }

    def execute(self, input_data: dict) -> ToolResult:
        """Detect tech stack from files.

        Args:
            input_data: Must contain 'files' (list of file paths)

        Returns:
            ToolResult with detected technologies
        """
        files = input_data.get("files", [])

        if not files:
            logger.warning("tech_detector_no_files")
            return ToolResult(
                success=True,
                data={
                    "primary_language": "Unknown",
                    "all_languages": [],
                    "frameworks": [],
                },
            )

        try:
            result = self._detect_tech(files)
            return ToolResult(success=True, data=result)

        except Exception as e:
            logger.error("tech_detector_error", error=str(e))
            return ToolResult(success=False, data={}, error=str(e))

    def _detect_tech(self, files: list[str]) -> dict:
        """Detect technologies from file list.

        Args:
            files: List of file paths

        Returns:
            Dict with detected languages and frameworks
        """
        # Filter out vendor/build directories
        filtered_files = [f for f in files if not self._should_skip_file(f)]

        language_counts: Counter[str] = Counter()
        frameworks = set()

        # Detect by file extension (case-insensitively: "Main.PY" is Python)
        for filepath in filtered_files:
            lowered = filepath.lower()
            for ext, lang in self.EXT_TO_LANG.items():
                if lowered.endswith(ext):
                    language_counts[lang] += 1

        # Detect by config files
        for filepath in filtered_files:
            lowered = filepath.lower()
            for config_file, (framework, lang) in self.CONFIG_INDICATORS.items():
                indicator = config_file.lower()
                # Directory indicators (e.g. ".github/workflows") appear
                # mid-path, so they are matched by containment.
                matched = indicator in lowered if "/" in indicator else lowered.endswith(indicator)
                if matched:
                    if lang not in self.NON_LANGUAGE_CATEGORIES:
                        language_counts[lang] += 1
                    if framework not in ("Docker", "Infrastructure", "CI/CD", "Build"):
                        frameworks.add(framework)

        # Primary language is the one backed by the most files, with ties
        # broken alphabetically so the result is deterministic.
        primary = "Unknown"
        if language_counts:
            primary = min(language_counts, key=lambda lang: (-language_counts[lang], lang))

        all_languages = sorted(language_counts)
        all_frameworks = sorted(frameworks)

        logger.info(
            "tech_detected",
            primary_lang=primary,
            languages_count=len(all_languages),
            frameworks_count=len(all_frameworks),
        )

        return {
            "primary_language": primary,
            "all_languages": all_languages,
            "frameworks": all_frameworks,
        }

    @staticmethod
    def _should_skip_file(filepath: str) -> bool:
        """Check if file should be skipped.

        Args:
            filepath: File path

        Returns:
            True if file should be skipped
        """
        skip_dirs = {
            "node_modules",
            "vendor",
            "dist",
            "build",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
        }

        # Match on path segments so a top-level "node_modules/..." is skipped
        # just like a nested "src/node_modules/...".
        segments = filepath.split("/")[:-1]
        return any(segment in skip_dirs for segment in segments)
