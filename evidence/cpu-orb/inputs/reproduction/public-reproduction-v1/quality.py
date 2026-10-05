from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
FRAMES, FPS, WIDTH, HEIGHT = 300, 30, 1920, 1080
RGB_FILTER = 'scale=out_color_matrix=bt601:out_range=tv,format=yuv420p'
BUDGET = 6 * 1024 ** 3
REF_FILE_LIMIT = 1100 * 1024 ** 2
PNG_LIMIT = 1250 * 1024 ** 2


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
    graph = ('[0:v]settb=expr=1/30,setpts=N,split=2[o1][o2];[1:v]settb=expr=1/30,setpts=N,split=2[r1][r2];'
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
            producer = [F, '--raw-yuv', 'medium', '11', '1', '2', MEDIA]
        stream_reference(producer, consumer + lossless_args, directory)
    else:
        request.update(project=ready['cwd'], bundle=ready['bundle_path'],
                       browser=ready['browser_path'],
                       binariesDirectory=ready['binariesDirectory'],
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
