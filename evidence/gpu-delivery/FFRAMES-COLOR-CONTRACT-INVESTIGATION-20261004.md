# fframes full-performance color/chroma contract review

Ownership remains in the comparison harness. This slice inspected retained source and receipts only: no build, export, decoder run or timing window was started, and no source or frozen output was changed.

The original hardware path negotiates VideoToolbox/BGRA frames, renders into IOSurface-backed BGRA8Unorm, attaches ITU-R BT.601 and sets the encoder stream to limited-range SMPTE170M. Skia synchronously completes GPU work before the frame is handed to the original concurrent, segmented encoder pipeline. The pipeline retains MaxPerformance GPU contexts and bounded generator/render/encoder stages.

The lossless reference separately serial-renders BGRA hardware targets, downloads them and converts them with FFmpeg to limited BT.601 yuv420p/FFV1. It is not a direct byte oracle for the encoder’s opaque pre-compression YUV input and is not captured from the exact concurrently rendered candidate source stream.

The retained 500Mbps candidate passes luma (minimum SSIM-Y .999168, PSNR-Y49.0dB), but minimum U/V PSNR33.36/33.10dB fails the unchanged35dB floors. All twelve retained three-frame FFmpeg filter/location diagnostics also fail. The difference is established; its precise conversion/subsampling/compression cause remains unresolved. A simple BT.601/BT.709 metadata mismatch is not established. No reference fitting, retagging or threshold change is justified.

Next, freeze an excluded diagnostic slice that captures the actual same-stream hardware target at encoder handoff, indexed by source frame/segment, while preserving the original concurrency, GPU completion and buffer lifetime. Independently predetermined color/chroma controls should distinguish source variation and reference semantics. Capture overhead must never enter performance timings. If VideoToolbox’s opaque preprocessing cannot be bound, retain the limitation. Any explicit GPU NV12 conversion belongs to a separately labeled modified pipeline that preserves production concurrency; it cannot be represented as the unchanged upstream product path.

Before timing, all300 frames of the intended4K scenes must pass the unchanged reference, quality, cadence and color gates. New Metal HEVC and MoltenVK/VideoToolbox paths currently qualify only256x128 fixtures. The existing three-frame recorder profile measures CPU preparation only and cannot choose another GPU/export optimization.

The adjacent JSON contains exact read/write sets, SHA-256 evidence pins, source locations, diagnostic minima and acceptance requirements. No implementation handoff has been made and no timing window is open.
