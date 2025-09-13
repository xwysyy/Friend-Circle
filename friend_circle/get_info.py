from datetime import datetime, timedelta
from dateutil import parser
from typing import Any, Dict, List, Tuple, Optional
import logging
import time
import socket
import requests
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

# 标准化的请求头（更接近浏览器）
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

timeout = (20, 30)  # 连接超时和读取超时，防止 requests 接受时间过长


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


class IPv4Only:
    """上下文管理器：临时强制 socket 仅返回 IPv4 的解析结果。

    某些站点在 IPv6 路径下不可达或返回异常页面，CI 环境（如 GitHub Actions）常偏向 IPv6，
    这里通过过滤 getaddrinfo 的返回以规避该问题。
    """

    def __enter__(self):
        self._orig_getaddrinfo = socket.getaddrinfo

        def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
            results = self._orig_getaddrinfo(host, port, family, type, proto, flags)
            v4 = [ai for ai in results if ai[0] == socket.AF_INET]
            return v4 if v4 else results

        socket.getaddrinfo = _ipv4_only  # type: ignore

    def __exit__(self, exc_type, exc, tb):
        socket.getaddrinfo = self._orig_getaddrinfo  # type: ignore

def format_published_time(time_str: str) -> str:
    """
    格式化发布时间为统一格式 YYYY-MM-DD HH:MM
    """
    try:
        # 尝试自动解析
        parsed_time = parser.parse(time_str) + timedelta(hours=8)
        return parsed_time.strftime('%Y-%m-%d %H:%M')
    except (ValueError, parser.ParserError):
        pass
    
    time_formats = [
        '%a, %d %b %Y %H:%M:%S %z',       
        '%a, %d %b %Y %H:%M:%S GMT',      
        '%Y-%m-%dT%H:%M:%S%z',            
        '%Y-%m-%dT%H:%M:%SZ',             
        '%Y-%m-%d %H:%M:%S',             
        '%Y-%m-%d'                        
    ]

    for fmt in time_formats:
        try:
            parsed_time = datetime.strptime(time_str, fmt) + timedelta(hours=8)
            return parsed_time.strftime('%Y-%m-%d %H:%M')
        except ValueError:
            continue

    # 如果所有格式都无法匹配，返回原字符串或一个默认值
    return ''

"""
核心抓取与解析工具。
本模块已不再自动探测 feed 地址，必须在 friend.json 中提供第 4 项 feed_url。
"""

def parse_feed(url: str, session: requests.Session, count: int = 5) -> Optional[Dict[str, Any]]:
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

        result: Dict[str, Any] = {
            'website_name': feed.feed.title if 'title' in feed.feed else '',
            'author': feed.feed.author if 'author' in feed.feed else '',
            'link': feed.feed.link if 'link' in feed.feed else '',
            'articles': []
        }
        
        for i, entry in enumerate(feed.entries):
            if i >= count:
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
            article = {
                'title': entry.title if 'title' in entry else '',
                'author': entry.author if 'author' in entry else '',
                'link': entry.link if 'link' in entry else '',
                'published': published,
                'summary': entry.summary if 'summary' in entry else '',
                'content': entry.content[0].value if 'content' in entry and entry.content else entry.description if 'description' in entry else ''
            }
            result['articles'].append(article)
        
        return result
    except Exception as e:
        # 打印少量响应体片段以辅助定位（若可用）
        try:
            snippet = response.text[:180].replace('\n', ' ').replace('\r', ' ')  # type: ignore
        except Exception:
            snippet = ''
        logging.error(f"不可链接的 FEED 地址：{url}: {e}; 摘要：{snippet}")
        return None

def process_friend(friend: List[Any], session: requests.Session, count: int) -> Dict[str, Any]:
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
    feed_info = parse_feed(feed_url, session, count)
    if feed_info:
        articles = [
            {
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
    force_ipv4: bool = False,
) -> Tuple[Dict[str, Any], List[Any]]:
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
        # 在需要时，整个抓取过程强制走 IPv4
        ipv4_ctx = IPv4Only() if force_ipv4 else None
        if ipv4_ctx:
            ipv4_ctx.__enter__()
        try:
            if json_url.startswith('http://') or json_url.startswith('https://'):
                response = session.get(json_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                friends_data = response.json()
            else:
                import json as _json
                with open(json_url, 'r', encoding='utf-8') as f:
                    friends_data = _json.load(f)
        finally:
            if ipv4_ctx:
                ipv4_ctx.__exit__(None, None, None)
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
    # 在需要时，抓取各 Feed 时也强制走 IPv4
    ipv4_ctx = IPv4Only() if force_ipv4 else None
    if ipv4_ctx:
        ipv4_ctx.__enter__()
    try:
        with ThreadPoolExecutor(max_workers=safe_workers) as executor:
            future_to_friend = {
                executor.submit(process_friend, friend, session, count): friend
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
    finally:
        if ipv4_ctx:
            ipv4_ctx.__exit__(None, None, None)

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

def sort_articles_by_time(data):
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
