//! Fixed scene benchmark: wall-clock time to render a complete H.264 MP4.
use std::{path::Path, time::Instant};

use fframes::{
    AudioMap, Color, Duration, EncoderOptions, FFramesContext, FFramesLoggerVariant,
    FFramesRenderBackend, Frame, RenderOptions, StaticMediaProvider, Svgr, Transform, Video,
    cpu::CpuRenderingBackend,
};
use fframes_skia_renderer::{
    SkiaBackend, SkiaCacheConfig, SkiaFFramesRenderer, SkiaPipelineConcurrencyPolicy,
    SkiaPipelineConfig,
};

fframes::include_media_dir!(struct BenchMedia, "render-bench/vs-remotion/media");

const VIDEO_WIDTH: usize = 3840;
const VIDEO_HEIGHT: usize = 2160;
const CIRCLES: usize = 99_000;
const TEXTS: usize = 1000;
const NODES: usize = CIRCLES + TEXTS;
const PANELS: usize = 20;
const PER_PANEL: usize = NODES / PANELS;
const TEXT_STEP: usize = NODES / TEXTS;
const CACHE_CAPACITY: usize = 100_000;
const FRAMES: usize = 300;
const WARMUP: usize = 3;
const CACHE: SkiaCacheConfig = SkiaCacheConfig {
    text_capacity: CACHE_CAPACITY,
    geometry_capacity: CACHE_CAPACITY,
    geometry_bytes: CACHE_CAPACITY * 512,
};

fn cpu_backend() -> CpuRenderingBackend {
    CpuRenderingBackend {
        concurrency: fframes::get_thread_count(),
        text_cache_capacity: CACHE_CAPACITY,
        ..Default::default()
    }
}

fn circle_radius(slot: usize, frame: usize) -> f64 {
    if slot % 10 != 1 {
        return (16 + slot % 4 * 4) as f64;
    }
    let phase = ((slot + frame) % 60) as f64;
    let (progress, from, to) = if phase <= 30. {
        (phase / 30., 16., 28.)
    } else {
        ((phase - 30.) / 30., 28., 16.)
    };
    let amount = progress * progress * (3. - 2. * progress);
    amount * (to - from) + from
}

struct Grid;

impl Video for Grid {
    const FPS: usize = 30;
    const WIDTH: usize = VIDEO_WIDTH;
    const HEIGHT: usize = VIDEO_HEIGHT;
    const BACKGROUND_COLOR: Color = Color::hex("#18202c");
    fn duration(&self) -> Duration<'_> {
        Duration::Frames(FRAMES + WARMUP)
    }
    fn audio(&self) -> AudioMap<'_> {
        AudioMap::none()
    }
    fn render_frame<'a>(&'a self, frame: Frame, _ctx: &FFramesContext<'a, '_>) -> Svgr<'a> {
        let panels: Vec<_> = (0..PANELS)
            .map(|panel| {
                let circles: Vec<_> = (panel * PER_PANEL..(panel + 1) * PER_PANEL)
                    .filter(|slot| slot % TEXT_STEP != 0)
                    .map(|slot| {
                        let id = (slot + frame.index * 37) % NODES;
                        let radius = circle_radius(slot, frame.index);
                        let fill = Color::rgba(
                            ((id * 13 + frame.index * 17) % 256) as u8,
                            ((id * 7 + frame.index * 29) % 256) as u8,
                            ((id * 3 + frame.index * 43) % 256) as u8,
                            255,
                        );
                        fframes::svgr!(<circle cx={32 + (slot * 13 + frame.index * 3) % 128}
                        cy={32 + (slot * 17 + frame.index * 5) % 176}
                        r={radius} fill={fill} />)
                    })
                    .collect();
                let transform =
                    Transform::translate((panel % 5 * 200) as f64, (panel / 5 * 250) as f64);
                fframes::svgr!(<g transform={transform}>{circles}</g>)
            })
            .collect();
        let texts: Vec<_> = (0..NODES).step_by(TEXT_STEP).map(|slot| {
            let panel = slot / PER_PANEL;
            let index = slot % PER_PANEL / TEXT_STEP;
            let id = (slot + frame.index * 37) % NODES;
            fframes::svgr!(<text x={panel % 5 * 200 + 24 + index % 10 * 16}
                y={panel / 5 * 250 + 40 + index / 10 * 40}
                font-family="DM Sans" font-size="16" fill="#fff">{((id + frame.index) % 10).to_string()}</text>)
        }).collect();
        fframes::svgr!(
            <svg xmlns="http://www.w3.org/2000/svg" width={VIDEO_WIDTH} height={VIDEO_HEIGHT}
                viewBox="0 0 1000 1000" preserveAspectRatio="none">
                {panels}
                {texts}
            </svg>
        )
    }
}


use std::io::Write;
use fframes::{MediaDirectory, Previewer, VideoEncoderInfo, EncoderFrameRenderer};
use fframes_skia_renderer::{SkiaEncoderFrameRenderer, SkiaFrameExport, FrameExportPath};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 6 { return Err("usage: textgrid-adapter raw|hardware OUTPUT FONT_DIRECTORY FRAMES BITRATE".into()); }
    let mode = args[1].as_str();
    if mode != "raw" && mode != "hardware" && mode != "raw-hardware" { return Err("unknown mode".into()); }
    let frames: usize = args[4].parse()?;
    if frames == 0 || frames > 300 { return Err("frame count must be 1..300".into()); }
    let bitrate: i64 = args[5].parse()?;
    if bitrate < 100_000 || bitrate > 200_000_000 { return Err("bitrate out of range".into()); }
    let started = Instant::now();
    let folder = MediaDirectory::read_folder(&args[3])?;
    let media = folder.process_media_source()?;
    let video = Grid;
    let device = fframes_skia_renderer::metal::metal_rs::Device::system_default().ok_or("no Metal device")?;
    let device_name = device.name().to_owned();
    let queue = device.new_command_queue();
    let ctx = fframes_skia_renderer::metal::SkiaMetalCtx::new_with_device(device, queue, 3840, 2160)?;
    let config = SkiaPipelineConfig {
        concurrency_policy: SkiaPipelineConcurrencyPolicy::MaxPerformance,
        cache: CACHE, ..Default::default()
    };
    let backend = SkiaFFramesRenderer::new(config, &ctx);
    let codec_params = [("allow_sw", "0"), ("threads", "1"), ("bf", "0")];
    let options = RenderOptions {
        media: Some(&media), load_system_fonts: false, default_font: "DM Sans",
        logger: FFramesLoggerVariant::Silent, frame_range: Some(WARMUP..WARMUP+frames),
        video_encoder_options: EncoderOptions {
            preferred_encoder: Some("h264_videotoolbox"), codec_params: Some(&codec_params),
            bitrate: Some(bitrate), gop_size: 30, qmin: 0, qmax: 69, ..Default::default()
        }, ..Default::default()
    };
    if mode == "raw" {
        let mut preview = Previewer::new(&video, &options)?;
        let mut renderer = backend.frame_renderer().ok_or("no GPU frame renderer")?;
        let mut stdout = std::io::stdout().lock();
        for index in 0..frames {
            let frame = preview.render(WARMUP+index, &mut renderer)?;
            if frame.width != 3840 || frame.height != 2160 || frame.pixels.len() != 3840*2160*4 { return Err("bad raw geometry".into()); }
            stdout.write_all(&frame.pixels)?;
        }
        stdout.flush()?;
        eprintln!("{}", serde_json::json!({"mode":"raw", "frames":frames, "device":device_name,
            "rasterizer":"skia-metal", "explicitRawReadbackBytes":frames*3840*2160*4,
            "renderingMs":started.elapsed().as_secs_f64()*1000., "zeroCopyProved":false}));
    } else {
        let out = Path::new(&args[2]);
        if let Some(parent) = out.parent() { std::fs::create_dir_all(parent)?; }
        let info = VideoEncoderInfo::for_output(out, (3840,2160,30), &options.video_encoder_options).map_err(|e| std::io::Error::other(format!("{e:?}")))?;
        if info.name() != "h264_videotoolbox" { return Err("required VideoToolbox encoder unavailable".into()); }
        let input = backend.negotiate_encoder_input(&info).map_err(|e| std::io::Error::other(format!("{e:?}")))?;
        if !input.is_hardware() { return Err("required hardware-frame interop unavailable".into()); }
        let renderer = SkiaEncoderFrameRenderer::new(&ctx, SkiaFrameExport::Auto, &input,3840,2160)?;
        if renderer.path() != FrameExportPath::HardwareFrames { return Err("hardware frame negotiation mismatch".into()); }
        drop(renderer);
        if mode == "raw-hardware" {
            let mut preview = Previewer::new(&video, &options)?;
            let mut renderer = SkiaEncoderFrameRenderer::new(&ctx, SkiaFrameExport::Auto, &input,3840,2160)?;
            let mut stdout = std::io::stdout().lock();
            for index in 0..frames {
                let tree = preview.svg_tree(WARMUP+index)?;
                let frame = renderer.render_tree(&tree, Grid::BACKGROUND_COLOR)?;
                let downloaded = frame.download().map_err(|e| std::io::Error::other(format!("{e:?}")))?;
                let raw = unsafe { &*downloaded.as_ptr() };
                if raw.format != fframes::ffmpeg_sys_fframes::AVPixelFormat::AV_PIX_FMT_BGRA as i32 || raw.width != 3840 || raw.height != 2160 || raw.linesize[0] < 3840*4 { return Err("hardware reference download has unexpected format".into()); }
                for y in 0..2160 {
                    let row = unsafe { std::slice::from_raw_parts(raw.data[0].offset((y*raw.linesize[0]) as isize),3840*4) };
                    stdout.write_all(row)?;
                }
            }
            stdout.flush()?;
            eprintln!("{}",serde_json::json!({"mode":"raw-hardware","frames":frames,"source":"actual BGRA hardware frames, explicit reference-only download","zeroCopyProved":false}));
            return Ok(());
        }
        // The comparison diagnostic patch also rejects a fallback in every actual pipeline worker.
        fframes::render(out, &video, backend, &options)?;
        println!("{}", serde_json::json!({"mode":"hardware", "frames":frames, "nodes":NODES,
            "device":device_name, "rasterizer":"skia-metal", "encoder":"h264_videotoolbox",
            "allowSoftwareEncoder":false, "requiredPath":"HardwareFrames", "zeroCopyProved":false,
            "bitrate":bitrate, "gop":30, "colorSemantics":"upstream BT.601 attachments; opaque encoder conversion",
            "pipeline":"MaxPerformance", "renderingMs":started.elapsed().as_secs_f64()*1000.}));
    }
    Ok(())
}
