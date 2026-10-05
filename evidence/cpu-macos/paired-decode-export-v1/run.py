#!/usr/bin/python3
"""Frozen paired CPU exports. Launch only after the decoder study selects threads."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import time

HERE = Path(__file__).resolve().parent
NODE = Path('/Users/gavinbintz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
FFMPEG = Path('/opt/homebrew/bin/ffmpeg')
FFPROBE = Path('/opt/homebrew/bin/ffprobe')
PROFILES = {'medium': (4, 8, 3, True), 'ultrafast': (6, 4, 0, False)}
PATTERN = "['-v', 'error', '-threads', '1', packets ? '-count_packets' : '-count_frames', '-show_streams', '-show_format', '-of', 'json', path]"
BUDGET = 4 * 1024 ** 3


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def retained():
    return sum(p.stat().st_size for p in HERE.rglob('*.mp4') if p.is_file())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decode-threads', required=True, type=int, choices=(8,))
    parser.add_argument('--pairs', type=int, default=3)
    parser.add_argument('--warmups', type=int, choices=(0, 1), default=1)
    parser.add_argument('--results', type=Path)
    args = parser.parse_args()
    if args.pairs < 1:
        parser.error('pairs must be positive')
    snapshot = json.loads((HERE / 'snapshot.json').read_text())
    frozen = {HERE / name: value for name, value in snapshot['snapshotSha256'].items()}
    if any(sha(path) != value for path, value in frozen.items()):
        raise RuntimeError('frozen snapshot changed; prepare a new study')
    original = (HERE / 'baseline/dist/render.js').read_text()
    if original.count(PATTERN) != 1 or original.count('async function probeVideoCount(path, options, packets) {') != 1:
        raise RuntimeError('expected exactly one probeVideoCount argv pattern; no candidate generated')
    candidate = HERE / 'candidate'
    compiled = (candidate / 'dist/render.js').read_text()
    expected = PATTERN.replace("'-threads', '1'", "'-threads', packets ? '1' : String(Math.min(8, availableParallelism()))")
    if compiled.count(expected) != 1:
        raise RuntimeError('compiled candidate does not match expected decoder policy')
    host = json.loads(subprocess.run([str(NODE), '--input-type=module', '-e', "import { availableParallelism } from 'node:os'; console.log(JSON.stringify({availableParallelism:availableParallelism(),decoderThreads:Math.min(8,availableParallelism())}));"], capture_output=True, text=True, check=True).stdout)
    if host['decoderThreads'] != args.decode_threads:
        raise RuntimeError('actual compiled decoder budget does not match requested threads')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = args.results.resolve() if args.results else HERE / 'results' / stamp
    if not destination.is_relative_to(HERE / 'results'):
        parser.error('results must stay inside paired-decode-export-v1/results/')
    if retained() >= BUDGET:
        raise RuntimeError('retained-output budget exhausted; outputs preserved')
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'candidate.diff').write_text((HERE / 'candidate.diff').read_text())
    baseline_hashes = {str(p.relative_to(HERE / 'baseline')): sha(p) for p in sorted((HERE / 'baseline').rglob('*')) if p.is_file()}
    candidate_hashes = {str(p.relative_to(candidate)): sha(p) for p in sorted(candidate.rglob('*')) if p.is_file()}
    candidate_js = {name: value for name, value in candidate_hashes.items() if name.endswith('.js')}
    baseline_js = {name: value for name, value in baseline_hashes.items() if name.endswith('.js')}
    if baseline_js.keys() != candidate_js.keys() or [name for name in baseline_js if baseline_js[name] != candidate_js[name]] != ['dist/render.js']:
        raise RuntimeError('candidate changed files other than render.js')
    bound = {**frozen, **{candidate / name: value for name, value in candidate_hashes.items()},
             **{p: sha(p) for p in (HERE / 'run.py', HERE / 'snapshot.json', NODE, FFMPEG, FFPROBE)}}
    metadata = {'createdUtc': stamp, 'decodeThreads': args.decode_threads, 'hostDecoderBudget': host, 'snapshot': snapshot,
                'candidateBuild': json.loads((HERE / 'build-result.json').read_text()),
                'sourceSha256': {str(p): value for p, value in bound.items()}, 'baselineSha256': baseline_hashes,
                'candidateSha256': candidate_hashes, 'exactDiff': 'candidate.diff', 'warmupsPerVariantPerProfile': args.warmups,
                'timedPairsPerProfile': args.pairs, 'maxRetainedOutputBytes': BUDGET,
                'fixture': {'frames': 300, 'labels': 3334, 'width': 1920, 'height': 1080, 'fps': 30}, 'records': []}
    manifest = destination / 'manifest.json'
    save(manifest, metadata)

    def export(preset, options, phase, index, variant):
        if retained() >= BUDGET or any(sha(p) != value for p, value in bound.items()):
            raise RuntimeError('output budget exhausted or bound source changed before export')
        run = destination / f'{preset}-{phase}-{index}-{variant}'
        run.mkdir()
        composition = run / 'composition.mjs'
        composition.write_text("import { readFile } from 'node:fs/promises';\n"
                               f"import {{ createTextGrid }} from {json.dumps((HERE / 'inputs/fframes-textgrid.mjs').as_uri())};\n"
                               f"export default createTextGrid(await readFile({json.dumps(str(HERE / 'inputs/DMSans-Regular.ttf'))}));\n")
        source = HERE / 'baseline' if variant == 'baseline' else candidate
        config = {'poolModule': str(source / 'dist/canvas-pool.js'), 'composition': str(composition),
                  'output': str(run / 'output.mp4'), 'stats': str(run / 'component-stats.json'), 'options': options}
        save(run / 'config.json', config)
        command = [str(NODE), str(HERE / 'worker.mjs'), str(run / 'config.json')]
        record = {'profile': preset, 'phase': phase, 'index': index, 'variant': variant, 'command': command,
                  'exitCode': None, 'directory': str(run), 'compositionSha256': sha(composition),
                  'sourceSha256': baseline_hashes if variant == 'baseline' else candidate_hashes}
        print(f'Launching {preset} {phase} {index} {variant}; results: {run}', flush=True)
        with (run / 'stdout.log').open('wb') as stdout, (run / 'stderr.log').open('wb') as stderr:
            started = time.perf_counter_ns()
            try:
                record['exitCode'] = subprocess.run(command, stdout=stdout, stderr=stderr, cwd=HERE).returncode
            except BaseException as error:
                record['launcherFailure'] = f'{type(error).__name__}: {error}'
                raise
            finally:
                record['externalProcessWallNs'] = time.perf_counter_ns() - started
                record['externalProcessWallMs'] = record['externalProcessWallNs'] / 1_000_000
                output = Path(config['output'])
                record.update(outputBytes=0, outputSha256=None, sourceUnchanged=False)
                try:
                    record['outputBytes'] = output.stat().st_size if output.is_file() else 0
                    record['outputSha256'] = sha(output) if output.is_file() else None
                    record['retainedOutputBytes'] = retained()
                    record['sourceUnchanged'] = all(p.is_file() and sha(p) == value for p, value in bound.items())
                except OSError as error:
                    record['artifactFailure'] = f'{type(error).__name__}: {error}'
                metadata['records'].append(record)
                save(run / 'process-result.json', record)
                save(manifest, metadata)
        return record

    for preset, (workers, threads, bframes, scene_cut) in PROFILES.items():
        options = {'ffmpeg': str(FFMPEG), 'ffprobe': str(FFPROBE), 'concurrency': workers,
                   'chunkFrames': math.ceil(300 / workers), 'encoder': {'preset': preset, 'crf': 11, 'threads': threads,
                   'gop': 24, 'bframes': bframes, 'sceneCut': scene_cut, 'qmin': 15, 'qmax': 60,
                   'qcompress': 0.6, 'maxQdiff': 4, 'colorConversion': 'rgb-bt601'}}
        ratios = []
        for phase, count in [('warmup', args.warmups), ('timed', args.pairs)]:
            for index in range(1, count + 1):
                order = ['baseline', 'candidate'] if index % 2 else ['candidate', 'baseline']
                pair = {'profile': preset, 'phase': phase, 'index': index, 'order': order, 'records': []}
                pair_path = destination / f'{preset}-{phase}-pair-{index}.json'
                save(pair_path, pair)
                for variant in order:
                    record = export(preset, options, phase, index, variant)
                    pair['records'].append(record)
                    save(pair_path, pair)
                    if record['exitCode'] != 0 or not record['outputBytes'] or not (Path(record['directory']) / 'component-stats.json').is_file() or not record['sourceUnchanged'] or record['retainedOutputBytes'] > BUDGET:
                        raise RuntimeError(f'export failed, source changed, or budget exceeded; preserved {record["directory"]}')
                if phase == 'timed':
                    values = {r['variant']: r['externalProcessWallNs'] for r in pair['records']}
                    pair['candidateOverBaselineWallRatio'] = values['candidate'] / values['baseline']
                    ratios.append(pair['candidateOverBaselineWallRatio'])
                    save(pair_path, pair)
                    metadata.setdefault('summary', {})[preset] = {'candidateOverBaselinePairedWallRatios': ratios,
                                                                'medianCandidateOverBaselineWallRatio': statistics.median(ratios)}
                    save(manifest, metadata)
    print(f'Complete; manifest: {manifest}', flush=True)


if __name__ == '__main__':
    main()
