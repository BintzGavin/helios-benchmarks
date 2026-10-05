"""Adapt the pinned original TextGrid scene to current fframes; retain originals."""
import pathlib
root = pathlib.Path(__file__).resolve().parent.parent
old = (root/'sources/fframes/render-bench/vs-remotion/fframes/src/main.rs').read_text()
scene = old[old.index('const NODES:'):old.index('\nfn main()')]
prefix = '''// TextGrid equations from fframes bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b.
// MIT, copyright Dmitriy Kovalenko. Current engine f89cbd572524b70a709ba3569fa23b0bbc8a0d9c.
use std::{io::Write, path::Path, time::Instant};
use fframes::{AudioMap, Color, Duration, EncoderOptions, FFramesContext, Frame,
    MediaDirectory, RenderOptions, Svgr, Video, FFramesLoggerVariant,
    FFramesRenderBackend, Previewer, VideoEncoderInfo};
use fframes_skia_renderer::{SkiaFFramesRenderer, SkiaPipelineConcurrencyPolicy,
    SkiaPipelineConfig, SkiaEncoderFrameRenderer, SkiaFrameExport, FrameExportPath};
'''
suffix = '''
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 6 { return Err("usage: textgrid-adapter raw|hardware OUTPUT FONT_DIRECTORY FRAMES BITRATE".into()); }
    let mode = args[1].as_str();
    if mode != "raw" && mode != "hardware" { return Err("unknown mode".into()); }
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
        let info = VideoEncoderInfo::for_output(out, (1920,1080,30), &options.video_encoder_options)?;
        if info.name() != "h264_videotoolbox" { return Err("required VideoToolbox encoder unavailable".into()); }
        let input = backend.negotiate_encoder_input(&info)?;
        if !input.is_hardware() { return Err("required hardware-frame interop unavailable".into()); }
        let renderer = SkiaEncoderFrameRenderer::new(&ctx, SkiaFrameExport::Auto, &input,1920,1080)?;
        if renderer.path() != FrameExportPath::HardwareFrames { return Err("hardware frame negotiation mismatch".into()); }
        drop(renderer);
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
'''
destination = root/'sources/fframes-current/render-bench/vs-remotion/src/bin/textgrid-adapter.rs'
destination.parent.mkdir(exist_ok=True)
destination.write_text(prefix+scene+suffix)
target = root/'sources/fframes-current/fframes-skia-renderer/src/frame_export/mod.rs'
original = target.read_text()
backup = root/'checkpoint/fframes-current/frame_export.original.rs'
if backup.exists(): raise SystemExit('Refusing to repeat diagnostic mutation')
backup.write_text(original)
needle = '        Ok(Self {\n            target: Some(target),'
replacement = '''        let actual_path = match &target {
            Target::Hardware(_) => FrameExportPath::HardwareFrames,
            Target::Planes { .. } => FrameExportPath::GpuConversion,
            Target::Rgba { .. } => FrameExportPath::CpuConversion,
        };
        if std::env::var_os("COMPARISON_REQUIRE_HARDWARE_FRAMES").is_some() {
            eprintln!("COMPARISON_ACTUAL_EXPORT_PATH={actual_path:?}");
            if actual_path != FrameExportPath::HardwareFrames {
                return Err(FFramesRendererError::Skia("comparison requires hardware frames; fallback refused".to_owned()));
            }
        }

        Ok(Self {
            target: Some(target),'''
if original.count(needle) != 1: raise SystemExit('Diagnostic patch context ambiguous')
target.write_text(original.replace(needle,replacement))
print(destination)
