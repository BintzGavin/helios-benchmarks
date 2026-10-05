# Source-backed GPU target for later reproduction

Inspected pinned upstream `dmtrKovalenko/fframes@f89cbd572524b70a709ba3569fa23b0bbc8a0d9c` through primary source files. This is a separate workload from continuity TextGrid. Do not pool either workload or clocks.

Upstream reported one GPU export of 7.225018333 seconds on Apple M5 Max (18 logical CPUs,128 GiB), using Skia Metal and H.264 VideoToolbox. Its scene is 3840x2160,99,000 overlapping circles plus1,000 changing DM Sans digits in20 panels,300 measured frames at30fps after3 warm-up frames. Target8Mbps,GOP30,4:2:0. Timing excludes build/media prep/browser launch/bundling/warmup and final checks; the export interval includes draw/conversion/encoder setup/encode/drain/mux/write. The current local M3 Pro is a different host. End-to-end delivered clocks including startup/full decode cannot be compared directly with that upstream interval.

Raw provenance records measured fframes renderer commit `04865260b13f66fa5004b472b95877990882de9a`, fframes base `68ef9722d54443d4058cf2d2e051159cfe684b8e`, optimized usvgr `1c2a088217eb3365e965fd8dbd62acf265a07d33` (base `8657f976ce221dcffaf28c2a5de5103e922b30eb`) and individual scene/runner SHA256 values. Source documentation says cleanup changed identifiers/formatting/metadata, not circle math. Reproducing the claim requires this dependency optimization and disclosed source mapping, not merely current main's version label.

The published Remotion FFmpeg measurement used software rasterization plus hardware encode. MediaBunny reported Metal but only requested WebCodecs prefer-hardware. These should not be labeled attested all-GPU comparisons. Upstream discloses equal bitrate targets do not imply equal quality and that results are one run per pipeline. Our same-host repeats/quality qualification remain necessary.

Current source HardwareFrames path passes a Metal-backed BGRA CVPixelBuffer to VideoToolbox, tags BT.601 and uses explicit GPU submit/synchronization. GpuConversion mode reads converted planes back; CpuConversion reads RGBA back. Record the actually negotiated path; Auto is not a zero-copy proof. Compare native Helios's reported BT.709/NV12 path with explicit color handling and disclose necessary differences. Opaque driver/encoder work does not become proved zero-copy just because application readback is absent.

The current fframes Cargo manifest uses upstream skia-safe0.153.3 and backend-specific prebuilt feature combinations, unlike the failed old custom fframes-skia-safe0.91.0 build. A supported current Metal-only build may avoid the old failed dependency combination; verify compatible source/version/ABI and all pipeline quality gates before timed comparison. Do not silently substitute Skia versions in a claimed unmodified-source run.

Primary sources:

- https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/render-bench/vs-remotion/README.md
- https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/render-bench/vs-remotion/measurements/m5-max-4k-circles.json
- https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/render-bench/vs-remotion/src/main.rs
- https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/fframes-skia-renderer/Cargo.toml
- https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/fframes-skia-renderer/src/frame_export/mod.rs
- https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/fframes-skia-renderer/src/frame_export/videotoolbox.rs

## Source provenance qualification

A later exact-source inspection found the recorded renderer04865260b13f66fa5004b472b95877990882de9a checked-in main is an older filtered-rectangle benchmark, not the measured4K circle program. The record includes uncommitted benchmark changes and hashes whose complete source is not available at that commit. Current public f89cbd circle source plus the recorded optimized usvgr revision can support a documented-scene replication, but not an exact measured-source reproduction. The primary old source is https://raw.githubusercontent.com/dmtrKovalenko/fframes/04865260b13f66fa5004b472b95877990882de9a/render-bench/vs-remotion/src/main.rs . The saved GitHub comparison and source hashes remain in checkpoint/fframes-current/claim-renderer-source-comparison.json and comparison/circles-source-pins.json.
