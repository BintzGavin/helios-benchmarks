# fframes GPU benchmark source report

Verified October 2, 2026. Source inspection only; no GPU measurement was run here.

## Recommended comparison

Preserve the TextGrid workload and fframes revision used by the CPU study:
`bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b`.

This ready upstream lane compares fframes GPU rasterization with CPU rasterization using the same software libx264 encoder, CRF 18 and medium preset. Its existing commands do not select hardware HEVC encoding. The current full-hardware pipeline is a separate future lane and is not ready to run TextGrid without implementation and hardware validation.

## Original TextGrid workload

- 1920 x 1080 pixels, 30 fps, 300 frames, 10 seconds, no audio
- 3,334 changing text nodes per frame, 47 columns by 71 rows
- Scene background `#0b1020`; video background is black but a full-size background rectangle covers it
- Font family `DM Sans`, regular weight, 10 px
- Remotion uses absolutely positioned spans, line-height 1, and baseline adjustment `0.841 * 10` pixels
- fframes uses SVG text; the position, opacity, HSL-to-RGB conversion and label equations are matched
- The implementations have renderer-specific glyph rasterization differences, so they are not expected to produce byte-identical images

Sources:
- [fframes scene and binary](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/render-bench/vs-remotion/fframes/src/main.rs)
- [Remotion scene](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/render-bench/vs-remotion/remotion/src/TextGrid.tsx)
- [Remotion composition](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/render-bench/vs-remotion/remotion/src/Root.tsx)

## Font asset

`DM-Sans.ttf` in this package is the original 72,000-byte font, with SHA-256:
`9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5`.

Both original paths were independently fetched and verified byte-identical:
- `render-bench/vs-remotion/fframes/media/DMSans-Regular.ttf`
- `render-bench/vs-remotion/remotion/public/DMSans-Regular.ttf`

The files have Git blob SHA `cad73f073f3f34ac72a31f79166a5a916e8519b6`.
Font version is 1.200. The original embedded metadata identifies SIL OFL 1.1.
Keep `DM-Sans-OFL.txt` and `DM-Sans-NOTICE.txt` with the font. The notice preserves the exact embedded copyright and documents the upstream license source.

## fframes build and commands

From the pinned repository root:

```sh
cargo build --release -p vs-remotion-bench

# CPU renderer, software libx264 encoder
target/release/vs-remotion-bench cpu out/fframes-cpu.mp4 medium

# Vulkan renderer, software libx264 encoder
GPU_CONTEXTS=2 target/release/vs-remotion-bench vulkan out/fframes-vulkan.mp4 medium

# macOS Metal renderer, software libx264 encoder
GPU_CONTEXTS=2 DYLD_LIBRARY_PATH=/opt/homebrew/lib \
  target/release/vs-remotion-bench metal out/fframes-metal.mp4 medium
```

The crate is at `render-bench/vs-remotion/fframes/Cargo.toml`. It uses the workspace's fframes and Skia dependencies. Building requires the normal repository Rust, FFmpeg and Skia build prerequisites; the source README specifically mentions LIBCLANG_PATH/CLANG_PATH when Skia builds from source.

The positional arguments are backend, output file and x264 preset. Backend is cpu, vulkan, or metal on macOS. The default backend is metal, so always pass it explicitly. The preset defaults to medium; ultrafast is the documented secondary test. `GPU_CONTEXTS` defaults to 1 and maps to `SkiaPipelineConcurrencyPolicy::Concurrency(n)`.

All paths hardcode `preferred_encoder: Some("libx264")` and codec parameters `crf=18` and the requested preset. There is no HEVC command-line option.

[Source crate](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/render-bench/vs-remotion/fframes/Cargo.toml)

## Remotion adapter and commands

The source pins Remotion 4.0.529, React 19.2.0 and TypeScript 5.9.3 and includes package-lock.json.

From `render-bench/vs-remotion/remotion`:

```sh
npm ci
npx remotion browser ensure
npx remotion bundle src/index.ts --out-dir build

# Warm-up, excluded from repeated measurements
npx remotion render build TextGrid ../out/remotion-warmup.mp4 \
  --codec=h264 --overwrite --concurrency=8

# Timed, prebundled medium lane
node_modules/.bin/remotion render build TextGrid ../out/remotion.mp4 \
  --codec=h264 --overwrite --concurrency=8

# Optional secondary lane
node_modules/.bin/remotion render build TextGrid ../out/remotion-ultrafast.mp4 \
  --codec=h264 --overwrite --concurrency=8 --x264-preset=ultrafast
```

The original comparison also swept concurrency 12 and 16. The prebundled command excludes bundling while including Chrome startup, rendering, encoding and muxing. Default H.264 settings in this pinned benchmark are libx264, CRF 18 and medium preset. The published Remotion output uses yuvj420p from JPEG frames, versus fframes yuv420p; retain and report that difference unless intentionally changing the experiment.

The upstream adapter does not force or verify Chrome GPU rasterization. Do not label a Remotion run GPU-accelerated based on these flags alone.

[Package versions](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/render-bench/vs-remotion/remotion/package.json)
[Original run script](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/render-bench/vs-remotion/run.sh)

## Required validity gates

1. Reject software Vulkan. The old `SkiaVulkanCtx::new` selects the first enumerated physical device without checking device type. A Vulkan loader or successful lavapipe render does not establish hardware GPU execution. The orchestrator must verify the actual selected device, or use an explicitly verified hardware-only device configuration.
2. Verify libx264 is the actual encoder. The old core can warn and fall back when a preferred encoder is unavailable; parse logs and output metadata rather than trusting only the requested string.
3. Decode/probe every output after timing. Require 1920 x 1080, 30 fps, 300 decoded frames, expected codec, no audio and correct duration. The old README reports 299-frame CPU outputs in its published experiment, so frame-count validation is mandatory even if the particular checkout has subsequently repaired that behavior.
4. Match source revisions, fonts and workload; record GPU/driver, CPU limits, encoder versions, browser version, thread/concurrency settings, process return code and full logs.
5. Keep warm-up and compilation outside the timed interval. Use interleaved repeated runs and report every run plus median.
6. Validate sampled frame content and quality. Equal CRF or equal bitrate does not imply identical quality across different encoders.
7. Do not run the original shell benchmark unchanged on Linux: it uses macOS sysctl and unconditional Metal runs.

[Old Vulkan device selection](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/fframes-skia-renderer/src/backends/vulkan.rs#L76)
[Old encoder fallback](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/fframes/src/renderer/stream.rs#L141)
[Published benchmark limitations](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/render-bench/vs-remotion/README.md)

## Separate current full-hardware path

Current main inspected: `f89cbd572524b70a709ba3569fa23b0bbc8a0d9c`, October 2, 2026, 20:41:02 UTC.

This commit has APIs absent from the old TextGrid core:

- Metal: fframes feature `videotoolbox`, Skia feature `metal`, `SkiaMetalCtx::new(W,H)`, `SkiaFFramesRenderer::new_metal(&ctx, config)`, encoder `hevc_videotoolbox`
- Vulkan: Skia feature `vulkan-video`, `SkiaVulkanCtx::new_shared_with_encoder(W,H)`, `new_vulkan(&ctx, config)`, encoder `hevc_vulkan`; requires FFmpeg Vulkan 1.3 and driver Vulkan Video encoding
- Set `EncoderOptions.preferred_encoder` explicitly; keep yuv420p/default or NV12 and `SkiaFrameExport::Auto`
- VideoToolbox `allow_sw=0` disallows software encoder fallback
- Verify `VideoEncoderInfo::for_output(...).name() == requested` and `backend.negotiate_encoder_input(&info)?.is_hardware()`
- Log the actual frame-export path. Auto may choose HardwareFrames, GpuConversion or CpuConversion. A requested encoder name alone is insufficient

The upstream Vulkan test shows the exact hardware gate:
https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/fframes-skia-renderer/tests/frame_export.rs#L258

Current frame-export behavior:
https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/fframes-skia-renderer/src/frame_export/mod.rs

This is a source-verified implementation route, not a completed TextGrid adapter or a measured result.

## Current upstream circles benchmark

At current main, `./render-bench/vs-remotion/run.sh --out DIR` is an entirely different fixed experiment: 3840 x 2160, 99,000 circles plus 1,000 digits, 300 measured frames after three warm-up frames, H.264 at 8 Mbps target and GOP 30.

It compares CPU, Skia GPU, Remotion renderMedia and MediaBunny. GPU runs are explicitly skipped if hardware is unavailable. macOS GPU uses h264_videotoolbox; Linux GPU still uses libx264. It has no TextGrid, 1080p or HEVC option.

[Current benchmark README](https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/render-bench/vs-remotion/README.md)
[Current benchmark source](https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/render-bench/vs-remotion/src/main.rs)

