# Repository Guidelines

## Project Structure & Module Organization
- `app/`: Code package
  - `core.py`: Core scraping + config loader.
- `config/`: Config and friend list
  - `conf.yaml`: Spider settings (`json_url`, `article_count`, `enable`).
  - `friend.json`: Friend list (data source for feeds).
- `results/`: Runtime outputs (generated)
  - `all.json`, `errors.json`, `grab.log`
- `run.py`: One-off fetch/regeneration of JSON outputs.
- `requirements.txt`: Python dependencies.

## Build and Development Commands
- Install deps (uv): `uv pip install -r requirements.txt`.
- One-off fetch: `uv run python run.py` (respects `config/conf.yaml`).

## Coding Style & Naming Conventions
- Follow PEP 8; 4-space indentation; snake_case for functions/variables; lower_snake_case modules.
- Add docstrings and type hints where reasonable. Use `logging` (writes to `grab.log`) over prints.

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
- Respect timeouts; reuse `requests.Session`.
- Don’t commit large run artifacts; `results/` is generated and should be gitignored.
