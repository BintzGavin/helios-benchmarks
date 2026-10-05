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



use std::ffi::{c_void, CString};
use fframes::{MediaDirectory, Previewer, VideoEncoderInfo, EncoderFrameRenderer};
use fframes_skia_renderer::{SkiaEncoderFrameRenderer, SkiaFrameExport, FrameExportPath};
unsafe extern "C" {
 fn helios_create(w:u32,h:u32,num:u32,den:u32,bitrate:u32,gop:u32,pool:u32,path:*const i8,hardware:bool,trace:*const i8,capture:*const i8)->*mut c_void;
 fn comparison_import_bgra(state:*mut c_void,input:*mut c_void,index:u32)->bool;
 fn helios_raster_submitted(state:*mut c_void,index:u32);
 fn helios_encode(state:*mut c_void,index:u32)->bool;
 fn helios_reference(state:*mut c_void,index:u32)->bool;
 fn helios_finish(state:*mut c_void,count:u32)->bool;
 fn helios_close(state:*mut c_void)->bool;
}
struct Converter(*mut c_void);
impl Drop for Converter { fn drop(&mut self) {unsafe{helios_close(self.0);}} }
fn main()->Result<(),Box<dyn std::error::Error>> {
 let args:Vec<_>=std::env::args().collect();
 if args.len()!=6 {return Err("usage: circles-common-gpu-adapter hardware|reference OUTPUT FONT_DIRECTORY FRAMES BITRATE".into());}
 let reference=match args[1].as_str(){"reference"=>true,"hardware"=>false,_=>return Err("unknown mode".into())};
 let frames:u32=args[4].parse()?;let bitrate:u32=args[5].parse()?;
 if !(1..=300).contains(&frames)||!(100_000..=1_000_000_000).contains(&bitrate){return Err("frame count/bitrate outside bounds".into());}
 let started=Instant::now();let folder=MediaDirectory::read_folder(&args[3])?;let media=folder.process_media_source()?;let video=Grid;
 let device=fframes_skia_renderer::metal::metal_rs::Device::system_default().ok_or("noMetaldevice")?;let device_name=device.name().to_owned();
 if device_name!="Apple M3 Pro" {return Err("comparison expected physicalAppleM3Pro".into());}
 let queue=device.new_command_queue();let ctx=fframes_skia_renderer::metal::SkiaMetalCtx::new_with_device(device,queue,3840,2160)?;
 let backend=SkiaFFramesRenderer::new(SkiaPipelineConfig{concurrency_policy:SkiaPipelineConcurrencyPolicy::MaxPerformance,cache:CACHE,..Default::default()},&ctx);
 let codec_params=[("allow_sw","0"),("threads","1"),("bf","0")];
 let options=RenderOptions{media:Some(&media),load_system_fonts:false,default_font:"DM Sans",logger:FFramesLoggerVariant::Silent,frame_range:Some(WARMUP..WARMUP+frames as usize),video_encoder_options:EncoderOptions{preferred_encoder:Some("h264_videotoolbox"),codec_params:Some(&codec_params),bitrate:Some(i64::from(bitrate)),gop_size:30,qmin:0,qmax:69,..Default::default()},..Default::default()};
 let output=Path::new(&args[2]);if let Some(p)=output.parent(){std::fs::create_dir_all(p)?;}
 let probe=VideoEncoderInfo::for_output(output,(3840,2160,30),&options.video_encoder_options).map_err(|e|std::io::Error::other(format!("{e:?}")))?;
 let input=backend.negotiate_encoder_input(&probe).map_err(|e|std::io::Error::other(format!("{e:?}")))?;
 if probe.name()!="h264_videotoolbox"||!input.is_hardware(){return Err("requiredhardwareinputunavailable".into());}
 let mut renderer=SkiaEncoderFrameRenderer::new(&ctx,SkiaFrameExport::Auto,&input,3840,2160)?;
 if renderer.path()!=FrameExportPath::HardwareFrames {return Err("FHardwareFrames required".into());}
 let elementary=output.with_extension("h264");let path=CString::new(if reference{String::new()}else{elementary.to_string_lossy().into_owned()})?;
 let trace=CString::new(output.with_extension("transfer.jsonl").to_string_lossy().as_bytes())?;
 let capture=CString::new(std::env::var("COMPARISON_METAL_CAPTURE").unwrap_or_default())?;
 let raw=unsafe{helios_create(3840,2160,30,1,bitrate,30,3,path.as_ptr(),true,trace.as_ptr(),capture.as_ptr())};
 if raw.is_null(){return Err("requiredcommonMetal/VT initialization failed".into());}let converter=Converter(raw);
 let mut preview=Previewer::new(&video,&options)?;
 for index in 0..frames {
  let tree=preview.svg_tree(WARMUP+index as usize)?;let frame=renderer.render_tree(&tree,Grid::BACKGROUND_COLOR)?;
  if frame.width()!=3840||frame.height()!=2160||frame.pixel_format()!=fframes::ffmpeg_sys_fframes::AVPixelFormat::AV_PIX_FMT_VIDEOTOOLBOX {return Err("sourcehardwareformatmismatch".into());}
  let pixel_buffer=unsafe{(*frame.as_ptr()).data[3].cast::<c_void>()};
  if pixel_buffer.is_null(){return Err("missingCVPixelBuffer".into());}
  // finish_frame flush_submit_and_sync_cpu completes fframes GPU writes. Keep
  // VideoFrame alive through import wait; compressed-output pool owns its buffers.
  unsafe{helios_raster_submitted(converter.0,index);}
  if !unsafe{comparison_import_bgra(converter.0,pixel_buffer,index)}{return Err("GPU BGRAimport failed".into());}
  let ok=unsafe{if reference{helios_reference(converter.0,index)}else{helios_encode(converter.0,index)}};
  if !ok{return Err("common GPUconvert/encode failed".into());}
 }
 if !reference&&!unsafe{helios_finish(converter.0,frames)}{return Err("ordered fullencoder drain failed".into());}
 let receipt=serde_json::json!({"mode":if reference{"reference"}else{"hardware"},"frames":frames,"sourceFrames":[3,frames+2],"device":device_name,"rasterizer":"fframesSkia0.153.3MetalHardwareFrames","converter":"taskcommonGPU BGRAcopy + explicitBT709NV12","encoder":if reference{"none"}else{"requiredVideoToolboxH264"},"pool":3,"gop":30,"bitrate":bitrate,"serialRenderer":true,"extraGpuTextureCopy":true,"explicitRawReadbackBytes":if reference{u64::from(frames)*3840*2160*3/2}else{0},"zeroCopyProved":false,"elementary":elementary,"renderingMs":started.elapsed().as_secs_f64()*1000.});
 if reference{eprintln!("{receipt}");}else{println!("{receipt}");}Ok(())
}
