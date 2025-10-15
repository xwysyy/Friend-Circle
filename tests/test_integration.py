"""Integration tests exercising the Friend Circle pipeline end-to-end."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Iterator, Tuple

import pytest

from app import core


FEED_XML = """<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <title>Example Feed</title>
    <link>https://example.com/</link>
    <description>Sample feed for integration tests</description>
    <item>
      <title>Welcome Post</title>
      <link>https://example.com/welcome</link>
      <description>Hello world</description>
      <pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
""".strip()


class _FeedRequestHandler(BaseHTTPRequestHandler):
    """Serve a minimal friend list JSON and RSS feed for integration testing."""

    feed_xml = FEED_XML.encode("utf-8")

    def do_GET(self) -> None:  # pragma: no cover - exercised via integration tests
        if self.path == "/feed.xml":
            self._write_response(self.feed_xml, content_type="application/rss+xml")
            return

        if self.path == "/friends.json":
            host = self.headers.get("Host", f"127.0.0.1:{self.server.server_address[1]}")
            feed_url = f"http://{host}/feed.xml"
            payload = {
                "friends": [
                    [
                        "Integration User",
                        "https://example.com",
                        "https://example.com/avatar.png",
                        feed_url,
                    ]
                ]
            }
            body = json.dumps(payload).encode("utf-8")
            self._write_response(body, content_type="application/json")
            return

        self.send_error(404, "Not Found")

    def log_message(self, *_: object) -> None:  # pragma: no cover - silence stdout
        return

    def _write_response(self, body: bytes, *, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def local_feed_server() -> Iterator[str]:
    """Start a lightweight HTTP server that hosts friend JSON and feed data."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), _FeedRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base_url
    finally:
        server.shutdown()
        thread.join()


def test_fetch_and_process_data_http_end_to_end(local_feed_server: str) -> None:
    """`fetch_and_process_data` processes live HTTP responses correctly."""

    result, errors = core.fetch_and_process_data(
        f"{local_feed_server}/friends.json", count=3, max_workers=3
    )

    assert errors == []

    stats = result["statistical_data"]
    assert stats["friends_num"] == 1
    assert stats["active_num"] == 1
    assert stats["error_num"] == 0
    assert stats["article_num"] == 1

    assert result["article_data"] == [
        {
            "title": "Welcome Post",
            "created": "2024-01-01 08:00",
            "link": "https://example.com/welcome",
            "author": "Integration User",
            "avatar": "https://example.com/avatar.png",
        }
    ]


_FRIEND_FEED_TEMPLATE = """<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <title>{site_title}</title>
    <link>{site_link}</link>
    <description>Mocked feed for {friend_name}</description>
    <item>
      <title>{article_title}</title>
      <link>{article_link}</link>
      <description>Integration check for {friend_name}</description>
      <pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
""".strip()


class _FriendFeedResponse:
    """Minimal HTTP response object compatible with ``requests`` usage."""

    def __init__(self, body: str):
        self.content = body.encode("utf-8")
        self.status_code = 200
        self.headers = {"Content-Type": "application/rss+xml"}
        self.reason = "OK"
        self.text = body

    def raise_for_status(self) -> None:
        return


class _FriendFeedSession:
    """Session double that returns deterministic feeds per friend URL."""

    def __init__(self, payloads: Dict[str, str]):
        self._payloads = payloads

    def get(
        self,
        url: str,
        headers: Dict[str, str] | None = None,
        timeout: Tuple[float, float] | None = None,
        allow_redirects: bool = True,
    ) -> _FriendFeedResponse:
        try:
            body = self._payloads[url]
        except KeyError as exc:  # pragma: no cover - indicates unexpected network calls
            raise AssertionError(f"Unexpected network request: {url}") from exc
        return _FriendFeedResponse(body)


def _generate_feed(friend_name: str, blog_url: str) -> Tuple[str, str]:
    """Return feed XML and the expected article link for a friend."""

    normalized_blog = blog_url.rstrip("/")
    article_link = f"{normalized_blog}/integration-check"
    feed_xml = _FRIEND_FEED_TEMPLATE.format(
        site_title=f"{friend_name} Feed",
        site_link=normalized_blog,
        friend_name=friend_name,
        article_title=f"{friend_name} integration check",
        article_link=article_link,
    )
    return feed_xml, article_link


def test_fetch_and_process_data_with_real_friend_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pipeline handles the bundled ``friend.json`` using mocked network calls."""

    friend_path = Path(__file__).resolve().parents[1] / "config" / "friend.json"
    friends_data = json.loads(friend_path.read_text("utf-8"))
    feed_payloads: Dict[str, str] = {}
    expected_articles = []

    for name, blog_url, avatar, feed_url in friends_data["friends"]:
        feed_xml, article_link = _generate_feed(name, blog_url)
        feed_payloads[feed_url] = feed_xml
        expected_articles.append(
            {
                "title": f"{name} integration check",
                "created": "2024-01-01 08:00",
                "link": article_link,
                "author": name,
                "avatar": avatar,
            }
        )

    monkeypatch.setattr(core, "_make_session", lambda: _FriendFeedSession(feed_payloads))

    result, errors = core.fetch_and_process_data(str(friend_path), count=1, max_workers=4)

    assert errors == []

    stats = result["statistical_data"]
    total_friends = len(friends_data["friends"])
    assert stats["friends_num"] == total_friends
    assert stats["active_num"] == total_friends
    assert stats["error_num"] == 0
    assert stats["article_num"] == total_friends

    actual_articles = sorted(result["article_data"], key=lambda item: (item["author"], item["link"]))
    expected_sorted = sorted(expected_articles, key=lambda item: (item["author"], item["link"]))
    assert actual_articles == expected_sorted
