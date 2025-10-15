"""Unit tests for Friend Circle core helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List
import json
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import core
from app.core import (
    _normalize_datetime,
    _parse_time_string,
    collect_from_config,
    fetch_and_process_data,
    format_published_time,
    load_config,
    parse_feed,
    process_friend,
    sort_articles_by_time,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2024-01-01T00:00:00Z", "2024-01-01 08:00"),
        ("Mon, 01 Jan 2024 00:00:00 +0900", "2023-12-31 23:00"),
        ("2024-01-01 12:00:00", "2024-01-01 20:00"),
    ],
)
def test_format_published_time_default_timezone(raw: str, expected: str) -> None:
    """Times are normalized to Asia/Shanghai."""
    assert format_published_time(raw) == expected


def test_format_published_time_custom_timezone() -> None:
    """Custom target timezones are supported."""
    result = format_published_time("2024-01-01T00:00:00Z", target_timezone="UTC")
    assert result == "2024-01-01 00:00"


def test_format_published_time_invalid_string() -> None:
    """Invalid strings fall back to an empty response."""
    assert format_published_time("not-a-date") == ""


@pytest.mark.parametrize(
    "time_str, expected",
    [
        ("2024-01-01T00:00:00Z", datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)),
        ("2024-01-01 12:00:00", datetime(2024, 1, 1, 12, 0)),
    ],
)
def test_parse_time_string_success(time_str: str, expected: datetime) -> None:
    """Parsing succeeds for multiple supported formats."""
    parsed = _parse_time_string(time_str)
    assert isinstance(parsed, datetime)
    assert parsed.replace(tzinfo=None) == expected.replace(tzinfo=None)


def test_parse_time_string_failure() -> None:
    """Unsupported formats return ``None``."""
    assert _parse_time_string("not-a-date") is None


def test_normalize_datetime_naive_assigns_utc() -> None:
    """Naive datetimes are treated as UTC before conversion."""
    naive = datetime(2024, 1, 1, 12, 0, 0)
    result = _normalize_datetime(naive, core.ZoneInfo("Asia/Shanghai"))
    assert result.tzinfo is not None
    assert result.strftime("%Y-%m-%d %H:%M") == "2024-01-01 20:00"


def test_normalize_datetime_preserves_offset() -> None:
    """Timezone-aware datetimes keep their offset information."""
    aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=core.timezone.utc)
    result = _normalize_datetime(aware, core.ZoneInfo("UTC"))
    assert result.tzinfo is not None
    assert result.strftime("%Y-%m-%d %H:%M") == "2024-01-01 12:00"


class _DictLike(dict):
    """Simple helper providing attribute access used in feeds."""

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - passthrough
        try:
            return self[item]
        except KeyError as exc:  # pragma: no cover - mirrors dict behaviour
            raise AttributeError(item) from exc


class _FakeResponse:
    """Minimal response object for session mocks."""

    def __init__(self, *, content: bytes = b"", status_code: int = 200, headers: Dict[str, str] | None = None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/xml"}
        self.reason = "OK"
        self.text = content.decode("utf-8", errors="ignore")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise core.requests.HTTPError(f"{self.status_code} {self.reason}")


class _FakeSession:
    """Session stub returning predefined responses."""

    def __init__(self, responses: Iterable[_FakeResponse]):
        self._responses = list(responses)

    def get(self, *_: Any, **__: Any) -> _FakeResponse:
        return self._responses.pop(0)


def test_parse_feed_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Feed entries are converted into article dictionaries."""

    def fake_parse(_: bytes) -> SimpleNamespace:
        feed_meta = _DictLike(title="Site", author="Alice", link="https://example.com")
        entries = [
            _DictLike(
                title="Post",
                author="Bob",
                link="https://example.com/post",
                published="2024-01-01T00:00:00Z",
                summary="Summary",
                content=[_DictLike(value="<p>Body</p>")],
            )
        ]
        return SimpleNamespace(feed=feed_meta, entries=entries, bozo=False)

    session = _FakeSession([_FakeResponse(content=b"<feed />")])
    monkeypatch.setattr(core.feedparser, "parse", fake_parse)

    result = parse_feed("https://example.com/feed", session, count=1)

    assert result == {
        "website_name": "Site",
        "author": "Alice",
        "link": "https://example.com",
        "articles": [
            {
                "title": "Post",
                "author": "Bob",
                "link": "https://example.com/post",
                "published": "2024-01-01 08:00",
                "summary": "Summary",
                "content": "<p>Body</p>",
            }
        ],
    }


def test_parse_feed_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP failures return ``None`` and log the issue."""

    session = _FakeSession([_FakeResponse(status_code=500)])

    def fake_parse(_: bytes) -> None:  # pragma: no cover - not executed in this test
        return None

    monkeypatch.setattr(core.feedparser, "parse", fake_parse)

    assert parse_feed("https://example.com/feed", session) is None


def test_process_friend_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful feeds are marked active with transformed articles."""

    friend = ["Alice", "https://blog", "https://avatar", "https://feed"]
    fake_feed = {
        "articles": [
            {"title": "Post", "published": "2024-01-01 00:00", "link": "https://post", "author": "Alice"}
        ]
    }
    monkeypatch.setattr(core, "parse_feed", lambda *_: fake_feed)

    session = _FakeSession([])
    result = process_friend(friend, session, count=5)

    assert result["status"] == "active"
    assert result["articles"] == [
        {
            "title": "Post",
            "created": "2024-01-01 00:00",
            "link": "https://post",
            "author": "Alice",
            "avatar": "https://avatar",
        }
    ]


def test_process_friend_missing_feed() -> None:
    """Missing feed URLs result in an error payload."""

    friend = ["Bob", "https://blog", "https://avatar", ""]
    session = _FakeSession([])
    result = process_friend(friend, session, count=5)

    assert result == {"name": "Bob", "status": "error", "articles": []}


def test_process_friend_fetch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Upstream failures propagate the error state."""

    friend = ["Carol", "https://blog", "https://avatar", "https://feed"]
    monkeypatch.setattr(core, "parse_feed", lambda *_: None)
    session = _FakeSession([])

    result = process_friend(friend, session, count=5)

    assert result == {"name": "Carol", "status": "error", "articles": []}


def test_fetch_and_process_data_local_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aggregates statistics and article data from friend entries."""

    friends_json = tmp_path / "friends.json"
    friends_data = {"friends": [["Alice", "https://blog", "avatar", "feed"]]}
    friends_json.write_text(json.dumps(friends_data), encoding="utf-8")

    def fake_process_friend(friend: List[Any], _session: Any, count: int) -> Dict[str, Any]:
        assert friend == ["Alice", "https://blog", "avatar", "feed"]
        assert count == 2
        return {
            "name": "Alice",
            "status": "active",
            "articles": [
                {
                    "title": "Post",
                    "created": "2024-01-01 00:00",
                    "link": "https://post",
                    "author": "Alice",
                    "avatar": "avatar",
                }
            ],
        }

    monkeypatch.setattr(core, "_make_session", lambda: SimpleNamespace())
    monkeypatch.setattr(core, "process_friend", fake_process_friend)

    result, errors = fetch_and_process_data(str(friends_json), count=2, max_workers=4)

    assert errors == []
    assert result["statistical_data"]["friends_num"] == 1
    assert result["statistical_data"]["active_num"] == 1
    assert result["statistical_data"]["error_num"] == 0
    assert result["statistical_data"]["article_num"] == 1
    assert result["article_data"] == [
        {
            "title": "Post",
            "created": "2024-01-01 00:00",
            "link": "https://post",
            "author": "Alice",
            "avatar": "avatar",
        }
    ]


def test_fetch_and_process_data_fetch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Errors when retrieving the JSON source produce empty results."""

    fake_session = SimpleNamespace(
        get=lambda *_args, **_kwargs: (_ for _ in ()).throw(core.requests.HTTPError("boom"))
    )
    monkeypatch.setattr(core, "_make_session", lambda: fake_session)

    result, errors = fetch_and_process_data("https://example.com/friends.json")

    assert errors == []
    assert result["statistical_data"]["friends_num"] == 0
    assert result["article_data"] == []


def test_sort_articles_by_time_handles_missing_time() -> None:
    """Missing timestamps are replaced and the list is sorted descending."""

    data = {
        "article_data": [
            {"title": "First", "created": "2024-01-01 12:00"},
            {"title": "Missing", "created": ""},
            {"title": "Latest", "created": "2024-01-02 08:00"},
        ]
    }

    sorted_data = sort_articles_by_time(data)

    assert [article["title"] for article in sorted_data["article_data"]] == [
        "Latest",
        "First",
        "Missing",
    ]
    assert sorted_data["article_data"][2]["created"] == "2024-01-01 00:00"


def test_collect_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configuration is relayed to fetch helpers and results are sorted."""

    def fake_fetch(json_url: str, count: int, max_workers: int):
        assert json_url == "friends.json"
        assert count == 3
        assert max_workers == 2
        return (
            {
                "statistical_data": {},
                "article_data": [
                    {"title": "B", "created": "2024-01-01 10:00"},
                    {"title": "A", "created": "2024-01-02 09:00"},
                ],
            },
            ["failed"],
        )

    monkeypatch.setattr(core, "fetch_and_process_data", fake_fetch)

    config = {"spider_settings": {"json_url": "friends.json", "article_count": 3, "max_workers": 2}}
    result, errors = collect_from_config(config)

    assert errors == ["failed"]
    assert [article["title"] for article in result["article_data"]] == ["A", "B"]


def test_load_config(tmp_path: Path) -> None:
    """YAML configuration files are loaded into dictionaries."""

    config_path = tmp_path / "conf.yaml"
    config_path.write_text("spider_settings:\n  json_url: friends.json\n", encoding="utf-8")

    loaded = load_config(str(config_path))

    assert loaded == {"spider_settings": {"json_url": "friends.json"}}
