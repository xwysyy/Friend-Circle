# Repository Guidelines

## Project Structure & Module Organization
- `main.go`: Go entry point.
- `scraper/`: Go scraping package
  - `types.go`: Shared data types (Article, Result, Config, etc.).
  - `config.go`: YAML/JSON config loading + ignore list fetching.
  - `fetcher.go`: HTTP client (HTTP/2, retry, connection pooling) + concurrent processing.
  - `feed.go`: RSS/Atom feed parsing via `gofeed` + time normalization.
  - `rewriter.go`: Link rewriting (prefix + regex).
- `config/`: Config and friend list
  - `conf.yaml`: Spider settings (`enable`, `json_url`, `article_count`, `max_workers`, optional `ignore_url`, optional `link_rewrites`).
  - `*.json`: Friend lists (each file = a category; merged when `json_url` points at a local path).
- `results/`: Runtime outputs (generated)
  - `all.json` / `errors.json`: full scrape.
  - `all.personal.json` / `errors.personal.json`: second pass that skips IDs from `ignore_url` (or env `FRIEND_CIRCLE_IGNORE_URL`); falls back to the full scrape when the ignore list is empty/unreachable.
  - `grab.log`: run log (gitignored).
- `agentic-rss/`: RSS adapter templates for sites without a reliable RSS feed
  - `prompts/adapter-author.md`: instructions for generating a site adapter.
  - `runtime-worker/`: Cloudflare Worker template.
  - `runtime-nodejs/`: Node.js + Docker template.
  - Both runtimes expose the same `FeedAdapter` shape: `build(ctx) -> RSS XML string`.

## Build and Development Commands
- Build: `go build .`
- One-off fetch: `go run .` (respects `config/conf.yaml`).
- Worker adapter dev: `cd agentic-rss/runtime-worker && npm run dev`
- Worker adapter typecheck: `cd agentic-rss/runtime-worker && npm run typecheck`
- Node adapter dev: `cd agentic-rss/runtime-nodejs && npm run dev`
- Node adapter typecheck: `cd agentic-rss/runtime-nodejs && npm run typecheck`
- Node adapter Docker run: `cd agentic-rss/runtime-nodejs && docker compose up -d --build`

## Coding Style & Naming Conventions
- Go: Follow standard Go conventions; use `gofmt`; exported names PascalCase, unexported camelCase.
- Use `log` package (writes to `results/grab.log`) for logging.
- Agentic RSS: edit `src/adapter.ts` for site-specific logic. Keep shared runtime files (`src/types.ts`, `src/lib/*`, `src/index.ts`, `src/server.ts`) stable unless updating the template itself.
- TypeScript import paths differ by runtime: Worker imports omit `.js`; Node.js uses NodeNext-style `.js` suffixes.

## Testing Guidelines
- Tests have been removed from this repository.
- For Go changes, at minimum run `go build .`.
- For Agentic RSS template changes, run the matching `npm run typecheck`.

## Commit & Pull Request Guidelines
- Conventional Commits:
  - Format: `type(scope)!: subject`
  - Types: `build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test`
  - CI uses message `chore: update rss feeds`
- PRs include: clear description, linked issues, config changes, sample commands/endpoints, and screenshots/log snippets when relevant.

## Security & Configuration Tips
- Keep secrets out of `config/conf.yaml`; use reachable `json_url` and realistic `article_count`.
- Respect timeouts; reuse `http.Client` (connection pooling via Transport).
- `results/` JSON outputs are committed (CI publishes them); only `results/grab.log` is gitignored.
- Do not commit `agentic-rss/**/node_modules/`, `agentic-rss/**/dist/`, or runtime-local lockfiles. They are local tooling artifacts.
- Adapter secrets should come from Worker secrets or Node.js environment variables, not source files.
