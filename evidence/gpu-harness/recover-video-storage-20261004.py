"""Preserve each frozen video's exact bytes using APFS copy-on-write sharing."""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import shutil
import stat
import uuid

ROOT = Path('/Users/gavinbintz/Documents/Codex/2026-10-02/task')
RECEIPT = ROOT / 'checkpoint/storage-recovery-20261004.json'
PLAN = json.loads((ROOT / 'checkpoint/storage-recovery-candidates-20261004.json').read_text())
PAIRS = [x for x in PLAN['nearDuplicates'] if '/circles-common-' in x['target'] and x['differing1MiBChunks'] == 1]
libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
clone = libc.clonefile
clone.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
clone.restype = ctypes.c_int
libc.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
libc.listxattr.restype = ctypes.c_ssize_t
libc.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
libc.getxattr.restype = ctypes.c_ssize_t
libc.setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
libc.setxattr.restype = ctypes.c_int
libc.removexattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
libc.removexattr.restype = ctypes.c_int

def list_xattrs(path):
    count = libc.listxattr(os.fsencode(path), None, 0, 0)
    if count < 0:
        raise OSError(ctypes.get_errno(), 'listxattr failed')
    if count == 0:
        return []
    buffer = ctypes.create_string_buffer(count)
    written = libc.listxattr(os.fsencode(path), buffer, count, 0)
    if written < 0:
        raise OSError(ctypes.get_errno(), 'listxattr failed')
    return [os.fsdecode(name) for name in buffer.raw[:written].split(b'\0') if name]

def get_xattr(path, name):
    count = libc.getxattr(os.fsencode(path), os.fsencode(name), None, 0, 0, 0)
    if count < 0:
        raise OSError(ctypes.get_errno(), 'getxattr failed')
    buffer = ctypes.create_string_buffer(count)
    written = libc.getxattr(os.fsencode(path), os.fsencode(name), buffer, count, 0, 0)
    if written < 0:
        raise OSError(ctypes.get_errno(), 'getxattr failed')
    return buffer.raw[:written]

def set_xattr(path, name, value):
    buffer = ctypes.create_string_buffer(value)
    if libc.setxattr(os.fsencode(path), os.fsencode(name), buffer, len(value), 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'setxattr failed')

def remove_xattr(path, name):
    if libc.removexattr(os.fsencode(path), os.fsencode(name), 0) != 0:
        raise OSError(ctypes.get_errno(), 'removexattr failed')

result = {'method': 'APFS clone, independently restore differing blocks, exact SHA validation before atomic replacement', 'files': [], 'freeBytesBefore': shutil.disk_usage(ROOT).free, 'originalPathsAndBytesPreserved': True, 'newBenchmarks': False}

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def save():
    result['freeBytesAfter'] = shutil.disk_usage(ROOT).free
    result['measuredFreeBytesGain'] = result['freeBytesAfter'] - result['freeBytesBefore']
    RECEIPT.write_text(json.dumps(result, indent=2) + '\n')

save()
for pair in PAIRS:
    base, target = Path(pair['base']), Path(pair['target'])
    for path in (base, target):
        if not path.is_relative_to(ROOT) or path.is_symlink() or path.resolve() != path:
            raise RuntimeError('unsafe path')
    original_stat = target.stat()
    if not stat.S_ISREG(original_stat.st_mode) or original_stat.st_nlink != 1 or original_stat.st_size != base.stat().st_size:
        raise RuntimeError('target changed or is shared')
    original_hash, base_hash = digest(target), digest(base)
    original_xattrs = {name: get_xattr(target, name) for name in list_xattrs(target)}
    temporary = target.with_name('.storage-recovery-' + uuid.uuid4().hex)
    entry = {'base': str(base), 'target': str(target), 'originalSha256': original_hash, 'baseSha256': base_hash, 'bytes': original_stat.st_size, 'originalInode': original_stat.st_ino, 'originalMtimeNs': original_stat.st_mtime_ns, 'originalBirthtime': original_stat.st_birthtime, 'differingBlocks': [], 'status': 'pending'}
    result['files'].append(entry)
    save()
    try:
        if clone(os.fsencode(base), os.fsencode(temporary), 0) != 0:
            raise OSError(ctypes.get_errno(), 'clonefile failed')
        block_size = 64 * 1024
        with base.open('rb') as source, target.open('rb') as old, temporary.open('r+b') as new:
            offset = 0
            while True:
                source_bytes, original_bytes = source.read(block_size), old.read(block_size)
                if not source_bytes:
                    break
                if source_bytes != original_bytes:
                    entry['differingBlocks'].append({'offset': offset, 'bytes': len(original_bytes)})
                    if sum(x['bytes'] for x in entry['differingBlocks']) > 16 * 1024 * 1024:
                        raise RuntimeError('difference exceeds bounded plan')
                    new.seek(offset)
                    new.write(original_bytes)
                offset += len(source_bytes)
            new.flush()
            os.fsync(new.fileno())
        new_stat = temporary.stat()
        if (new_stat.st_uid, new_stat.st_gid) != (original_stat.st_uid, original_stat.st_gid):
            raise RuntimeError('owner mismatch')
        os.chmod(temporary, stat.S_IMODE(original_stat.st_mode))
        for name in list_xattrs(temporary):
            if name not in original_xattrs:
                remove_xattr(temporary, name)
        for name, value in original_xattrs.items():
            set_xattr(temporary, name, value)
        os.utime(temporary, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        entry['restoredSha256'] = digest(temporary)
        if entry['restoredSha256'] != original_hash or digest(base) != base_hash:
            raise RuntimeError('byte validation failed; original preserved')
        current = target.stat()
        if (current.st_ino, current.st_size, current.st_mtime_ns) != (original_stat.st_ino, original_stat.st_size, original_stat.st_mtime_ns):
            raise RuntimeError('original changed while preparing')
        os.replace(temporary, target)
        entry['finalSha256'] = digest(target)
        if entry['finalSha256'] != original_hash:
            raise RuntimeError('post-replacement validation failed')
        entry['newInode'] = target.stat().st_ino
        entry['xattrsPreserved'] = {name: get_xattr(target, name) for name in list_xattrs(target)} == original_xattrs
        entry['mtimePreserved'] = target.stat().st_mtime_ns == original_stat.st_mtime_ns
        entry['status'] = 'exact-bytes-preserved'
        save()
        print(json.dumps({'target': str(target), 'status': entry['status'], 'freeBytesNow': result['freeBytesAfter']}), flush=True)
    except Exception as error:
        entry['status'] = 'failed'
        entry['error'] = str(error)
        save()
        raise
    finally:
        if temporary.exists():
            temporary.unlink()
result['allExact'] = all(x['status'] == 'exact-bytes-preserved' and x['xattrsPreserved'] and x['mtimePreserved'] for x in result['files'])
result['minimumTwoGiBFreeSatisfied'] = shutil.disk_usage(ROOT).free >= 2 * 1024 ** 3
save()
print(json.dumps({'receipt': str(RECEIPT), 'files': len(result['files']), 'allExact': result['allExact'], 'freeBytesAfter': result['freeBytesAfter'], 'measuredFreeBytesGain': result['measuredFreeBytesGain'], 'minimumTwoGiBFreeSatisfied': result['minimumTwoGiBFreeSatisfied']}), flush=True)
