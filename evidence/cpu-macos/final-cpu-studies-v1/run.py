#!/usr/bin/python3
"""Focused CPU resource screens and independently matched holdout. No exports without --run."""
import argparse
import ast
import datetime
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helpers = load_module('delivered_helpers', ROOT / 'three-engine-v1/run.py')
quality = load_module('quality_helpers', ROOT / 'quality-measurement-v1/run.py')
sha, save = helpers.sha, helpers.save
NODE, FFMPEG, FFPROBE, H, INPUT, F = helpers.NODE, helpers.FFMPEG, helpers.FFPROBE, helpers.H, helpers.INPUT, helpers.F
POLICY = Path('/Users/gavinbintz/Developer/helios/packages/portable/benchmarks/fframes-quality.ts')
QUALITY_MANIFEST = ROOT / 'quality-measurement-v1/results/full-v1/manifest.json'
BUDGETS = {'medium-screen': 3 * 1024 ** 3, 'ul-screen': 10 * 1024 ** 3, 'holdout': 6 * 1024 ** 3}
UL_PHYSICAL_BUDGET = 4 * 1024 ** 3
RESERVATION = 256 * 1024 ** 2
LIMITS = {'minSsimY': .995, 'minPsnrY': 40., 'minPsnrU': 35., 'minPsnrV': 35.}
FIELDS = {'minSsimY': ('ssim', 'Y'), 'minPsnrY': ('psnr', 'psnr_y'), 'minPsnrU': ('psnr', 'psnr_u'), 'minPsnrV': ('psnr', 'psnr_v')}


def profile(engine, workers, threads, preset):
    return {'id': f'{engine}-{preset}-w{workers}-t{threads}', 'engine': engine, 'workers': workers,
            'encoderThreads': threads, 'preset': preset, 'jpegQuality': 100 if engine == 'R' else None}


MEDIUM = [profile('H', w, t, 'medium') for w, t in [(4, 4), (6, 2), (8, 2), (11, 1)]]
UL = ([profile('H', w, t, 'ultrafast') for w, t in [(6, 4), (8, 2), (11, 1)]] +
      [profile('F', w, 2, 'ultrafast') for w in [6, 11]] +
      [profile('R', w, t, 'ultrafast') for w, t in [(6, 1), (11, 1), (6, 8), (11, 8)]])
MEDIUM_ORDERS = [[0, 1, 2, 3], [3, 2, 1, 0], [1, 3, 0, 2]]
UL_ORDERS = [list(range(9)), list(range(3, 9)) + list(range(3)), list(range(6, 9)) + list(range(6))]
HOLDOUT_ORDERS = [['H', 'F', 'R'], ['F', 'R', 'H'], ['R', 'H', 'F']]


def collect_inputs():
    ready = json.loads((ROOT / 'remotion-setup/ready.json').read_text())
    project, bundle, browser = (Path(ready[k]) for k in ['cwd', 'bundle_path', 'browser_path'])
    renderer = project / 'node_modules/@remotion/renderer'
    compositor = project / 'node_modules/@remotion/compositor-darwin-arm64'
    files = {ROOT / 'three-engine-v1/run.py', ROOT / 'three-engine-v1/worker.mjs',
             ROOT / 'encoder-thread-study-v1/worker.mjs', ROOT / 'remotion-cpu-jpeg-study-v1/worker.mjs',
             ROOT / 'remotion-cpu-jpeg-study-v1/chrome-cpu.sh', ROOT / 'quality-measurement-v1/run.py',
             ROOT / 'quality-clock-revision-v1.py', QUALITY_MANIFEST,
             ROOT / 'quality-clock-revision-v1/results/full-v1/manifest.json',
             ROOT / 'quality-policy-results-clock-v1.json', POLICY,
             ROOT / 'remotion-setup/ready.json', ROOT / 'remotion-setup/source-manifest.json',
             ROOT / 'fframes-setup/setup.json', ROOT / 'fframes-setup/fframes-cpu/src/main.rs',
             ROOT / 'fframes-setup/fframes-cpu/Cargo.toml', ROOT / 'fframes-setup/fframes-cpu/Cargo.lock',
             ROOT / 'paired-decode-export-v1/build-result.json', ROOT / 'paired-decode-export-v1/snapshot.json',
             ROOT / 'paired-decode-export-v1/candidate.diff', NODE, FFMPEG, FFPROBE, helpers.X264, F, browser,
             INPUT / 'fframes-textgrid.mjs', INPUT / 'DMSans-Regular.ttf', renderer / 'package.json',
             project / 'package-lock.json', project / 'public/DMSans-Regular.ttf',
             compositor / 'remotion', H / 'node_modules/@napi-rs/canvas-darwin-arm64/skia.darwin-arm64.node'}
    # Explicit rendering modules only: no authentication/config/state discovery.
    for name in ['canvas', 'canvas-pool', 'canvas-worker', 'render', 'process', 'skia-binding', 'text', 'plan', 'media']:
        files.add(H / 'dist' / (name + '.js'))
    for name in ['encoder', 'stream', 'cpu', 'segment_writer', 'scheduler']:
        files.add(ROOT / 'source/fframes/fframes/src/renderer' / (name + '.rs'))
    for directory in [bundle, renderer / 'dist', project / 'src']:
        files.update(p for p in directory.rglob('*') if p.is_file() and p.suffix in ['.js', '.map', '.tsx', '.ts', '.html', '.ttf'])
    files.update(compositor.glob('*.dylib'))
    refs = json.loads(QUALITY_MANIFEST.read_text())['references']
    files.update(Path(refs[key]['path']) for key in ['H', 'F', 'R-cpu'])
    return files, ready, refs


def preflight():
    binding = json.loads((HERE / 'bindings.json').read_text())
    files, ready, refs = collect_inputs()
    if set(map(str, files)) != set(binding['inputs']):
        raise RuntimeError('Bound input file set changed')
    for path, expected in {**binding['inputs'], **binding['runner']}.items():
        if not Path(path).is_file() or sha(Path(path)) != expected:
            raise RuntimeError(f'Frozen input/runner changed: {path}')
    if ready['versions']['@remotion/renderer'] != '4.0.529':
        raise RuntimeError('Remotion version mismatch')
    if (H / 'dist/render.js').read_text().count("'-threads', packets ? '1' : String(Math.min(8, availableParallelism()))") != 1:
        raise RuntimeError('Actual compiled candidate is not cap8')
    if sha(INPUT / 'DMSans-Regular.ttf') != helpers.FONT_SHA:
        raise RuntimeError('Pinned font mismatch')
    for key in ['H', 'F', 'R-cpu']:
        if sha(Path(refs[key]['path'])) != refs[key]['sha256'] or not refs[key]['cadence']['matchesExact30fps300Frames']:
            raise RuntimeError('Existing own-source reference binding/cadence changed')
    policy = POLICY.read_text()
    limits = {key: float(re.search(r'result\.' + key + r' >= ([0-9.]+)', policy).group(1)) for key in LIMITS}
    if limits != LIMITS:
        raise RuntimeError('Existing quality floor changed')
    revision = subprocess.run(['/usr/bin/git', '-C', str(ROOT / 'source/fframes'), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    if revision != helpers.PIN:
        raise RuntimeError('FFRAMES upstream pin changed')
    subprocess.run(['/usr/bin/git', '-C', str(ROOT / 'source/fframes'), 'diff', '--quiet', 'HEAD'], check=True)
    binaries = ROOT / 'three-engine-v1/results/full-v1/binaries'
    project = Path(ready['cwd'])
    compositor = project / 'node_modules/@remotion/compositor-darwin-arm64'
    for name, target in [('ffmpeg', FFMPEG), ('ffprobe', FFPROBE), ('remotion', compositor / 'remotion')] + [(p.name, p) for p in compositor.glob('*.dylib')]:
        link = binaries / name
        if not link.is_symlink() or not link.is_file() or link.resolve() != target.resolve():
            raise RuntimeError(f'Existing binary link changed: {name}')
    host = json.loads(subprocess.run([str(NODE), '--input-type=module', '-e',
        "import {availableParallelism,cpus} from 'node:os'; console.log(JSON.stringify({availableParallelism:availableParallelism(),cpu:cpus()[0].model,node:process.version}));"],
        capture_output=True, text=True, check=True).stdout)
    if host['availableParallelism'] < 11 or host['node'] != 'v24.19.0':
        raise RuntimeError('Pinned runtime/resources unavailable')
    versions = {name: subprocess.run([str(tool), '-version'], capture_output=True, text=True, check=True).stdout for name, tool in [('ffmpeg', FFMPEG), ('ffprobe', FFPROBE)]}
    if any('version 9.0' not in v for v in versions.values()):
        raise RuntimeError('Expected FFmpeg/probe 9.0')
    source = (ROOT / 'quality-measurement-v1/run.py').read_text()
    function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'metrics')
    corrected = ast.get_source_segment(source, function)
    if corrected.count('setpts=N/(30*TB)') != 2:
        raise RuntimeError('Frozen metric graph shape changed')
    corrected = corrected.replace('setpts=N/(30*TB)', 'settb=expr=1/30,setpts=N')
    exec(compile(corrected, str(ROOT / 'quality-clock-revision-v1.py'), 'exec'), quality.__dict__)
    return binding, ready, refs, host, versions, corrected


def retained(mode):
    return sum(p.stat().st_size for p in (HERE / 'results' / mode).rglob('*.mp4') if p.is_file())


def physical_bytes(mode):
    # Unique inode sizes conservatively bound our hardlinked MP4 byte storage.
    files = {(p.stat().st_dev, p.stat().st_ino): p.stat() for p in (HERE / 'results' / mode).rglob('*.mp4') if p.is_file()}
    return {'uniqueInodeBytes': sum(s.st_size for s in files.values()),
            'reportedAllocatedBytes': sum(s.st_blocks * 512 for s in files.values())}


def choose(path, engine, mode):
    if not path.is_relative_to((HERE / 'results' / mode).resolve()):
        raise RuntimeError('Selection manifest must belong to this new screen study')
    data = json.loads(path.read_text())
    if data['status'] != 'complete' or data['mode'] != mode:
        raise RuntimeError('Screen is not complete; holdout selection refused')
    eligible = [p for p in data['profileSummary'] if p['profile']['engine'] == engine and p['eligible']]
    if not eligible:
        raise RuntimeError(f'No fully eligible screened {engine} profile')
    eligible.sort(key=lambda p: (p['medianDeliveredWallNs'], p['profile']['workers'] * p['profile']['encoderThreads'],
                                 p['profile']['workers'], p['profile']['encoderThreads']))
    return eligible[0]['profile'], {'manifest': str(path), 'sha256': sha(path), 'engine': engine,
        'selected': eligible[0]['profile']['id'], 'eligibleMediansNs': {p['profile']['id']: p['medianDeliveredWallNs'] for p in eligible},
        'tieRule': 'exact equal median: fewest workers*encoderThreads, then workers, then threads',
        'claimScope': 'fastest fully eligible among these tested profiles; no broader optimum claim'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--mode', choices=list(BUDGETS))
    parser.add_argument('--results', type=Path)
    parser.add_argument('--medium-screen', type=Path)
    parser.add_argument('--ul-screen', type=Path)
    args = parser.parse_args()
    binding, ready, refs, host, versions, corrected = preflight()
    if args.preflight:
        if args.run:
            parser.error('--preflight and --run are exclusive')
        print(json.dumps({'status': 'preflight-passed', 'inputFiles': len(binding['inputs']), 'host': host,
                          'references': {k: refs[k]['sha256'] for k in ['H', 'F', 'R-cpu']}}))
        return
    if not args.run or not args.mode or not args.results:
        parser.error('exports require --run --mode --results')
    selections = []
    if args.mode == 'holdout':
        if not args.medium_screen or not args.ul_screen:
            parser.error('holdout requires both terminal screen manifest paths')
        medium_h, selected = choose(args.medium_screen.resolve(), 'H', 'medium-screen')
        selections.append(selected)
        profiles = [medium_h, profile('F', 11, 2, 'medium'), profile('R', 11, 8, 'medium')]
        for engine in ['H', 'F', 'R']:
            chosen, selected = choose(args.ul_screen.resolve(), engine, 'ul-screen')
            profiles.append(chosen)
            selections.append(selected)
        binding['inputs'].update({s['manifest']: s['sha256'] for s in selections})
        groups = []
        for preset in ['medium', 'ultrafast']:
            ids = {p['engine']: p['id'] for p in profiles if p['preset'] == preset}
            groups.append((list(ids.values()), [[ids[e] for e in order] for order in HOLDOUT_ORDERS]))
    else:
        profiles, indexes = (MEDIUM, MEDIUM_ORDERS) if args.mode == 'medium-screen' else (UL, UL_ORDERS)
        groups = [([p['id'] for p in profiles], [[profiles[i]['id'] for i in order] for order in indexes])]
    destination = args.results.resolve()
    allowed = (HERE / 'results' / args.mode).resolve()
    if not destination.is_relative_to(allowed) or destination == allowed:
        parser.error('results must be a fresh child of results/<mode>/')
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {'createdUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'mode': args.mode,
        'status': 'running', 'profiles': profiles, 'groups': groups, 'selection': selections,
        'sourceRuntimeSha256': binding['inputs'], 'runnerSha256': binding['runner'], 'host': host, 'versions': versions,
        'references': {k: refs[k] for k in ['H', 'F', 'R-cpu']}, 'workload': {'frames': 300, 'width': 1920, 'height': 1080, 'fps': 30, 'labels': 3334},
        'maxRetainedOutputBytes': BUDGETS[args.mode], 'timingPolicy': 'fresh-process external perf_counter_ns through successful final full-decode validation; H internal once, F/R external once; source/hash/SEI/cadence/quality excluded',
        'qualityPolicy': LIMITS, 'ulMaxPhysicalMp4Bytes': UL_PHYSICAL_BUDGET if args.mode == 'ul-screen' else None,
        'qualityOperatorSource': str(ROOT / 'quality-measurement-v1/run.py'),
        'comparisonClockRevisionSource': str(ROOT / 'quality-clock-revision-v1.py'), 'correctedMetricFunction': corrected,
        'records': [], 'qualityArtifacts': [], 'retryPolicy': 'none; execution errors stop, failed fidelity excludes profile'}
    manifest_path = destination / 'manifest.json'
    save(manifest_path, manifest)
    by_id = {p['id']: p for p in profiles}
    dedup = {}

    def unchanged():
        return all(Path(p).is_file() and sha(Path(p)) == digest for p, digest in {**binding['inputs'], **binding['runner']}.items())

    def execute(command, run, label, receipts, cwd=None):
        # Defer receipt serialization until after delivered timing.
        receipt = {'command': list(map(str, command)), 'exitCode': None}
        receipts[label] = receipt
        with (run / (label + '.stdout.log')).open('xb') as out, (run / (label + '.stderr.log')).open('xb') as err:
            start = time.perf_counter_ns()
            try:
                receipt['exitCode'] = subprocess.run(receipt['command'], stdout=out, stderr=err, cwd=cwd).returncode
            finally:
                receipt['wallNs'] = time.perf_counter_ns() - start
        if receipt['exitCode'] != 0:
            raise RuntimeError(f'{label} failed; original attempt preserved')

    def export(key, phase, index):
        p = by_id[key]
        reservation = RESERVATION * (2 if p['engine'] == 'F' and p['preset'] == 'ultrafast' else 1)
        if retained(args.mode) + reservation > BUDGETS[args.mode] or not unchanged():
            raise RuntimeError('Logical MP4 budget reservation exhausted or inputs drifted')
        run = destination / f'{phase}-{index}-{key}'
        run.mkdir()
        output = run / 'output.mp4'
        record = {**p, 'phase': phase, 'index': index, 'directory': str(run), 'status': 'running', 'components': {},
                  'encoderThreadScope': 'per segment/worker encoder' if p['engine'] in ['H', 'F'] else 'per active Remotion encoder; renderer concurrency is not encoder concurrency',
                  'initialAggregateEncoderThreads': p['workers'] * p['encoderThreads'] if p['engine'] in ['H', 'F'] else None}
        config = {**p, 'output': str(output), 'details': str(run / 'details.json')}
        if p['engine'] == 'H':
            composition = run / 'composition.mjs'
            composition.write_text("import {readFile} from 'node:fs/promises';\n" +
                f"import {{createTextGrid}} from {json.dumps((INPUT / 'fframes-textgrid.mjs').as_uri())};\n" +
                f"export default createTextGrid(await readFile({json.dumps(str(INPUT / 'DMSans-Regular.ttf'))}));\n")
            config.update(poolModule=str(H / 'dist/canvas-pool.js'), composition=str(composition),
                options={'ffmpeg': str(FFMPEG), 'ffprobe': str(FFPROBE), 'concurrency': p['workers'],
                    'chunkFrames': math.ceil(300 / p['workers']), 'encoder': {'preset': p['preset'], 'crf': 11,
                    'threads': p['encoderThreads'], 'gop': 24, 'bframes': 0 if p['preset'] == 'ultrafast' else 3,
                    'sceneCut': p['preset'] != 'ultrafast', 'qmin': 15, 'qmax': 60, 'qcompress': .6, 'maxQdiff': 4,
                    'colorConversion': 'rgb-bt601'}})
            record['compositionSha256'] = sha(composition)
        if p['engine'] == 'R':
            config.update(project=ready['cwd'], bundle=ready['bundle_path'],
                browser=str(ROOT / 'remotion-cpu-jpeg-study-v1/chrome-cpu.sh'),
                binariesDirectory=str(ROOT / 'three-engine-v1/results/full-v1/binaries'))
        save(run / 'config.json', config)
        command = ([F, output, p['preset'], '11', str(p['workers']), str(p['encoderThreads'])] if p['engine'] == 'F'
            else [NODE, ROOT / 'three-engine-v1/worker.mjs' if p['engine'] == 'H' else HERE / 'worker.mjs', run / 'config.json'])
        manifest['records'].append(record)
        save(manifest_path, manifest)
        print(f"Running {args.mode} {phase} {index} {key}: {run}", flush=True)
        start = time.perf_counter_ns()
        try:
            execute(command, run, 'engine', record['components'], cwd=ready['cwd'] if p['engine'] == 'R' else HERE)
            if p['engine'] == 'F' and p['preset'] == 'ultrafast':
                original = run / 'original.mp4'
                output.rename(original)
                execute([FFMPEG, '-v', 'error', '-y', '-ignore_editlist', '1', '-i', original,
                    '-map', '0:v:0', '-c:v', 'copy', '-an', '-use_editlist', '0', output], run, 'repair', record['components'])
            if p['engine'] in ['F', 'R']:
                execute([FFPROBE, '-v', 'error', '-threads', '8', '-count_frames', '-show_streams', '-show_format', '-of', 'json', output],
                    run, 'verify', record['components'])
                record['verifiedProbe'] = helpers.validate_probe(run / 'verify.stdout.log')
            if p['engine'] == 'H':
                record['details'] = json.loads((run / 'details.json').read_text())
                stats = record['details']['stats']
                if stats['frames'] != 300 or not math.isfinite(stats['finalVerifyMs']):
                    raise RuntimeError('Missing internal final full-decode proof')
            record['deliveredWallNs'] = time.perf_counter_ns() - start
            record['encoding'] = helpers.encoder_info(output, p['preset'], p['encoderThreads'])
            if p['engine'] == 'R':
                record['details'] = json.loads((run / 'details.json').read_text())
                if not record['details']['gpuEvidence']['admissionPassed']:
                    raise RuntimeError('Missing strict CPU DOM-stage evidence')
            record['status'] = 'export-complete'
        except BaseException as error:
            if 'deliveredWallNs' not in record:
                record['failedDeliveredAttemptWallNs'] = time.perf_counter_ns() - start
            record.update(status='failed', failure=f'{type(error).__name__}: {error}')
            raise
        finally:
            for label, receipt in record['components'].items():
                save(run / (label + '.process.json'), receipt)
            record['outputs'] = []
            for path in sorted(run.glob('*.mp4')):
                digest = sha(path)
                record['outputs'].append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest})
                # Only fresh files from this invocation; preserve names/bytes/hash atomically.
                if digest in dedup:
                    first = dedup[digest]
                    if path.stat().st_size == first.stat().st_size:
                        temporary = path.with_name(path.name + '.dedup')
                        os.link(first, temporary)
                        os.replace(temporary, path)
                        if sha(path) != digest:
                            raise RuntimeError('Owned dedup hash verification failed')
                else:
                    dedup[digest] = path
            record['retainedLogicalMp4Bytes'] = retained(args.mode)
            save(run / 'result.json', record)
            save(manifest_path, manifest)
        if record['retainedLogicalMp4Bytes'] > BUDGETS[args.mode]:
            raise RuntimeError('Logical MP4 storage budget exceeded; preserved files')
        record['physicalMp4Storage'] = physical_bytes(args.mode)
        if args.mode == 'ul-screen' and record['physicalMp4Storage']['uniqueInodeBytes'] > UL_PHYSICAL_BUDGET:
            raise RuntimeError('UL unique-inode MP4 storage exceeded 4 GiB; preserved files')
        if not unchanged():
            raise RuntimeError('Inputs drifted during export')

    try:
        # No metric work between timed exports; screens and holdout are distinct fresh processes/files.
        for warmup, orders in groups:
            for key in warmup:
                export(key, 'warmup', 1)
            for index, order in enumerate(orders, 1):
                for key in order:
                    export(key, 'timed', index)
        cache = {}
        for record_index, record in enumerate(manifest['records']):
            output = Path(record['directory']) / 'output.mp4'
            digest = next(p['sha256'] for p in record['outputs'] if p['path'] == str(output))
            reference_key = 'R-cpu' if record['engine'] == 'R' else record['engine']
            cache_key = (digest, reference_key)
            if cache_key not in cache:
                directory = destination / 'quality' / (reference_key + '-' + digest)
                directory.mkdir(parents=True)
                artifact = {'outputSha256': digest, 'referenceKey': reference_key, 'referenceSha256': refs[reference_key]['sha256'],
                            'directory': str(directory), 'savedCopies': [], 'status': 'running'}
                cache[cache_key] = artifact
                manifest['qualityArtifacts'].append(artifact)
                data = quality.probe(output, directory, 'actual-cadence')
                artifact['cadence'] = quality.cadence(data)
                stream = data['streams'][0]
                if (not artifact['cadence']['matchesExact30fps300Frames'] or stream.get('codec_name') != 'h264' or
                    stream.get('pix_fmt') != 'yuv420p' or stream.get('color_space') != 'smpte170m' or
                    stream.get('color_range') != 'tv' or stream.get('width') != 1920 or stream.get('height') != 1080):
                    raise RuntimeError('Actual output cadence/format failed before metric normalization')
                artifact['quality'] = quality.metrics(directory, output, Path(refs[reference_key]['path']))
                frames = artifact['quality']['frames']
                violations, minima = [], {k: math.inf for k in FIELDS}
                for frame in frames:
                    for key, (kind, plane) in FIELDS.items():
                        value = float(frame[kind][plane])
                        minima[key] = min(minima[key], value)
                        if math.isnan(value) or value < LIMITS[key] or (kind == 'ssim' and (not math.isfinite(value) or not 0 <= value <= 1)):
                            violations.append({'frameIndex': frame['index'], 'criterion': key, 'actual': str(value), 'required': LIMITS[key]})
                complete = [frame['index'] for frame in frames] == list(range(300))
                artifact.update(status='complete', minima={k: str(v) for k, v in minima.items()}, violations=violations,
                                passedExistingFidelityAndCadencePolicy=complete and not violations)
                if sha(output) != digest or sha(Path(refs[reference_key]['path'])) != refs[reference_key]['sha256']:
                    raise RuntimeError('Output/reference drifted during quality measurement')
            artifact = cache[cache_key]
            artifact['savedCopies'].append({'recordIndex': record_index, 'path': str(output), 'profile': record['id'], 'phase': record['phase']})
            record['qualityArtifact'] = str(Path(artifact['directory']) / 'measurement.json')
            record['eligible'] = artifact['passedExistingFidelityAndCadencePolicy']
            record['status'] = 'complete' if record['eligible'] else 'quality-excluded'
            save(Path(artifact['directory']) / 'measurement.json', artifact)
            save(Path(record['directory']) / 'result.json', record)
            save(manifest_path, manifest)
        manifest['profileSummary'] = []
        for p in profiles:
            rows = [r for r in manifest['records'] if r['id'] == p['id']]
            timed = [r['deliveredWallNs'] for r in rows if r['phase'] == 'timed']
            manifest['profileSummary'].append({'profile': p, 'eligible': len(rows) == 4 and len(timed) == 3 and all(r['eligible'] for r in rows),
                                              'timedDeliveredWallNs': timed, 'medianDeliveredWallNs': statistics.median(timed)})
        if not unchanged():
            raise RuntimeError('Bound inputs changed during study')
        manifest['retainedLogicalMp4Bytes'] = retained(args.mode)
        owned = list(destination.rglob('*.mp4'))
        physical = {(p.stat().st_dev, p.stat().st_ino): p.stat().st_size for p in owned}
        manifest['newPhysicalMp4Bytes'] = sum(physical.values())
        manifest['status'] = 'complete'
    except BaseException as error:
        manifest.update(status='failed', failure=f'{type(error).__name__}: {error}')
        for artifact in manifest['qualityArtifacts']:
            if artifact['status'] == 'running':
                artifact.update(status='failed', failure=manifest['failure'])
                save(Path(artifact['directory']) / 'measurement.json', artifact)
        raise
    finally:
        save(manifest_path, manifest)
    print(f"Complete: {manifest_path}", flush=True)


if __name__ == '__main__':
    main()
