#!/usr/bin/python3
"""Prepared strict CPU Remotion JPEG TextGrid study; launch only after lead preflight."""
import argparse
import datetime
from fractions import Fraction
import hashlib
import json
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
BASELINE = ROOT / 'three-engine-v1/results/full-v1'
BINARIES = BASELINE / 'binaries'
CONFIGS = {'A': {'name': 'jpeg80-c6', 'jpegQuality': 80, 'workers': 6},
           'B': {'name': 'jpeg100-c6', 'jpegQuality': 100, 'workers': 6},
           'C': {'name': 'jpeg100-c11', 'jpegQuality': 100, 'workers': 11}}
ORDERS = [('A', 'B', 'C'), ('B', 'C', 'A'), ('C', 'A', 'B')]
BUDGET = 3 * 1024 ** 3
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
    """One actual subprocess, without polling; metadata saved after delivery timing."""
    result = {'command': [str(a) for a in command], 'exitCode': None}
    with (directory / (label + '.stdout.log')).open('wb') as stdout, (directory / (label + '.stderr.log')).open('wb') as stderr:
        start = time.perf_counter_ns()
        try:
            result['exitCode'] = subprocess.run(result['command'], stdout=stdout, stderr=stderr,
                                                cwd=cwd).returncode
        except BaseException as error:
            result['failure'] = f'{type(error).__name__}: {error}'
        finally:
            result['wallNs'] = time.perf_counter_ns() - start
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


def encoder_info(path):
    # A bounded SEI header read after timing, without a second full decode.
    with path.open('rb') as stream:
        header = stream.read(2 * 1024 * 1024).decode('latin1')
    match = re.search(r'x264 - core[^\x00]+', header)
    if not match:
        raise RuntimeError('Missing x264 user SEI metadata')
    text = match.group(0)
    parameters = dict(re.findall(r'(?<![A-Za-z_])([A-Za-z_][A-Za-z_0-9]*)=([^\s\x00]+)', text))
    expected = {'threads': 8, 'bframes': 3, 'keyint': 24, 'crf': 11, 'qpmin': 15,
                'qpmax': 60, 'qcomp': .6, 'qpstep': 4, 'scenecut': 40, 'cabac': 1,
                'ref': 3, 'subme': 7, 'trellis': 1}
    for key, wanted in expected.items():
        if float(parameters.get(key, 'nan')) != wanted:
            raise RuntimeError(f'x264 {key} mismatch: expected {wanted}, got {parameters.get(key)}')
    if parameters.get('me') != 'hex':
        raise RuntimeError('x264 medium motion estimation mismatch')
    return {'rawUserSei': text, 'parameters': parameters, 'expected': expected, 'presetLiteralAvailable': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Launch only after existing studies finish and lead preflight')
    parser.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    if not args.run:
        parser.error('prepared only; --run is required after lead preflight')
    destination = args.results.resolve()
    if not destination.is_relative_to(HERE / 'results'):
        parser.error('results must stay inside remotion-cpu-jpeg-study-v1/results/')
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {'createdUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'status': 'preparing', 'records': [], 'upstreamPin': PIN, 'preamble': None,
                'configs': CONFIGS, 'preset': 'medium', 'encoderThreads': 8, 'decodeThreads': 8,
                'workload': {'labels': 3334, 'width': 1920, 'height': 1080, 'frames': 300,
                             'fps': 30, 'durationSeconds': 10},
                'warmupsPerConfig': 1, 'timedRunsPerConfig': 3, 'balancedOrders': ORDERS,
                'maxRetainedOutputBytes': BUDGET, 'reservationBytesPerExport': RESERVATION_FILE_BYTES,
                'qualityAndCompleteCadence': 'pending lossless strict CPU PNG reference and every-frame qualification'}
    try:
        ready_path = ROOT / 'remotion-setup/ready.json'
        ready = json.loads(ready_path.read_text())
        project = Path(ready['cwd'])
        bundle = Path(ready['bundle_path'])
        browser = Path(ready['browser_path'])
        wrapper = HERE / 'chrome-cpu.sh'
        renderer = project / 'node_modules/@remotion/renderer'
        compositor = project / 'node_modules/@remotion/compositor-darwin-arm64/remotion'
        source_manifest_path = ROOT / 'remotion-setup/source-manifest.json'
        source_manifest = json.loads(source_manifest_path.read_text())
        baseline_manifest_path = BASELINE / 'manifest.json'
        baseline = json.loads(baseline_manifest_path.read_text())
        if ready['versions']['@remotion/renderer'] != '4.0.529':
            raise RuntimeError('Remotion version mismatch')
        if str(browser) not in wrapper.read_text():
            raise RuntimeError('CPU wrapper does not point at pinned browser')
        libraries = list(compositor.parent.glob('*.dylib'))
        required_binaries = [('remotion', compositor), ('ffmpeg', FFMPEG), ('ffprobe', FFPROBE)] + [(p.name, p) for p in libraries]
        for name, target in required_binaries:
            link = BINARIES / name
            if not link.is_symlink() or not link.is_file() or link.resolve() != target.resolve():
                raise RuntimeError(f'Missing or mismatched existing binary link: {link}')
        files = {HERE / 'run.py', HERE / 'worker.mjs', HERE / 'README.md', wrapper, ready_path,
                 source_manifest_path, baseline_manifest_path, NODE, FFMPEG, FFPROBE, X264,
                 browser, compositor, project / 'package-lock.json', renderer / 'package.json',
                 project / 'public/DMSans-Regular.ttf'}
        files.update(libraries)
        for directory in [bundle, renderer / 'dist', project / 'src']:
            files.update(p for p in directory.rglob('*') if p.is_file())
        bound = {str(p): sha(p) for p in sorted(files)}
        for path, expected in baseline['sourceRuntimeSha256'].items():
            if path in bound and bound[path] != expected:
                raise RuntimeError(f'Existing study source/runtime binding changed: {path}')
        for relative, expected in source_manifest['bundle_hashes'].items():
            if bound[str(bundle / relative)] != expected:
                raise RuntimeError('Prepared Remotion bundle changed')
        for relative, expected in source_manifest['final_copied_hashes'].items():
            path = project / relative
            if sha(path) != expected:
                raise RuntimeError(f'Prepared Remotion project changed: {relative}')
            bound[str(path)] = expected
        if sha(bundle / 'public/DMSans-Regular.ttf') != FONT_SHA:
            raise RuntimeError('Pinned font mismatch')
        revision = subprocess.run(['/usr/bin/git', '-C', str(ROOT / 'source/fframes'), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        if revision != PIN:
            raise RuntimeError('Upstream revision mismatch')
        subprocess.run(['/usr/bin/git', '-C', str(ROOT / 'source/fframes'), 'diff', '--quiet', 'HEAD'], check=True)
        host = json.loads(subprocess.run([str(NODE), '--input-type=module', '-e',
            "import {availableParallelism,cpus,platform,arch} from 'node:os'; console.log(JSON.stringify({availableParallelism:availableParallelism(),logicalCpus:cpus().length,cpu:cpus()[0].model,platform:platform(),arch:arch(),node:process.version}));"], capture_output=True, text=True, check=True).stdout)
        if host['availableParallelism'] < 11:
            raise RuntimeError('This study requires 11 renderer workers and eight decode threads')
        versions = {name: subprocess.run([str(executable), '-version'], capture_output=True, text=True, check=True).stdout
                    for name, executable in [('ffmpeg', FFMPEG), ('ffprobe', FFPROBE)]}
        manifest.update(status='running', host=host, versions=versions, sourceRuntimeSha256=bound,
                        remotionReady={'project': str(project), 'bundle': str(bundle), 'browser': str(browser)},
                        binariesDirectory=str(BINARIES))
        save(destination / 'manifest.json', manifest)

        def unchanged():
            return all(Path(p).is_file() and sha(Path(p)) == value for p, value in bound.items())

        def export(phase, index, key):
            if retained() + RESERVATION_FILE_BYTES > BUDGET or not unchanged():
                raise RuntimeError('Budget reservation failed or source/runtime drifted')
            spec = CONFIGS[key]
            run = destination / f'{phase}-{index}-{spec["name"]}'
            run.mkdir()
            output = run / 'output.mp4'
            record = {'config': spec['name'], 'preset': 'medium', 'phase': phase, 'index': index,
                      'directory': str(run), **spec, 'encoderThreads': 8, 'preamble': None,
                      'status': 'running', 'components': {}}
            config = {**spec, 'engine': 'R', 'preset': 'medium', 'encoderThreads': 8,
                      'output': str(output), 'details': str(run / 'details.json'),
                      'project': str(project), 'bundle': str(bundle), 'browser': str(wrapper),
                      'binariesDirectory': str(BINARIES)}
            save(run / 'config.json', config)
            manifest['records'].append(record)
            save(destination / 'manifest.json', manifest)
            print(f'Running {phase} {index} {spec["name"]}: {run}', flush=True)
            start = time.perf_counter_ns()
            try:
                record['components']['engineProcess'] = process([NODE, HERE / 'worker.mjs', run / 'config.json'], run, 'engine', cwd=project)
                record['processNs'] = record['components']['engineProcess']['wallNs']
                if record['components']['engineProcess']['exitCode'] != 0:
                    raise RuntimeError('Engine process failed; retained attempt')
                record['components']['externalVerification'] = process([FFPROBE, '-v', 'error', '-threads', '8',
                    '-count_frames', '-show_streams', '-show_format', '-of', 'json', output], run, 'verify')
                record['decodeNs'] = record['components']['externalVerification']['wallNs']
                if record['components']['externalVerification']['exitCode'] != 0:
                    raise RuntimeError('Final full decode failed; retained attempt')
                probe = validate_probe(run / 'verify.stdout.log')
                record['deliveredWallNs'] = time.perf_counter_ns() - start
                save(run / 'ffprobe.json', probe)
                record['verificationPolicy'] = 'one external eight-thread full decode and format validation included in deliveredWallNs'
                record['encoding'] = encoder_info(output)
                record['sourceRuntimeUnchanged'] = unchanged()
                if not record['sourceRuntimeUnchanged']:
                    raise RuntimeError('Source/runtime changed during export')
                if retained() > BUDGET:
                    raise RuntimeError('Retained MP4 budget exceeded; preserved attempt')
                record['status'] = 'complete'
            except BaseException as error:
                if 'deliveredWallNs' not in record:
                    record['failedDeliveredAttemptWallNs'] = time.perf_counter_ns() - start
                record.update(status='failed', failure=f'{type(error).__name__}: {error}')
                raise
            finally:
                for label, component in [('engine', 'engineProcess'), ('verify', 'externalVerification')]:
                    if component in record['components']:
                        save(run / (label + '.process.json'), record['components'][component])
                details_path = run / 'details.json'
                if details_path.is_file():
                    record['details'] = json.loads(details_path.read_text())
                record['outputs'] = [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(run.glob('*.mp4'))]
                record['retainedOutputBytes'] = retained()
                save(run / 'result.json', record)
                save(destination / 'manifest.json', manifest)

        for key in ORDERS[0]:
            export('warmup', 1, key)
        for index, order in enumerate(ORDERS, 1):
            for key in order:
                export('timed', index, key)
        manifest['status'] = 'performance-complete; quality and cadence pending'
    except BaseException as error:
        manifest.update(status='failed', failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        save(destination / 'manifest.json', manifest)
    print(f'Performance complete; inspect {destination / "manifest.json"}', flush=True)


if __name__ == '__main__':
    main()
