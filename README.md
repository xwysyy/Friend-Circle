<div align="center">

# Friend Circle · 友链文章聚合器 ✨

[![CI - Friend Circle](https://github.com/xwysyy/Friend-Circle/actions/workflows/friend_circle.yml/badge.svg)](https://github.com/xwysyy/Friend-Circle/actions/workflows/friend_circle.yml)
![RSS](https://img.shields.io/badge/RSS-Feed-FFA500?logo=rss&logoColor=white)
![uv](https://img.shields.io/badge/Package%20Manager-uv-5C6EE3)
![Last commit](https://img.shields.io/github/last-commit/xwysyy/Friend-Circle?color=57A64A)
<br>
![Vercel](https://img.shields.io/badge/Vercel-333?logo=vercel)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/xwysyy/Friend-Circle)

一个简洁稳健的「友链文章聚合器」，从 `config/conf.yaml` 读取数据源，抓取各博客的 RSS/Atom，输出统一 JSON：`results/all.json`。

</div>

---

## 🚀 特性亮点

- ⚡ 并发抓取：可配置 `max_workers`，快且稳。
- 🔁 请求重试：`requests.Session` + 指数回退，提升成功率。
- 🧭 时间统一：输出时间格式 `YYYY-MM-DD HH:MM`，缺失时合理兜底。
- 🧩 RSS/Atom 兼容：多源解析，结构化为统一 JSON。
- 🧪 可本地/远程数据源：`json_url` 支持文件或 HTTP(S)。
- 🛰️ 自动化：GitHub Actions 每 6 小时定时更新，可手动触发。

## 📦 快速开始

1) 安装依赖（使用 `uv`）

- 安装 uv（推荐）：https://docs.astral.sh/uv/
- 安装项目依赖：

```
uv pip install -r requirements.txt
```

2) 配置抓取参数（`config/conf.yaml`）

- `spider_settings.enable`：是否启用抓取（`true/false`）
- `spider_settings.json_url`：你的 `friend.json`（本地路径或 HTTP/HTTPS，默认 `config/friend.json`）
- `spider_settings.article_count`：每个博客抓取的最大文章数
- `spider_settings.max_workers`：抓取并发（建议 5–20，视机器与友链规模）

3) 一次性抓取生成 JSON

```
uv run python run.py
```

完成后在 `results/` 下生成：`all.json`、`errors.json`、`grab.log`。

## 🔧 配置详解（conf.yaml）

```yaml
spider_settings:
  enable: true              # 是否启用爬虫
  json_url: "config/friend.json" # 数据源（本地/远程 JSON）
  article_count: 10         # 每个博客最多抓取文章数
  max_workers: 5            # 并发数，建议 ≤ 20
```

## 🤝 数据源（friend.json）

- 条目顺序固定：`[name, blog_url, avatar, feed_url]`
- `feed_url` 必须可访问 RSS/Atom，否则会被记录到 `errors.json`

示例：

```json
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

## 📤 运行产物与日志（`results/`）

- `all.json`：聚合后的文章数据
- `errors.json`：抓取失败的友链条目（原始 4 元组）
- `grab.log`：运行日志（抓取进度、错误摘要等）

## 🗓️ 自动化（GitHub Actions）

- 工作流：`.github/workflows/friend_circle.yml`
- 计划任务：每 6 小时执行一次（可手动 `workflow_dispatch`）
- 你也可以 Fork 后在自己仓库开启同名 Workflow 并配置 `PAT_TOKEN`

## 🧱 项目结构

```
.
├── app/
│   └── core.py           # 配置加载、RSS/Atom 抓取、解析与聚合（核心逻辑）
├── config/
│   ├── conf.yaml         # 抓取配置（开关、并发、文章数、数据源）
│   └── friend.json       # 友链列表（数据源）
├── results/              # 运行时生成：all.json, errors.json, grab.log
├── run.py                # 一次性抓取入口
├── requirements.txt      # 依赖列表
└── .github/workflows/    # CI 定时抓取
```

## ❓常见问题（FAQ）

- 抓取不到/没数据？
  - 检查 `json_url` 可达性及 `friend.json` 结构是否符合规范；确保每条目包含有效 `feed_url`。
- 某个 RSS 失败？
  - 查看 `results/grab.log` 中对应错误与 HTTP 状态码；必要时更新该站点的 `feed_url`。
- 时间字段缺失？
  - 会记录警告并采用默认值，以保证排序稳定；建议源头补齐时间信息。

## 🧪 开发与测试

- 依赖安装：`uv pip install -r requirements.txt`
- 安装测试框架：`uv pip install pytest`（或 `pip install pytest`）
- 本地运行：`uv run python run.py`
- 运行全部测试：

```
pytest -q
# 或使用 uv 执行
uv run pytest -q
```

- 选择性运行：

```
# 只跑核心单测
pytest -q tests/test_core.py

# 只跑某个用例
pytest -q tests/test_core.py::test_format_published_time_default_timezone

# 按关键字筛选
pytest -q -k parse_feed

# 更详细输出/打印日志
pytest -vv -s
```

- 覆盖率（可选）：

```
uv pip install pytest-cov  # 或 pip install pytest-cov
pytest --cov=app -q
```

- 测试说明：
  - 测试位于 `tests/`，包括 `tests/test_core.py` 与 `tests/test_integration.py`。
  - 集成测试会本地起一个轻量 HTTP 服务，或使用 monkeypatch 伪造网络会话，不访问外网。
  - 编写新测试时，建议使用 `responses` / `requests-mock` 模拟网络，并固定随机种子以保证一致性。
  - 本仓库包含一个“实网”测试用例，会直接拉取 `config/friend.json` 中的真实 RSS 链接，并对结果做基本校验（带容错），默认会随 `pytest` 一起运行；若你不希望访问外网，可在运行时排除该用例：

```
pytest -q -k "not fetch_live_from_config_friend_json"
# 或使用 uv
uv run pytest -q -k "not fetch_live_from_config_friend_json"
```

注意：
- 为了避免对上游施加过大压力，实网测试每个友链只抓 1 篇，且并发限制为 4；同时收敛了超时与重试以加快失败路径。
- 若网络或上游不稳定，测试可能标记为 xfail（预期失败），而不是硬失败。

## 🪪 许可协议

本项目使用 MIT License，详见 `LICENSE`。

---

如果你觉得有用，欢迎点亮 ⭐ Star、提 Issue/PR！
