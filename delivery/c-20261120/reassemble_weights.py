"""Join downloaded weight parts in a new directory; never replace an existing target."""
import argparse
import hashlib
import json
from pathlib import Path

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            value.update(block)
    return value.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path.cwd())
    args = parser.parse_args()
    directory = args.directory.resolve(strict=True)
    plan = json.loads((directory / 'GITHUB-ASSETS.json').read_text(encoding='utf-8'))
    join = plan['reassembly']
    names = [join['target'], *join['parts']]
    if any(Path(name).name != name or '/' in name or '\\' in name for name in names):
        raise ValueError('Manifest names must be simple filenames')
    target = directory / join['target']
    if target.exists():
        if target.stat().st_size != join['size'] or digest(target) != join['sha256']:
            raise ValueError('Existing target differs; preserved without overwrite')
        print('Existing complete archive verified; nothing overwritten.')
        return
    assets = {item['name']: item for item in plan['assets']}
    for name in join['parts']:
        part = directory / name
        if part.stat().st_size != assets[name]['size'] or digest(part) != assets[name]['sha256']:
            raise ValueError(f'Part checksum mismatch: {name}')
    temporary = target.with_name(target.name + '.joining')
    total = 0
    whole = hashlib.sha256()
    with temporary.open('xb') as output:
        for name in join['parts']:
            with (directory / name).open('rb') as stream:
                while block := stream.read(4 * 1024 * 1024):
                    output.write(block)
                    whole.update(block)
                    total += len(block)
    if total != join['size'] or whole.hexdigest() != join['sha256']:
        raise ValueError('Joined checksum mismatch; .joining file retained for inspection')
    temporary.rename(target)
    print(f'Verified {target.name}: {whole.hexdigest()}')

if __name__ == '__main__':
    main()
