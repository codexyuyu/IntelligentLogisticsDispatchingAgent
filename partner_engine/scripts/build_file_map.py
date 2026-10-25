"""Generate a complete path/owner map; no manual duplicate ownership table."""
from project_files import ROOT, source_files, owner_of
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    paths = {p.relative_to(ROOT).as_posix() for p in source_files()}
    paths.add('FILE_MAP.md')
    rows = ['# 文件骨架与责任清单', '', '由 scripts/build_file_map.py 根据实际文件和 OWNERSHIP.json 生成。业务实现状态以文件 TODO 和开发日志为准；文件存在不等于功能完成。', '', '| 文件 | 负责人 |', '| --- | --- |']
    rows += [f'| [{path}]({path}) | {owner_of(path)} |' for path in sorted(paths)]
    result = '\n'.join(rows) + '\n'
    file = ROOT / 'FILE_MAP.md'
    if args.check:
        if not file.exists() or file.read_text(encoding='utf-8') != result:
            raise SystemExit('FILE_MAP drift: run python scripts/build_file_map.py')
    else:
        file.write_text(result, encoding='utf-8')
    print(f'File map: {len(paths)} source files')


if __name__ == '__main__':
    main()
