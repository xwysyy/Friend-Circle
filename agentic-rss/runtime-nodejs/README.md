# Agentic RSS Adapter — Node.js Runtime

部署在自托管机器（VPS / 树莓派 / 家里 NAS）上的 RSS 适配器。

适合自托管出口、较重 HTML/JSON 解析。

轻量解析优先用 `runtime-worker/`。

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

公网消费方可以用以下入口：

Cloudflare Tunnel 最简单，零端口转发：

```bash
docker run -d --restart unless-stopped --network host \
  -e TUNNEL_TOKEN=<your-tunnel-token> \
  cloudflare/cloudflared:latest tunnel --no-autoupdate run
```

在 CF Zero Trust 控制台把 tunnel 路由到 `http://localhost:8080`，得到 `https://<subdomain>.<your-domain>`。

公网 IP 场景可用 Caddy 反代加 Let's Encrypt：

```caddy
<subdomain>.<your-domain> {
    reverse_proxy localhost:8080
}
```

直接用 IP+端口通常只适合内网。公网消费方需要稳定入口。

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

两个 runtime 共用 `FeedAdapter` 接口（`build(ctx) -> string`）。`Article` / `FeedMeta` 数据形态一致，`ctx` 暴露 `request` 和 `fetchUrl`。Worker import 不带 `.js`，Node.js runtime 使用 `.js` 后缀。
