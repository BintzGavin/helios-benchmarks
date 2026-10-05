#!/usr/bin/python3
"""Reproduce the qualified CPU TextGrid holdout with explicit local inputs."""
import argparse
import datetime
import json
import math
import os
from pathlib import Path
import platform
import shlex
import statistics
import subprocess
import time
import helpers
import quality

HERE = Path(__file__).resolve().parent
sha, save = helpers.sha, helpers.save
PIN = 'bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b'
FONT_SHA = '9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5'
LIMITS = {'minSsimY': .995, 'minPsnrY': 40., 'minPsnrU': 35., 'minPsnrV': 35.}
FIELDS = {'minSsimY': ('ssim', 'Y'), 'minPsnrY': ('psnr', 'psnr_y'), 'minPsnrU': ('psnr', 'psnr_u'), 'minPsnrV': ('psnr', 'psnr_v')}
BUDGETS = {'qualification': 6 * 1024 ** 3, 'holdout': 6 * 1024 ** 3}
UL_PHYSICAL_BUDGET = 4 * 1024 ** 3
RESERVATION = 256 * 1024 ** 2
HOLDOUT_ORDERS = [['H', 'F', 'R'], ['F', 'R', 'H'], ['R', 'H', 'F']]
STUDY = None


def profile(engine, workers, threads, preset):
    return {'id': f'{engine}-{preset}-w{workers}-t{threads}', 'engine': engine, 'workers': workers,
            'encoderThreads': threads, 'preset': preset, 'jpegQuality': 100 if engine == 'R' else None}


def retained(mode):
    return sum(p.stat().st_size for p in STUDY.rglob('*.mp4') if p.is_file())


def physical_bytes(mode):
    files = {(p.stat().st_dev, p.stat().st_ino): p.stat() for p in STUDY.rglob('*.mp4') if p.is_file()}
    return {'uniqueInodeBytes': sum(s.st_size for s in files.values()),
            'reportedAllocatedBytes': sum(s.st_blocks * 512 for s in files.values())}


def preflight(args):
    global NODE, FFMPEG, FFPROBE, H, INPUT, F, MEDIA
    NODE, FFMPEG, FFPROBE = args.node.resolve(), args.ffmpeg.resolve(), args.ffprobe.resolve()
    H = args.helios_package.resolve() if args.helios_package else args.helios_repo.resolve() / 'packages/portable'
    INPUT = HERE
    ff_repo, crate, project = args.fframes_repo.resolve(), args.fframes_crate.resolve(), args.remotion_project.resolve()
    F = args.fframes_binary.resolve() if args.fframes_binary else crate / 'target/release/helios-fframes-cpu-comparison'
    MEDIA = ff_repo / 'render-bench/vs-remotion/fframes/media'
    font = MEDIA / 'DMSans-Regular.ttf'
    bundle, browser = args.remotion_bundle.resolve(), args.browser.resolve()
    renderer = project / 'node_modules/@remotion/renderer'
    compositor = project / 'node_modules/@remotion/compositor-linux-x64-gnu'
    if not bundle.is_dir() or not crate.is_dir() or not project.is_dir():
        raise RuntimeError('Explicit crate/project/bundle prerequisites missing')
    if args.run and sha(crate / 'src/main.rs') != sha(HERE / 'fframes-cpu/src/main.rs'):
        raise RuntimeError('Export launch requires the bundled Rust source with explicit media CLI; legacy crate is allowed only for read-only preflight')
    if sha(font) != FONT_SHA or sha(project / 'public/DMSans-Regular.ttf') != FONT_SHA or sha(bundle / 'public/DMSans-Regular.ttf') != FONT_SHA:
        raise RuntimeError('Pinned DM Sans missing or mismatched in upstream/project/bundle')
    if json.loads((renderer / 'package.json').read_text())['version'] != '4.0.529':
        raise RuntimeError('Requires Remotion renderer4.0.529')
    for expected in (HERE / 'remotion-project/src').iterdir():
        if expected.is_file() and sha(project / 'src' / expected.name) != sha(expected):
            raise RuntimeError('Remotion TextGrid project source differs from bundled pinned source')
    revision = subprocess.run(['/usr/bin/git', '-C', str(ff_repo), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    if revision != PIN:
        raise RuntimeError('FFRAMES revision mismatch')
    subprocess.run(['/usr/bin/git', '-C', str(ff_repo), 'diff', '--quiet', 'HEAD'], check=True)
    # Importing this helper is unnecessary for preflight: bind the actual compiled files.
    if (H / 'dist/render.js').read_text().count("'-threads', packets ? '1' : String(Math.min(8, availableParallelism()))") != 1:
        raise RuntimeError('Requires Helios compiled cap8 decoder candidate')
    host = json.loads(subprocess.run([str(NODE), '--input-type=module', '-e',
        "import {availableParallelism,cpus,platform,arch} from 'node:os'; console.log(JSON.stringify({availableParallelism:availableParallelism(),cpu:cpus()[0].model,node:process.version,platform:platform(),arch:arch()}));"],
        capture_output=True, text=True, check=True).stdout)
    if host['node'] != 'v24.19.0' or host['availableParallelism'] != 2:
        raise RuntimeError('This Linux study requires Node24.19.0 and the measured two-CPU cpuset')
    if host['platform'] != 'linux' or host['arch'] != 'x64':
        raise RuntimeError('This adapted study binds the Linux x64 compositor')
    versions = {name: subprocess.run([str(tool), '-version'], capture_output=True, text=True, check=True).stdout
                for name, tool in [('ffmpeg', FFMPEG), ('ffprobe', FFPROBE)]}
    versions['browser'] = subprocess.run([str(browser), '--version'], capture_output=True, text=True, check=True).stdout.strip()
    if any('version 5.1.9' not in versions[k] for k in ['ffmpeg', 'ffprobe']) or '149.0.7790.0' not in versions['browser']:
        raise RuntimeError('Requires the recorded Debian FFmpeg/probe5.1.9 and Chrome149.0.7790.0')
    if '164' not in args.x264_library.name or not args.x264_library.is_file():
        raise RuntimeError('Explicit shared x264164 library is required')
    files = {NODE, FFMPEG, FFPROBE, browser, F, font, args.x264_library.resolve(),
             H / 'node_modules/@napi-rs/canvas/node_modules/@napi-rs/canvas-linux-x64-gnu/skia.linux-x64-gnu.node',
             project / 'package.json', project / 'package-lock.json', renderer / 'package.json',
             project / 'public/DMSans-Regular.ttf', compositor / 'remotion',
             crate / 'Cargo.toml', crate / 'Cargo.lock', crate / 'src/main.rs'}
    receipt = json.loads((HERE / 'holdout-receipts.json').read_text())
    for name in ['canvas', 'canvas-pool', 'canvas-worker', 'render', 'process', 'skia-binding', 'text', 'plan', 'media']:
        files.add(H / 'dist' / (name + '.js'))
        expected = receipt['originalSourceRuntimeSha256']['study/paired-decode-export-v1/candidate/dist/' + name + '.js']
        if sha(H / 'dist' / (name + '.js')) != expected:
            raise RuntimeError('Helios compiled rendering module differs from original candidate: ' + name)
    for name in ['encoder', 'stream', 'cpu', 'segment_writer', 'scheduler']:
        files.add(ff_repo / 'fframes/src/renderer' / (name + '.rs'))
    for directory in [bundle, renderer / 'dist', project / 'src']:
        files.update(p for p in directory.rglob('*') if p.is_file() and p.suffix in ['.js', '.map', '.tsx', '.ts', '.html', '.ttf'])
    files.update(compositor.glob('*.so'))
    binding = {'inputs': {str(p): sha(p) for p in sorted(files)},
               'runner': {str(p): sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in ['.py', '.mjs', '.sh']}}
    ready = {'cwd': str(project), 'bundle_path': str(bundle), 'browser_path': str(browser),
             'compositor': str(compositor)}
    for name, value in [('NODE', NODE), ('FFMPEG', FFMPEG), ('FFPROBE', FFPROBE), ('H', H), ('F', F), ('MEDIA', MEDIA)]:
        setattr(quality, name, value)
    corrected = 'quality.py metrics(): shared settb=expr=1/30,setpts=N; actual cadence first'
    return binding, ready, {}, host, versions, corrected


def prepare_local_runtime(destination, ready):
    binaries = destination / 'binaries'
    binaries.mkdir()
    compositor = Path(ready['compositor'])
    for name, target in [('ffmpeg', FFMPEG), ('ffprobe', FFPROBE), ('remotion', compositor / 'remotion')] + [(p.name, p) for p in compositor.glob('*.so')]:
        (binaries / name).symlink_to(target.resolve())
    wrapper = destination / 'chrome-cpu.sh'
    template = (HERE / 'chrome-cpu.sh').read_text()
    if template.count('@CHROME_BINARY@') != 1:
        raise RuntimeError('CPU browser wrapper template changed')
    wrapper.write_text(template.replace('@CHROME_BINARY@', shlex.quote(ready['browser_path'])))
    wrapper.chmod(0o755)
    ready.update(browser_path=str(wrapper), binariesDirectory=str(binaries))
    return ready


def generate_references(destination, ready, binding):
    reference_root = destination / 'quality-reference'
    reference_root.mkdir()
    composition = reference_root / 'composition.mjs'
    font = MEDIA / 'DMSans-Regular.ttf'
    composition.write_text("import {readFile} from 'node:fs/promises';\n" +
        f"import {{createTextGrid}} from {json.dumps((HERE / 'fframes-textgrid.mjs').as_uri())};\n" +
        f"export default createTextGrid(await readFile({json.dumps(str(font))}));\n")
    references = {}
    for key in ['H', 'F', 'R-cpu']:
        print(f'Untimed fresh own-source reference {key}', flush=True)
        references[key] = quality.make_reference(key, reference_root, HERE / 'reference-source.mjs', ready,
                                                {**binding['inputs'], **binding['runner']}, composition)
        save(reference_root / 'references.json', references)
    return references


def main():
    global STUDY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--mode', choices=['qualification', 'holdout'], default='holdout')
    parser.add_argument('--qualification-manifest', type=Path)
    parser.add_argument('--results', type=Path)
    for name in ['node', 'ffmpeg', 'ffprobe', 'browser', 'x264-library', 'fframes-repo', 'fframes-crate', 'remotion-project', 'remotion-bundle']:
        parser.add_argument('--' + name, required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--helios-repo', type=Path)
    group.add_argument('--helios-package', type=Path)
    parser.add_argument('--fframes-binary', type=Path)
    args = parser.parse_args()
    if args.preflight and args.run:
        parser.error('--preflight and --run are exclusive')
    binding, ready, refs, host, versions, corrected = preflight(args)
    if args.preflight:
        print(json.dumps({'status': 'preflight-passed', 'inputFiles': len(binding['inputs']), 'host': host,
                          'fontSha256': FONT_SHA, 'referenceGeneration': 'not run'}))
        return
    if not args.run or not args.results:
        parser.error('exports require --run --results; prerequisites must already be built')
    if args.mode == 'holdout' and not args.qualification_manifest:
        parser.error('holdout requires --qualification-manifest')
    selections = [{'settings': 'resource-derived two-CPU budget: two workers, one encoder thread per worker/active encoder; no timing-based tuning screen'}]
    if args.qualification_manifest:
        selections[0]['qualificationManifest'] = str(args.qualification_manifest.resolve())
        selections[0]['qualificationManifestSha256'] = sha(args.qualification_manifest.resolve())
    profiles = [profile('H', 2, 1, 'medium'), profile('F', 2, 1, 'medium'), profile('R', 2, 1, 'medium')]
    if args.mode == 'holdout':
        profiles += [profile('H', 2, 1, 'ultrafast'), profile('F', 2, 1, 'ultrafast'), profile('R', 2, 1, 'ultrafast')]
    groups = []
    if args.mode == 'holdout':
        for preset in ['medium', 'ultrafast']:
            ids = {p['engine']: p['id'] for p in profiles if p['preset'] == preset}
            groups.append((list(ids.values()), [[ids[e] for e in order] for order in HOLDOUT_ORDERS]))
    destination = args.results.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    STUDY = destination
    ready = prepare_local_runtime(destination, ready)
    manifest = {'createdUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'mode': args.mode,
        'status': 'running', 'profiles': profiles, 'groups': groups, 'selection': selections,
        'sourceRuntimeSha256': binding['inputs'], 'runnerSha256': binding['runner'], 'host': host, 'versions': versions,
        'references': refs, 'workload': {'frames': 300, 'width': 1920, 'height': 1080, 'fps': 30, 'labels': 3334},
        'maxRetainedOutputBytes': BUDGETS[args.mode], 'timingPolicy': 'fresh-process external perf_counter_ns through successful final full-decode validation; H internal once, F/R external once; source/hash/SEI/cadence/quality excluded',
        'qualityPolicy': LIMITS, 'ulMaxPhysicalMp4Bytes': UL_PHYSICAL_BUDGET if args.mode == 'ul-screen' else None,
        'qualityOperatorSource': 'quality.py (functions copied from original own-source measurement)',
        'comparisonClockRevisionSource': 'quality.py (exact common comparison clock)', 'correctedMetricFunction': corrected,
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
                f"export default createTextGrid(await readFile({json.dumps(str(MEDIA / 'DMSans-Regular.ttf'))}));\n")
            config.update(poolModule=str(H / 'dist/canvas-pool.js'), composition=str(composition),
                options={'ffmpeg': str(FFMPEG), 'ffprobe': str(FFPROBE), 'concurrency': p['workers'],
                    'chunkFrames': math.ceil(300 / p['workers']), 'encoder': {'preset': p['preset'], 'crf': 11,
                    'threads': p['encoderThreads'], 'gop': 24, 'bframes': 0 if p['preset'] == 'ultrafast' else 3,
                    'sceneCut': p['preset'] != 'ultrafast', 'qmin': 15, 'qmax': 60, 'qcompress': .6, 'maxQdiff': 4,
                    'colorConversion': 'rgb-bt601'}})
            record['compositionSha256'] = sha(composition)
        if p['engine'] == 'R':
            config.update(project=ready['cwd'], bundle=ready['bundle_path'],
                browser=ready['browser_path'],
                binariesDirectory=ready['binariesDirectory'])
        save(run / 'config.json', config)
        command = ([F, output, p['preset'], '11', str(p['workers']), str(p['encoderThreads']), MEDIA] if p['engine'] == 'F'
            else [NODE, HERE / 'helios-worker.mjs' if p['engine'] == 'H' else HERE / 'worker.mjs', run / 'config.json'])
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
                execute([FFPROBE, '-v', 'error', '-threads', '2', '-count_frames', '-show_streams', '-show_format', '-of', 'json', output],
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
        # No metric work between timed exports; qualification and holdout are distinct fresh processes/files.
        if args.mode == 'qualification':
            for p in profiles:
                export(p['id'], 'qualification', 1)
        else:
            for warmup, orders in groups:
                for key in warmup:
                    export(key, 'warmup', 1)
                for index, order in enumerate(orders, 1):
                    for key in order:
                        export(key, 'timed', index)
        refs = generate_references(destination, ready, binding)
        manifest['references'] = refs
        save(manifest_path, manifest)
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
            expected_rows = 1 if args.mode == 'qualification' else 4
            manifest['profileSummary'].append({'profile': p, 'eligible': len(rows) == expected_rows and
                                              (args.mode == 'qualification' or len(timed) == 3) and all(r['eligible'] for r in rows),
                                              'timedDeliveredWallNs': timed,
                                              'medianDeliveredWallNs': statistics.median(timed) if timed else None})
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
