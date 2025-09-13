# Repository Guidelines

## Project Structure & Module Organization
- `friend_circle/`: Core scraping and config helpers (`get_info.py`, `get_conf.py`).
- `server.py`: FastAPI app entrypoint; schedules periodic fetches and writes `all.json`, `errors.json`, `grab.log`.
- `run.py`: One-off fetch/regeneration of JSON outputs.
- `conf.yaml`: Spider settings (`json_url`, `article_count`, `enable`).
- `requirements.txt`: Python dependencies.
- Outputs: `all.json`, `errors.json`, `grab.log` are generated at runtime; avoid manual edits.

## Build, Test, and Development Commands
- Create env and install: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- One-off fetch: `python run.py` (respects `conf.yaml`).
- Run API with scheduler: `python server.py` (serves on `0.0.0.0:1223`).
- Dev API only (no scheduler/fetch): `uvicorn server:app --reload`.
- Quick check: `curl http://localhost:1223/all`, `/errors`, `/random`.

## Coding Style & Naming Conventions
- Follow PEP 8; 4-space indentation; snake_case for functions/variables; lower_snake_case modules.
- Prefer small, pure functions; isolate network I/O; keep side effects in `server.py`/CLI layers.
- Add docstrings and type hints where reasonable. Use `logging` (writes to `grab.log`) over prints.

## Testing Guidelines
- No test suite yet. Use `pytest` for new tests.
- Place tests under `tests/`; name files `test_*.py`; mirror package paths.
- Mock network via `responses`/`requests-mock`; fix random seeds for determinism.
- Run tests: `pytest -q`.

## Commit & Pull Request Guidelines
- Commits are concise and descriptive (history includes emoji, e.g., “⏱️ GitHub Action 定时更新”). No strict convention enforced.
- Prefer Conventional Commits for new work: `feat:`, `fix:`, `docs:`, `refactor:`.
- PRs include: clear description, linked issues, config changes, sample commands/endpoints, and screenshots/log snippets when relevant.

## Security & Configuration Tips
- Keep secrets out of `conf.yaml`; use reachable `json_url` and realistic `article_count`.
- Respect timeouts; reuse `requests.Session`.
- Don’t commit large run artifacts; if new outputs are needed, place them under `results/` and gitignore.
