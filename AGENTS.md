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
  - `conf.yaml`: Spider settings (`json_url`, `article_count`, `enable`).
  - `*.json`: Friend lists (each file = a category).
- `results/`: Runtime outputs (generated)
  - `all.json`, `errors.json`, `all.personal.json`, `errors.personal.json`, `grab.log`

## Build and Development Commands
- Build: `go build .`
- One-off fetch: `go run .` (respects `config/conf.yaml`).

## Coding Style & Naming Conventions
- Go: Follow standard Go conventions; use `gofmt`; exported names PascalCase, unexported camelCase.
- Use `log` package (writes to `results/grab.log`) for logging.

## Testing Guidelines
- Tests have been removed from this repository.

## Commit & Pull Request Guidelines
- Conventional Commits enforced via hook:
  - Format: `type(scope)!: subject`
  - Types: `build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test`
  - Enable local hooks: `git config core.hooksPath .githooks`
  - CI uses message `chore: update RSS feeds`
- PRs include: clear description, linked issues, config changes, sample commands/endpoints, and screenshots/log snippets when relevant.

## Security & Configuration Tips
- Keep secrets out of `config/conf.yaml`; use reachable `json_url` and realistic `article_count`.
- Respect timeouts; reuse `http.Client` (connection pooling via Transport).
- Don’t commit large run artifacts; `results/` is generated and should be gitignored.
