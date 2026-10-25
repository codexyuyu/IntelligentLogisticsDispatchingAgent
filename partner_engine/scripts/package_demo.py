"""Build a portable source ZIP with per-file hashes; never ship environments or keys."""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from project_files import ROOT, source_files, owner_of


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'archive/releases/demo.zip')
    parser.add_argument('--top-level', default='demo',
                        help='single top-level folder name inside the ZIP; delivery rule requires exactly one')
    parser.add_argument('--include-archive', action='store_true',
                        help='include preserved legacy sources and old release ZIPs; for complete handoff')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.suffix.lower() != '.zip':
        raise SystemExit('Output must be .zip')
    top = args.top_level.strip('/')
    if not top or '/' in top or '\\' in top:
        raise SystemExit('--top-level must be one folder name')
    output.parent.mkdir(parents=True, exist_ok=True)
    files = source_files()
    if args.include_archive:
        extra = [f for f in (ROOT / 'archive').rglob('*')
                 if f.is_file() and f.resolve() != output
                 and not any(part in {'.git', '.venv', 'venv', 'node_modules', '__pycache__',
                                      '.pytest_cache', '.ruff_cache', 'dist', 'build', 'target',
                                      'r18_runs', 'r19_runs'}
                             for part in f.relative_to(ROOT).parts)
                 and not f.name.endswith(('.pyc', '.log', '.err'))]
        files = sorted(set(files).union(extra))
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(),
                'contract_version': (ROOT / 'contracts/VERSION').read_text().strip(),
                'top_level': top,
                'files': []}
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for file in files:
            rel = file.relative_to(ROOT).as_posix()
            content = file.read_bytes()
            manifest['files'].append({'path': rel, 'owner': owner_of(rel), 'sha256': sha256(content).hexdigest()})
            archive.writestr(f'{top}/' + rel, content)
        archive.writestr(f'{top}/PACKAGE_MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise SystemExit('ZIP CRC failed')
        names = archive.namelist()
        if {name.split('/', 1)[0] for name in names} != {top}:
            raise SystemExit('ZIP must contain exactly one top-level folder')
        for item in manifest['files']:
            if sha256(archive.read(f'{top}/' + item['path'])).hexdigest() != item['sha256']:
                raise SystemExit('ZIP content mismatch')
    # Keep the adjacent on-disk manifest consistent with the one inside this ZIP.
    (ROOT / 'PACKAGE_MANIFEST.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    digest = sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    print(f'Packaged {len(files)} source files + manifest: {output} ({output.stat().st_size} bytes)')
    print(f'SHA256: {digest}')
    return output


if __name__ == '__main__':
    main()
