#!/usr/bin/env python3
"""Fetch exact evidence objects for one namespace; never execute artifacts."""
import argparse
import hashlib
import json
import pathlib
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

def identity(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return path.stat().st_size, h.hexdigest()

def destination(root, name):
    p = (root / name).resolve()
    if not p.is_relative_to(root):
        raise ValueError('unsafe evidence path')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--match', required=True, help='Evidence namespace prefix, e.g. cpu-orb')
    parser.add_argument('--directory', type=pathlib.Path, required=True, help='New output directory')
    args = parser.parse_args()
    output = args.directory.resolve()
    if output.exists():
        raise ValueError('output directory must be new')
    catalog = json.loads((ROOT / 'data/evidence-catalog.json').read_text())
    rows = [r for r in catalog['files'] if r['path'].startswith(args.match) and r['kind'] == 'file']
    if not rows:
        raise ValueError('no matching files')
    needed = {r['storage']['name'] for r in rows if r['storage']['kind'] != 'git'}
    assets = {a['name']: a for a in catalog['assets']}
    print(json.dumps({'matchingFiles': len(rows), 'assetDownloads': len(needed), 'downloadBytes': sum(assets[n]['bytes'] for n in needed)}, indent=2))
    output.mkdir(parents=True)
    cache = output / '.download-cache'
    cache.mkdir()
    for name in sorted(needed):
        asset = assets[name]
        p = destination(cache, name)
        request = urllib.request.Request(asset['url'], headers={'User-Agent': 'helios-benchmarks-evidence-verifier'})
        with urllib.request.urlopen(request, timeout=120) as response, p.open('xb') as stream:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                stream.write(block)
        if identity(p) != (asset['bytes'], asset['sha256']):
            raise ValueError('download mismatch: ' + name)
    bundle_handles = {}
    try:
        for row in rows:
            p = destination(output, row['path'])
            storage = row['storage']
            if storage['kind'] == 'git':
                source = (ROOT / storage['path']).open('rb')
            elif storage['kind'] == 'release-asset':
                source = (cache / storage['name']).open('rb')
            else:
                name = storage['name']
                if name not in bundle_handles:
                    bundle_handles[name] = tarfile.open(cache / name, 'r:gz')
                archive = bundle_handles[name]
                member = archive.getmember(storage['member'])
                if not member.isfile() or member.size != row['bytes']:
                    raise ValueError('invalid object member')
                source = archive.extractfile(member)
            with source, p.open('xb') as target:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    target.write(block)
            if identity(p) != (row['bytes'], row['sha256']):
                raise ValueError('restored identity mismatch: ' + row['path'])
    finally:
        for archive in bundle_handles.values():
            archive.close()
    print(json.dumps({'restoredFiles': len(rows), 'byteIdentitiesVerified': True}))

if __name__ == '__main__':
    main()
