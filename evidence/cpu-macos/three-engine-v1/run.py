#!/usr/bin/python3
"""Prepared three-engine CPU TextGrid timer. Run only after lead approval."""
import argparse
import datetime
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NODE = Path('/Users/gavinbintz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
FFMPEG = Path('/opt/homebrew/bin/ffmpeg')
FFPROBE = Path('/opt/homebrew/bin/ffprobe')
X264 = Path('/opt/homebrew/opt/x264/lib/libx264.165.dylib')
PIN = 'bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b'
FONT_SHA = '9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5'
H = ROOT / 'paired-decode-export-v1/candidate'
INPUT = ROOT / 'paired-decode-export-v1/inputs'
F = ROOT / 'fframes-setup/cargo-target/release/helios-fframes-cpu-comparison'
PROFILES = {'medium': {'H': (4, 8), 'F': (11, 2), 'R': (4, 8)},
            'ultrafast': {'H': (6, 4), 'F': (6, 2), 'R': (4, 1)}}
ORDERS = [('H', 'F', 'R'), ('F', 'R', 'H'), ('R', 'H', 'F')]
BUDGET = 6 * 1024 ** 3
RESERVATION_FILE_BYTES = 256 * 1024 ** 2


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


def process(command, directory, label, cwd=None):
    """Measure one actual subprocess; no polling or memory sampling."""
    result = {'command': [str(a) for a in command], 'exitCode': None}
    with (directory / (label + '.stdout.log')).open('wb') as stdout, (directory / (label + '.stderr.log')).open('wb') as stderr:
        start = time.perf_counter_ns()
        try:
            result['exitCode'] = subprocess.run(result['command'], stdout=stdout, stderr=stderr,
                                                cwd=cwd).returncode
        except BaseException as error:
            result['failure'] = f'{type(error).__name__}: {error}'
            raise
        finally:
            result['wallNs'] = time.perf_counter_ns() - start
            save(directory / (label + '.process.json'), result)
    if result['exitCode'] != 0:
        raise RuntimeError(f'{label} exited {result["exitCode"]}; preserved {directory}')
    return result


def validate_probe(path):
    probe = json.loads(path.read_text())
    video = [s for s in probe['streams'] if s.get('codec_type') == 'video']
    if len(video) != 1 or any(s.get('codec_type') == 'audio' for s in probe['streams']):
        raise RuntimeError('Expected exactly one silent video stream')
    s = video[0]
    if (s.get('codec_name') != 'h264' or s.get('pix_fmt') != 'yuv420p' or
        int(s.get('nb_read_frames', -1)) != 300 or s.get('width') != 1920 or s.get('height') != 1080 or
        Fraction(s.get('avg_frame_rate', '0')) != 30 or Fraction(s.get('r_frame_rate', '0')) != 30 or
        abs(float(s.get('duration', probe['format']['duration'])) - 10) > 1 / 30 or
        s.get('color_range') != 'tv' or s.get('color_space') != 'smpte170m'):
        raise RuntimeError('Failed delivered completeness/format check')
    return probe


def encoder_info(path, preset, threads):
    # Tiny header read after the delivered timer; never perform another full decode.
    with path.open('rb') as stream:
        header = stream.read(2 * 1024 * 1024).decode('latin1')
    match = re.search(r'x264 - core[^\x00]+', header)
    if not match:
        raise RuntimeError('Missing x264 user SEI metadata')
    text = match.group(0)
    parameters = dict(re.findall(r'(?<![A-Za-z_])([A-Za-z_][A-Za-z_0-9]*)=([^\s\x00]+)', text))
    expected = {'threads': threads, 'bframes': 0 if preset == 'ultrafast' else 3, 'keyint': 24,
                'crf': 11, 'qpmin': 15, 'qpmax': 60, 'qcomp': .6, 'qpstep': 4,
                'scenecut': 0 if preset == 'ultrafast' else 40,
                'cabac': 0 if preset == 'ultrafast' else 1, 'ref': 1 if preset == 'ultrafast' else 3,
                'subme': 0 if preset == 'ultrafast' else 7, 'trellis': 0 if preset == 'ultrafast' else 1}
    for key, wanted in expected.items():
        if float(parameters.get(key, 'nan')) != wanted:
            raise RuntimeError(f'x264 {key} mismatch: expected {wanted}, got {parameters.get(key)}')
    if parameters.get('me') != ('dia' if preset == 'ultrafast' else 'hex'):
        raise RuntimeError('x264 preset motion estimation mismatch')
    return {'rawUserSei': text, 'parameters': parameters, 'expected': expected, 'presetLiteralAvailable': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Explicit launch gate; without this no work runs')
    parser.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    if not args.run:
        parser.error('prepared only; --run is required after lead approval')
    destination = args.results.resolve()
    if not destination.is_relative_to(HERE / 'results'):
        parser.error('results must stay inside three-engine-v1/results/')
    destination.mkdir(parents=True, exist_ok=False)
    ready_path = ROOT / 'remotion-setup/ready.json'
    ready = json.loads(ready_path.read_text())
    project = Path(ready['cwd'])
    bundle = Path(ready['bundle_path'])
    browser = Path(ready['browser_path'])
    renderer = project / 'node_modules/@remotion/renderer'
    compositor = project / 'node_modules/@remotion/compositor-darwin-arm64/remotion'
    binaries = destination / 'binaries'
    binaries.mkdir()
    compositor_libraries = list(compositor.parent.glob('*.dylib'))
    for name, target in [('remotion', compositor), ('ffmpeg', FFMPEG), ('ffprobe', FFPROBE)] + [(p.name, p) for p in compositor_libraries]:
        (binaries / name).symlink_to(target.resolve())
    # All assembly, source reads, binding, and runtime version queries precede all timers.
    files = {HERE / 'run.py', HERE / 'worker.mjs', HERE / 'README.md', ready_path, NODE, FFMPEG, FFPROBE, X264,
             F, browser, compositor, INPUT / 'fframes-textgrid.mjs', INPUT / 'DMSans-Regular.ttf',
             ROOT / 'paired-decode-export-v1/snapshot.json', ROOT / 'paired-decode-export-v1/build-result.json',
             ROOT / 'paired-decode-export-v1/candidate.diff',
             ROOT / 'fframes-setup/fframes-cpu/src/main.rs', ROOT / 'fframes-setup/setup.json',
             ROOT / 'source/fframes/fframes/src/renderer/encoder.rs', ROOT / 'source/fframes/fframes/src/renderer/stream.rs',
             ROOT / 'remotion-setup/source-manifest.json', project / 'package-lock.json', renderer / 'package.json',
             project / 'public/DMSans-Regular.ttf', ROOT / 'source/fframes/render-bench/vs-remotion/fframes/media/DMSans-Regular.ttf'}
    files.update(compositor_libraries)
    for directory in [H / 'dist', H / 'src', bundle, renderer / 'dist', project / 'src']:
        files.update(p for p in directory.rglob('*') if p.is_file())
    canvas_native = H / 'node_modules/@napi-rs/canvas-darwin-arm64/skia.darwin-arm64.node'
    files.add(canvas_native)
    bound = {str(p): sha(p) for p in sorted(files)}
    if bound[str(INPUT / 'DMSans-Regular.ttf')] != FONT_SHA or sha(bundle / 'public/DMSans-Regular.ttf') != FONT_SHA:
        raise RuntimeError('Pinned font mismatch')
    revision = subprocess.run(['/usr/bin/git', '-C', str(ROOT / 'source/fframes'), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    if revision != PIN:
        raise RuntimeError('Upstream revision mismatch')
    subprocess.run(['/usr/bin/git', '-C', str(ROOT / 'source/fframes'), 'diff', '--quiet', 'HEAD'], check=True)
    expected_decoder = "'-threads', packets ? '1' : String(Math.min(8, availableParallelism()))"
    if (H / 'dist/render.js').read_text().count(expected_decoder) != 1:
        raise RuntimeError('Compiled Helios candidate decoder policy mismatch')
    r_manifest = json.loads((ROOT / 'remotion-setup/source-manifest.json').read_text())
    if ready['versions']['@remotion/renderer'] != '4.0.529':
        raise RuntimeError('Remotion version mismatch')
    for relative, expected in r_manifest['bundle_hashes'].items():
        if sha(bundle / relative) != expected:
            raise RuntimeError('Prepared Remotion bundle changed')
    host = json.loads(subprocess.run([str(NODE), '--input-type=module', '-e',
        "import {availableParallelism,cpus,platform,arch} from 'node:os'; console.log(JSON.stringify({availableParallelism:availableParallelism(),logicalCpus:cpus().length,cpu:cpus()[0].model,platform:platform(),arch:arch(),node:process.version}));"], capture_output=True, text=True, check=True).stdout)
    decode_threads = min(8, host['availableParallelism'])
    if decode_threads != 8:
        raise RuntimeError('This prepared protocol expects eight decoder threads')
    versions = {}
    for name, executable in [('ffmpeg', FFMPEG), ('ffprobe', FFPROBE)]:
        versions[name] = subprocess.run([str(executable), '-version'], capture_output=True, text=True, check=True).stdout
    manifest = {'createdUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'upstreamPin': PIN,
                'workload': {'labels': 3334, 'width': 1920, 'height': 1080, 'frames': 300, 'fps': 30, 'durationSeconds': 10},
                'profiles': PROFILES, 'profileStatus': 'provisional tuned configurations; historical selection evidence is not established',
                'host': host, 'versions': versions, 'remotionReady': ready, 'decodeThreads': decode_threads,
                'sourceRuntimeSha256': bound, 'warmupsPerEnginePreset': 1, 'timedRunsPerEnginePreset': 3,
                'balancedOrders': ORDERS, 'maxRetainedOutputBytes': BUDGET, 'reservationBytesPerExport': 2 * RESERVATION_FILE_BYTES,
                'records': [], 'status': 'running', 'qualityAndCompleteCadence': 'deferred until performance ends'}
    save(destination / 'manifest.json', manifest)

    def unchanged():
        return all(Path(p).is_file() and sha(Path(p)) == value for p, value in bound.items())

    def export(preset, phase, index, engine):
        # Reserve final + original conservatively; this is not a per-file write limit.
        if retained() + 2 * RESERVATION_FILE_BYTES > BUDGET or not unchanged():
            raise RuntimeError('Budget reservation failed or source/runtime drifted')
        run = destination / f'{preset}-{phase}-{index}-{engine}'
        run.mkdir()
        output = run / 'output.mp4'
        workers, threads = PROFILES[preset][engine]
        record = {'engine': engine, 'preset': preset, 'phase': phase, 'index': index, 'directory': str(run),
                  'workers': workers, 'encoderThreads': threads, 'status': 'running', 'components': {}}
        config = {'engine': engine, 'preset': preset, 'workers': workers, 'encoderThreads': threads,
                  'output': str(output), 'details': str(run / 'details.json')}
        if engine == 'H':
            composition = run / 'composition.mjs'
            composition.write_text("import {readFile} from 'node:fs/promises';\n"
                f"import {{createTextGrid}} from {json.dumps((INPUT / 'fframes-textgrid.mjs').as_uri())};\n"
                f"export default createTextGrid(await readFile({json.dumps(str(INPUT / 'DMSans-Regular.ttf'))}));\n")
            config.update(poolModule=str(H / 'dist/canvas-pool.js'), composition=str(composition),
                          options={'ffmpeg': str(FFMPEG), 'ffprobe': str(FFPROBE), 'concurrency': workers,
                            'chunkFrames': math.ceil(300 / workers), 'encoder': {'preset': preset, 'crf': 11,
                            'threads': threads, 'gop': 24, 'bframes': 0 if preset == 'ultrafast' else 3,
                            'sceneCut': preset != 'ultrafast', 'qmin': 15, 'qmax': 60, 'qcompress': .6,
                            'maxQdiff': 4, 'colorConversion': 'rgb-bt601'}})
            record['compositionSha256'] = sha(composition)
        elif engine == 'R':
            config.update(project=str(project), bundle=str(bundle), browser=str(browser), binariesDirectory=str(binaries))
        save(run / 'config.json', config)
        command = [str(F), str(output), preset, '11', str(workers), str(threads)] if engine == 'F' else [str(NODE), str(HERE / 'worker.mjs'), str(run / 'config.json')]
        manifest['records'].append(record)
        save(destination / 'manifest.json', manifest)
        print(f'Running {preset} {phase} {index} {engine}: {run}', flush=True)
        start = time.perf_counter_ns()
        try:
            record['components']['engineProcess'] = process(command, run, 'engine', cwd=project if engine == 'R' else HERE)
            if engine == 'F' and preset == 'ultrafast':
                original = run / 'original.mp4'
                output.rename(original)
                record['components']['editListRepair'] = process([FFMPEG, '-v', 'error', '-y', '-ignore_editlist', '1', '-i', original,
                    '-map', '0:v:0', '-c:v', 'copy', '-an', '-use_editlist', '0', output], run, 'repair')
            if engine in ('F', 'R'):
                record['components']['externalVerification'] = process([FFPROBE, '-v', 'error', '-threads', str(decode_threads),
                    '-count_frames', '-show_streams', '-show_format', '-of', 'json', output], run, 'verify')
                record['verifiedProbe'] = validate_probe(run / 'verify.stdout.log')
            record['deliveredWallNs'] = time.perf_counter_ns() - start
            # Completeness is already inside H's compiled API. Do not decode it twice.
            if engine in ('H', 'R'):
                record['details'] = json.loads((run / 'details.json').read_text())
            if engine == 'H':
                record['verificationPolicy'] = 'compiled H finalVerifyMs (8-thread full decode); internal checks retained'
            else:
                record['verificationPolicy'] = 'external 8-thread full decode included in deliveredWallNs'
            if engine == 'F':
                match = re.search(r'renderSeconds=([0-9.]+)', (run / 'engine.stderr.log').read_text())
                record['upstreamRenderSeconds'] = float(match.group(1)) if match else None
            record['encoding'] = encoder_info(output, preset, threads)
            record['sourceRuntimeUnchanged'] = unchanged()
            if not record['sourceRuntimeUnchanged']:
                raise RuntimeError('Source/runtime changed during export')
            record['status'] = 'complete'
        except BaseException as error:
            if 'deliveredWallNs' not in record:
                record['failedDeliveredAttemptWallNs'] = time.perf_counter_ns() - start
            record.update(status='failed', failure=f'{type(error).__name__}: {error}')
            raise
        finally:
            record['outputs'] = [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(run.glob('*.mp4'))]
            record['retainedOutputBytes'] = retained()
            save(run / 'result.json', record)
            save(destination / 'manifest.json', manifest)
        if record['retainedOutputBytes'] > BUDGET:
            raise RuntimeError('Retained budget exceeded; preserved artifacts')

    try:
        for preset in PROFILES:
            for engine in ORDERS[0]:
                export(preset, 'warmup', 1, engine)
            for index, order in enumerate(ORDERS, 1):
                for engine in order:
                    export(preset, 'timed', index, engine)
        manifest['status'] = 'performance-complete; quality and cadence pending'
    except BaseException as error:
        manifest.update(status='failed', failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        save(destination / 'manifest.json', manifest)
    print(f'Performance complete; inspect {destination / "manifest.json"}', flush=True)


if __name__ == '__main__':
    main()
