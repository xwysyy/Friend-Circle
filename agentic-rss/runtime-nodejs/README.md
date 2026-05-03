# Agentic RSS Adapter — Node.js Runtime

部署在自托管机器（VPS / 树莓派 / 家里 NAS）上的 RSS 适配器。

两种情况下用它：源站有 RSS 但 CF Worker 段也被反爬，需要换出口 IP；或者源站没 RSS，要做较重的 HTML 解析（cheerio、jsdom 一类），Worker 的 CPU 预算撑不住。

如果源站有 RSS、CF 段又能过，用 `runtime-worker/` 更轻、不用维护机器。

## 部署

推荐 Docker。

```bash
# 1. 在 cp 出来的目录里填好 src/adapter.ts（按 prompts/adapter-author.md 让 AI 生成）
# 2. 起服务
docker compose up -d --build
# 3. 验证
curl http://localhost:8080/health        # → ok
curl http://localhost:8080/feed          # → RSS XML
```

服务暴露 `:8080/feed`、`/feed.xml`、`/`、`/health`。

## 暴露给公网

如果消费方要从公网拉，三种做法按可用性排：

Cloudflare Tunnel 最简单，零端口转发：

```bash
docker run -d --restart unless-stopped --network host \
  -e TUNNEL_TOKEN=<your-tunnel-token> \
  cloudflare/cloudflared:latest tunnel --no-autoupdate run
```

在 CF Zero Trust 控制台把 tunnel 路由到 `http://localhost:8080`，得到 `https://<subdomain>.<your-domain>`。

如果有公网 IP，Caddy 反代加 Let's Encrypt 也够用：

```caddy
<subdomain>.<your-domain> {
    reverse_proxy localhost:8080
}
```

直接用 IP+端口仅 LAN 内能跑——公网消费方一般过不了 NAT/防火墙，IP 变了还要改消费方配置。不推荐。

## 接入消费方

部署得到 RSS endpoint 后，把消费方源列表里那一行的 URL 改成它：

```diff
- "https://<old-feed-url>"
+ "https://<new-endpoint>/feed"
```

## 本地开发

```bash
npm install
npm run dev      # tsx watch 热重启
npm run typecheck
```

## 跟 runtime-worker 的关系

两个 runtime 用同一份 `FeedAdapter` 接口（`build(ctx) → string`），同一组 `Article` / `FeedMeta` 数据形态，`ctx` 暴露同样的 `request` 和 `fetchUrl`。差别只在 import 路径：worker 不带 `.js`，NodeNext 必须带 `.js`。
