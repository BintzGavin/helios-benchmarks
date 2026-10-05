#!/usr/bin/env python3
"""Verify retained Git evidence and relative documentation links; no exports."""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    catalog = json.loads((ROOT / 'data/evidence-catalog.json').read_text())
    failures = []
    count = 0
    logical_paths = set()
    assets = {item['name']: item for item in catalog['assets']}
    for row in catalog['files']:
        if row['path'] in logical_paths:
            failures.append('duplicate logical path: ' + row['path'])
        logical_paths.add(row['path'])
        if row['kind'] != 'file':
            continue
        storage = row['storage']
        if storage['kind'] == 'git':
            path = ROOT / storage['path']
            if not path.is_file() or path.stat().st_size != row['bytes'] or sha256(path) != row['sha256']:
                failures.append('evidence mismatch: ' + row['path'])
            count += 1
        else:
            asset = assets.get(storage['name'])
            if asset is None or storage['url'] != asset['url']:
                failures.append('unbound asset: ' + row['path'])
            elif storage['kind'] == 'release-asset' and (row['sha256'], row['bytes']) != (asset['sha256'], asset['bytes']):
                failures.append('asset identity mismatch: ' + row['path'])
            elif storage['kind'] == 'release-bundle' and storage['member'] != 'objects/' + row['sha256']:
                failures.append('bundle identity mismatch: ' + row['path'])
    # Historical evidence uses original machine paths; only authored documents
    # claim that relative links resolve in this relocated repository.
    for path in [ROOT / 'README.md', *ROOT.glob('docs/*.md'), *ROOT.glob('studies/*.md')]:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if ':' in target or target.startswith('#'):
                continue
            resolved = (path.parent / target.split('#')[0]).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                failures.append('broken link in ' + str(path.relative_to(ROOT)) + ': ' + target)
    print(json.dumps({'gitEvidenceChecked': count, 'catalogPaths': len(logical_paths), 'assets': len(assets), 'failures': failures}, indent=2))
    return bool(failures)

if __name__ == '__main__':
    sys.exit(main())
