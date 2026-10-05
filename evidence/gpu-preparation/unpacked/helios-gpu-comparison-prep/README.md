# Helios GPU comparison preparation

Prepared October 2, 2026. **No GPU benchmark result exists in this package.**

## What was verified

The available cloud host has no visible DRM render or NVIDIA device. Tiny actual HEVC encode attempts fail: NVENC cannot load `libcuda.so.1`; Vulkan returns `VK_ERROR_INCOMPATIBLE_DRIVER`. The repeatable `preflight.py` test also fails closed. FFmpeg 7.1.5 lists hardware encoders, but compiled support is not device availability. A browser launch was additionally blocked by the restricted runtime's socket creation; no browser acceleration result is claimed.

An authorized, online physical GPU host is the next required input. The previously tested Apple M3 Pro is the best continuity target. No paid provisioning, deployment, repository push, or persistent account access was performed.

## Two questions, measured separately

1. **GPU rendering with controlled software encoding.** Keep the original 1080p TextGrid scene and software libx264 CRF18/medium. Compare Helios browser Canvas, fframes Skia Metal/Vulkan, and Remotion DOM. Record which stages actually use the GPU. This isolates a broadly comparable raster/capture pipeline while holding the final encoder family/settings constant. It is not perfectly identical rasterization or a pure GPU-kernel microbenchmark.
2. **End-to-end hardware-accelerated product pipelines.** Use current fframes GPU hardware-frame APIs and the corresponding supported Helios/Remotion paths. Match scene, output dimensions/cadence, codec family when genuinely supported, and per-frame quality floors; calibrate bitrate/quality on excluded screening exports. Report bytes too. Do not equate CRF, bitrate, or preset names across codecs. Unsupported architecture/codec cells are “unavailable”, not forced through software. This lane still needs a current-core matched-scene adapter and real hardware testing.

The old TextGrid fframes harness **cannot select hardware HEVC**; it always uses libx264. Current fframes's upstream benchmark instead uses 4K, 99,000 circles plus 1,000 digits. On macOS its GPU benchmark selects H.264 VideoToolbox; Linux currently uses libx264. Neither is automatically the screenshot's HEVC comparison. Details and source links are in `REPORT-FFRAMES.md`.

## Contents and validation status

- `preflight.py`: actual hardware-encoder probes plus physical-device inventory; executed here and blocked, as expected
- `browser_probe.mjs`: CDP GPU/device and WebCodecs capability recorder; syntax checked, full launch blocked here
- `textgrid.mjs`, `textgrid.html`, `DM-Sans.ttf`: pinned 3,334-label scene and exact original font; font hash checked
- `render_helios.mjs`: concrete candidate Helios browser adapter, PNG capture/software x264; syntax checked, full export untested here
- `matrix.template.json`: candidate commands and prerequisites, deliberately not marked ready
- `run_matrix.py`: balanced fresh-process supervisor; dry-run/unit checked, full GPU matrix unexecuted
- `validate_video.py`: exact cadence/full decode/every-frame quality validator; see tests and machine-readable reports
- `evidence/`: environment probes and validation receipts, not performance measurements

The package is a prepared harness and source-grounded run plan, **not an end-to-end reproduced benchmark**. fframes/Remotion release builds, per-engine lossless reference exports, runtime acceleration attestation, and a qualified hardware-encoding adapter remain hardware-stage work. Dependency installations/builds are not silently performed by these scripts.

## Start on the real host

Use existing authorized source checkouts. Pin Helios to `507de4c29b5b4f526cf97bd81ad126762b839685` (renderer 1.79.0), original fframes to `bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b`, Remotion to 4.0.529. Retain lockfiles and compiler/browser/FFmpeg/driver versions. Do not overwrite a dirty checkout. Build/setup happens outside the measured export clock.

```sh
python3 preflight.py --output evidence/host-preflight.json
python3 -m http.server 8765 --bind 127.0.0.1
# Separate terminal, with existing local module/browser paths:
node browser_probe.mjs /PATH/playwright/index.mjs /PATH/Chrome evidence/browser.json http://localhost:8765/textgrid.html
python3 run_matrix.py matrix.template.json > evidence/planned-order.json
```

Physical GPU plus a successful encode smoke is necessary for lane 2, but not sufficient to prove every renderer uses it. Capture the selected Metal/Vulkan device, actual frame-export path and actual encoder in the timed engine. Reject SwiftShader, llvmpipe, lavapipe and software fallback. Old fframes Vulkan selects its first enumerated physical device; a separate machine-wide real-GPU listing does not prove that selection. Browser GPU feature flags/capability checks likewise do not establish actual Canvas2D GPU rasterization. Review per-engine runtime evidence before enabling it.

For the controlled lane, hardware encoding is not required, but a real GPU and attested GPU stage are. Generate each engine's **own** lossless reference through the same rasterizer/font/scene, freeze its hash, qualify all 300 frames, fill local paths in a copy of the matrix, and only then set `ready` and `runtime_attestation_reviewed`. The runner blocks by default rather than manufacturing a comparison.

```sh
python3 run_matrix.py matrix.qualified.json --preflight evidence/host-preflight.json --execute --out outputs/run-001
```

## Fairness and stopping rules

- 1920×1080, 300 frames at 30 fps, no audio, same TextGrid equations, DM Sans bytes and background
- Font SHA-256: `9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5`
- One excluded warmup per engine, then three fresh timed rounds in H/F/R, F/R/H, R/H/F order; no discarded slow attempts
- Screen worker counts/context counts separately, within a disclosed common resource envelope. The template values are starting candidates, not established optimal settings
- Primary delivery clock: fresh export process through one complete final decode check. Capture process-only timing separately. Reference building, hashing and SSIM/PSNR metrics stay outside performance clocks
- Do not pool these runs with old native-CPU results or separate screening studies. Same-host fresh CPU controls can be added as a separate declared lane
- Require exact count, dimensions and rational frame cadence before quality comparison. Every frame must satisfy Y SSIM ≥0.995, Y PSNR ≥40 dB, U/V PSNR ≥35 dB
- Own-rasterizer fidelity is codec/capture fidelity, not cross-engine pixel identity or equal perceptual output. Retain representative visuals for semantic comparison
- Disclose color matrix/range, output pixel format, actual codec/encoder, bitrate/file size, capture losses and hardware path. Before final lane qualification, normalize intended delivery color consistently, verify actual metadata, and record any unavoidable difference
- If any engine cannot meet the scene, quality, cadence or actual hardware-path gate, stop the affected comparison and report the unavailable cell. Do not downgrade to software and retain a GPU label

## Sources

- [Helios CPU baseline protocol](https://github.com/BintzGavin/helios/blob/507de4c29b5b4f526cf97bd81ad126762b839685/docs/rfcs/2026-10-01-cpu-benchmarks.md)
- [Helios renderer API](https://github.com/BintzGavin/helios/blob/507de4c29b5b4f526cf97bd81ad126762b839685/docs/site/api/renderer.md)
- [Original fframes TextGrid GPU harness](https://github.com/dmtrKovalenko/fframes/blob/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/render-bench/vs-remotion/fframes/src/main.rs)
- [Current fframes hardware-frame negotiation tests](https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/fframes-skia-renderer/tests/frame_export.rs)
- [Current upstream comparison](https://github.com/dmtrKovalenko/fframes/blob/f89cbd572524b70a709ba3569fa23b0bbc8a0d9c/render-bench/vs-remotion/README.md)

See `LICENSE.fframes.txt`, `DM-Sans-OFL.txt`, and `DM-Sans-NOTICE.txt` for retained third-party notices. Generated orchestration code is supplied for this user's benchmark preparation.
