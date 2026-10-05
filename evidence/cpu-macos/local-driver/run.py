#!/usr/bin/python3
"""Sequential fresh-process CPU exports; component stats and external wall time stay separate."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = Path('/Users/gavinbintz/Developer/helios')
NODE = Path('/Users/gavinbintz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
FFMPEG = Path('/opt/homebrew/bin/ffmpeg')
FFPROBE = Path('/opt/homebrew/bin/ffprobe')
PROFILES = {'medium': (4, 8, 3, True), 'ultrafast': (6, 4, 0, False)}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def hashes(paths):
    return {str(path): sha256(path) for path in paths}


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def version(binary):
    flag = '--version' if binary == NODE else '-version'
    result = subprocess.run([str(binary), flag], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', required=True, type=Path)
    parser.add_argument('--timed', type=int, default=3)
    parser.add_argument('--warmups', type=int, default=1)
    parser.add_argument('--max-output-bytes', type=int, default=3 * 1024 ** 3)
    parser.add_argument('--results', type=Path)
    args = parser.parse_args()
    if args.timed < 1 or args.warmups < 0 or args.max_output_bytes < 1:
        parser.error('timed and output budget must be positive; warmups must be nonnegative')
    font = args.font.resolve(strict=True)
    portable = REPO / 'packages/portable'
    fixture = portable / 'benchmarks/fframes-textgrid.mjs'
    pool = portable / 'dist/canvas-pool.js'
    paths = sorted((portable / 'dist').glob('*.js')) + [fixture, font, portable / 'package.json',
                                                            HERE / 'run.py', HERE / 'worker.mjs', NODE, FFMPEG, FFPROBE]
    for required in [pool, *paths]:
        if not required.is_file():
            parser.error(f'missing file: {required}')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = args.results.resolve() if args.results else HERE / 'results' / stamp
    if not destination.is_relative_to(HERE):
        parser.error('results must stay inside local-driver/')
    destination.mkdir(parents=True, exist_ok=False)
    baseline = hashes(paths)
    metadata = {'createdUtc': stamp, 'python': sys.version, 'platform': platform.platform(),
                'machine': platform.machine(), 'logicalCpuCount': os.cpu_count(),
                'node': version(NODE), 'ffmpeg': version(FFMPEG), 'ffprobe': version(FFPROBE),
                'sourceSha256': baseline, 'sourcePolicy': 'live files hashed before and after each export; no frozen snapshot',
                'fixture': {'frames': 300, 'width': 1920, 'height': 1080, 'fps': 30, 'labels': 3334},
                'warmupsPerProfile': args.warmups, 'timedPerProfile': args.timed,
                'maxRetainedOutputBytes': args.max_output_bytes, 'records': []}
    manifest = destination / 'manifest.json'
    save(manifest, metadata)
    for preset, (workers, threads, bframes, scene_cut) in PROFILES.items():
        options = {'ffmpeg': str(FFMPEG), 'ffprobe': str(FFPROBE), 'concurrency': workers,
                   'chunkFrames': math.ceil(300 / workers), 'encoder': {'preset': preset, 'crf': 11,
                   'threads': threads, 'gop': 24, 'bframes': bframes, 'sceneCut': scene_cut,
                   'qmin': 15, 'qmax': 60, 'qcompress': 0.6, 'maxQdiff': 4, 'colorConversion': 'rgb-bt601'}}
        for phase, count in [('warmup', args.warmups), ('timed', args.timed)]:
            for index in range(1, count + 1):
                if hashes(paths) != baseline:
                    raise RuntimeError('source changed before export; start a new baseline')
                run = destination / f'{preset}-{phase}-{index}'
                run.mkdir()
                composition = run / 'composition.mjs'
                composition.write_text("import { readFile } from 'node:fs/promises';\n"
                                       f"import {{ createTextGrid }} from {json.dumps(fixture.as_uri())};\n"
                                       f"export default createTextGrid(await readFile({json.dumps(str(font))}));\n")
                config = {'poolModule': str(pool), 'composition': str(composition),
                          'output': str(run / 'output.mp4'), 'stats': str(run / 'component-stats.json'),
                          'options': options}
                save(run / 'config.json', config)
                command = [str(NODE), str(HERE / 'worker.mjs'), str(run / 'config.json')]
                record = {'profile': preset, 'phase': phase, 'index': index, 'command': command, 'exitCode': None,
                          'directory': str(run), 'compositionSha256': sha256(composition)}
                print(f'Launching {preset} {phase} {index}; results: {run}', flush=True)
                with (run / 'stdout.log').open('wb') as stdout, (run / 'stderr.log').open('wb') as stderr:
                    started = time.perf_counter_ns()
                    try:
                        result = subprocess.run(command, stdout=stdout, stderr=stderr, cwd=REPO)
                        record['exitCode'] = result.returncode
                    except BaseException as error:
                        record['launcherFailure'] = f'{type(error).__name__}: {error}'
                        raise
                    finally:
                        record['externalProcessWallNs'] = time.perf_counter_ns() - started
                        record['externalProcessWallMs'] = record['externalProcessWallNs'] / 1_000_000
                        record['outputBytes'] = Path(config['output']).stat().st_size if Path(config['output']).is_file() else 0
                        record['retainedOutputBytes'] = sum(path.stat().st_size for path in destination.glob('*/output.mp4'))
                        try:
                            record['sourceUnchanged'] = hashes(paths) == baseline
                        except OSError as error:
                            record['sourceUnchanged'] = False
                            record['sourceHashFailure'] = f'{type(error).__name__}: {error}'
                        metadata['records'].append(record)
                        save(run / 'process-result.json', record)
                        save(manifest, metadata)
                if record['exitCode'] != 0:
                    raise RuntimeError(f'export failed with exit {record["exitCode"]}; inspect {run}')
                if not Path(config['stats']).is_file() or not record['outputBytes']:
                    raise RuntimeError(f'export omitted stats or output; inspect {run}')
                if not record['sourceUnchanged']:
                    raise RuntimeError('source changed during export; measurement invalid')
                if record['retainedOutputBytes'] > args.max_output_bytes:
                    raise RuntimeError('retained-output budget exceeded; outputs preserved and further exports stopped')
    print(f'Complete; manifest: {manifest}', flush=True)


if __name__ == '__main__':
    main()
