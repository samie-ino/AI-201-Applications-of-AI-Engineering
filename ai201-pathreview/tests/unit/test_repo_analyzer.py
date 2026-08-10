"""Regression tests for repo metadata analysis."""

from ingestion.parsers.repo_analyzer import RepoAnalyzer


class TestRepoAnalyzer:
    """Tests for repository metadata parsing."""

    def test_calculate_contribution_streak_empty_history(self):
        assert RepoAnalyzer()._calculate_contribution_streak({}) == 0

    def test_calculate_contribution_streak_single_day(self):
        repo_data = {"contribution_history": [{"date": "2024-03-01", "count": 1}]}

        assert RepoAnalyzer()._calculate_contribution_streak(repo_data) == 1

    def test_calculate_contribution_streak_non_consecutive_days(self):
        repo_data = {
            "contribution_history": [
                {"date": "2024-03-01", "count": 1},
                {"date": "2024-03-03", "count": 1},
                {"date": "2024-03-04", "count": 1},
            ]
        }

        assert RepoAnalyzer()._calculate_contribution_streak(repo_data) == 2

    def test_calculate_contribution_streak_duplicate_dates(self):
        repo_data = {
            "contribution_history": [
                {"date": "2024-03-01", "count": 1},
                {"date": "2024-03-02", "count": 1},
                {"date": "2024-03-02", "count": 2},
                {"date": "2024-03-03", "count": 1},
            ]
        }

        assert RepoAnalyzer()._calculate_contribution_streak(repo_data) == 3

    def test_calculate_contribution_streak_prefers_explicit_value(self):
        repo_data = {
            "contribution_streak": 7,
            "contribution_history": [
                {"date": "2024-03-01", "count": 1},
                {"date": "2024-03-02", "count": 1},
            ],
        }

        assert RepoAnalyzer()._calculate_contribution_streak(repo_data) == 7

    def test_parse_includes_contribution_streak_from_history(self):
        """The analyzer should expose the longest consecutive commit streak."""
        parser = RepoAnalyzer()
        repo_data = {
            "name": "demo-repo",
            "description": "A sample repository",
            "language": "Python",
            "stargazers_count": 12,
            "forks_count": 3,
            "open_issues_count": 0,
            "readme_content": "# Demo",
            "file_structure": "src/app.py\ntests/test_app.py",
            "pushed_at": "2024-03-02T10:00:00Z",
            "contribution_history": [
                {"date": "2024-03-01", "count": 1},
                {"date": "2024-03-02", "count": 3},
                {"date": "2024-03-04", "count": 2},
            ],
        }

        result = parser.parse(repo_data)

        assert result.metadata["contribution_streak"] == 2
