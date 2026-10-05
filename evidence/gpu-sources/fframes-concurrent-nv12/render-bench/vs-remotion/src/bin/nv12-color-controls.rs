//! Excluded predetermined color/chroma controls, original MaxPerformance pipeline.
use fframes::{
    AudioMap, Color, Duration, EncoderOptions, FFramesContext, FFramesLoggerVariant,
    FFramesRenderBackend, Frame, RenderOptions, Svgr, Video, VideoEncoderInfo,
};
use fframes_skia_renderer::{
    SkiaCacheConfig, SkiaFFramesRenderer, SkiaPipelineConcurrencyPolicy, SkiaPipelineConfig,
};
use std::path::Path;
struct Controls;
impl Video for Controls {
    const WIDTH: usize = 256;
    const HEIGHT: usize = 128;
    const FPS: usize = 30;
    const BACKGROUND_COLOR: Color = Color::BLACK;
    fn duration(&self) -> Duration<'_> {
        Duration::Frames(39)
    }
    fn audio(&self) -> AudioMap<'_> {
        AudioMap::none()
    }
    fn render_frame<'a>(&'a self, frame: Frame, _: &FFramesContext<'a, '_>) -> Svgr<'a> {
        let colors = [
            (0, 0, 0),
            (255, 255, 255),
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (0, 255, 255),
            (255, 0, 255),
            (255, 255, 0),
        ];
        let bars: Vec<_> = colors
            .into_iter()
            .enumerate()
            .map(|(i, (r, g, b))| {
                let fill = Color::rgba(r, g, b, 255);
                fframes::svgr!(<rect x={i*32} y="0" width="32" height="32" fill={fill}/>)
            })
            .collect();
        let checks: Vec<_> = (0..2048)
            .map(|i| {
                let x = (i % 128) * 2;
                let y = 32 + (i / 128) * 2;
                let fill = if ((x / 2 + y / 2 + frame.index) % 2) == 0 {
                    Color::rgba(255, 0, 0, 255)
                } else {
                    Color::rgba(0, 255, 255, 255)
                };
                fframes::svgr!(<rect x={x} y={y} width="2" height="2" fill={fill}/>)
            })
            .collect();
        let stripes: Vec<_> = (0..256)
            .map(|x| {
                let fill = if (x + frame.index) % 2 == 0 {
                    Color::rgba(0, 255, 0, 255)
                } else {
                    Color::rgba(255, 0, 255, 255)
                };
                fframes::svgr!(<rect x={x} y="64" width="1" height="32" fill={fill}/>)
            })
            .collect();
        let gray: Vec<_> = (0..256)
            .map(|x| {
                let g = ((x + frame.index) % 256) as u8;
                let fill = Color::rgba(g, g, g, 255);
                fframes::svgr!(<rect x={x} y="96" width="1" height="32" fill={fill}/>)
            })
            .collect();
        fframes::svgr!(<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 128" width="256" height="128">{bars}{checks}{stripes}{gray}</svg>)
    }
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 3 && args.len() != 4 {
        return Err("usage: handoff-color-controls OUTPUT CAPTURE_DIRECTORY".into());
    }
    if std::env::var_os("FFRAMES_EXPLICIT_NV12").is_none() {
        return Err("explicit NV12 required".into());
    }
    let frames: usize = if args.len() == 4 {
        args[3].parse()?
    } else {
        36
    };
    if !(1..=36).contains(&frames) {
        return Err("control frame bound".into());
    }
    let out = Path::new(&args[1]);
    let capture = Path::new(&args[2]);
    if std::env::var_os("FFRAMES_HANDOFF_CAPTURE").as_deref() != Some(capture.as_os_str()) {
        return Err("capture env and argument must agree".into());
    }
    fframes::diagnostic_capture::initialize(capture, frames, 3, 256, 128)
        .map_err(|e| format!("{e:?}"))?;
    let device = fframes_skia_renderer::metal::metal_rs::Device::system_default()
        .ok_or("no Metal device")?;
    let ctx = fframes_skia_renderer::metal::SkiaMetalCtx::new_with_device(
        device.clone(),
        device.new_command_queue(),
        256,
        128,
    )?;
    let backend = SkiaFFramesRenderer::new(
        SkiaPipelineConfig {
            concurrency_policy: SkiaPipelineConcurrencyPolicy::MaxPerformance,
            cache: SkiaCacheConfig {
                text_capacity: 100000,
                geometry_capacity: 100000,
                geometry_bytes: 100000 * 512,
            },
            ..Default::default()
        },
        &ctx,
    );
    let params = [("allow_sw", "0"), ("threads", "1"), ("bf", "0")];
    let options = RenderOptions {
        logger: FFramesLoggerVariant::Silent,
        frame_range: Some(3..3 + frames),
        load_system_fonts: false,
        video_encoder_options: EncoderOptions {
            preferred_encoder: Some("h264_videotoolbox"),
            codec_params: Some(&params),
            bitrate: Some(300000000),
            gop_size: 30,
            qmin: 0,
            qmax: 69,
            ..Default::default()
        },
        ..Default::default()
    };
    let info = VideoEncoderInfo::for_output(out, (256, 128, 30), &options.video_encoder_options)
        .map_err(|e| format!("{e:?}"))?;
    if info.name() != "h264_videotoolbox"
        || !backend
            .negotiate_encoder_input(&info)
            .map_err(|e| format!("{e:?}"))?
            .is_hardware()
    {
        return Err("required hardware unavailable".into());
    }
    if std::env::var_os("FFRAMES_NV12_POOL_TEST").is_some() {
        use fframes_skia_renderer::metal::metal_rs::foreign_types::ForeignType;
        if !unsafe { fframes_nv12_pool_test(device.as_ptr().cast()) } {
            return Err("actual CoreVideo pool lifetime test failed".into());
        }
    }
    fframes::render(out, &Controls, backend, &options)?;
    unsafe { fframes_nv12_profile_finish() };
    fframes::diagnostic_capture::finalize().map_err(|e| format!("{e:?}"))?;
    println!(
        "{}",
        serde_json::json!({"benchmarkTiming":false,"frames":frames,"sourceFrames":[3,38],"pipeline":"modified MaxPerformance explicitGPU NV12","originalProduct":false,"encoder":"h264_videotoolbox","bitrate":300000000,"gop":30,"zeroCopyProved":false})
    );
    Ok(())
}

unsafe extern "C" {
    fn fframes_nv12_profile_finish();
    fn fframes_nv12_pool_test(device: *mut std::ffi::c_void) -> bool;
}
