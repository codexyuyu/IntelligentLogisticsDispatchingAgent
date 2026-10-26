# Windows setup

1. Open PowerShell in this folder.
2. Create a fresh virtual environment: `py -3.14 -m venv .venv`
3. Install dependencies: `./.venv/Scripts/python.exe -m pip install -r backend/requirements-lock.txt`
4. Install algorithm deps: `./.venv/Scripts/python.exe -m pip install ortools==9.15.6755 simpy==4.1.1`
5. Run tests: `./.venv/Scripts/python.exe -m pytest backend`
6. Start API: `./.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`

This archive intentionally excludes `.venv`, caches, and generated Python bytecode.
