from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re


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
