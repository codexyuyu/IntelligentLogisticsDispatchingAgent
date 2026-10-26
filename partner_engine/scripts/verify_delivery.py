"""Run the same non-mutating acceptance commands on either developer's checkout."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True,
                        help='New evidence directory; existing records are never overwritten')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if not npm:
        raise SystemExit('npm is required; install Node and run npm ci in frontend first')
    commands = [
        ('python-version', [sys.executable, '--version'], ROOT),
        ('node-version', ['node', '--version'], ROOT),
        ('npm-version', [npm, '--version'], ROOT),
        ('dependencies', [sys.executable, '-m', 'pip', 'check'], ROOT),
        ('backend-contracts', [sys.executable, 'scripts/export_contracts.py', '--check'], ROOT),
        ('preparation', [sys.executable, 'scripts/import_preparation_bundle.py', '--check'], ROOT),
        ('backend-tests', [sys.executable, '-m', 'pytest', '-q'], ROOT / 'backend'),
        ('frontend-contracts', [npm, 'run', 'contracts:check'], ROOT / 'frontend'),
        ('frontend-tests', [npm, 'test'], ROOT / 'frontend'),
        ('frontend-build', [npm, 'run', 'build'], ROOT / 'frontend'),
        ('file-map', [sys.executable, 'scripts/build_file_map.py', '--check'], ROOT),
        ('architecture', [sys.executable, 'scripts/check_project.py'], ROOT),
    ]
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'root': str(ROOT),
              'python': sys.executable, 'commands': []}
    for name, argv, cwd in commands:
        log = out / (name + '.log')
        print(f'Running {name}', flush=True)
        with log.open('wb') as stream:
            result = subprocess.run(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        report['commands'].append({'name': name, 'argv': argv, 'cwd': str(cwd),
                                   'exit_code': result.returncode, 'log': log.name,
                                   'sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
        (out / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'{name}: exit {result.returncode}', flush=True)
    report['passed'] = all(c['exit_code'] == 0 for c in report['commands'])
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    (out / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
