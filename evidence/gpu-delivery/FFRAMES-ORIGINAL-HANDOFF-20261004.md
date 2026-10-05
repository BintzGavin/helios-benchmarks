The excluded same-stream capture is complete. The original fully enabled fframes MaxPerformance 4K lane still fails the unchanged chroma quality floors. This slice does not establish a production speed winner or complete the broader comparison.

The isolated release adapter captures each original BGRA VideoToolbox hardware frame immediately before its original encoder send. Skia's existing `flush_submit_and_sync_cpu` fence, scheduler, queues, segment writer and encoder settings remain intact. The original AVFrame, CVPixelBuffer and AVBuffer identities stay unchanged through download and encoder return. The capture adds readback, compression, writes and event locks, so its clocks are excluded from timing comparisons.

The actual M3 Pro run started all 3 GPU, 5 generator and 5 encoder workers, retaining the configured 11 encoder-thread policy and queue size 10. All 300 source frames 3–302 were captured from the production pipeline, in five ordered 60-frame segments. Every indexed GPU completion, capture, send, return and AVBuffer final-reference release passed the independent audit. Original codec drains completed. AVBuffer release observations do not reveal opaque VideoToolbox ownership or prove total zero-copy.

The predetermined 36-frame controls contain solid RGB bars, a 2×2 red/cyan checker, one-pixel green/magenta stripes and an indexed gray ramp. Every captured BGRA byte matches the independent Python oracle. Decoded solid interiors agree with nominal BT.601 limited values within one code value. Fine chroma patterns disagree strongly with the fixed FFmpeg proxy; no scaler or matrix was selected to fit those outputs.

For the full scene, the reference uses the retained protocol: exact captured BGRA → `scale=out_color_matrix=bt601:out_range=tv,format=yuv420p` → FFV1. All 300 decoded FFV1 frame hashes match the direct converted stream. This removes the separate-render source ambiguity. It is a lossless **proxy**, not a measurement of VideoToolbox's opaque pre-compression NV12 pixels.

| Full 4K gate | Minimum | Required floor | Failing frames |
| --- | ---: | ---: | ---: |
| SSIM Y | 0.999168 | 0.995 | 0 |
| PSNR Y | 49.00 dB | 40 dB | 0 |
| PSNR U | 33.36 dB | 35 dB | 296 |
| PSNR V | 33.10 dB | 35 dB | 300 |

Both videos fully decode. The full candidate has exactly 300 frames at 3840×2160, exact decoded `n/30` timestamps and `1/30` durations, GOP spacing 30, BT.601 limited metadata and left chroma location. Transfer and primaries remain unspecified as in the original lane. The encoder request is required VideoToolbox H.264, 500 Mbps, GOP 30, with the original hardware frames. The device's ignored qmax warning remains in the raw logs.

Three Rust capture tests, eleven independent audit tests (including ten rejected receipt mutations), and two actual initialization refusal controls pass. The locked release build passes. Clippy completes with retained warnings; a warnings-free lint gate is not claimed. All eleven prior investigation read-set pins and the original production executable remain unchanged, including the failed 8/200/500 Mbps screens and twelve conversion diagnostics.

The remaining original-product gate is the independently specified conversion/chroma oracle: the exact source capture and nominal solid controls place this disagreement downstream of rasterization, but cannot separate reference subsampling choices, opaque VideoToolbox conversion and compression. A concurrent explicit GPU NV12 pipeline could provide a controlled reference; it must be separately frozen, qualified and labeled a modified pipeline. No such replacement or new optimization was implemented in this slice. No timing window is open.

Raw receipts and frozen helpers: [evidence directory](/Users/gavinbintz/Documents/Codex/2026-10-02/task/comparison/fframes-original-handoff-20261004). Exact bindings: [final report](/Users/gavinbintz/Documents/Codex/2026-10-02/task/comparison/fframes-original-handoff-20261004/FINAL-REPORT.json). Reviewable changes: [patch](/Users/gavinbintz/Documents/Codex/2026-10-02/task/comparison/fframes-original-handoff-20261004/capture-adapter.patch). Representative full output: [MP4](/Users/gavinbintz/Documents/Codex/2026-10-02/task/comparison/fframes-original-handoff-20261004/circles300/video.mp4).

Library publication remains blocked by the required helper's unavailable `prepare_uploads` workflow; no replacement container or new Library ID is claimed. Vulkan publication remains pending in the native thread after its automatic approval review rejected an unapproved push destination; this slice did not push or bypass that block. Full 4K HEVC/Vulkan performance qualification and beating the separate M5 Max claim remain incomplete.
