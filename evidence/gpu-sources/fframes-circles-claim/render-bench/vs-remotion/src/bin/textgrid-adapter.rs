// TextGrid equations from fframes bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b.
// MIT, copyright Dmitriy Kovalenko. Current engine f89cbd572524b70a709ba3569fa23b0bbc8a0d9c.
use std::{io::Write, path::Path, time::Instant};
use fframes::{AudioMap, Color, Duration, EncoderOptions, FFramesContext, Frame,
    MediaDirectory, RenderOptions, Svgr, Video, FFramesLoggerVariant,
    FFramesRenderBackend, Previewer, VideoEncoderInfo, EncoderFrameRenderer};
use fframes_skia_renderer::{SkiaFFramesRenderer, SkiaPipelineConcurrencyPolicy,
    SkiaPipelineConfig, SkiaEncoderFrameRenderer, SkiaFrameExport, FrameExportPath};
const NODES: usize = 3334;
const COLS: usize = 47;
const ROWS: usize = 71;
const CELL_W: f64 = 1920.0 / COLS as f64;
const CELL_H: f64 = 1080.0 / ROWS as f64;

struct TextGrid;

/// Same function as `hslToRgb` in ../remotion/src/TextGrid.tsx.
fn hsl_to_rgb(h: f64, s: f64, l: f64) -> (u8, u8, u8) {
    let c = (1.0 - (2.0 * l - 1.0).abs()) * s;
    let hp = h / 60.0;
    let x = c * (1.0 - ((hp % 2.0) - 1.0).abs());
    let (r, g, b) = if hp < 1.0 {
        (c, x, 0.0)
    } else if hp < 2.0 {
        (x, c, 0.0)
    } else if hp < 3.0 {
        (0.0, c, x)
    } else if hp < 4.0 {
        (0.0, x, c)
    } else if hp < 5.0 {
        (x, 0.0, c)
    } else {
        (c, 0.0, x)
    };
    let m = l - c / 2.0;
    let q = |v: f64| ((v + m) * 255.0).round() as u8;
    (q(r), q(g), q(b))
}

impl Video for TextGrid {
    const FPS: usize = 30;
    const WIDTH: usize = 1920;
    const HEIGHT: usize = 1080;
    const BACKGROUND_COLOR: Color = Color::BLACK;

    fn duration(&self) -> Duration<'_> {
        Duration::Frames(300)
    }

    fn audio(&self) -> AudioMap<'_> {
        AudioMap::none()
    }

    fn render_frame<'a>(&'a self, frame: Frame, _ctx: &FFramesContext<'a, '_>) -> Svgr<'a> {
        let f = frame.index as f64;
        let fi = frame.index;
        let mut nodes: Vec<Svgr> = Vec::with_capacity(NODES);
        for i in 0..NODES {
            let fl = i as f64;
            let col = (i % COLS) as f64;
            let row = (i / COLS) as f64;
            let x = col * CELL_W + 2.0 + 4.0 * (f * 0.12 + fl * 0.37).sin();
            let y = row * CELL_H + 11.0 + 3.0 * (f * 0.09 + fl * 0.23).cos();
            let alpha = 0.3 + 0.7 * (0.5 + 0.5 * (f * 0.2 + fl * 0.05).sin());
            let (r, g, b) = hsl_to_rgb((fl * 0.9 + f * 4.0) % 360.0, 0.75, 0.62);
            let label = if (i + fi).is_multiple_of(9) {
                "fframes".to_string()
            } else {
                ((fi * 37 + i * 101) % 10000).to_string()
            };
            nodes.push(fframes::svgr!(
                <text x={x} y={y} font-family="DM Sans" font-size="10"
                    fill={format!("#{r:02x}{g:02x}{b:02x}")} fill-opacity={format!("{alpha:.3}")}>
                    {label}
                </text>
            ));
        }

        fframes::svgr!(
            <svg xmlns="http://www.w3.org/2000/svg" width={Self::WIDTH} height={Self::HEIGHT}>
                <rect width={Self::WIDTH} height={Self::HEIGHT} fill="#0b1020" />
                {nodes}
            </svg>
        )
    }
}

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
    let video = TextGrid;
    let device = fframes_skia_renderer::metal::metal_rs::Device::system_default().ok_or("no Metal device")?;
    let device_name = device.name().to_owned();
    let queue = device.new_command_queue();
    let ctx = fframes_skia_renderer::metal::SkiaMetalCtx::new_with_device(device, queue, 1920, 1080)?;
    let config = SkiaPipelineConfig {
        concurrency_policy: SkiaPipelineConcurrencyPolicy::MaxPerformance,
        ..Default::default()
    };
    let backend = SkiaFFramesRenderer::new(config, &ctx);
    let codec_params = [("allow_sw", "0"), ("threads", "1"), ("bf", "0")];
    let options = RenderOptions {
        media: Some(&media), load_system_fonts: false, default_font: "DM Sans",
        logger: FFramesLoggerVariant::Silent, frame_range: Some(0..frames),
        video_encoder_options: EncoderOptions {
            preferred_encoder: Some("h264_videotoolbox"), codec_params: Some(&codec_params),
            bitrate: Some(bitrate), gop_size: 90, ..Default::default()
        }, ..Default::default()
    };
    if mode == "raw" {
        let mut preview = Previewer::new(&video, &options)?;
        let mut renderer = backend.frame_renderer().ok_or("no GPU frame renderer")?;
        let mut stdout = std::io::stdout().lock();
        for index in 0..frames {
            let frame = preview.render(index, &mut renderer)?;
            if frame.width != 1920 || frame.height != 1080 || frame.pixels.len() != 1920*1080*4 { return Err("bad raw geometry".into()); }
            stdout.write_all(&frame.pixels)?;
        }
        stdout.flush()?;
        eprintln!("{}", serde_json::json!({"mode":"raw", "frames":frames, "device":device_name,
            "rasterizer":"skia-metal", "explicitRawReadbackBytes":frames*1920*1080*4,
            "renderingMs":started.elapsed().as_secs_f64()*1000., "zeroCopyProved":false}));
    } else {
        let out = Path::new(&args[2]);
        if let Some(parent) = out.parent() { std::fs::create_dir_all(parent)?; }
        let info = VideoEncoderInfo::for_output(out, (1920,1080,30), &options.video_encoder_options).map_err(|e| std::io::Error::other(format!("{e:?}")))?;
        if info.name() != "h264_videotoolbox" { return Err("required VideoToolbox encoder unavailable".into()); }
        let input = backend.negotiate_encoder_input(&info).map_err(|e| std::io::Error::other(format!("{e:?}")))?;
        if !input.is_hardware() { return Err("required hardware-frame interop unavailable".into()); }
        let renderer = SkiaEncoderFrameRenderer::new(&ctx, SkiaFrameExport::Auto, &input,1920,1080)?;
        if renderer.path() != FrameExportPath::HardwareFrames { return Err("hardware frame negotiation mismatch".into()); }
        drop(renderer);
        if mode == "raw-hardware" {
            let mut preview = Previewer::new(&video, &options)?;
            let mut renderer = SkiaEncoderFrameRenderer::new(&ctx, SkiaFrameExport::Auto, &input,1920,1080)?;
            let mut stdout = std::io::stdout().lock();
            for index in 0..frames {
                let tree = preview.svg_tree(index)?;
                let frame = renderer.render_tree(&tree, Color::BLACK)?;
                let downloaded = frame.download().map_err(|e| std::io::Error::other(format!("{e:?}")))?;
                let raw = unsafe { &*downloaded.as_ptr() };
                if raw.format != fframes::ffmpeg_sys_fframes::AVPixelFormat::AV_PIX_FMT_BGRA as i32 || raw.width != 1920 || raw.height != 1080 || raw.linesize[0] < 1920*4 { return Err("hardware reference download has unexpected format".into()); }
                for y in 0..1080 {
                    let row = unsafe { std::slice::from_raw_parts(raw.data[0].offset((y*raw.linesize[0]) as isize),1920*4) };
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
            "bitrate":bitrate, "gop":90, "colorSemantics":"upstream BT.601 attachments; opaque encoder conversion",
            "pipeline":"MaxPerformance", "renderingMs":started.elapsed().as_secs_f64()*1000.}));
    }
    Ok(())
}
