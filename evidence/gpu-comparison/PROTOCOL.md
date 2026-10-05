# Connected-Mac GPU comparison

This protocol keeps the continuity TextGrid comparison separate from the published 4K circle claim. Results are whole recorded pipelines, not isolated GPU throughput.

## Continuity scene and host

TextGrid is 3,334 changing labels, 1,920×1,080, 300 frames at exactly 30/1 fps, ten seconds, no audio, opaque #0b1020 background. The 72,000-byte DM Sans file has SHA-256 `9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5`. Scene equations come from fframes commit `bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b`; native Canvas, current fframes SVG and Remotion DOM use the same labels, positions, RGB values and rounded alpha. Rasterization and font antialiasing can differ; own-reference quality does not prove cross-engine pixel identity.

The host is an Apple M3 Pro with 11 CPU cores, 14 GPU cores and 18 GiB memory, running macOS 26.3. Read-only process samples accompany each export. The machine remains an interactive host; background activity is recorded, not claimed absent.

## Recorded lanes

The software lane uses GPU rasterization followed by explicit raw-frame download and the same FFmpeg 9.0.2/x264 medium CRF11, two encoder threads, GOP90, no B frames or scene-cut keyframes, sRGB→BT.709 limited-range 4:2:0 conversion. Helios uses its serial native Metal helper; fframes uses its serial Metal Previewer adapter. Remotion 4.0.529 uses Chrome 154 ANGLE Metal, PNG/CDP transport and one tab. Its eight-tab warmup failed after browser crashes and an incomplete screenshot; the aborted series is retained and has no timed results. A new one-tab screen and fresh balanced series follow it.

The hardware lane compares actual product encoding paths: Helios Metal→GPU BT.709/NV12→required hardware VideoToolbox H.264 at 100 Mbps; fframes Metal BGRA HardwareFrames→required hardware VideoToolbox H.264 at 180 Mbps with upstream BT.601 attachments and opaque encoder conversion. Every fframes worker rejects CpuConversion/GpuConversion fallback. Both settings pass the same own-reference floors. Color transforms, bitrate, concurrency and encoder internals differ; this lane does not isolate rasterization or establish identical encoder quality. Lower-bitrate failures remain excluded evidence.

## Timing and acceptance

Each series has one excluded warmup per engine and four fresh rounds in forward/reverse/reverse/forward order. Every pair appears in both orders twice. Engines run sequentially. Export time includes adapter process startup, scene/font work, rasterization, transport/conversion, encoding, drain, mux and file write. Delivered time adds exactly one full eight-thread FFmpeg decode. Native public-API verification overhead is not silently substituted for this adapter clock. Full independent cadence and fidelity checks run after the delivery clock.

Every included candidate must fully decode, contain exactly 300 1080p frames with decoded PTS n/30, and pass every-frame SSIM-Y ≥0.995, PSNR-Y ≥40 dB and PSNR-U/V ≥35 dB against its engine's lossless reference. No resize, skipped frames, repeated-reference-frame repair or relaxed floor is allowed. Warmups, screens, profiles and failed attempts do not enter medians. Source/executable/reference/screen hashes are frozen and rechecked before each run.

The corrected Helios hardware reference is bound to all 300 direct GPU NV12 frames by planar MD5 without color arithmetic. Its old reference and qualifications are invalidated, with original videos/clocks retained. The first Remotion reference differed at six decoded frame indices, including an inspected black frame138; it is retained and invalidated. The complete one-tab reference replaces it without changing the original screened candidate. fframes' hardware reference downloads actual BGRA hardware targets solely for lossless-reference generation and converts them explicitly to BT.601 planar YUV.

## Acceleration evidence and boundaries

Native Metal capture, 300-frame external interposition and positive controls demonstrate actual GPU conversion and no observed application raw-frame download in the measured hardware path. Pointer queries, unknown buffer accesses and opaque driver/encoder work remain; `zeroCopyProved=false`. Separate fframes probes observe three Metal downloads for three software frames and actual HardwareFrames in the hardware path; no total zero-copy claim is made. Remotion's separate trace contains real raster/Graphite submissions; capability flags alone are insufficient, and external profiling is not attached to every timed frame.

Frozen native helper SHA-256: `87aec3f3d39db8956490942429e6a865741c04515ad6b98753aaf6599c197a90`. Feature PR5009 and corrected-oracle PR5010 were merged externally. Current fframes engine pin: `f89cbd572524b70a709ba3569fa23b0bbc8a0d9c`, skia-safe0.153.3; the older custom0.91 build failed and is not relabeled or substituted.

Helios HEVC, Vulkan encoder interoperability, Intel/Windows GPU paths, GPU image/video nodes and broad Canvas paths are unsupported here. The original frozen Canvas/Plan envelope cannot represent the separate99k-circle claim. A separate bounded full-circle/GOP extension is build-ready in PR5011, commit ed0cc7575cb4ce2d2e19be943ca5b4e54363ba39, helper4b2b2598a4604be3104e284fec7d5d1cc3368acf1917e3e1e23ce76a1f0ac6ca; its full4K quality and balanced timings remain pending. The 4K M5 Max single-run claim is not beaten by a faster 1080p TextGrid result.

## Separate 4K scene replication

The current public fframes scene is99,000 circles plus1,000 digits,20panels,3840×2160,300frames@30, source frames3..302, nonuniform1000×1000 viewBox scaling, circles before text, pinned DM Sans. Hardware claim cell requests8Mbps/GOP30. A source-only independent scene test checks equations, counts, painter order and source frame offsets. Three-frame hardware smoke exports pass for both engines but are excluded from performance summaries.

The published M5 Max record points to renderer04865260b13f66fa5004b472b95877990882de9a, whose checked-in benchmark is an older filtered rectangle workload. The measured circle main has uncommitted changes not recoverable byte-for-byte from that pin. Our replication uses current public f89cbd572524b70a709ba3569fa23b0bbc8a0d9c scene source with the recorded optimized SVG revision1c2a088217eb3365e965fd8dbd62acf265a07d33. Its lock changes only the three SVG path packages, preserving other dependency versions. It is a documented-scene replication, not an exact measured-source reproduction.
