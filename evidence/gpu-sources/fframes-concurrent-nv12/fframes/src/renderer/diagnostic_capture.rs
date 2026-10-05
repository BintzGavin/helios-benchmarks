//! Task-only, excluded same-stream encoder-handoff capture. Never used for timing.
//! Downloads a borrowed hardware frame without replacing it or changing encoder options.
use std::{
    cell::Cell,
    collections::{HashMap, HashSet},
    ffi::{c_int, c_ulong},
    fs::{File, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    sync::{Mutex, OnceLock},
};

use super::{RenderEncodingError, RenderEncodingResult, VideoFrame};
use crate::media::ffmpeg_sys_fframes::AVPixelFormat;

#[link(name = "z")]
unsafe extern "C" {
    fn compressBound(source_len: c_ulong) -> c_ulong;
    fn compress2(
        dest: *mut u8,
        dest_len: *mut c_ulong,
        source: *const u8,
        source_len: c_ulong,
        level: c_int,
    ) -> c_int;
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Ticket {
    index: usize,
    segment: usize,
}
struct Ledger {
    log: File,
    seq: usize,
    frames: HashMap<usize, (Ticket, usize)>,
    owners: HashMap<usize, Ticket>,
    captured: HashSet<usize>,
    submitted: HashSet<usize>,
    released: HashSet<usize>,
    callback_error: Option<String>,
}
struct Capture {
    dir: PathBuf,
    count: usize,
    offset: usize,
    width: i32,
    height: i32,
    ledger: Mutex<Ledger>,
}
static CAPTURE: OnceLock<Capture> = OnceLock::new();
thread_local! { static TICKET: Cell<Option<Ticket>> = const { Cell::new(None) }; }

fn error(message: impl Into<String>) -> RenderEncodingError {
    RenderEncodingError::Internal(message.into())
}
fn io_error(e: std::io::Error) -> RenderEncodingError {
    error(format!("excluded capture IO: {e}"))
}
fn locked(c: &Capture) -> RenderEncodingResult<std::sync::MutexGuard<'_, Ledger>> {
    c.ledger
        .lock()
        .map_err(|_| error("excluded capture ledger poisoned"))
}
fn event(l: &mut Ledger, fields: &str) -> RenderEncodingResult<()> {
    l.seq += 1;
    writeln!(
        l.log,
        "{{\"seq\":{},\"thread\":\"{:?}\",{}}}",
        l.seq,
        std::thread::current().id(),
        fields
    )
    .map_err(io_error)
}

/// Initializes an explicitly excluded, bounded capture. Existing log/files are refused.
pub fn initialize(
    dir: &Path,
    count: usize,
    offset: usize,
    width: i32,
    height: i32,
) -> RenderEncodingResult<()> {
    if !dir.is_absolute()
        || !(1..=300).contains(&count)
        || width <= 0
        || height <= 0
        || width > 3840
        || height > 2160
        || offset > 300
    {
        return Err(error("invalid excluded capture bounds"));
    }
    std::fs::create_dir_all(dir).map_err(io_error)?;
    let log = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(dir.join("handoff.jsonl"))
        .map_err(io_error)?;
    CAPTURE
        .set(Capture {
            dir: dir.to_owned(),
            count,
            offset,
            width,
            height,
            ledger: Mutex::new(Ledger {
                log,
                seq: 0,
                frames: HashMap::new(),
                owners: HashMap::new(),
                captured: HashSet::new(),
                submitted: HashSet::new(),
                released: HashSet::new(),
                callback_error: None,
            }),
        })
        .map_err(|_| error("capture already initialized"))?;
    let c = CAPTURE
        .get()
        .ok_or_else(|| error("capture initialization lost"))?;
    event(
        &mut *locked(c)?,
        &format!(
            "\"event\":\"initialize\",\"frames\":{count},\"sourceOffset\":{offset},\"width\":{width},\"height\":{height},\"benchmarkTiming\":false,\"zeroCopyProved\":false"
        ),
    )
}

/// Records policy-derived counts without changing them.
pub fn pipeline(
    gpu: usize,
    generators: usize,
    encoders: usize,
    configured: usize,
    queue: usize,
    offset: usize,
    frames: usize,
) -> RenderEncodingResult<()> {
    if let Some(c) = CAPTURE.get() {
        if c.offset != offset || c.count != frames {
            return Err(error("capture range disagrees with actual pipeline"));
        }
        event(
            &mut *locked(c)?,
            &format!(
                "\"event\":\"pipeline\",\"gpuContexts\":{gpu},\"generators\":{generators},\"encoderWorkers\":{encoders},\"configuredEncoderThreads\":{configured},\"queueSize\":{queue}"
            ),
        )?;
    }
    Ok(())
}

/// Records each actually started worker, independently from configured counts.
pub fn worker(role: &str) -> RenderEncodingResult<()> {
    if !matches!(role, "generator" | "gpu" | "encoder") {
        return Err(error("invalid worker role"));
    }
    if let Some(c) = CAPTURE.get() {
        event(
            &mut *locked(c)?,
            &format!("\"event\":\"worker-start\",\"role\":\"{role}\""),
        )?;
    }
    Ok(())
}

/// Output ordinal of the current production GPU claim; trials use a sentinel.
pub fn current_index() -> u32 {
    TICKET.get().map_or(u32::MAX, |t| t.index as u32)
}
/// Records source raster completion before explicit conversion, while source is owned.
pub fn raster_complete(frame: &VideoFrame, texture: usize) -> RenderEncodingResult<()> {
    if let (Some(c), Some(t)) = (CAPTURE.get(), TICKET.get()) {
        let (ptr, pixel, buffer) = identity(frame)?;
        event(
            &mut *locked(c)?,
            &format!(
                "\"event\":\"raster-complete\",\"index\":{},\"sourceIndex\":{},\"segment\":{},\"avframe\":{ptr},\"sourcePixelBuffer\":{pixel},\"avbuffer\":{buffer},\"sourceTexture\":{texture},\"fence\":\"flush_submit_and_sync_cpu returned\"",
                t.index,
                t.index + c.offset,
                t.segment
            ),
        )?;
    }
    Ok(())
}

/// Associates a scheduler claim with the synchronous render on this GPU thread.
pub fn begin_render(index: usize, segment: usize) {
    if CAPTURE.get().is_some() {
        TICKET.set(Some(Ticket { index, segment }));
    }
}
/// Clears the ticket on success or renderer failure.
pub fn end_render() {
    TICKET.set(None);
}

/// Called only AFTER the unchanged Skia CPU completion fence, while the frame is owned.
pub fn gpu_complete(frame: &VideoFrame, renderer: usize) -> RenderEncodingResult<()> {
    let Some(c) = CAPTURE.get() else {
        return Ok(());
    };
    let Some(t) = TICKET.get() else {
        return Ok(());
    }; // Negotiation/trial frame, never a candidate.
    let (ptr, pixel, buffer) = identity(frame)?;
    let mut l = locked(c)?;
    if t.index >= c.count || l.frames.contains_key(&ptr) || l.owners.contains_key(&pixel) {
        return Err(error("duplicate/live frame identity"));
    }
    l.frames.insert(ptr, (t, pixel));
    l.owners.insert(pixel, t);
    event(
        &mut l,
        &format!(
            "\"event\":\"gpu-complete\",\"index\":{},\"sourceIndex\":{},\"segment\":{},\"avframe\":{ptr},\"pixelBuffer\":{pixel},\"avbuffer\":{buffer},\"renderer\":{renderer},\"fence\":\"Skia raster then Metal conversion completion returned\"",
            t.index,
            t.index + c.offset,
            t.segment
        ),
    )
}

fn identity(frame: &VideoFrame) -> RenderEncodingResult<(usize, usize, usize)> {
    let raw = unsafe { &*frame.as_ptr() };
    if raw.format != AVPixelFormat::AV_PIX_FMT_VIDEOTOOLBOX as i32
        || raw.data[3].is_null()
        || raw.buf[0].is_null()
    {
        return Err(error("capture requires original owned VideoToolbox frame"));
    }
    Ok((
        frame.as_ptr() as usize,
        raw.data[3] as usize,
        raw.buf[0] as usize,
    ))
}

fn packed_rows(
    data: &[u8],
    stride: usize,
    row: usize,
    height: usize,
) -> RenderEncodingResult<Vec<u8>> {
    let required = stride
        .checked_mul(height)
        .ok_or_else(|| error("row bounds overflow"))?;
    if stride < row || data.len() < required {
        return Err(error("invalid BGRA row bounds"));
    }
    let mut result = Vec::with_capacity(
        row.checked_mul(height)
            .ok_or_else(|| error("packed bounds overflow"))?,
    );
    for line in data[..required].chunks_exact(stride) {
        result.extend_from_slice(&line[..row]);
    }
    Ok(result)
}
fn compress(bytes: &[u8]) -> RenderEncodingResult<Vec<u8>> {
    let mut size = unsafe { compressBound(bytes.len() as c_ulong) };
    let mut out = vec![0; size as usize];
    let status = unsafe {
        compress2(
            out.as_mut_ptr(),
            &raw mut size,
            bytes.as_ptr(),
            bytes.len() as c_ulong,
            1,
        )
    };
    if status != 0 {
        return Err(error(format!("zlib capture failed {status}")));
    }
    out.truncate(size as usize);
    Ok(out)
}

/// Downloads the exact borrowed input immediately before avcodec_send_frame. The original
/// AVFrame/CVPixelBuffer/AVBufferRef remain unchanged and owned throughout download/write.
pub fn before_send(
    frame: &VideoFrame,
    pts: i64,
    encoder: usize,
    segment: usize,
) -> RenderEncodingResult<()> {
    let Some(c) = CAPTURE.get() else {
        return Ok(());
    };
    let before = identity(frame)?;
    let t = {
        let mut l = locked(c)?;
        let (t, pixel) = *l
            .frames
            .get(&before.0)
            .ok_or_else(|| error("no completed source GPU frame"))?;
        if pts != t.index as i64
            || segment != t.segment
            || pixel != before.1
            || !l.captured.insert(t.index)
        {
            return Err(error("handoff ticket/segment mismatch or duplicate"));
        }
        event(
            &mut l,
            &format!(
                "\"event\":\"capture-begin\",\"index\":{},\"segment\":{segment},\"encoder\":{encoder},\"avframe\":{},\"pixelBuffer\":{},\"avbuffer\":{}",
                t.index, before.0, before.1, before.2
            ),
        )?;
        t
    };
    let download_enabled = std::env::var_os("FFRAMES_CAPTURE_NO_DOWNLOAD").is_none();
    let mut raw_bytes = 0;
    let mut compressed_bytes = 0;
    if download_enabled {
        let downloaded = frame.download()?;
        let raw = unsafe { &*downloaded.as_ptr() };
        if raw.width != c.width
            || raw.height != c.height
            || raw.format != AVPixelFormat::AV_PIX_FMT_NV12 as i32
            || raw.data[0].is_null()
            || raw.data[1].is_null()
            || raw.linesize[0] < c.width
            || raw.linesize[1] < c.width
        {
            return Err(error("NV12 download geometry mismatch"));
        }
        let mut packed = Vec::with_capacity(c.width as usize * c.height as usize * 3 / 2);
        for (plane, rows) in [(0, c.height as usize), (1, c.height as usize / 2)] {
            let data = unsafe {
                std::slice::from_raw_parts(raw.data[plane], raw.linesize[plane] as usize * rows)
            };
            packed.extend_from_slice(&packed_rows(
                data,
                raw.linesize[plane] as usize,
                c.width as usize,
                rows,
            )?);
        }
        let compressed = compress(&packed)?;
        raw_bytes = packed.len();
        compressed_bytes = compressed.len();
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(c.dir.join(format!("{:06}.nv12.zlib", t.index)))
            .map_err(io_error)?;
        file.write_all(&compressed).map_err(io_error)?;
        file.flush().map_err(io_error)?;
    }
    if before != identity(frame)? {
        return Err(error("capture changed original hardware identity"));
    }
    let mut l = locked(c)?;
    event(
        &mut l,
        &format!(
            "\"event\":\"capture-complete\",\"index\":{},\"sourceIndex\":{},\"segment\":{segment},\"encoder\":{encoder},\"avframe\":{},\"pixelBuffer\":{},\"avbuffer\":{},\"packedBytes\":{},\"compressedBytes\":{},\"downloadFormat\":\"nv12\",\"originalIdentityUnchanged\":true",
            t.index,
            t.index + c.offset,
            before.0,
            before.1,
            before.2,
            raw_bytes,
            compressed_bytes
        ),
    )?;
    event(
        &mut l,
        &format!(
            "\"event\":\"encoder-send-begin\",\"index\":{},\"segment\":{segment},\"encoder\":{encoder},\"pts\":{pts}",
            t.index
        ),
    )
}

/// Observes the original send result; never replaces or manually recycles the frame.
pub fn after_send(
    frame: &VideoFrame,
    pts: i64,
    encoder: usize,
    success: bool,
) -> RenderEncodingResult<()> {
    if let Some(c) = CAPTURE.get() {
        let (ptr, pixel, buffer) = identity(frame)?;
        let mut l = locked(c)?;
        let (t, original) = l
            .frames
            .remove(&ptr)
            .ok_or_else(|| error("missing frame after send"))?;
        if original != pixel || pts != t.index as i64 || !success || !l.submitted.insert(t.index) {
            return Err(error("encoder send failed or identity changed"));
        }
        event(
            &mut l,
            &format!(
                "\"event\":\"encoder-send-return\",\"index\":{},\"segment\":{},\"encoder\":{encoder},\"avframe\":{ptr},\"pixelBuffer\":{pixel},\"avbuffer\":{buffer},\"success\":true",
                t.index, t.segment
            ),
        )?;
    }
    Ok(())
}

/// Records successful completion of the original codec flush, after packet draining.
pub fn drained(encoder: usize) -> RenderEncodingResult<()> {
    if let Some(c) = CAPTURE.get() {
        event(
            &mut *locked(c)?,
            &format!("\"event\":\"encoder-drained\",\"encoder\":{encoder}"),
        )?;
    }
    Ok(())
}

/// Observes the existing AVBuffer final-reference callback, not opaque encoder ownership.
/// Cannot return an error across C ABI; records one for mandatory finalization instead.
pub fn avbuffer_release(pixel: usize) {
    if let Some(c) = CAPTURE.get() {
        if let Ok(mut l) = c.ledger.lock() {
            if let Some(t) = l.owners.remove(&pixel) {
                l.released.insert(t.index);
                if let Err(e) = event(
                    &mut l,
                    &format!(
                        "\"event\":\"avbuffer-final-reference-release\",\"index\":{},\"segment\":{},\"pixelBuffer\":{pixel},\"opaqueEncoderOwnershipKnown\":false",
                        t.index, t.segment
                    ),
                ) {
                    l.callback_error = Some(format!("{e:?}"));
                }
            }
        }
    }
}
/// Requires all indexed captures, sends and AVBuffer callbacks, with no outstanding ticket.
pub fn finalize() -> RenderEncodingResult<()> {
    let c = CAPTURE
        .get()
        .ok_or_else(|| error("capture not initialized"))?;
    let mut l = locked(c)?;
    let expected: HashSet<_> = (0..c.count).collect();
    if l.captured != expected
        || l.submitted != expected
        || l.released != expected
        || !l.frames.is_empty()
        || !l.owners.is_empty()
        || l.callback_error.is_some()
    {
        return Err(error(format!(
            "incomplete capture ledger: captured={}, submitted={}, released={}, error={:?}",
            l.captured.len(),
            l.submitted.len(),
            l.released.len(),
            l.callback_error
        )));
    }
    event(
        &mut l,
        "\"event\":\"finalize\",\"passed\":true,\"benchmarkTiming\":false,\"opaqueEncoderOwnershipKnown\":false",
    )?;
    l.log.flush().map_err(io_error)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn packs_padding_without_changing_pixels() {
        assert_eq!(
            packed_rows(&[1, 2, 3, 4, 90, 91, 5, 6, 7, 8, 92, 93], 6, 4, 2).unwrap(),
            vec![1, 2, 3, 4, 5, 6, 7, 8]
        );
    }
    #[test]
    fn rejects_short_stride_and_overflow() {
        assert!(packed_rows(&[0; 8], 3, 4, 2).is_err());
        assert!(packed_rows(&[], usize::MAX, 4, 2).is_err());
        assert!(packed_rows(&[0; 7], 4, 4, 2).is_err());
    }
    #[test]
    fn zlib_roundtrip_preserves_all_bytes() {
        #[link(name = "z")]
        unsafe extern "C" {
            fn uncompress(
                dest: *mut u8,
                size: *mut c_ulong,
                source: *const u8,
                len: c_ulong,
            ) -> c_int;
        }
        let input: Vec<u8> = (0..65536).map(|i| (i * 37 % 256) as u8).collect();
        let compressed = compress(&input).unwrap();
        let mut output = vec![0; input.len()];
        let mut size = output.len() as c_ulong;
        assert_eq!(
            unsafe {
                uncompress(
                    output.as_mut_ptr(),
                    &raw mut size,
                    compressed.as_ptr(),
                    compressed.len() as c_ulong,
                )
            },
            0
        );
        assert_eq!(size as usize, input.len());
        assert_eq!(output, input);
    }
}
