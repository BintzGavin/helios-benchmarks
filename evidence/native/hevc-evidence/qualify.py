import hashlib, json, re, subprocess
from pathlib import Path

root = Path('/Users/gavinbintz/.codex/visualizations/2026/10/03/01a101cb-eaad-7290-9c09-0640b9deae94/hevc-evidence')
worktree = Path('/Users/gavinbintz/.codex/worktrees/gpu-hevc/helios')
directory = root / 'qualification-01'
directory.mkdir(exist_ok=True)
(directory / 'logs').mkdir(exist_ok=True)
helper = root / 'helper-candidate-01'
sdk = '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
ffmpeg = '/opt/homebrew/bin/ffmpeg'
ffprobe = '/opt/homebrew/bin/ffprobe'
node = '/opt/homebrew/bin/node'
executions = []

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(name, args, data=None, output=None, expected=0):
    with (Path(output) if output else directory / 'logs' / (name + '.stdout')).open('wb') as out, (directory / 'logs' / (name + '.stderr')).open('wb') as err:
        result = subprocess.run(args, input=data, stdout=out, stderr=err, timeout=120)
    executions.append({'name': name, 'args': [str(x) for x in args], 'exit': result.returncode})
    (directory / 'executions.json').write_text(json.dumps(executions, indent=2))
    if result.returncode != expected:
        raise RuntimeError(name + ' unexpected exit ' + str(result.returncode))

run('prepare', [node, str(root / 'prepare-qualification.mjs'), 'prepare'])
frames = (directory / 'frames-300.bin').read_bytes()
controls = (directory / 'frames-3.bin').read_bytes()
candidate = json.loads((root / 'CANDIDATE-01.json').read_text())
assert digest(helper) == candidate['sha256']
source_pins = {}
for name in ['src/gpu.ts', 'src/gpu-commands.ts', 'native/metal.mm', 'native/src/main.rs', 'native/src/binary.rs', 'native/encoder-flight.hpp', 'native/build.rs', 'native/Cargo.toml', 'native/Cargo.lock', 'benchmarks/profile-gpu.mm']:
    source_pins[name] = digest(worktree / 'packages/portable' / name)

def native(mode, output, trace, capture='', codec='hevc'):
    return [str(helper), mode, '256', '128', '30000', '1001', '20000000', str(output), str(trace), str(capture), '30', '3', codec]

def interposed(library, args):
    return ['/usr/bin/env', 'DYLD_INSERT_LIBRARIES=' + str(library), *args]

libraries = {}
for lane in ['hardware', 'nv12-control', 'rgba-control']:
    library = directory / (lane + '.dylib')
    profile = directory / (lane + '-profile.jsonl')
    assert not profile.exists(), 'Never append to a prior qualification profile'
    run('compile-' + lane, ['/usr/bin/xcrun', 'clang++', '-dynamiclib', '-fobjc-arc', '-isysroot', sdk, '-DHELIOS_PROFILE_PATH="' + str(profile) + '"', str(worktree / 'packages/portable/benchmarks/profile-gpu.mm'), '-framework', 'Foundation', '-framework', 'Metal', '-framework', 'CoreVideo', '-framework', 'IOSurface', '-o', str(library)])
    libraries[lane] = library
wrapper = directory / 'profiled-helper'
wrapper.write_text('#!/bin/sh\nexec /usr/bin/env DYLD_INSERT_LIBRARIES=' + str(libraries['hardware']) + ' ' + str(helper) + ' "$@"\n')
wrapper.chmod(0o755)
run('api-encode-profiled', [node, str(root / 'prepare-qualification.mjs'), 'encode'])
run('direct-reference', native('reference-binary', '/unused', directory / 'reference-trace.jsonl'), frames, directory / 'reference.nv12')
raw = (directory / 'reference.nv12').read_bytes()
y_size, frame_size = 256 * 128, 256 * 128 * 3 // 2
assert len(raw) == frame_size * 300
planar, frame_hashes = bytearray(), []
for index in range(300):
    frame = raw[index * frame_size:(index + 1) * frame_size]
    split = frame[:y_size] + frame[y_size::2] + frame[y_size + 1::2]
    planar.extend(split)
    frame_hashes.append({'frame': index, 'nv12Sha256': hashlib.sha256(frame).hexdigest(), 'planarMd5': hashlib.md5(split).hexdigest()})
(directory / 'reference-direct.yuv').write_bytes(planar)
run('lossless-reference', [ffmpeg, '-v', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'nv12', '-video_size', '256x128', '-framerate', '30000/1001', '-i', str(directory / 'reference.nv12'), '-vf', 'setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709,format=yuv420p', '-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', str(directory / 'reference.mkv')])
run('lossless-direct-binding', [ffmpeg, '-v', 'error', '-i', str(directory / 'reference.mkv'), '-f', 'framemd5', '-'], output=directory / 'reference-framemd5.txt')
decoded_hashes = [line.rsplit(',', 1)[-1].strip() for line in (directory / 'reference-framemd5.txt').read_text().splitlines() if not line.startswith('#')]
assert decoded_hashes == [row['planarMd5'] for row in frame_hashes]
(directory / 'direct-byte-binding.json').write_text(json.dumps({'all300Exact': True, 'frames': frame_hashes, 'helperSha256': digest(helper), 'nv12Sha256': digest(directory / 'reference.nv12'), 'losslessReferenceSha256': digest(directory / 'reference.mkv')}, indent=2))
run('decoded-cadence', [ffprobe, '-v', 'error', '-threads', '1', '-select_streams', 'v:0', '-show_streams', '-show_frames', '-show_entries', 'frame=best_effort_timestamp,key_frame:stream=codec_name,codec_tag_string,profile,width,height,pix_fmt,color_range,color_space,color_transfer,color_primaries,avg_frame_rate,time_base', '-of', 'json', str(directory / 'video.mp4')], output=directory / 'decoded-cadence.json')
decoded = json.loads((directory / 'decoded-cadence.json').read_text())
stream = decoded['streams'][0]
assert len(decoded['frames']) == 300
assert stream['codec_name'] == 'hevc' and stream['codec_tag_string'] == 'hvc1' and stream['profile'] == 'Main'
assert (stream['width'], stream['height']) == (256, 128)
assert stream['pix_fmt'] == 'yuv420p' and stream['avg_frame_rate'] == '30000/1001'
assert stream['color_range'] == 'tv' and all(stream[key] == 'bt709' for key in ['color_space', 'color_transfer', 'color_primaries'])
num, den = map(int, stream['time_base'].split('/'))
for index, frame in enumerate(decoded['frames']): assert frame['best_effort_timestamp'] * num * 30000 == index * 1001 * den
keyframes = [i for i, frame in enumerate(decoded['frames']) if frame['key_frame']]
assert keyframes[0] == 0 and max(b - a for a, b in zip(keyframes, keyframes[1:])) <= 30
graph = '[0:v]settb=1001/30000,setpts=N,split=2[a][b];[1:v]settb=1001/30000,setpts=N,split=2[c][d];[a][c]ssim=shortest=1:repeatlast=0:stats_file=' + str(directory / 'ssim.txt') + '[s];[b][d]psnr=shortest=1:repeatlast=0:stats_file=' + str(directory / 'psnr.txt') + '[p]'
run('every-frame-quality', [ffmpeg, '-v', 'error', '-filter_complex_threads', '1', '-threads', '1', '-i', str(directory / 'video.mp4'), '-threads', '1', '-i', str(directory / 'reference.mkv'), '-filter_complex', graph, '-map', '[s]', '-map', '[p]', '-f', 'null', '-'])
def stats(path):
    return [{key: float(value) for key, value in re.findall(r'([A-Za-z_]+):([\d.e+\-]+|inf)', line)} for line in path.read_text().splitlines()]
ssim, psnr = stats(directory / 'ssim.txt'), stats(directory / 'psnr.txt')
assert len(ssim) == len(psnr) == 300
for index, (s, p) in enumerate(zip(ssim, psnr)):
    assert s['n'] == p['n'] == index + 1
    assert s['Y'] >= .995 and p['psnr_y'] >= 40 and p['psnr_u'] >= 35 and p['psnr_v'] >= 35
run('nv12-positive-control', interposed(libraries['nv12-control'], native('reference-binary', '/unused', directory / 'nv12-control-trace.jsonl')), controls, directory / 'nv12-control.raw')
run('rgba-positive-control', interposed(libraries['rgba-control'], native('raster-binary', '/unused', directory / 'rgba-control-trace.jsonl')), controls, directory / 'rgba-control.raw')
def rows(path): return [json.loads(line) for line in path.read_text().splitlines()]
profiles = {}
downloads = {'CVPixelBufferLockBaseAddress', 'IOSurfaceLock', 'MTLTextureGetBytes', 'MTLBlitTextureToBuffer'}
for lane in libraries:
    profile = rows(directory / (lane + '-profile.jsonl'))
    assert any(row['event'] == 'profiler-hooks-installed' for row in profile)
    assert not any(row['event'] == 'profiler-hooks-incomplete' for row in profile)
    counts = {event: sum(row['event'] == event for row in profile) for event in sorted(set(row['event'] for row in profile))}
    profiles[lane] = {'events': counts, 'hookedRawDownloadCalls': sum(counts.get(event, 0) for event in downloads), 'interposerSha256': digest(libraries[lane]), 'traceSha256': digest(directory / (lane + '-profile.jsonl'))}
assert profiles['hardware']['hookedRawDownloadCalls'] == 0
assert profiles['nv12-control']['hookedRawDownloadCalls'] >= 3 and profiles['rgba-control']['hookedRawDownloadCalls'] >= 3
trace = rows(directory / 'hardware-trace.jsonl')
assert trace[0]['codec'] == 'hevc' and trace[0]['hardwareUsed'] is True and trace[0]['poolCapacity'] == 3
assert trace[-1]['allCallbacksComplete'] is True and trace[-1]['frames'] == 300
for event in ['raster-submitted', 'conversion-complete', 'encoder-callback', 'callback-owner-release']:
    selected = [row for row in trace if row['event'] == event]
    assert [row['frame'] for row in selected] == list(range(300))
conversion = {row['frame']: i for i, row in enumerate(trace) if row['event'] == 'conversion-complete'}
callback = {row['frame']: i for i, row in enumerate(trace) if row['event'] == 'encoder-callback'}
assert all(conversion[i] < callback[i] for i in range(300))
for kind in ['DEVICE', 'ENCODER', 'BITRATE', 'HEVC_FORMAT']:
    library = directory / ('fault-' + kind.lower() + '.dylib')
    run('compile-fault-' + kind, ['/usr/bin/xcrun', 'clang++', '-dynamiclib', '-fobjc-arc', '-isysroot', sdk, '-DHELIOS_FAIL_' + kind, str(worktree / 'packages/portable/native/fault-init.mm'), '-framework', 'Metal', '-framework', 'VideoToolbox', '-framework', 'CoreMedia', '-o', str(library)])
    if kind == 'HEVC_FORMAT':
        wrapper = directory / 'format-fault-helper'
        wrapper.write_text('#!/bin/sh\nexec /usr/bin/env DYLD_INSERT_LIBRARIES=' + str(library) + ' ' + str(helper) + ' "$@"\n'); wrapper.chmod(0o755)
        run('format-fault-public-api', [node, str(root / 'prepare-qualification.mjs'), 'format-fault'])
    else:
        run('fault-' + kind, interposed(library, [str(helper), 'probe', 'hevc']), expected=1)
        assert 'GPU_INIT_FAILED' in (directory / 'logs' / ('fault-' + kind + '.stderr')).read_text()
run('metal-capture-3-excluded', ['/usr/bin/env', 'MTL_CAPTURE_ENABLED=1', *native('encode-binary', directory / 'capture-3.hevc', directory / 'capture-3-trace.jsonl', directory / 'capture-3.gputrace')], controls)
run('review-image', [ffmpeg, '-v', 'error', '-y', '-i', str(directory / 'video.mp4'), '-vf', 'select=eq(n\,0)+eq(n\,150)+eq(n\,299),tile=3x1', '-frames:v', '1', str(directory / 'review.png')])
report = {'status': 'all300 HEVC functional qualification passed; not a benchmark', 'helperSha256': digest(helper), 'sourcePins': source_pins, 'config': json.loads((directory / 'CONFIG.json').read_text()), 'frames': 300, 'allDirectLosslessReferenceFramesExact': True, 'fullDecodedCadenceColorCodecPassed': True, 'everyFrameUnchangedFloorsPassed': True, 'minimumSsimY': min(row['Y'] for row in ssim), 'minimumPsnrY': min(row['psnr_y'] for row in psnr), 'minimumPsnrU': min(row['psnr_u'] for row in psnr), 'minimumPsnrV': min(row['psnr_v'] for row in psnr), 'keyframeIndices': keyframes, 'actualHardwareHevc': trace[0], 'all300GpuConversionCallbacksPassed': True, 'profiles': profiles, 'faults': ['device', 'encoder', 'bitrate', 'hevc-format atomic publication'], 'separateActualMetalCaptureFrames': 3, 'captureExcludedFromDownloadProof': True, 'applicationRawDownloadsObservedWithinHooks': False, 'opaqueDriverEncoderTransfers': 'unknown', 'pointerAndBufferAccessIntent': 'unknown', 'zeroCopyProved': False, 'videoSha256': digest(directory / 'video.mp4'), 'referenceSha256': digest(directory / 'reference.mkv'), 'executions': executions}
(directory / 'REPORT.json').write_text(json.dumps(report, indent=2))
print(json.dumps({key: report[key] for key in ['status', 'helperSha256', 'minimumSsimY', 'minimumPsnrY', 'minimumPsnrU', 'minimumPsnrV', 'zeroCopyProved']}))
