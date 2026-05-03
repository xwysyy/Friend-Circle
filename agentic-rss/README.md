# Agentic RSS

一套 **手动触发、AI 编写、Cloudflare Worker 部署** 的 RSS 适配器工具集。

定位：Friend-Circle 主程序在 GitHub Actions 上抓不到、但站点本身有 RSS 或可解析页面的友链 —— 用一个跑在 Cloudflare 边缘的 worker 把那个 feed 重新拉出来。

## 何时使用

`results/errors.json` 里某个 `feed_url` 持续失败，且本地手动 curl 能拿到内容 —— 这通常是站点对 GitHub Runner IP 段做了反爬挑战（Vercel / Cloudflare / nginx 限频）。

你不想从 `config/*.json` 里移除这个友链 → 给它做一个 worker adapter。

**不在自动化里**：本工具是一次性的「人 + AI」配合流程，不监测、不自动触发。

## 工作流

```
1. 用户：发现 https://example.com/rss.xml 在 errors.json 里持续躺着
2. 用户：把 prompts/adapter-author.md 喂给 AI（Claude / Codex / GPT），附上目标 URL
3. AI：探查站点 → 选实现策略 → 填模板 → 给出 adapter 代码
4. 用户：把 template/ 拷到仓库外（如 ~/Code/ginblog/agentic-rss-instances/<site>/）
        → 粘贴 AI 输出 → npx wrangler deploy
5. 用户：把 config/*.json 里的 feed_url 改成 worker URL（一行 diff）
6. 下一轮 CI 跑：成功
```

## 目录

- `template/` — Cloudflare Worker 骨架（fetch / rss 输出 / types 等公共代码，**版本化在仓内**）
- `prompts/adapter-author.md` — 给 AI 的操作手册（定义探查步骤 / 实现策略 / 输出格式）

**实例不入仓**：每个站点的 worker 是从 `template/` 拷出来的一次性产物，部署到用户自己的 Cloudflare 账户，**不提交回 Friend-Circle**。这样仓内只有"骨架 + prompt"，骨架升级时所有实例可以重新拷一份。

## 与 RSSHub 的区别

| | RSSHub | Agentic RSS（本工具） |
|---|---|---|
| 适配器来源 | 社区贡献 PR | AI 现场推断 + 用户审 |
| 部署粒度 | 单服务多 route | 每站点一个独立 worker |
| 用途 | 通用聚合站 | 解决「源 RSS 被反爬」单点问题 |
| 维护 | 跟踪上游变化 | 失效后重跑一次 prompt 即可 |

不替代 RSSHub —— 它是 RSSHub 没收录或不便部署时的轻量替代。

## 部署所需

- Node.js 18+
- Cloudflare 账户（免费 plan 足够，每天 100k 请求 + 30 个 worker 上限）
- 一次性 `npx wrangler login` 授权本机

具体步骤见 `template/README.md` 和各 `adapters/<site>/README.md`。
