"""GitHub repository metadata tool."""

import httpx
import structlog

from .base import BaseTool, ToolResult

logger = structlog.get_logger()


class GitHubTool(BaseTool):
    """Fetch repository metadata from GitHub."""

    name = "github_tool"
    description = "Fetch repository metadata from GitHub"

    def __init__(self, api_token: str | None = None) -> None:
        """Initialize GitHub tool.

        Args:
            api_token: GitHub API token (optional for unauthenticated requests)
        """
        self.api_token = api_token
        self.base_url = "https://api.github.com"

    def execute(self, input_data: dict) -> ToolResult:
        """Fetch GitHub repository metadata.

        Args:
            input_data: Must contain 'github_username' and 'repo_name'

        Returns:
            ToolResult with repository metadata
        """
        username = input_data.get("github_username")
        repo_name = input_data.get("repo_name")

        if not username or not repo_name:
            return ToolResult(success=False, data={}, error="Missing github_username or repo_name")

        try:
            repo_data = self._fetch_repo_metadata(username, repo_name)
            return ToolResult(success=True, data=repo_data)

        except httpx.HTTPStatusError as e:
            logger.error(
                "github_request_failed",
                status=e.response.status_code,
                username=username,
                repo=repo_name,
            )
            if e.response.status_code == 404:
                return ToolResult(success=False, data={}, error="Repository not found")
            elif e.response.status_code == 403:
                return ToolResult(success=False, data={}, error="Rate limited or access denied")
            return ToolResult(
                success=False, data={}, error=f"GitHub API error: {e.response.status_code}"
            )

        except Exception as e:
            logger.error("github_tool_error", error=str(e))
            return ToolResult(success=False, data={}, error=str(e))

    def _fetch_repo_metadata(self, username: str, repo_name: str) -> dict:
        """Fetch repository metadata from GitHub API.

        Args:
            username: GitHub username
            repo_name: Repository name

        Returns:
            Dict with repository metadata
        """
        url = f"{self.base_url}/repos/{username}/{repo_name}"

        headers = {}
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"

        response = httpx.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()

        repo_json = response.json()

        # Extract metadata, handling null values
        metadata = {
            "name": repo_json.get("name", ""),
            "description": repo_json.get("description") or "",
            "primary_language": repo_json.get("language") or "Unknown",
            "star_count": repo_json.get("stargazers_count", 0),
            "fork_count": repo_json.get("forks_count", 0),
            "open_issues_count": repo_json.get("open_issues_count", 0),
            "last_commit_date": repo_json.get("pushed_at", ""),
            "contribution_history": repo_json.get("contribution_history", []),
            "contribution_streak": repo_json.get("contribution_streak", 0),
            "has_readme": self._has_readme(username, repo_name),
            "topics": repo_json.get("topics", []),
            "homepage": repo_json.get("homepage") or "",
        }

        # Compute user's contribution streak (longest consecutive days with commits)
        try:
            metadata["contribution_streak"] = self._compute_contribution_streak(username)
        except Exception:
            metadata["contribution_streak"] = 0

        logger.info(
            "github_repo_fetched",
            username=username,
            repo=repo_name,
            language=metadata["primary_language"],
            stars=metadata["star_count"],
        )

        return metadata

    def _has_readme(self, username: str, repo_name: str) -> bool:
        """Check if repository has a README file.

        Args:
            username: GitHub username
            repo_name: Repository name

        Returns:
            True if README exists
        """
        url = f"{self.base_url}/repos/{username}/{repo_name}/readme"

        headers = {}
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"

        try:
            response = httpx.head(url, headers=headers, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def _compute_contribution_streak(self, username: str) -> int:
        """Compute the longest consecutive-day commit streak for a user.

        Strategy: use the public events API (`/users/{username}/events/public`) and
        mark days where the user performed a `PushEvent`. This provides a recent
        activity-based approximation for contribution streaks.

        Returns:
            int: longest consecutive-day streak (0 if none or on error)
        """
        if not username:
            return 0

        headers = {}
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"

        active_days = set()

        # Fetch up to 3 pages of events (max ~300 events) to cover recent history
        for page in range(1, 4):
            url = f"{self.base_url}/users/{username}/events/public?page={page}&per_page=100"
            try:
                resp = httpx.get(url, headers=headers, timeout=10.0)
                resp.raise_for_status()
                events = resp.json()
            except Exception:
                break

            if not events:
                break

            for ev in events:
                if ev.get("type") == "PushEvent":
                    created = ev.get("created_at")
                    if not created:
                        continue
                    # parse ISO timestamp like 2023-07-01T12:34:56Z
                    try:
                        if created.endswith("Z"):
                            created = created[:-1] + "+00:00"
                        dt = __import__("datetime").datetime.fromisoformat(created)
                        active_days.add(dt.date())
                    except Exception:
                        continue

        if not active_days:
            return 0

        # Compute longest consecutive streak from the set of dates
        days = sorted(active_days)
        longest = 1
        current = 1
        for i in range(1, len(days)):
            prev = days[i - 1]
            cur = days[i]
            if (cur - prev).days == 1:
                current += 1
            else:
                if current > longest:
                    longest = current
                current = 1

        if current > longest:
            longest = current

        return longest
