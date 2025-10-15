"""Live test that fetches real feeds (runs by default).

This test performs real HTTP requests to the feed URLs listed in
`config/friend.json` (as referenced by `config/conf.yaml`). It runs by default
with the suite. To skip only this test:

    pytest -q -k "not fetch_live_from_config_friend_json"

Notes:
- The test is intentionally tolerant of upstream instability. If fewer than
  20% of friends respond successfully, it xfails to avoid flakiness.
- It limits per-friend articles to 1 and caps concurrency to be polite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from app import core


def test_fetch_live_from_config_friend_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the full pipeline against real feeds, checking basic integrity."""

    conf_path = Path(__file__).resolve().parents[1] / "config" / "conf.yaml"
    config = core.load_config(str(conf_path))
    spider = config.get("spider_settings", {})
    json_url = spider.get("json_url", "config/friend.json")

    # Soften timeouts and retries for test determinism and speed.
    monkeypatch.setattr(core, "timeout", (5, 10))

    def _make_quick_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=1,
            connect=1,
            read=1,
            status=1,
            backoff_factor=0.2,
            status_forcelist=(403, 408, 425, 429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=5)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    monkeypatch.setattr(core, "_make_session", _make_quick_session)

    # Be polite: only 1 article per friend, moderate concurrency.
    result, errors = core.fetch_and_process_data(json_url, count=1, max_workers=4)

    # Basic structure checks
    assert isinstance(errors, list)
    assert isinstance(result, dict)
    assert "statistical_data" in result and "article_data" in result

    stats = result["statistical_data"]
    assert {"friends_num", "active_num", "error_num", "article_num"} <= set(stats)

    friends_num = int(stats["friends_num"])  # may be 0 if input is empty
    active_num = int(stats["active_num"]) if stats.get("active_num") is not None else 0
    error_num = int(stats["error_num"]) if stats.get("error_num") is not None else 0
    article_num = int(stats["article_num"]) if stats.get("article_num") is not None else 0

    # Invariants and soft bounds
    assert active_num + error_num == friends_num
    assert 0 <= article_num <= friends_num * 1  # 1 article per friend requested

    # If nearly all feeds fail, consider it a transient upstream/network issue
    # and xfail to keep this "live" test informative but not flaky.
    if friends_num > 0:
        active_ratio = active_num / max(friends_num, 1)
        if active_ratio < 0.20:
            pytest.xfail(
                f"Too many feed failures (active ratio {active_ratio:.2%}); "
                "likely network or upstream outage."
            )

    # Shape checks for returned articles
    for item in result["article_data"]:
        assert {"title", "created", "link", "author", "avatar"} <= set(item)
        assert isinstance(item["title"], str)
        assert isinstance(item["link"], str)
        assert isinstance(item["author"], str)
        # created may be empty for some feeds; core handles defaults/sorting
