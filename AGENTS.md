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

## Build, Test, and Development Commands
- Install deps (uv): `uv pip install -r requirements.txt`.
- Install pytest (if missing): `uv pip install pytest` (or `pip install pytest`).
- One-off fetch: `uv run python run.py` (respects `config/conf.yaml`).
- Run all tests: `pytest -q` (or `uv run pytest -q`).
- Run a single test: `pytest -q tests/test_core.py::test_format_published_time_default_timezone`.
- Coverage (optional): install `pytest-cov`, run `pytest --cov=app -q`.

## Coding Style & Naming Conventions
- Follow PEP 8; 4-space indentation; snake_case for functions/variables; lower_snake_case modules.
- Add docstrings and type hints where reasonable. Use `logging` (writes to `grab.log`) over prints.

## Testing Guidelines
- Test suite lives in `tests/` (e.g., `tests/test_core.py`, `tests/test_integration.py`, `tests/test_live_e2e.py`).
- Use `pytest`; name files `test_*.py`; mirror package paths for new tests.
- Most tests avoid real network (local HTTP server or monkeypatch). One live E2E test hits real feeds by default.
- To skip live E2E locally: `pytest -q -k "not fetch_live_from_config_friend_json"`.
- Common commands:
  - Run all: `pytest -q`
  - Filter by keyword: `pytest -q -k parse_feed`
  - Verbose/stream logs: `pytest -vv -s`
  - Coverage: `pytest --cov=app -q`

## Commit & Pull Request Guidelines
- Commits are concise and descriptive (history includes emoji, e.g., “⏱️ GitHub Action 定时更新”). No strict convention enforced.
- Prefer Conventional Commits for new work: `feat:`, `fix:`, `docs:`, `refactor:`.
- PRs include: clear description, linked issues, config changes, sample commands/endpoints, and screenshots/log snippets when relevant.

## Security & Configuration Tips
- Keep secrets out of `config/conf.yaml`; use reachable `json_url` and realistic `article_count`.
- Respect timeouts; reuse `requests.Session`.
- Don’t commit large run artifacts; `results/` is generated and should be gitignored.
