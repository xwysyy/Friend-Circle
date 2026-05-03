# Agentic RSS Adapter — Node.js Runtime

部署在你**自己的机器**（VPS / 树莓派 / 家里 NAS）上的 RSS 适配器。

适用场景：
1. **源站有 RSS 但 CF Worker 段也被反爬** —— 用这台机器的 IP 出口去抓
2. **源站完全没 RSS** —— 复杂 HTML 解析（`cheerio` / `jsdom`）放在 Node.js 比 Worker 自由

不适用：源站有 RSS、且 CF Worker 段没被反爬 —— 那种用 `runtime-worker/` 更轻、零运维。

## 部署（Docker，推荐）

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

如果消费方需要从公网拉取，三种方式按可用性排：

### 方式 A：Cloudflare Tunnel（最简，零端口转发）

```bash
docker run -d --restart unless-stopped --network host \
  -e TUNNEL_TOKEN=<your-tunnel-token> \
  cloudflare/cloudflared:latest tunnel --no-autoupdate run
```

在 CF Zero Trust 控制台把 tunnel 路由到 `http://localhost:8080`，得到 `https://<subdomain>.<your-domain>`。

### 方式 B：Caddy 反代 + Let's Encrypt（如有公网 IP）

```caddy
<subdomain>.<your-domain> {
    reverse_proxy localhost:8080
}
```

### 方式 C：直接用 IP+端口（仅 LAN）

不推荐——公网消费方访问家里 IP 通常不行（NAT/防火墙），且 IP 变动后要改消费方配置。

## 接入消费方

部署得到 RSS endpoint 后，把消费方源列表里对应行的 URL 改成它：

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

## 与 runtime-worker 的关系

两个 runtime 共享 `src/types.ts`、`src/lib/rss.ts` 的设计（同源不同构）。`adapter.ts` 接口完全一致——AI 生成的 adapter 代码可以在两个 runtime 间无改动迁移，只是 import 路径细节（worker 不带 `.js`，nodejs NodeNext 必须带 `.js`）由 AI 在生成时自适应。
