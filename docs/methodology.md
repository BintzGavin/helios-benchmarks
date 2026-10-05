# Methodology

## Workloads and hosts

TextGrid renders 3,334 labels, pinned DM Sans, 1920×1080, 300 frames at 30/1 fps, no audio. The 4K workload renders 99,000 circles and 1,000 digits over 20 panels, 3840×2160, source indices 3–302, 300 output frames at 30/1 fps. Small native backend qualification uses 256×128, 300 frames at 30000/1001 fps. These are distinct workloads.

M3 Pro macOS arm64 local measurements are separate from the Linux x86_64 Amp a1.small Orb (Intel Xeon 2.60GHz, one physical core, two SMT threads, 3 GiB workload memory cap, Debian 12). Never compare their wall times as a host-normalized engine result. Exact versions, host receipts, source archives and compiled-module hashes are retained for every study.

## CPU holdouts

Select local settings only from eligible resource screens, then run a fresh holdout. One excluded warmup per engine/preset; three timed rounds in H/F/R, F/R/H, R/H/F order. Processes are fresh and engines run sequentially. Frozen source/runtime/reference hashes precede the holdout. Retain every clock and failed screen.

Local medium settings: H 4 workers × 4 encoder threads; F 11 × 2; R JPEG100, 11 browser workers and 8 final encoder threads. Local ultrafast: H 8 × 2; F 11 × 2; R JPEG100, 11 browser workers and 8 final encoder threads. Browser workers and encoder concurrency are different quantities. Linux settings are adapted to its two logical CPUs: H/F up to two one-thread encoders, R one one-thread final encoder. Neither frozen configuration proves a universal optimum.

CPU uses software x264 CRF11 and matched preset/codec fields where recorded. GPU-free means measured software compositor/rasterizer/encoder admission. Chromium may retain a software GPU process/SwiftShader; the process name alone does not establish physical GPU use. Reference rasterizers differ: native Canvas, native SVG, and browser DOM.

## Clocks

CPU delivered wall time includes startup, rendering, encoding, drain/stitch/write, required fframes ultrafast edit-list repair, and one complete final decode. Preserve original nanosecond durations. Component receipts expose their boundaries. The Linux compact receipts preserve durations but not absolute monotonic start/end counters.

GPU **export** includes fresh adapter startup, scene/font setup, raster, transfer/conversion, encoding, drain, mux and output write. **Delivered** adds the required final decode and supervisor cleanup. Later centered-chroma lanes must also include the entire mandatory conformance parse/probe/identity/copy/hash/fsync/signaling/mux cost. Reference generation, quality analysis, independent invariance checks, warmups and profiling/captures are excluded. Do not reconstruct old clocks around new costs.

Summaries use the median of the eligible timed repetitions, and ratios of medians where stated. Paired decoder studies report paired ratios separately. Screening medians, different bitrate settings, failed-quality runs, warmups and captured profiles are never pooled into a holdout statistic. Original timers remain the authority.

## Eligibility before performance

Every decoded frame must meet SSIM-Y ≥ 0.995 and PSNR Y/U/V ≥ 40/35/35 dB against the engine's qualified lossless reference. A good average cannot hide a bad frame. Verify exact decoded frame count, dimensions, PTS/durations, source order, no unexpected audio, required codec/color/range and actual GOP. The reference's Matroska timestamp quantization is explicitly separate from exact candidate cadence.

References are source/runtime bound. Native NV12 references use raw plane SHA-256 and a pure NV12→planar split, with inverse reconstruction and lossless decoded identities. This proves per-engine binding; it does not make different rasterizers pixel-identical. Fixed FFmpeg BGRA conversion proxies are labeled as such and never asserted to be private VideoToolbox precompression surfaces.

## GPU evidence

Require actual physical GPU selection, Skia GPU submissions/completions, GPU color conversion, required VideoToolbox hardware encoding and ordered resource lifetimes. Feature flags or an installed Vulkan library do not qualify a lane. Native pool 3 differs from modified fframes 64 buffers/context, three contexts, five generators, five encoders, queue 10.

Use excluded uncaptured interposers and independent positive controls to test hook coverage. Report hook counts and limitations, actual fences, source/destination identity, callbacks and owner release before reuse. Capture artifacts are separate, and capture-induced locks are not extrapolated into the uncaptured export. CPU geometry/font uploads and compressed-packet CPU output are disclosed. Opaque driver/encoder copies and pointer intent remain unknown: **zeroCopyProved=false**.

## Color conformance and storage

Native equal four-sample 2×2 chroma averaging is physically centered. Historical streams sometimes signal default-left and references unspecified siting. The old numeric results remain scoped to their original artifacts; new aligned lanes require separately frozen conformance and fresh qualification. Codec-specific SPS semantic/remaining-RBSP invariance, PPS/VPS and every non-SPS NAL, every decoded YUV frame, and predetermined independent color controls are required. Correct signaling can alter display interpretation; RGB/display invariance is not claimed.

Resource guards are per stage and per lane, with previously retained outputs consuming free space. Current serial retained-raw gate is 9 GiB incremental; the balanced retained set needs 15 GiB with references already present. The proposed 6 GiB streaming gate is disabled until actual bridge/full resource acceptance. CPU fixture tests do not establish 4K memory or GPU execution. Preserve partial failures and never erase original evidence to make a run fit.
