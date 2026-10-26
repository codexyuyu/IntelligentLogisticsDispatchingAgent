"""Shared source-only package filter and ownership resolver."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
# 'archive/legacy' and 'archive/releases' are included only by packaging with --include-archive.
# 'r18_runs'/'r19_runs' hold transient benchmark runs; the frozen, hash-registered copies of
# the accepted runs live in benchmarks/b03/r18_accepted and benchmarks/b04/r19_accepted and
# are still shipped.
EXCLUDED = {'.venv', 'venv', 'node_modules', '__pycache__', '.git', '.pytest_cache', '.ruff_cache', 'dist', 'build', 'releases', 'legacy', 'coverage', 'r18_runs', 'r19_runs'}
ROOT_FILES = {'COLLABORATION_SPLIT_20261021.md', 'MERGE_NOTES.md', 'README.md', 'AGENTS.md', 'DEV_LOG.md', 'OWNERSHIP.json', 'FILE_MAP.md', '.gitignore', '.gitattributes', '.editorconfig', '.env.example'}
ROOT_DIRS = {'backend', 'frontend', 'contracts', 'docs', 'scripts', 'data', 'benchmarks', 'infra', 'archive', '.github'}


def source_files():
    return sorted(file for file in ROOT.rglob('*')
                  if file.is_file() and not file.is_symlink()
                  and not any(p in EXCLUDED or p.endswith('.egg-info') for p in file.relative_to(ROOT).parts)
                  and not file.name.endswith(('.pyc', '.zip', '.log', '.err'))
                  and (not file.name.startswith('.env') or file.name == '.env.example')
                  and (file.relative_to(ROOT).parts[0] in ROOT_DIRS or file.relative_to(ROOT).as_posix() in ROOT_FILES))


def owner_of(path: str):
    config = json.loads((ROOT / 'OWNERSHIP.json').read_text(encoding='utf-8'))
    matches = [(prefix, owner) for prefix, owner in config['paths'].items()
               if (prefix.endswith('/') and path.startswith(prefix)) or path == prefix]
    return max(matches, key=lambda pair: len(pair[0]))[1] if matches else config['default_owner']
