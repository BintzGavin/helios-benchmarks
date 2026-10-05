#!/usr/bin/python3
"""Untimed own-source quality and complete PTS measurement of saved TextGrid exports."""
import argparse
import datetime
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NODE = Path('/Users/gavinbintz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
FFMPEG = Path('/opt/homebrew/bin/ffmpeg')
FFPROBE = Path('/opt/homebrew/bin/ffprobe')
H = ROOT / 'paired-decode-export-v1/candidate'
INPUT = ROOT / 'paired-decode-export-v1/inputs'
F = ROOT / 'fframes-setup/cargo-target/release/helios-fframes-cpu-comparison'
RGB_FILTER = 'scale=out_color_matrix=bt601:out_range=tv,format=yuv420p'
STUDIES = ['three-engine-v1', 'encoder-thread-study-v1', 'fframes-worker-study-v1',
           'paired-decode-export-v1', 'remotion-cpu-jpeg-study-v1']
FRAMES, FPS, WIDTH, HEIGHT = 300, 30, 1920, 1080
BUDGET = 6 * 1024 ** 3
REF_FILE_LIMIT = 1100 * 1024 ** 2
PNG_LIMIT = 1250 * 1024 ** 2
FONT_SHA = '9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5'

# Emitted only inside a new owned result directory at launch. No separate build,
# source rewrite, benchmark exporter, environment access, or dependency install.
REFERENCE_JS = r'''import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {once} from 'node:events';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const c = JSON.parse(await readFile(process.argv[2], 'utf8'));
const details = {reference: c.reference, node: process.version, frames: [], imageFormat: 'png'};
let browser, renderer;
const flags = ['--disable-gpu', '--disable-gpu-compositing', '--disable-gpu-rasterization'];
const featureKeys = ['gpu_compositing', 'rasterization', '2d_canvas', 'canvas_oop_rasterization',
  'webgl', 'webgl2', 'webgpu', 'video_decode', 'video_encode', 'vulkan', 'skia_graphite'];
async function gpuReceipt() {
  const receipt = {expectedGpuFlags: [], featureStatus: {}, glRenderer: null, glVendor: null};
  const [system, command] = await Promise.allSettled([
    browser.connection.send('SystemInfo.getInfo'), browser.connection.send('Browser.getBrowserCommandLine')]);
  if (system.status === 'fulfilled') {
    const gpu = system.value.value.gpu ?? {};
    for (const key of featureKeys) {
      if (Object.hasOwn(gpu.featureStatus ?? {}, key)) receipt.featureStatus[key] = gpu.featureStatus[key];
    }
    receipt.glRenderer = gpu.auxAttributes?.glRenderer ?? null;
    receipt.glVendor = gpu.auxAttributes?.glVendor ?? null;
  } else receipt.systemInfoFailure = String(system.reason);
  if (command.status === 'fulfilled') {
    receipt.expectedGpuFlags = (command.value.value.arguments ?? []).filter(arg => flags.includes(arg));
  } else receipt.commandLineFailure = String(command.reason);
  // Raw browser argv and GPU device/auxiliary lists are deliberately never retained.
  receipt.missingFlags = flags.filter(flag => !receipt.expectedGpuFlags.includes(flag));
  receipt.invalidRequiredStages = ['gpu_compositing', 'rasterization'].filter(key => {
    const value = receipt.featureStatus[key];
    return typeof value !== 'string' || !value.trim() || !/software|disabled|unavailable/i.test(value);
  });
  receipt.admissionPassed = system.status === 'fulfilled' && command.status === 'fulfilled' &&
    !receipt.missingFlags.length && !receipt.invalidRequiredStages.length;
  return receipt;
}
try {
  if (c.reference === 'H') {
    const {CanvasFrameRenderer} = await import(pathToFileURL(c.canvasModule).href);
    const {default: composition} = await import(pathToFileURL(c.compositionModule).href);
    renderer = new CanvasFrameRenderer(composition);
    details.imageFormat = 'raw-rgba';
    for (let index = 0; index < 300; index++) {
      const pixels = await renderer.render(index);
      if (pixels.length !== 1920 * 1080 * 4) throw new Error('Unexpected RGBA size');
      details.frames.push({index, bytes: pixels.length, sha256: createHash('sha256').update(pixels).digest('hex')});
      if (!process.stdout.write(pixels)) await once(process.stdout, 'drain');
    }
  } else {
    const strictCpu = c.reference === 'R-cpu';
    details.cpuLabel = strictCpu ? 'strict-CPU-PNG-reference' : 'GPU-stages-unattested-legacy-PNG-reference';
    const require = createRequire(c.project + '/package.json');
    const {openBrowser, selectComposition, renderFrames} = require('@remotion/renderer');
    browser = await openBrowser('chrome', {browserExecutable: c.browser, chromeMode: 'headless-shell',
      chromiumOptions: {gl: 'swangle', headless: true}, logLevel: 'warn'});
    details.gpuBefore = await gpuReceipt();
    if (strictCpu && !details.gpuBefore.admissionPassed) throw new Error('Strict CPU PNG reference admission failed');
    const shared = {serveUrl: c.bundle, inputProps: {}, puppeteerInstance: browser,
      browserExecutable: c.browser, chromeMode: 'headless-shell',
      chromiumOptions: {gl: 'swangle', headless: true}, binariesDirectory: c.binariesDirectory, logLevel: 'warn'};
    const composition = await selectComposition({...shared, id: 'TextGrid'});
    if (composition.width !== 1920 || composition.height !== 1080 || composition.fps !== 30 ||
      composition.durationInFrames !== 300) throw new Error('Unexpected TextGrid composition');
    await mkdir(c.pngDirectory);
    let totalBytes = 0;
    const seen = new Set();
    await renderFrames({...shared, composition, imageFormat: 'png', frameRange: [0, 299],
      muted: true, concurrency: c.workers, outputDir: null, onStart: () => {}, onFrameUpdate: () => {},
      onFrameBuffer: async (buffer, frame) => {
        if (!Number.isInteger(frame) || frame < 0 || frame >= 300 || seen.has(frame)) throw new Error('Invalid/duplicate PNG frame');
        // Reserve synchronously before concurrent writes, keeping retained PNGs bounded.
        totalBytes += buffer.length;
        if (totalBytes > c.pngLimit) throw new Error('PNG reference scratch budget exceeded');
        seen.add(frame);
        const file = c.pngDirectory + '/frame-' + String(frame).padStart(3, '0') + '.png';
        await writeFile(file, buffer, {flag: 'wx'});
        details.frames.push({index: frame, bytes: buffer.length, sha256: createHash('sha256').update(buffer).digest('hex')});
      }});
    if (seen.size !== 300) throw new Error('Missing PNG frames');
    details.frames.sort((a, b) => a.index - b.index);
    details.pngBytes = totalBytes;
    details.gpuAfter = await gpuReceipt();
    if (strictCpu && !details.gpuAfter.admissionPassed) throw new Error('Strict CPU PNG reference final stage check failed');
  }
} catch (error) {
  details.failure = error?.stack ?? String(error);
  console.error(details.failure);
  process.exitCode = 1;
} finally {
  try { renderer?.close(); } catch (error) { details.cleanupFailure = String(error); process.exitCode = 1; }
  if (browser) {
    try { await browser.close({silent: true}); }
    catch (error) { details.cleanupFailure = String(error); process.exitCode = 1; }
  }
  await writeFile(c.details, JSON.stringify(details, null, 2) + '\n');
}
'''


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def retained(directory):
    return sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())


def execute(command, directory, label, stdin=None):
    receipt = {'command': [str(a) for a in command]}
    with (directory / (label + '.stdout.log')).open('wb') as out, (directory / (label + '.stderr.log')).open('wb') as err:
        receipt['exitCode'] = subprocess.run(receipt['command'], stdin=stdin, stdout=out, stderr=err, cwd=directory).returncode
    save(directory / (label + '.process.json'), receipt)
    if receipt['exitCode'] != 0:
        raise RuntimeError(f'{label} failed; see {directory}')


def stream_reference(producer, consumer, directory):
    # Binary frames go straight through a bounded OS pipe, never into a Python array.
    p = q = None
    codes = {'producer': None, 'consumer': None}
    try:
        with (directory / 'source.stderr.log').open('wb') as source_err, (directory / 'lossless.stderr.log').open('wb') as target_err, (directory / 'lossless.stdout.log').open('wb') as target_out:
            p = subprocess.Popen([str(a) for a in producer], stdout=subprocess.PIPE, stderr=source_err, cwd=directory)
            q = subprocess.Popen([str(a) for a in consumer], stdin=p.stdout, stdout=target_out, stderr=target_err, cwd=directory)
            p.stdout.close()
            codes['consumer'] = q.wait()
            if codes['consumer'] != 0 and p.poll() is None:
                p.terminate()
            codes['producer'] = p.wait()
    finally:
        for process in [q, p]:
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait()
        save(directory / 'pipeline.process.json', {'producerCommand': list(map(str, producer)),
             'consumerCommand': list(map(str, consumer)), 'exitCodes': codes})
    if any(code != 0 for code in codes.values()):
        raise RuntimeError(f'Reference pipeline failed: {directory}')


def probe(path, directory, label):
    execute([FFPROBE, '-v', 'error', '-threads', '4', '-select_streams', 'v:0', '-show_frames', '-show_streams',
             '-show_entries', 'frame=pts,best_effort_timestamp,pkt_dts,duration,pkt_duration,key_frame,pict_type:stream=codec_name,codec_type,width,height,pix_fmt,color_space,color_range,time_base,start_pts,duration_ts,avg_frame_rate,r_frame_rate,nb_frames',
             '-of', 'json', path], directory, label)
    return json.loads((directory / (label + '.stdout.log')).read_text())


def cadence(probe_data):
    streams, frames = probe_data.get('streams', []), probe_data.get('frames', [])
    if len(streams) != 1:
        raise RuntimeError('Missing/ambiguous video stream')
    stream = streams[0]
    tb = Fraction(stream['time_base'])
    per_frame, issues, previous = [], [], None
    for index, frame in enumerate(frames):
        pts = frame.get('pts')
        actual = Fraction(pts) * tb if isinstance(pts, int) else None
        expected = Fraction(index, FPS)
        delta = actual - previous if actual is not None and previous is not None else None
        duration = frame.get('duration', frame.get('pkt_duration'))
        item = {'index': index, 'pts': pts, 'ptsSecondsExact': str(actual) if actual is not None else None,
                'expectedSecondsExact': str(expected), 'deltaSecondsExact': str(delta) if delta is not None else None,
                'durationTicks': duration, 'bestEffortTimestamp': frame.get('best_effort_timestamp'),
                'pktDts': frame.get('pkt_dts'), 'pictureType': frame.get('pict_type')}
        per_frame.append(item)
        if actual != expected:
            issues.append({'index': index, 'issue': 'actual PTS missing or different from index/30'})
        if isinstance(duration, int) and Fraction(duration) * tb != Fraction(1, FPS):
            issues.append({'index': index, 'issue': 'frame duration different from 1/30'})
        previous = actual
    if len(frames) != FRAMES:
        issues.append({'issue': 'decoded frame count', 'actual': len(frames), 'expected': FRAMES})
    for key in ['avg_frame_rate', 'r_frame_rate']:
        try:
            rate = Fraction(stream.get(key, '0'))
        except (ValueError, ZeroDivisionError):
            rate = None
        if rate != FPS:
            issues.append({'issue': key, 'actual': stream.get(key), 'expected': '30/1'})
    duration_ts = stream.get('duration_ts')
    if isinstance(duration_ts, int) and Fraction(duration_ts) * tb != Fraction(10):
        issues.append({'issue': 'stream duration not exactly 10 seconds'})
    return {'timeBase': str(tb), 'decodedFrames': len(frames), 'expectedFrames': FRAMES,
            'expectedFps': FPS, 'matchesExact30fps300Frames': not issues, 'issues': issues,
            'stream': stream, 'frames': per_frame}


def metrics(directory, output, reference):
    graph = ('[0:v]setpts=N/(30*TB),split=2[o1][o2];[1:v]setpts=N/(30*TB),split=2[r1][r2];'
             '[o1][r1]psnr=stats_file=psnr.stats:stats_version=2:output_max=1:shortest=1[p];'
             '[o2][r2]ssim=stats_file=ssim.stats:shortest=1[s]')
    execute([FFMPEG, '-v', 'info', '-nostdin', '-threads', '4', '-i', output, '-threads', '4', '-i', reference,
             '-filter_complex_threads', '4', '-filter_complex', graph, '-map', '[p]', '-map', '[s]',
             '-fps_mode', 'passthrough', '-f', 'null', '-'], directory, 'metrics')
    psnr_rows, ssim_rows = [], []
    for name, rows in [('psnr', psnr_rows), ('ssim', ssim_rows)]:
        for line in (directory / (name + '.stats')).read_text().splitlines():
            if not line.startswith('n:'):
                continue
            values = dict(re.findall(r'([A-Za-z_]+):([^\s]+)', line))
            values['n'] = int(values['n'])
            rows.append(values)
        if [r['n'] for r in rows] != list(range(1, FRAMES + 1)):
            raise RuntimeError(f'{name} did not measure exactly 300 ordered frames')
    per_frame = [{'index': i, 'psnr': psnr_rows[i], 'ssim': ssim_rows[i]} for i in range(FRAMES)]
    mse = [float(row['mse_avg']) for row in psnr_rows]
    if not all(math.isfinite(v) and v >= 0 for v in mse):
        raise RuntimeError('Invalid PSNR MSE')
    pooled_mse = sum(mse) / FRAMES
    finite_psnr = [float(row['psnr_avg']) for row in psnr_rows if math.isfinite(float(row['psnr_avg']))]
    scores = [float(row['All']) for row in ssim_rows]
    if not all(math.isfinite(v) for v in scores):
        raise RuntimeError('Invalid SSIM')
    worst_psnr = max(range(FRAMES), key=lambda i: mse[i])
    worst_ssim = min(range(FRAMES), key=lambda i: scores[i])
    aggregate = re.search(r'PSNR y:[^\n]*?average:([^\s]+)', (directory / 'metrics.stderr.log').read_text())
    return {'framesMeasured': FRAMES, 'domain': 'native 8-bit YUV420P, BT.601 limited-range samples; no RGB decode round-trip',
            'qualityPassThreshold': None, 'psnr': {'pooledMse': pooled_mse,
              'pooledDb': 10 * math.log10(255 ** 2 / pooled_mse) if pooled_mse else 'inf',
              'ffmpegReportedAggregateDb': aggregate.group(1) if aggregate else None,
              'precision': 'per-frame and derived pooled metrics use FFmpeg text precision; aggregate line retained separately',
              'meanFiniteFrameDb': sum(finite_psnr) / len(finite_psnr) if finite_psnr else None,
              'infiniteFrameCount': FRAMES - len(finite_psnr),
              'minimumFrameDb': psnr_rows[worst_psnr]['psnr_avg'], 'worstFrameIndex': worst_psnr},
            'ssim': {'meanAll': sum(scores) / FRAMES, 'minimumAll': scores[worst_ssim], 'worstFrameIndex': worst_ssim},
            'frames': per_frame}


def load_saved():
    studies, outputs = {}, []
    for name in STUDIES:
        manifest_path = ROOT / name / 'results/full-v1/manifest.json'
        data = json.loads(manifest_path.read_text())
        if 'status' in data and not str(data['status']).startswith('performance-complete'):
            raise RuntimeError(f'{name} performance not complete; do not overlap timed work')
        studies[name] = {'path': str(manifest_path), 'sha256': sha(manifest_path), 'data': data}
        for index, record in enumerate(data['records']):
            if record.get('status', 'complete') != 'complete' or record.get('exitCode', 0) != 0:
                raise RuntimeError(f'{name} contains a failed/incomplete export')
            engine = record.get('engine', 'F' if name == 'fframes-worker-study-v1' else 'R' if name == 'remotion-cpu-jpeg-study-v1' else 'H')
            reference = ('R-cpu' if name == 'remotion-cpu-jpeg-study-v1' else 'R-legacy') if engine == 'R' else engine
            output = Path(record['directory']) / 'output.mp4'
            if not output.resolve().is_relative_to(ROOT / name / 'results/full-v1'):
                raise RuntimeError('Saved output escaped its original study directory')
            bindings = [p for p in record.get('outputs', []) if Path(p['path']) == output]
            expected_sha = bindings[0]['sha256'] if len(bindings) == 1 else record.get('outputSha256')
            expected_bytes = bindings[0]['bytes'] if len(bindings) == 1 else record.get('outputBytes')
            actual = sha(output)
            if expected_sha != actual or expected_bytes != output.stat().st_size:
                raise RuntimeError(f'Saved output binding mismatch: {output}')
            composition_sha = record.get('compositionSha256')
            if composition_sha and sha(output.parent / 'composition.mjs') != composition_sha:
                raise RuntimeError('Saved Helios composition binding mismatch')
            if engine == 'H':
                expected_wrapper = ("import {readFile} from 'node:fs/promises';\n"
                    f"import {{createTextGrid}} from {json.dumps((INPUT / 'fframes-textgrid.mjs').as_uri())};\n"
                    f"export default createTextGrid(await readFile({json.dumps(str(INPUT / 'DMSans-Regular.ttf'))}));\n")
                wrapper = (output.parent / 'composition.mjs').read_text()
                if re.sub(r'\s+', '', wrapper) != re.sub(r'\s+', '', expected_wrapper):
                    raise RuntimeError('Saved Helios wrapper does not import the exact pinned TextGrid factory/font')
            # Original timer keys and values retain their original units; no new timing claims.
            timers = {k: v for k, v in record.items() if k.endswith(('Ns', 'Ms', 'Seconds'))}
            outputs.append({'study': name, 'recordIndex': index, 'path': str(output), 'bytes': expected_bytes,
                'sha256': actual, 'engine': engine, 'referenceKey': reference, 'phase': record.get('phase'),
                'preset': record.get('preset', record.get('profile')), 'config': record.get('config'),
                'workers': record.get('workers'), 'variant': record.get('variant'), 'originalTimerFields': timers,
                'originalCompositionSha256': composition_sha,
                'originalResultSha256': sha(output.parent / 'result.json') if (output.parent / 'result.json').is_file() else None,
                'cpuLabel': 'GPU-stages-unattested' if reference == 'R-legacy' else 'strict-CPU-stages-attested' if reference == 'R-cpu' else 'CPU-renderer'})
            if reference == 'R-cpu' and not record.get('details', {}).get('gpuEvidence', {}).get('admissionPassed'):
                raise RuntimeError('Strict CPU saved Remotion artifact lacks stage admission receipt')
    return studies, outputs


def bind_reference_sources(studies, ready):
    project, bundle = Path(ready['cwd']), Path(ready['bundle_path'])
    files = {HERE / 'run.py', HERE / 'README.md', NODE, FFMPEG, FFPROBE, F,
             ROOT / 'fframes-setup/fframes-cpu/src/main.rs', INPUT / 'fframes-textgrid.mjs', INPUT / 'DMSans-Regular.ttf',
             ROOT / 'remotion-setup/ready.json', ROOT / 'remotion-setup/source-manifest.json',
             ROOT / 'remotion-cpu-jpeg-study-v1/chrome-cpu.sh', Path(ready['browser_path']),
             project / 'node_modules/@remotion/renderer/package.json',
             H / 'node_modules/@napi-rs/canvas-darwin-arm64/skia.darwin-arm64.node'}
    # Bind only the render path; do not touch authentication/configuration/state files.
    modules = ['canvas.js', 'canvas-pool.js', 'canvas-worker.js', 'skia-binding.js', 'text.js', 'plan.js', 'render.js', 'process.js']
    for directory in [H, ROOT / 'paired-decode-export-v1/baseline']:
        files.update(directory / 'dist' / name for name in modules)
    for directory in [bundle, project / 'src', project / 'node_modules/@remotion/renderer/dist']:
        files.update(p for p in directory.rglob('*') if p.is_file() and p.suffix in ['.js', '.map', '.tsx', '.ts', '.html', '.ttf'])
    compositor_dir = project / 'node_modules/@remotion/compositor-darwin-arm64'
    files.add(compositor_dir / 'remotion')
    files.update(compositor_dir.glob('*.dylib'))
    binaries = ROOT / 'three-engine-v1/results/full-v1/binaries'
    for name, target in [('ffmpeg', FFMPEG), ('ffprobe', FFPROBE), ('remotion', compositor_dir / 'remotion')] + [(p.name, p) for p in compositor_dir.glob('*.dylib')]:
        link = binaries / name
        if not link.is_file() or not link.is_symlink() or link.resolve() != target.resolve():
            raise RuntimeError(f'Original Remotion binary link changed: {name}')
    bound = {str(p): sha(p) for p in sorted(files)}
    if bound[str(INPUT / 'DMSans-Regular.ttf')] != FONT_SHA or bound[str(bundle / 'public/DMSans-Regular.ttf')] != FONT_SHA:
        raise RuntimeError('Pinned font mismatch')
    for study in studies.values():
        data = study['data']
        for key in ['sourceRuntimeSha256', 'sourceSha256']:
            for path, expected in data.get(key, {}).items():
                if path in bound and bound[path] != expected:
                    raise RuntimeError(f'Reference/source binding differs from original study: {path}')
        for key, directory in [('candidateSha256', H), ('baselineSha256', ROOT / 'paired-decode-export-v1/baseline')]:
            for relative, expected in data.get(key, {}).items():
                path = str(directory / relative)
                if path in bound and bound[path] != expected:
                    raise RuntimeError(f'Saved Helios module changed: {path}')
    # Decoder threading differs, but the exact raw frame producer must be identical.
    for name in ['canvas.js', 'skia-binding.js', 'text.js', 'plan.js']:
        if bound[str(H / 'dist' / name)] != bound[str(ROOT / 'paired-decode-export-v1/baseline/dist' / name)]:
            raise RuntimeError(f'Helios baseline/candidate raw frame producer differs: {name}')
    if RGB_FILTER not in (H / 'dist/render.js').read_text():
        raise RuntimeError('Pinned Helios RGB conversion filter missing')
    source = json.loads((ROOT / 'remotion-setup/source-manifest.json').read_text())
    for relative, expected in source['bundle_hashes'].items():
        path = bundle / relative
        if sha(path) != expected:
            raise RuntimeError(f'Frozen Remotion bundle changed: {relative}')
    return bound


def make_reference(key, destination, helper, ready, bound, h_composition):
    directory = destination / 'references' / key
    directory.mkdir(parents=True)
    output = directory / 'reference.nut'
    lossless_args = ['-an', '-c:v', 'ffv1', '-level', '3', '-g', '1', '-threads', '4', '-pix_fmt', 'yuv420p',
                     '-colorspace', 'smpte170m', '-color_range', 'tv', '-fs', str(REF_FILE_LIMIT), output]
    request = {'reference': key, 'details': str(directory / 'source-details.json')}
    if retained(destination) + REF_FILE_LIMIT + (PNG_LIMIT if key.startswith('R-') else 0) > BUDGET:
        raise RuntimeError('Insufficient owned storage budget for lossless reference')
    if key in ['H', 'F']:
        fmt = 'rgba' if key == 'H' else 'yuv420p'
        consumer = [FFMPEG, '-v', 'error', '-nostdin', '-n', '-threads', '4', '-filter_threads', '1',
                    '-f', 'rawvideo', '-pixel_format', fmt, '-video_size', '1920x1080', '-framerate', '30', '-i', 'pipe:0']
        if key == 'H':
            request.update(canvasModule=str(H / 'dist/canvas.js'), compositionModule=str(h_composition))
            save(directory / 'reference-request.json', request)
            producer = [NODE, helper, directory / 'reference-request.json']
            consumer += ['-vf', RGB_FILTER]
        else:
            # Existing pinned helper applies upstream's actual accelerated CPU converter.
            producer = [F, '--raw-yuv', 'medium', '11', '1', '2']
        stream_reference(producer, consumer + lossless_args, directory)
    else:
        request.update(project=ready['cwd'], bundle=ready['bundle_path'],
                       browser=str(ROOT / 'remotion-cpu-jpeg-study-v1/chrome-cpu.sh') if key == 'R-cpu' else ready['browser_path'],
                       binariesDirectory=str(ROOT / 'three-engine-v1/results/full-v1/binaries'),
                       workers=6 if key == 'R-cpu' else 4, pngDirectory=str(directory / 'png'), pngLimit=PNG_LIMIT)
        save(directory / 'reference-request.json', request)
        execute([NODE, helper, directory / 'reference-request.json'], directory, 'source')
        execute([FFMPEG, '-v', 'error', '-nostdin', '-n', '-threads', '4', '-filter_threads', '1',
                 '-framerate', '30', '-start_number', '0', '-i', directory / 'png/frame-%03d.png',
                 '-vf', RGB_FILTER] + lossless_args, directory, 'lossless')
    data = probe(output, directory, 'probe')
    stream = data['streams'][0]
    reference_cadence = cadence(data)
    if len(data['frames']) != FRAMES or stream['width'] != WIDTH or stream['height'] != HEIGHT or stream['pix_fmt'] != 'yuv420p' or stream['codec_name'] != 'ffv1':
        raise RuntimeError('Lossless reference incomplete or wrong format')
    if any(not Path(p).is_file() or sha(Path(p)) != expected for p, expected in bound.items()):
        raise RuntimeError('Reference source/runtime changed during generation')
    receipt = {'referenceKey': key, 'path': str(output), 'sha256': sha(output), 'bytes': output.stat().st_size,
               'frames': FRAMES, 'frameIndexes': [0, 299], 'encoding': 'lossless FFV1 level3 in NUT; no timed exporter invoked',
               'rgbConversionFilter': RGB_FILTER if key != 'F' else None,
               'converter': 'pinned fframes fill_yuv420_from_rgba_pixmap_accelerated' if key == 'F' else 'pinned shared software FFmpeg RGB→BT.601 TV YUV420P',
               'cpuLabel': 'GPU-stages-unattested' if key == 'R-legacy' else 'strict-CPU-stages-attested' if key == 'R-cpu' else 'CPU-renderer'}
    receipt['cadence'] = reference_cadence
    details = directory / 'source-details.json'
    if details.is_file():
        receipt['sourceDetailsSha256'] = sha(details)
        receipt['sourceDetails'] = json.loads(details.read_text())
    save(directory / 'receipt.json', receipt)
    if key.startswith('R-'):
        # Only owned generated scratch PNGs; full frame hashes/CPU receipts remain.
        shutil.rmtree(directory / 'png')
    if retained(destination) > BUDGET:
        raise RuntimeError('Owned result storage budget exceeded')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Explicit launch gate, only after timed jobs finish')
    parser.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    if not args.run:
        parser.error('Prepared only; --run is required after timed studies finish')
    destination = args.results.resolve()
    if not destination.is_relative_to(HERE / 'results'):
        parser.error('Results must be inside quality-measurement-v1/results/')
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {'createdUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'running',
                'qualityPassThreshold': None, 'maxOwnedBytes': BUDGET, 'references': {}, 'artifacts': [], 'savedOutputs': []}
    save(destination / 'manifest.json', manifest)
    try:
        studies, outputs = load_saved()
        ready = json.loads((ROOT / 'remotion-setup/ready.json').read_text())
        bound = bind_reference_sources(studies, ready)
        for output in outputs:
            if output['engine'] == 'H':
                bound[str(Path(output['path']).parent / 'composition.mjs')] = output['originalCompositionSha256']
        h_composition = Path(next(output['path'] for output in outputs if output['engine'] == 'H')).parent / 'composition.mjs'
        manifest['sourceRuntimeSha256'] = bound
        manifest['studyManifests'] = {name: {k: v for k, v in value.items() if k != 'data'} for name, value in studies.items()}
        manifest['savedOutputs'] = outputs
        manifest['metricImplementation'] = 'FFmpeg psnr stats_version2 and ssim; all Y/U/V and weighted all-plane rows saved'
        manifest['versions'] = {name: subprocess.run([str(tool), '-version'], capture_output=True, text=True, check=True).stdout
                                for name, tool in [('ffmpeg', FFMPEG), ('ffprobe', FFPROBE)]}
        helper = destination / 'reference-source.mjs'
        helper.write_text(REFERENCE_JS)
        manifest['referenceHelperSha256'] = sha(helper)
        save(destination / 'manifest.json', manifest)
        for key in sorted({output['referenceKey'] for output in outputs}):
            print(f'Untimed reference {key}', flush=True)
            manifest['references'][key] = make_reference(key, destination, helper, ready, bound, h_composition)
            save(destination / 'manifest.json', manifest)
        # Source mode is part of the key: never borrow a legacy GPU-unattested
        # reference for a strict CPU artifact, even if their export bytes match.
        unique = {}
        for output in outputs:
            key = (output['sha256'], output['referenceKey'])
            unique.setdefault(key, []).append(output)
        for (digest, reference_key), copies in unique.items():
            directory = destination / 'artifacts' / (reference_key + '-' + digest)
            directory.mkdir(parents=True)
            original = Path(copies[0]['path'])
            record = {'outputSha256': digest, 'referenceKey': reference_key, 'savedCopies': [{'study': c['study'], 'recordIndex': c['recordIndex'], 'path': c['path']} for c in copies],
                      'directory': str(directory), 'status': 'running'}
            manifest['artifacts'].append(record)
            print(f'Measure {reference_key}: {digest[:12]} ({len(copies)} saved copies)', flush=True)
            try:
                reference = manifest['references'][reference_key]
                data = probe(original, directory, 'probe')
                record['cadence'] = cadence(data)
                stream = data['streams'][0]
                if stream.get('codec_name') != 'h264' or stream.get('pix_fmt') != 'yuv420p' or stream.get('color_space') != 'smpte170m' or stream.get('color_range') != 'tv' or stream.get('width') != WIDTH or stream.get('height') != HEIGHT or len(data['frames']) != FRAMES:
                    raise RuntimeError('Saved artifact not the expected 300-frame H264 BT.601 TV YUV420P output')
                record['quality'] = metrics(directory, original, Path(reference['path']))
                record['referenceSha256'] = reference['sha256']
                if any(sha(Path(copy['path'])) != digest for copy in copies) or sha(Path(reference['path'])) != reference['sha256']:
                    raise RuntimeError('Saved output/reference changed during measurement')
                record['status'] = 'complete'
            except Exception as error:
                record.update(status='failed', failure=f'{type(error).__name__}: {error}')
            save(directory / 'measurement.json', record)
            save(destination / 'manifest.json', manifest)
            if retained(destination) > BUDGET:
                raise RuntimeError('Owned result storage budget exceeded')
        if any(sha(Path(path)) != expected for path, expected in bound.items()):
            raise RuntimeError('Source/runtime changed during measurement')
        if any(sha(Path(value['path'])) != value['sha256'] for value in studies.values()):
            raise RuntimeError('Original study manifest changed during measurement')
        manifest['status'] = 'measurement-complete' if all(record['status'] == 'complete' for record in manifest['artifacts']) else 'measurement-complete-with-failures'
        manifest['summary'] = {'savedOutputs': len(outputs), 'uniqueArtifactReferencePairs': len(unique),
            'ownReferences': len(manifest['references']), 'failedMeasurements': sum(r['status'] != 'complete' for r in manifest['artifacts']),
            'cadenceMismatchArtifacts': sum(not r.get('cadence', {}).get('matchesExact30fps300Frames', False) for r in manifest['artifacts']),
            'ownedBytes': retained(destination)}
    except BaseException as error:
        manifest.update(status='failed', failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        save(destination / 'manifest.json', manifest)
    print(f'Untimed measurement finished; inspect {destination / "manifest.json"}', flush=True)
    if manifest['status'] != 'measurement-complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
