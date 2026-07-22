import sys
import types
import pytest

# Provide a lightweight stub for structlog so tests don't need external deps
structlog_stub = types.SimpleNamespace(get_logger=lambda *a, **k: lambda *aa, **kk: None)
sys.modules.setdefault("structlog", structlog_stub)

from agent.tools.github_tool import GitHubTool


class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception("HTTP error")


@pytest.mark.unit
def test_compute_contribution_streak(monkeypatch):
    # Construct fake events: PushEvents on 2026-07-20,21,22 and 2026-07-24,25
    events = [
        {"type": "PushEvent", "created_at": "2026-07-20T10:00:00Z"},
        {"type": "PushEvent", "created_at": "2026-07-21T11:00:00Z"},
        {"type": "PushEvent", "created_at": "2026-07-22T12:00:00Z"},
        {"type": "PushEvent", "created_at": "2026-07-24T09:00:00Z"},
        {"type": "PushEvent", "created_at": "2026-07-25T09:00:00Z"},
    ]

    # Mock httpx.get to return our events for page 1 and empty for page 2
    def fake_get(url, headers=None, timeout=None):
        if "page=1" in url:
            return DummyResponse(events)
        return DummyResponse([], 200)

    monkeypatch.setattr("agent.tools.github_tool.httpx.get", fake_get)

    tool = GitHubTool(api_token=None)
    streak = tool._compute_contribution_streak("someuser")

    assert streak == 3
