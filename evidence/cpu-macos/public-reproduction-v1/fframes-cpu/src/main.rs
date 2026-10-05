use std::time::Instant;
use std::io::Write;
use fframes::{AudioMap, Color, Duration, EncoderOptions, FFramesContext, Frame, MediaDirectory, RenderOptions, Svgr, Video, fframes_logger::FFramesLoggerVariant};
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

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let output = args.get(1).expect("output path required");
    let preset = args.get(2).map(String::as_str).unwrap_or("medium");
    let crf = args.get(3).map(String::as_str).unwrap_or("18");
    let workers = args.get(4).map(|value| value.parse::<usize>().unwrap()).unwrap_or_else(|| std::thread::available_parallelism().unwrap().get());
    let encoder_threads = args.get(5).map(String::as_str).unwrap_or("0");
    let started = Instant::now();
    let media_dir = MediaDirectory::read_folder(args.get(6).expect("explicit media directory argument required")).unwrap();
    let media = media_dir.process_media_source().unwrap();
    let options = RenderOptions {
        media: Some(&media), load_system_fonts: false, default_font: "DM Sans", logger: FFramesLoggerVariant::Compact,
        video_encoder_options: EncoderOptions { preferred_encoder: Some("libx264"), codec_params: Some(&[("crf", crf), ("preset", preset), ("threads", encoder_threads)]), ..Default::default() }, ..Default::default()
    };
    let backend = fframes::cpu::CpuRenderingBackend { cache_capacity: 20, text_cache_capacity: 10, concurrency: workers };
    if output == "--raw-yuv" {
        let width = TextGrid::WIDTH;
        let height = TextGrid::HEIGHT;
        let area = width * height;
        // Upstream's scalar converter creates slices with padding beyond the
        // visible planes. Allocate that padding even on the SIMD platform.
        let padded = area + width;
        let mut y = vec![0u8; padded];
        let mut u = vec![0u8; padded / 2];
        let mut v = vec![0u8; padded / 2];
        let mut stdout = std::io::stdout().lock();
        for index in 0..300 {
            let rgba = fframes::render_frame(index, &TextGrid, backend, &options).expect("raw frame failed");
            unsafe { fframes::pix_fmt::fill_yuv420_from_rgba_pixmap_accelerated(width as i32, height as i32, width as i32, (width / 2) as i32, (width / 2) as i32, &rgba, y.as_mut_ptr(), u.as_mut_ptr(), v.as_mut_ptr()); }
            stdout.write_all(&y[..area]).unwrap();
            stdout.write_all(&u[..area / 4]).unwrap();
            stdout.write_all(&v[..area / 4]).unwrap();
        }
        return;
    }
    fframes::render(output, &TextGrid, backend, &options).expect("render failed");
    eprintln!("renderSeconds={:.6}", started.elapsed().as_secs_f64());
}
