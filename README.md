# Friend Circle

一个简洁的“友链文章聚合器”。从你维护的 `friend.json` 读取友链列表，抓取各博客的 RSS/Atom，生成统一的文章数据 `all.json`，并提供简单的 HTTP 接口与定时刷新。

使用步骤
- 安装依赖
  - `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- 配置抓取参数 `conf.yaml`
  - `spider_settings.enable`: 是否启用抓取（`true/false`）
  - `spider_settings.json_url`: 指向你的 `friend.json`（可为本地路径或 http(s) 地址）
  - `spider_settings.article_count`: 每个博客抓取的最大文章数
  - `spider_settings.max_workers`: 抓取并发（建议 5~20，根据服务器与友链规模调整）
- 一次性抓取生成 JSON
  - `python run.py`
- 启动 API（含定时刷新，每 4 小时）
  - `python server.py`
  - 访问 `http://localhost:1223/all`、`/errors`、`/random`

friend.json 规范
- 结构示例（必含 4 项的条目）：
```
{
  "friends": [
    [
      "xwysyy",
      "https://www.xwysyy.cn/",
      "https://www.xwysyy.cn/avatar.webp",
      "https://www.xwysyy.cn/rss.xml"
    ]
  ]
}
```
- 条目顺序：[name, blog_url, avatar, feed_url]
- `feed_url` 必须有效且可访问 RSS/Atom，否则该友链将被记录到 `errors.json`

HTTP 接口
- `/all`: 返回完整聚合结果
  - `statistical_data`: friends_num/active_num/error_num/article_num/last_updated_time
  - `article_data`: 统一文章列表（title/author/link/created/avatar）
- `/errors`: 返回抓取失败的友链原始条目列表
- `/random`: 随机返回一篇文章（用于前端小组件）

输出与日志
- `all.json`: 聚合文章数据（运行时生成）
- `errors.json`: 抓取失败的友链列表（运行时生成）
- `grab.log`: 运行日志（写入抓取与错误信息）

时间与解析说明
- 对文章时间进行统一格式化：`YYYY-MM-DD HH:MM`；若无时区信息，按 `+08:00` 处理。
- 若条目缺少可用时间，将记录警告并赋默认值以便排序。

项目结构
- `friend_circle/`: 核心逻辑
  - `get_info.py`: RSS/Atom 抓取、解析与聚合
  - `get_conf.py`: 配置文件加载
- `run.py`: 一次性抓取，生成 `all.json`/`errors.json`
- `server.py`: FastAPI 服务与定时任务（每 4 小时刷新）
- `conf.yaml`: 抓取配置（开关、并发、文章数、friend.json 地址）
- `requirements.txt`: 依赖列表

部署建议
- 以服务方式长期运行：`python server.py`（配合反向代理/守护）
- 若只需静态数据：定时任务（如 cron/GitHub Actions）执行 `python run.py`，将生成的 `all.json` 提供给前端使用。

常见问题
- “抓取不到/没数据”：检查 `json_url` 可达性与 friend.json 是否为上述结构；确保每条目包含 `feed_url`。
- “某个 RSS 失败”：在 `grab.log` 中查看对应错误与 HTTP 状态码；必要时更新该站的 `feed_url`。
