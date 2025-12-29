"""
Friend Circle core: config loader + RSS/Atom aggregation helpers.

Public API: load_config, collect_from_config, fetch_and_process_data, sort_articles_by_time.
"""
from datetime import datetime, timezone
from dateutil import parser
from typing import Any, Dict, List, Tuple, Optional, Set
from urllib.parse import urlparse
import hashlib
import re
import logging
import time
import requests
import feedparser
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from zoneinfo import ZoneInfo
import os


headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/126.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/atom+xml,application/rss+xml,application/xml;q=0.9,text/xml;q=0.8,*/*;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

timeout = (20, 30)  


JSONDict = Dict[str, Any]
FriendEntry = List[Any]


def make_article_id(link: str, title: str = "", published: str = "", feed_url: str = "") -> str:
    """Create a stable id for an article.

    Prefer `link` (raw entry.link) as primary key; fallback to a tuple of other fields.
    The returned value is a SHA1 hex digest (40 chars).
    """
    base = (link or "").strip()
    if not base:
        base = "|".join([str(feed_url or ""), str(title or ""), str(published or "")]).strip()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _make_session() -> requests.Session:
    """
    创建带有重试策略的 requests.Session。
    对 403/429/5xx 等响应进行指数回退重试，提高在 CI/CD 中的稳定性。
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.6,
        status_forcelist=(403, 408, 425, 429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session



def _normalize_datetime(value: datetime, target_tz: ZoneInfo) -> datetime:
    """将解析出的时间标准化为目标时区。"""
    if value.tzinfo is None:
        # 将无时区信息的时间视作 UTC，保持与旧实现加 8 小时的行为一致
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(target_tz)


def _parse_time_string(time_str: str) -> Optional[datetime]:
    """尝试解析时间字符串，返回 ``datetime`` 或 ``None``。"""
    try:
        return parser.parse(time_str)
    except (ValueError, parser.ParserError):
        pass

    time_formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S GMT',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]

    for fmt in time_formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None


def format_published_time(time_str: str, target_timezone: str = 'Asia/Shanghai') -> str:
    """格式化发布时间为统一格式 ``YYYY-MM-DD HH:MM``。

    Args:
        time_str: 原始时间字符串。
        target_timezone: 目标时区名称，默认为 ``Asia/Shanghai``。

    Returns:
        统一格式的时间字符串，若解析失败则返回空字符串。
    """
    parsed_time = _parse_time_string(time_str)
    if not parsed_time:
        return ''

    target_tz = ZoneInfo(target_timezone)
    localized = _normalize_datetime(parsed_time, target_tz)
    return localized.strftime('%Y-%m-%d %H:%M')



def parse_feed(
    url: str,
    session: requests.Session,
    count: int = 5,
    ignore_ids: Optional[Set[str]] = None,
) -> Optional[JSONDict]:
    """
    解析 Atom 或 RSS2 feed 并返回包含网站名称、作者、原链接和每篇文章详细内容的字典。

    此函数接受一个 feed 的地址（atom.xml 或 rss2.xml），解析其中的数据，并返回一个字典结构，
    其中包括网站名称、作者、原链接和每篇文章的详细内容。

    参数：
    url (str): Atom 或 RSS2 feed 的 URL。
    session (requests.Session): 用于请求的会话对象。
    count (int): 获取文章数的最大数。如果小于则全部获取，如果文章数大于则只取前 count 篇文章。

    返回：
    dict | None: 解析成功返回包含网站信息与文章列表的字典；失败返回 None。
    """
    ignore_ids = ignore_ids or set()
    try:
        response = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        status = response.status_code
        ctype = response.headers.get('Content-Type', '')
        if status >= 400:
            raise requests.HTTPError(f"{status} {response.reason}")

        # 优先用 bytes 防止编码出错
        feed = feedparser.parse(response.content)

        # 如果解析失败或无 entries，尝试一次带轻微不同请求头的重试（可能规避防爬）
        if getattr(feed, 'bozo', False) and not getattr(feed, 'entries', []):
            logging.warning(
                f"Feed 初次解析失败，准备重试：{url}; status={status}; content-type={ctype}"
            )
            alt_headers = dict(headers)
            alt_headers['Accept'] = '*/*'
            time.sleep(0.6)
            response = session.get(url, headers=alt_headers, timeout=timeout, allow_redirects=True)
            status = response.status_code
            ctype = response.headers.get('Content-Type', '')
            if status >= 400:
                raise requests.HTTPError(f"{status} {response.reason}")
            feed = feedparser.parse(response.content)
            if getattr(feed, 'bozo', False) and not getattr(feed, 'entries', []):
                raise ValueError(f"Feed parse bozo and no entries; status={status}; content-type={ctype}")

        result: JSONDict = {
            'website_name': feed.feed.title if 'title' in feed.feed else '',
            'author': feed.feed.author if 'author' in feed.feed else '',
            'link': feed.feed.link if 'link' in feed.feed else '',
            'articles': []
        }

        kept = 0
        skipped = 0
        for entry in feed.entries:
            if kept >= count:
                break

            if 'published' in entry:
                published = format_published_time(entry.published)
            elif 'updated' in entry:
                published = format_published_time(entry.updated)
                # 输出警告信息
                logging.warning(f"文章 {entry.title} 未包含发布时间，使用更新时间 {published}")
            else:
                published = ''
                logging.warning(f"文章 {entry.title} 未包含任何时间信息")

            title = entry.title if 'title' in entry else ''
            link = entry.link if 'link' in entry else ''
            article_id = make_article_id(link=link, title=title, published=published, feed_url=url)
            if ignore_ids and article_id in ignore_ids:
                skipped += 1
                continue

            article = {
                'id': article_id,
                'title': title,
                'author': entry.author if 'author' in entry else '',
                'link': link,
                'published': published,
                'summary': entry.summary if 'summary' in entry else '',
                'content': entry.content[0].value if 'content' in entry and entry.content else entry.description if 'description' in entry else ''
            }
            result['articles'].append(article)

            kept += 1

        if skipped:
            logging.info(f"Feed 已跳过 {skipped} 篇被忽略文章：{url}")

        return result
    except Exception as e:
        # 打印少量响应体片段以辅助定位（若可用）
        try:
            snippet = response.text[:180].replace('\n', ' ').replace('\r', ' ')  # type: ignore
        except Exception:
            snippet = ''
        logging.error(f"不可链接的 FEED 地址：{url}: {e}; 摘要：{snippet}")
        return None

def process_friend(
    friend: FriendEntry,
    session: requests.Session,
    count: int,
    ignore_ids: Optional[Set[str]] = None,
) -> JSONDict:
    """
    处理单个朋友的博客信息。

    参数：
    friend (list): 必须为 [name, blog_url, avatar, feed_url]。
    session (requests.Session): 用于请求的会话对象。
    count (int): 获取每个博客的最大文章数。

    返回：
    dict: 包含朋友博客信息的字典。
    """
    # 强制要求提供自定义 feed 链接的格式：[name, blog_url, avatar, feed_url]
    if not isinstance(friend, (list, tuple)) or len(friend) < 4 or not isinstance(friend[3], str) or not friend[3].strip():
        # 缺少 feed_url，直接标记为错误
        try:
            name, blog_url = friend[0], friend[1]
        except Exception:
            name, blog_url = 'UNKNOWN', ''
        logging.error(f"{name} 的条目缺少必填的 feed_url（第4项）")
        return {
            'name': name,
            'status': 'error',
            'articles': []
        }

    name, blog_url, avatar, feed_url = friend[0], friend[1], friend[2], friend[3].strip()
    logging.info(f"{name} 使用自定义 feed：{feed_url}")

    # 仅使用提供的自定义 feed_url 进行解析
    feed_info = parse_feed(feed_url, session, count, ignore_ids=ignore_ids)
    if feed_info:
        articles = [
            {
                'id': article.get('id', ''),
                'title': article['title'],
                'created': article['published'],
                'link': article['link'],
                'author': name,
                'avatar': avatar
            }
            for article in feed_info['articles']
        ]
        
        for article in articles:
            logging.info(f"{name} 发布文章：{article['title']} @ {article['created']}")
        
        return {
            'name': name,
            'status': 'active',
            'articles': articles
        }
    else:
        logging.error(f"{name} 的 feed 抓取失败：{feed_url}")
        return {
            'name': name,
            'status': 'error',
            'articles': []
        }

def fetch_and_process_data(
    json_url: str,
    count: int = 5,
    max_workers: int = 10,
    ignore_ids: Optional[Set[str]] = None,
) -> Tuple[JSONDict, List[Any]]:
    """
    读取 JSON 数据并处理订阅信息，返回统计数据和文章信息。

    参数：
    json_url (str): 包含朋友信息的 JSON 文件的 URL。
    count (int): 获取每个博客的最大文章数。

    返回：
    dict: 包含统计数据和文章信息的字典。
    """
    session = _make_session()

    try:
        if json_url.startswith('http://') or json_url.startswith('https://'):
            response = session.get(json_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            friends_data = response.json()
        else:
            import json as _json
            with open(json_url, 'r', encoding='utf-8') as f:
                friends_data = _json.load(f)
    except Exception as e:
        logging.error(f"无法获取友链 JSON：{json_url}，错误：{e}")
        empty_result = {
            'statistical_data': {
                'friends_num': 0,
                'active_num': 0,
                'error_num': 0,
                'article_num': 0,
                'last_updated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'article_data': []
        }
        return empty_result, []

    total_friends = len(friends_data.get('friends', []))
    active_friends = 0
    error_friends = 0
    total_articles = 0
    article_data = []
    error_friends_info = []

    # 限制并发，防止过大
    safe_workers = max(1, min(max_workers, total_friends or 1))
    with ThreadPoolExecutor(max_workers=safe_workers) as executor:
        future_to_friend = {
            executor.submit(process_friend, friend, session, count, ignore_ids): friend
            for friend in friends_data.get('friends', [])
        }

        for future in as_completed(future_to_friend):
            friend = future_to_friend[future]
            try:
                result = future.result()
                if result['status'] == 'active':
                    active_friends += 1
                    article_data.extend(result['articles'])
                    total_articles += len(result['articles'])
                else:
                    error_friends += 1
                    error_friends_info.append(friend)
            except Exception as e:
                logging.error(f"处理 {friend} 时发生错误: {e}")
                error_friends += 1
                error_friends_info.append(friend)

    result = {
        'statistical_data': {
            'friends_num': total_friends,
            'active_num': active_friends,
            'error_num': error_friends,
            'article_num': total_articles,
            'last_updated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'article_data': article_data
    }
    
    logging.info("数据处理完成")
    logging.info("总共有 %d 位朋友，其中 %d 位博客可访问，%d 位博客无法访问" % (total_friends, active_friends, error_friends))

    return result, error_friends_info

def sort_articles_by_time(data: JSONDict) -> JSONDict:
    """
    对文章数据按时间排序

    参数：
    data (dict): 包含文章信息的字典

    返回：
    dict: 按时间排序后的文章信息字典
    """
    # 先确保每个元素存在时间
    for article in data['article_data']:
        if article['created'] == '' or article['created'] == None:
            article['created'] = '2024-01-01 00:00'
            logging.warning(f"文章 {article['title']} 无有效时间，设为默认 2024-01-01 00:00")
    
    if 'article_data' in data:
        sorted_articles = sorted(
            data['article_data'],
            key=lambda x: datetime.strptime(x['created'], '%Y-%m-%d %H:%M'),
            reverse=True
        )
        data['article_data'] = sorted_articles
    return data


def collect_from_config(config: JSONDict, ignore_ids: Optional[Set[str]] = None) -> Tuple[JSONDict, List[Any]]:
    """
    根据配置抓取并汇总文章数据，返回排序后的结果和抓取失败的友链列表。

    参数：
    config (dict): 通过 YAML 加载的配置字典，应包含 `spider_settings`。

    返回：
    (result, errors):
      - result (dict): 已按时间降序排序的聚合数据
      - errors (list): 抓取失败的友链原始条目
    """
    spider = config.get("spider_settings", {})
    json_url = spider.get('json_url', '')
    article_count = int(spider.get('article_count', 5))
    max_workers = int(spider.get('max_workers', 10))

    # 统一聚合容器（支持多 JSON 分类聚合）
    aggregated_result: JSONDict = {
        'statistical_data': {
            'friends_num': 0,
            'active_num': 0,
            'error_num': 0,
            'article_num': 0,
            'last_updated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        },
        'article_data': [],
    }
    aggregated_errors: List[Any] = []

    # 解析 json_url 所在目录；若为本地路径，则搜集该目录下所有 .json 作为分类来源
    json_sources: List[Tuple[str, str]] = []  # (json_path_or_url, category)
    try:
        if json_url and not (json_url.startswith('http://') or json_url.startswith('https://')):
            base_dir = os.path.dirname(json_url) or '.'
            if os.path.isdir(base_dir):
                for name in os.listdir(base_dir):
                    if not name.lower().endswith('.json'):
                        continue
                    # 使用文件名（无后缀）作为分类名
                    category = os.path.splitext(name)[0]
                    json_sources.append((os.path.join(base_dir, name), category))
                if json_sources:
                    logging.info(
                        f"已启用分类模式：共发现 {len(json_sources)} 个 JSON 数据源于 {base_dir}"
                    )
        # 若未发现本地多 JSON，则回退到单一来源（保持兼容现有配置）
        if not json_sources and json_url:
            # 尝试从路径/URL 中推断分类名
            try:
                base_name = os.path.basename(json_url)
                category = os.path.splitext(base_name)[0] or 'default'
            except Exception:
                category = 'default'
            json_sources.append((json_url, category))
    except Exception as e:
        logging.warning(f"发现分类数据源时出错，回退到单一来源：{e}")
        base_name = os.path.basename(json_url) if json_url else 'default'
        json_sources.append((json_url, os.path.splitext(base_name)[0] or 'default'))

    # 按来源逐个抓取并聚合，同时给每条文章写入 category 字段
    for src, category in json_sources:
        logging.info(f"开始处理数据源：{src}（分类：{category}）")
        result, errors = fetch_and_process_data(
            json_url=src,
            count=article_count,
            max_workers=max_workers,
            ignore_ids=ignore_ids,
        )
        # 注入分类字段
        for item in result.get('article_data', []) or []:
            item['category'] = category
        # 聚合统计与数据
        stat = result.get('statistical_data', {}) or {}
        aggregated_result['statistical_data']['friends_num'] += int(stat.get('friends_num', 0) or 0)
        aggregated_result['statistical_data']['active_num'] += int(stat.get('active_num', 0) or 0)
        aggregated_result['statistical_data']['error_num'] += int(stat.get('error_num', 0) or 0)
        aggregated_result['statistical_data']['article_num'] += int(stat.get('article_num', 0) or 0)
        aggregated_result['article_data'].extend(result.get('article_data', []) or [])
        aggregated_errors.extend(errors or [])

    # 可选：根据配置对文章链接进行改写（如按友链名或域名匹配，进行前缀/正则替换）
    link_rewrites = spider.get('link_rewrites') or []
    if link_rewrites and 'article_data' in aggregated_result:
        try:
            rewrite_article_links(aggregated_result['article_data'], link_rewrites)
        except Exception as e:
            logging.error(f"处理链接改写配置时发生错误: {e}")

    aggregated_result = sort_articles_by_time(aggregated_result)
    return aggregated_result, aggregated_errors


def fetch_ignore_ids(ignore_source: str) -> Set[str]:
    """Fetch ignore ids from an URL (http/https) or local json file path.

    Expected payload shapes:
    - {"status": 200, "data": ["id1", "id2"], ...}
    - ["id1", "id2"]
    """
    source = str(ignore_source or "").strip()
    if not source:
        return set()

    session = _make_session()
    try:
        if source.startswith("http://") or source.startswith("https://"):
            response = session.get(source, headers=headers, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        else:
            import json as _json
            with open(source, "r", encoding="utf-8") as f:
                payload = _json.load(f)
    except Exception as e:
        logging.warning(f"获取忽略列表失败，将视为无忽略：{source}；错误：{e}")
        return set()

    ids: Any = payload
    if isinstance(payload, dict):
        ids = payload.get("data") or payload.get("ids") or []

    if not isinstance(ids, list):
        logging.warning(f"忽略列表返回格式异常（非 list），将视为无忽略：{source}")
        return set()

    return {str(x).strip() for x in ids if str(x).strip()}


def load_config(config_file: str) -> JSONDict:
    """
    加载 YAML 配置文件为字典。

    参数：
    config_file (str): 配置文件路径，如 './conf.yaml'。

    返回：
    dict: 配置内容。
    """
    with open(config_file, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def _match_article(article: JSONDict, matcher: Dict[str, Any]) -> bool:
    """判断文章是否与改写规则的匹配条件吻合。

    支持按作者名（友链名）或域名匹配。多个条件取“或”。
    """
    if not matcher:
        return False

    author = str(article.get('author', '')).strip()
    link = str(article.get('link', '')).strip()
    host = ''
    try:
        host = urlparse(link).netloc
    except Exception:
        pass

    name_ok = bool(matcher.get('name')) and (author == matcher.get('name'))
    host_ok = bool(matcher.get('host')) and (host == matcher.get('host'))

    return name_ok or host_ok


def rewrite_article_links(article_data: List[JSONDict], link_rewrites: List[Dict[str, Any]]) -> None:
    """根据配置批量改写文章链接。

    配置示例：
        link_rewrites:
          - match: { name: "锦恢" }
            rules:
              - type: "prefix"
                from: "https://kirigaya.cn/api/rss/blog"
                to:   "https://kirigaya.cn/blog"

    也支持正则：
              - type: "regex"
                pattern: "^https://kirigaya\\.cn/api/rss/(.*)$"
                replace: "https://kirigaya.cn/\\1"
                # 可选：count: 1  # 替换次数，默认 1
    """
    if not link_rewrites:
        return

    for idx, article in enumerate(article_data):
        link = str(article.get('link', '')).strip()
        if not link:
            continue

        for group in link_rewrites:
            matcher = group.get('match', {}) or {}
            if not _match_article(article, matcher):
                continue

            rules = group.get('rules', []) or []
            updated_link = link
            for rule in rules:
                rtype = str(rule.get('type', '')).lower()
                try:
                    if rtype == 'prefix':
                        frm = rule.get('from')
                        to = rule.get('to')
                        if isinstance(frm, str) and isinstance(to, str) and updated_link.startswith(frm):
                            new_link = to + updated_link[len(frm):]
                            if new_link != updated_link:
                                logging.info(f"Rewrite link by prefix: {updated_link} -> {new_link}")
                                updated_link = new_link
                    elif rtype == 'regex':
                        pattern = rule.get('pattern')
                        repl = rule.get('replace')
                        if isinstance(pattern, str) and isinstance(repl, str):
                            count = rule.get('count', 1)
                            try:
                                new_link = re.sub(pattern, repl, updated_link, count=count)
                            except re.error as rex:
                                logging.warning(f"无效的正则表达式：{pattern}: {rex}")
                                continue
                            if new_link != updated_link:
                                logging.info(f"Rewrite link by regex: {updated_link} -> {new_link}")
                                updated_link = new_link
                except Exception as e:
                    logging.warning(f"应用改写规则异常（忽略继续）：{e}")

            if updated_link != link:
                article['link'] = updated_link
            # 命中一个组后继续允许命中下一个组，以便叠加改写（如有需要）
