#!/usr/bin/python3
"""Small frozen encoder-thread study; preparation alone does not launch exports."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time

HERE = Path(__file__).resolve().parent
SOURCE = Path('/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/paired-decode-export-v1')
NODE = Path('/Users/gavinbintz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
FFMPEG = Path('/opt/homebrew/bin/ffmpeg')
FFPROBE = Path('/opt/homebrew/bin/ffprobe')
FROZEN = {'build-result.json': '5cb58075bd01afd85de2096a67d41016c9798bd92925cb9f6bdc86b2cfe06605', 'candidate/dist/auth.d.ts': '5985778505b3c8f3fa4e638206d40889f31091dbdd5ba216853d683b482b5780', 'candidate/dist/auth.js': '5036664a0b4c6336c36e7a3b73afbee353e6394b95f4a806b737c0b76a46b6d3', 'candidate/dist/backend.d.ts': '99eed3d7054382affaaa1bdd0cb37cec2ee66480972657b77188f4d28147f9c8', 'candidate/dist/backend.js': '43a4dec50101eb767dbd1ec2e4324a668deea3f7b8b65e6c34fe384d202aad76', 'candidate/dist/canvas-pool.d.ts': '50810c6c2ce0ca4d6bdfe74179a9d18245c1e740a4c3a9f5192dff606e5fa6d1', 'candidate/dist/canvas-pool.js': '76faca79a66fdae5832337c317af6798e3c4d62d9f25ad2533d88d833a1837d0', 'candidate/dist/canvas-worker.d.ts': '8e609bb71c20b858c77f0e9f90bb1319db8477b13f9f965f1a1e18524bf50881', 'candidate/dist/canvas-worker.js': 'b1b9c3ae4359a41c5194b45e5cbb49591babaf4e3e9ff08d03929c0304fa8001', 'candidate/dist/canvas.d.ts': '6d0b484db26258c23dee7a4a0b3fe90e1764c890d3d90b59c69578fc0b993df4', 'candidate/dist/canvas.js': '4e7a3e38b67bf6761ab6b42de95a90e17b87f8c26346221b47a5fc2ea96e83fb', 'candidate/dist/cli.d.ts': '281a92618edf17eb794382ab570d7dcf63d83646b9f58922d644e185c11a63c9', 'candidate/dist/cli.js': 'd9edb48715e9146f221b6b903482346f68420f688a8ebebbeebeea438866be8b', 'candidate/dist/client.d.ts': 'e09b0b7ccebcfd20c99b8d45ec1ca8d9c85379c4ee1c50782f07f9a29eddcb7e', 'candidate/dist/client.js': 'c32458c091ff63874a58e38d2991044179485d89c856db0de17e2cc617200e90', 'candidate/dist/index.d.ts': 'f3304576674fdaf812afda0a84f024c74d0fab2260e904a5d41ccd157ab7d4dd', 'candidate/dist/index.js': '491b0a63973fd11a2502e8b3748b6d3c14690088d7f47b74dccb24ef4c253520', 'candidate/dist/jobs.d.ts': '067cf06688242a09b13f31f8fb6d914feeb1c5b7f48c52f1a8dd22b1de2951aa', 'candidate/dist/jobs.js': 'c90739169e9150adda16f45b10d7f4e77711843f3cd6661749e33e3664abd2d7', 'candidate/dist/media.d.ts': 'e960b3082d7dee24f2cf1772d042533e9a14a8e22911233b746644f7441b84f1', 'candidate/dist/media.js': '67993f258fef048892a954ab2282a31a9e1ac2637ebe7b7bbd6c14e413ffdba7', 'candidate/dist/plan.d.ts': '3bd7c83fab404aafbffb4a4f0c91cff0f6404bced79824607f296949f71fe975', 'candidate/dist/plan.js': '9552b7c36b54c3272d75e243d8ab4b53ebce7b860b88e5103af95e280cf471c6', 'candidate/dist/process.d.ts': '0b80096eac9d8dd3caf0e1f69181130643d92c06037f985792919e47d71751fa', 'candidate/dist/process.js': '9d448754cb40062e372746283e13ae245924a800e9938473b769e55b66761d7e', 'candidate/dist/render.d.ts': 'daf4c8a47fe4f288db5447ecd573b957e1bef1d17a398718564fc1452ef5c76f', 'candidate/dist/render.js': '00f4f847c4e02e9dd28a6189504b28b695393e37a00c651f1b88000146392ed2', 'candidate/dist/s3-storage.d.ts': '447a6c7f2fcd72cde7de1ae48389e1d04880c26abdf5ffc8b6868a41943cbd4a', 'candidate/dist/s3-storage.js': '0a62ef2fb0111ae5e9ad163c0d55400de9e71fecf8df5387bade65d85e9adbeb', 'candidate/dist/server.d.ts': '9ff38d9e6a2d7bdec5d09290b9cd5fbddb81853d5e323c0b9a63ecbab25a3de0', 'candidate/dist/server.js': 'ebc970e016af47dc501114c9e1d3202655613327b9d033c5cea2b69bbadeda03', 'candidate/dist/skia-binding.d.ts': '3722f966afb6604fca8ad06eb67ce887063f66afbebb4b99829171589db53309', 'candidate/dist/skia-binding.js': '8eeb285f6ce96c36dc32e854e1cd55731eb25bdcc287a99784c30569ce2d7262', 'candidate/dist/skia.d.ts': 'b4c8a328e9cf05aa1b4c7d5e30c7da039de9dbff5dca95c60e01170ab0cecb55', 'candidate/dist/skia.js': 'a5cd349fe76a9cbaca782d75d79b0382be46764a21f32673e73cfaa50c8149b6', 'candidate/dist/storage.d.ts': 'f2bb53360d43061991649507a3892415ec9420721ca94075417faec130b3490e', 'candidate/dist/storage.js': 'e3112525447391b24bd58e7241339e70bdb48d9cfcc971eda6e2c5ce40970fcf', 'candidate/dist/text.d.ts': '0a502e8b8cc49a75d5d7320a4b8e4a606895712fac3dff829b8f3891de8ee6ea', 'candidate/dist/text.js': 'dbfd047b6d8d6b2f9d1f7faa154947c8fa15ba11be2e08da20a6675bca4263d5', 'candidate/package.json': '1239d4d885dcad42201a27ed9324f8f0f760b78700d8db9ced39a511cffe7eae', 'candidate.diff': 'e3fb91187cf98e8a15e8d5ca110d3361f59d41fe423961faf17be2e3ff808011', 'inputs/DMSans-Regular.ttf': '9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5', 'inputs/fframes-textgrid.mjs': 'e3bc82a2cd5461136a1ee388e2a2e27eaf03937b5f65169c18630bbf9fe8df67', 'snapshot.json': 'a16e402f16ca78a86f7a54822c6a3762bc41eb15df151388ea72101c2c10db52', 'run.py': '089f962446f7a4df94dd7cf72d47687ec7dc3c02819c43da5779264230892d7b', 'worker.mjs': '9f539f1f67503b8c9f83c215d90b0564a29dcb96f22717fbff70dcdeb71ca272', 'README.md': '18f094a8f91677263f60359fc35bf28cb8a4a7e1634aa921ff59c233dbcbb785'}
BUDGET = 3 * 1024 ** 3
WARMUP_ORDER = (2, 4, 8)
TIMED_ORDERS = ((2, 4, 8), (4, 8, 2), (8, 2, 4))
PATTERN = "['-v', 'error', '-threads', packets ? '1' : String(Math.min(8, availableParallelism())), packets ? '-count_packets' : '-count_frames', '-show_streams', '-show_format', '-of', 'json', path]"


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def retained():
    return sum(p.stat().st_size for p in HERE.rglob('*.mp4') if p.is_file())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path)
    args = parser.parse_args()
    frozen = {SOURCE / name: value for name, value in FROZEN.items()}
    if any(sha(path) != value for path, value in frozen.items()):
        raise RuntimeError('frozen candidate or inputs changed; prepare a new study')
    candidate = SOURCE / 'candidate'
    expected_files = {name for name in FROZEN if name.startswith('candidate/')}
    actual_files = {str(p.relative_to(SOURCE)) for p in candidate.rglob('*') if p.is_file()}
    if actual_files != expected_files:
        raise RuntimeError('frozen candidate file set changed; prepare a new study')
    compiled = (candidate / 'dist/render.js').read_text()
    if compiled.count(PATTERN) != 1:
        raise RuntimeError('compiled candidate does not match cap-8 decoder policy')
    host = json.loads(subprocess.run([str(NODE), '--input-type=module', '-e', "import { availableParallelism } from 'node:os'; console.log(JSON.stringify({availableParallelism:availableParallelism(),decoderThreads:Math.min(8,availableParallelism())}));"], capture_output=True, text=True, check=True).stdout)
    if host['decoderThreads'] != 8:
        raise RuntimeError('host does not produce the required decoder budget of 8')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    results_root = (HERE / 'results').resolve()
    destination = args.results.resolve() if args.results else results_root / stamp
    if not destination.is_relative_to(results_root) or destination == results_root:
        parser.error('results must be a new directory inside encoder-thread-study-v1/results/')
    if retained() >= BUDGET:
        raise RuntimeError('retained-output budget exhausted; outputs preserved')
    destination.mkdir(parents=True, exist_ok=False)
    bound = {**frozen, **{p: sha(p) for p in (HERE / 'run.py', HERE / 'worker.mjs', HERE / 'README.md', NODE, FFMPEG, FFPROBE)}}
    options = {'ffmpeg': str(FFMPEG), 'ffprobe': str(FFPROBE), 'concurrency': 4,
               'chunkFrames': 75, 'encoder': {'preset': 'medium', 'crf': 11,
               'threads': 8, 'gop': 24, 'bframes': 3, 'sceneCut': True,
               'qmin': 15, 'qmax': 60, 'qcompress': 0.6, 'maxQdiff': 4,
               'colorConversion': 'rgb-bt601'}}
    metadata = {'createdUtc': stamp, 'hostDecoderBudget': host,
                'sourceStudy': str(SOURCE), 'candidateBuild': json.loads((SOURCE / 'build-result.json').read_text()),
                'sourceSha256': {str(p): value for p, value in bound.items()},
                'candidateSha256': {name.removeprefix('candidate/'): value for name, value in FROZEN.items() if name.startswith('candidate/')},
                'warmupOrder': WARMUP_ORDER, 'timedRoundOrders': TIMED_ORDERS,
                'warmupsPerThreadCount': 1, 'timedRounds': 3, 'totalExports': 12,
                'maxRetainedOutputBytes': BUDGET, 'optionsWith8Threads': options,
                'fixture': {'frames': 300, 'labels': 3334, 'width': 1920, 'height': 1080, 'fps': 30},
                'qualityStatus': 'pending; encoder threads may change bitstreams', 'records': []}
    manifest = destination / 'manifest.json'
    save(manifest, metadata)

    def export(phase, index, threads):
        if retained() >= BUDGET or any(sha(p) != value for p, value in bound.items()):
            raise RuntimeError('output budget exhausted or bound source changed before export')
        run = destination / f'medium-{phase}-{index}-threads-{threads}'
        run.mkdir()
        composition = run / 'composition.mjs'
        composition.write_text("import { readFile } from 'node:fs/promises';\n"
                               f"import {{ createTextGrid }} from {json.dumps((SOURCE / 'inputs/fframes-textgrid.mjs').as_uri())};\n"
                               f"export default createTextGrid(await readFile({json.dumps(str(SOURCE / 'inputs/DMSans-Regular.ttf'))}));\n")
        export_options = {**options, 'encoder': {**options['encoder'], 'threads': threads}}
        config = {'poolModule': str(candidate / 'dist/canvas-pool.js'), 'composition': str(composition),
                  'output': str(run / 'output.mp4'), 'stats': str(run / 'component-stats.json'), 'options': export_options}
        save(run / 'config.json', config)
        command = [str(NODE), str(HERE / 'worker.mjs'), str(run / 'config.json')]
        record = {'profile': 'medium', 'phase': phase, 'index': index, 'encoderThreadsPerWorker': threads,
                  'aggregateEncoderThreads': 4 * threads, 'command': command,
                  'exitCode': None, 'directory': str(run), 'compositionSha256': sha(composition)}
        print(f'Launching medium {phase} {index} threads={threads}; results: {run}', flush=True)
        with (run / 'stdout.log').open('xb') as stdout, (run / 'stderr.log').open('xb') as stderr:
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
        if record['exitCode'] != 0 or not record['outputBytes'] or not Path(config['stats']).is_file() or not record['sourceUnchanged'] or record.get('retainedOutputBytes', BUDGET + 1) > BUDGET:
            raise RuntimeError(f'export failed, source changed, or budget exceeded; preserved {run}')
        return record

    ratios = {2: [], 4: []}
    wall_ms = {2: [], 4: [], 8: []}
    for phase, orders in (('warmup', (WARMUP_ORDER,)), ('timed', TIMED_ORDERS)):
        for index, order in enumerate(orders, 1):
            round_record = {'profile': 'medium', 'phase': phase, 'index': index, 'order': order, 'records': []}
            round_path = destination / f'medium-{phase}-round-{index}.json'
            save(round_path, round_record)
            for threads in order:
                round_record['records'].append(export(phase, index, threads))
                save(round_path, round_record)
            if phase == 'timed':
                values = {r['encoderThreadsPerWorker']: r['externalProcessWallNs'] for r in round_record['records']}
                round_record['wallRatioTo8Threads'] = {str(threads): values[threads] / values[8] for threads in ratios}
                for threads in ratios:
                    ratios[threads].append(values[threads] / values[8])
                for threads in wall_ms:
                    wall_ms[threads].append(values[threads] / 1_000_000)
                save(round_path, round_record)
                metadata['summary'] = {'timedWallMsByThreads': wall_ms,
                                       'medianTimedWallMsByThreads': {str(t): statistics.median(v) for t, v in wall_ms.items()},
                                       'roundWallRatiosTo8Threads': ratios,
                                       'medianRoundWallRatioTo8Threads': {str(t): statistics.median(v) for t, v in ratios.items()},
                                       'ratioInterpretation': 'below 1 favors the tested thread count; quality remains pending'}
                save(manifest, metadata)
    print(f'Complete; manifest: {manifest}', flush=True)


if __name__ == '__main__':
    main()
