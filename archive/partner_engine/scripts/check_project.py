"""Verify package links, source-only import boundaries and generated contract files."""
import ast
import re
import subprocess
import sys
from project_files import ROOT, source_files


def main():
    errors = []
    for file in source_files():
        rel = file.relative_to(ROOT).as_posix()
        if file.suffix == '.py':
            tree = ast.parse(file.read_text(encoding='utf-8-sig'), filename=rel)
            for node in ast.walk(tree):
                imports = []
                if isinstance(node, ast.Import):
                    imports = [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imports = [node.module or '']
                for name in imports:
                    if rel.startswith('backend/app/domain/'):
                        root = name.split('.')[0]
                        if root not in sys.stdlib_module_names and not name.startswith(('app.domain', 'app.common')):
                            errors.append(f'{rel}: domain cannot import {name}')
                    if rel.startswith('backend/app/application/') and name.startswith('app.adapters'):
                        errors.append(f'{rel}: application cannot import adapters')
                    if rel.startswith('backend/app/') and name.startswith(('reference_demos', 'frontend')):
                        errors.append(f'{rel}: business code cannot import reference/frontend')
        if file.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', file.read_text(encoding='utf-8-sig')):
                if '://' in link or link.startswith('#'):
                    continue
                target = link.split('#')[0].strip('<>')
                if target and not (file.parent / target).exists():
                    errors.append(f'{rel}: broken link {target}')
    if errors:
        raise SystemExit('\n'.join(errors))
    subprocess.run([sys.executable, str(ROOT / 'scripts/export_contracts.py'), '--check'], check=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_file_map.py'), '--check'], check=True)
    print('Project source, links, boundaries and generated contracts: PASS')


if __name__ == '__main__':
    main()
