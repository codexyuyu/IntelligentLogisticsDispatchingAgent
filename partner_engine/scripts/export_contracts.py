"""Export the sole contract source, or fail if committed outputs have drifted."""
from pathlib import Path
import argparse
import importlib
import inspect
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.main import app
from app.contracts.common import CONTRACT_VERSION, ContractModel


def outputs():
    models = {}
    for name in ('common', 'entities', 'coldchain', 'planning', 'events', 'http'):
        module = importlib.import_module('app.contracts.' + name)
        for key, value in vars(module).items():
            if inspect.isclass(value) and issubclass(value, ContractModel) and value is not ContractModel and value.__module__ == module.__name__:
                models[key] = value.model_json_schema()
    def dump(obj):
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    return {'contracts/openapi.json': dump(app.openapi()),
            'contracts/schemas.json': dump({'contract_version': CONTRACT_VERSION, 'models': models}),
            'contracts/VERSION': CONTRACT_VERSION + '\n'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    changed = []
    for path, content in outputs().items():
        file = ROOT / path
        if args.check:
            if not file.exists() or file.read_text(encoding='utf-8') != content:
                changed.append(path)
        else:
            file.parent.mkdir(exist_ok=True, parents=True)
            file.write_text(content, encoding='utf-8')
    if changed:
        raise SystemExit('Contract drift: ' + ', '.join(changed))
    print('Contracts match source' if args.check else 'Exported contracts')


if __name__ == '__main__':
    main()
