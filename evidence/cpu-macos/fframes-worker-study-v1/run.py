#!/usr/bin/python3
"""Prepared FFRAMES medium worker-count study; exports require --run."""
import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import re
import statistics
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HELPERS = ROOT / 'three-engine-v1/run.py'
NODE = Path('/Users/gavinbintz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
FFPROBE = Path('/opt/homebrew/bin/ffprobe')
F = ROOT / 'fframes-setup/cargo-target/release/helios-fframes-cpu-comparison'
FONT = ROOT / 'source/fframes/render-bench/vs-remotion/fframes/media/DMSans-Regular.ttf'
FONT_SHA = '9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5'
PIN = 'bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b'
FROZEN = {'/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/three-engine-v1/run.py': 'ba2165a288a2048ecf1a1d97436fb7b0a1a8aad9369647f817cc497eb7e24892', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-setup/setup.json': '9ebb7cf02905b0b94149ec1e1c727f07375b44406d8a6aa3c2e56441afc2ee19', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-setup/fframes-cpu/src/main.rs': '384f27d220642436863f2969f6808209d6b1f64ef626245e0780f86f760590bf', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-setup/fframes-cpu/Cargo.toml': 'bd4be777cf30e70b912cd5c59b1cdb362e4cac06e19c60f18177b5aa741745a4', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-setup/fframes-cpu/Cargo.lock': '2aeb21d8416d0a6d0758d89453d253df8320355165429507ebc3d21afea67c01', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/fframes-setup/cargo-target/release/helios-fframes-cpu-comparison': '9ec1bd9b4b3f3594a929166e7fd5c849c828f10534cd3988ab918d6ce1978610', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/source/fframes/fframes/src/renderer/encoder.rs': '62ca6936c050f7b1a8e72e7d6bb909b1c2c20d2a16195ddeb696a197ff3bdb28', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/source/fframes/fframes/src/renderer/stream.rs': 'd705389d2eb81a9ac28dc9f1abc33551ac41ad606da140ac111f16d7d6b75fa4', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/source/fframes/fframes/src/renderer/cpu.rs': '67e5106a2779c7770ca29f3d99abc805623d844c6501c78d24b2ad82c0381038', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/source/fframes/fframes/src/renderer/segment_writer.rs': 'c5fd2c24479c271b9dca9a22898cf1f488dbe749b486d5906d1919a60f80f358', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/source/fframes/fframes/src/renderer/scheduler.rs': '27e0a604a653dbd2424d8c6b07dc5d495369724dce52468c471cfa01d2df67fb', '/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/source/fframes/render-bench/vs-remotion/fframes/media/DMSans-Regular.ttf': '9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5', '/Users/gavinbintz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node': '27db838bb204ef7c21df2931f5656e4c8fb32e6e947f363a402b49714d32b5b1', '/opt/homebrew/bin/ffprobe': '258fa480850eec6cf7b6831b2d3edd164cdd2f9ddb7a14965dc9fdaf9d175ff7', '/opt/homebrew/opt/x264/lib/libx264.165.dylib': 'dd765b37f50d44d3ce9593c2c1c2424b48bedac01c7999e93cef87e018bc65b4'}
BUDGET = 3 * 1024 ** 3
RESERVATION_FILE_BYTES = 256 * 1024 ** 2
WARMUP_ORDER = (4, 6, 11)
TIMED_ORDERS = ((4, 6, 11), (6, 11, 4), (11, 4, 6))


def retained():
    return sum(p.stat().st_size for p in HERE.rglob('*.mp4') if p.is_file())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Explicit launch gate')
    parser.add_argument('--results', required=True, type=Path)
    args = parser.parse_args()
    if not args.run:
        parser.error('prepared only; --run is required to launch')
    results_root = (HERE / 'results').resolve()
    destination = args.results.resolve()
    if not destination.is_relative_to(results_root) or destination == results_root:
        parser.error('results must be a new directory inside fframes-worker-study-v1/results/')
    # Reuse existing stdlib helpers. Loading this module does not call its main().
    spec = importlib.util.spec_from_file_location('fframes_study_helpers', HELPERS)
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    sha, save, process = helpers.sha, helpers.save, helpers.process
    if any(sha(Path(p)) != value for p, value in FROZEN.items()):
        raise RuntimeError('prepared source/binary/font/library bindings changed')
    setup = json.loads((ROOT / 'fframes-setup/setup.json').read_text())
    if setup['pinnedRevision'] != PIN or sha(FONT) != FONT_SHA:
        raise RuntimeError('pinned upstream metadata or font mismatch')
    if retained() + RESERVATION_FILE_BYTES > BUDGET:
        raise RuntimeError('retained-output budget reservation exhausted; outputs preserved')
    host = json.loads(subprocess.run([str(NODE), '--input-type=module', '-e',
        "import {availableParallelism,cpus,platform,arch} from 'node:os'; console.log(JSON.stringify({availableParallelism:availableParallelism(),logicalCpus:cpus().length,cpu:cpus()[0].model,platform:platform(),arch:arch(),node:process.version}));"], capture_output=True, text=True, check=True).stdout)
    decode_threads = min(8, host['availableParallelism'])
    if decode_threads != 8:
        raise RuntimeError('this protocol expects eight decoder threads')
    destination.mkdir(parents=True, exist_ok=False)
    bound = {**FROZEN, **{str(p): sha(p) for p in (HERE / 'run.py', HERE / 'README.md')}}
    manifest = {'createdUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'upstreamPin': PIN, 'setup': setup, 'host': host, 'decodeThreads': decode_threads,
                'sourceRuntimeSha256': bound,
                'workload': {'labels': 3334, 'frames': 300, 'width': 1920, 'height': 1080, 'fps': 30, 'durationSeconds': 10},
                'preset': 'medium', 'crf': 11, 'encoderThreadsPerSegment': 2,
                'inheritedEncoderDefaults': {'gop': 24, 'bframes': 3, 'scenecut': 40, 'qmin': 15, 'qmax': 60, 'qcomp': 0.6, 'qdiff': 4},
                'warmupOrder': WARMUP_ORDER, 'timedRoundOrders': TIMED_ORDERS,
                'warmupsPerWorkerCount': 1, 'timedRounds': 3, 'totalExports': 12,
                'maxRetainedOutputBytes': BUDGET, 'reservationBytesPerExport': RESERVATION_FILE_BYTES,
                'status': 'running', 'qualityAndCompleteCadence': 'pending; worker count changes segmentation and bitstreams',
                'records': []}
    manifest_path = destination / 'manifest.json'
    save(manifest_path, manifest)

    def unchanged():
        return all(Path(p).is_file() and sha(Path(p)) == value for p, value in bound.items())

    def export(phase, index, workers):
        if retained() + RESERVATION_FILE_BYTES > BUDGET or not unchanged():
            raise RuntimeError('budget reservation failed or source/runtime drifted')
        run = destination / f'medium-{phase}-{index}-workers-{workers}'
        run.mkdir()
        output = run / 'output.mp4'
        command = [str(F), str(output), 'medium', '11', str(workers), '2']
        record = {'engine': 'F', 'preset': 'medium', 'crf': 11, 'phase': phase, 'index': index,
                  'workers': workers, 'encoderThreadsPerSegment': 2,
                  'initialSegments': workers, 'initialAggregateEncoderThreads': workers * 2,
                  'directory': str(run), 'status': 'running', 'components': {}}
        save(run / 'config.json', {'output': str(output), 'command': command, 'workers': workers,
                                 'encoderThreadsPerSegment': 2, 'preset': 'medium', 'crf': 11})
        manifest['records'].append(record)
        save(manifest_path, manifest)
        print(f'Running F medium {phase} {index} workers={workers}: {run}', flush=True)
        start = time.perf_counter_ns()
        try:
            record['components']['engineProcess'] = process(command, run, 'engine', cwd=HERE)
            record['engineProcessWallNs'] = record['components']['engineProcess']['wallNs']
            record['components']['externalVerification'] = process([FFPROBE, '-v', 'error', '-threads', str(decode_threads),
                '-count_frames', '-show_streams', '-show_format', '-of', 'json', output], run, 'verify')
            record['decodeWallNs'] = record['components']['externalVerification']['wallNs']
            record['verifiedProbe'] = helpers.validate_probe(run / 'verify.stdout.log')
            record['deliveredWallNs'] = time.perf_counter_ns() - start
            record['deliveredWallMs'] = record['deliveredWallNs'] / 1_000_000
            record['verificationPolicy'] = 'external 8-thread full decode included in deliveredWallNs'
            # Existing header-only SEI extraction occurs after the delivered timer.
            record['encoding'] = helpers.encoder_info(output, 'medium', 2)
            match = re.search(r'renderSeconds=([0-9.]+)', (run / 'engine.stderr.log').read_text())
            record['upstreamRenderSeconds'] = float(match.group(1)) if match else None
            record['sourceRuntimeUnchanged'] = unchanged()
            if not record['sourceRuntimeUnchanged']:
                raise RuntimeError('source/runtime changed during export')
            record['status'] = 'complete'
        except BaseException as error:
            if 'deliveredWallNs' not in record:
                record['failedDeliveredAttemptWallNs'] = time.perf_counter_ns() - start
            record.update(status='failed', failure=f'{type(error).__name__}: {error}')
            raise
        finally:
            # Preserve original subprocess receipts, including failed components.
            for label, key in (('engine', 'engineProcessWallNs'), ('verify', 'decodeWallNs')):
                receipt = run / (label + '.process.json')
                if receipt.is_file() and key not in record:
                    record[key] = json.loads(receipt.read_text())['wallNs']
            record['outputs'] = [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(run.glob('*.mp4'))]
            record['retainedOutputBytes'] = retained()
            if record['retainedOutputBytes'] > BUDGET:
                record.update(status='failed', budgetExceeded=True)
            save(run / 'result.json', record)
            save(manifest_path, manifest)
        if record['retainedOutputBytes'] > BUDGET:
            raise RuntimeError('retained budget exceeded; preserved artifacts')
        return record

    ratios = {4: [], 6: []}
    wall_ms = {4: [], 6: [], 11: []}
    try:
        for phase, orders in (('warmup', (WARMUP_ORDER,)), ('timed', TIMED_ORDERS)):
            for index, order in enumerate(orders, 1):
                round_record = {'phase': phase, 'index': index, 'order': order, 'records': []}
                round_path = destination / f'medium-{phase}-round-{index}.json'
                save(round_path, round_record)
                for workers in order:
                    round_record['records'].append(export(phase, index, workers))
                    save(round_path, round_record)
                if phase == 'timed':
                    values = {r['workers']: r['deliveredWallNs'] for r in round_record['records']}
                    round_record['deliveredWallRatioTo11Workers'] = {str(w): values[w] / values[11] for w in ratios}
                    for workers in ratios:
                        ratios[workers].append(values[workers] / values[11])
                    for workers in wall_ms:
                        wall_ms[workers].append(values[workers] / 1_000_000)
                    save(round_path, round_record)
                    manifest['summary'] = {'timedDeliveredWallMsByWorkers': wall_ms,
                                           'medianTimedDeliveredWallMsByWorkers': {str(w): statistics.median(v) for w, v in wall_ms.items()},
                                           'roundDeliveredWallRatiosTo11Workers': ratios,
                                           'medianRoundDeliveredWallRatioTo11Workers': {str(w): statistics.median(v) for w, v in ratios.items()},
                                           'ratioInterpretation': 'below 1 favors tested worker count; all-frame quality remains pending'}
                    save(manifest_path, manifest)
        manifest['status'] = 'performance-complete; all-frame quality and cadence pending'
    except BaseException as error:
        manifest.update(status='failed', failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        save(manifest_path, manifest)
    print(f'Performance complete; inspect {manifest_path}', flush=True)


if __name__ == '__main__':
    main()
