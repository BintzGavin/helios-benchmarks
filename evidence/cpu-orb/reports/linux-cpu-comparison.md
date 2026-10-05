# Helios / fframes / Remotion CPU-only Linux comparison

**Result:** complete and eligible. All 24 holdout exports (6 excluded warmups + 18 timed) passed exact cadence and per-frame own-reference quality. No export failed, was retried, dropped, or replaced. This is a new Linux study and is not pooled with the historical M3 Pro study.

## Machine and frozen settings

- One Amp a1.small Orb: Debian 12, Linux 6.1.158+, x86_64 Intel Xeon 2.60 GHz; 1 physical core / 2 SMT logical CPUs; cpuset `0-1`; no cgroup CPU quota; 3 GiB workload memory cap; Node `availableParallelism() = 2`.
- Every profile: 2 workers, 1 x264 thread per active encoder; software x264 CRF11, GOP24, BT.601 limited-range YUV420P. H/F therefore start up to two segment encoders (2 aggregate x264 threads). Remotion has 2 renderer workers but emitted one non-copy stitcher encoder with 1 x264 thread; renderer concurrency is not encoder concurrency. The cpuset limits aggregate CPU service to two logical CPUs regardless of helper threads.
- No timing-based tuning screen was run. The configuration was selected from the measured CPU budget, qualified on one fresh medium export per engine, then frozen before holdout (`manifests/frozen-holdout-settings.json`, SHA-256 `75f78c913f9414c6e8cd090828d24fa469342f4f0383781f7bf1af70a0c6278e`).
- Delivered time is fresh-process startup through drawing/rasterizing, encoding, required F-ultrafast stream-copy edit-list repair, and one final 2-thread full decode. Hashing, SEI inspection, references, cadence, and quality are outside the clock.

## Excluded warmups

| Preset | Engine | Raw ns | Seconds |
|---|---:|---:|---:|
| medium | H | 69710696959 | 69.710696959 |
| medium | F | 92335255667 | 92.335255667 |
| medium | R | 153350877287 | 153.350877287 |
| ultrafast | H | 20533185911 | 20.533185911 |
| ultrafast | F | 39099349173 | 39.099349173 |
| ultrafast | R | 60778124735 | 60.778124735 |

## Timed holdout

| Preset | Round order | Engine | Raw ns | Seconds |
|---|---:|---:|---:|---:|
| medium | 1 H/F/R | H | 69156139448 | 69.156139448 |
| medium | 1 H/F/R | F | 92045448392 | 92.045448392 |
| medium | 1 H/F/R | R | 151413629799 | 151.413629799 |
| medium | 2 F/R/H | F | 91910993266 | 91.910993266 |
| medium | 2 F/R/H | R | 152851689415 | 152.851689415 |
| medium | 2 F/R/H | H | 69059951412 | 69.059951412 |
| medium | 3 R/H/F | R | 152316073808 | 152.316073808 |
| medium | 3 R/H/F | H | 69426166154 | 69.426166154 |
| medium | 3 R/H/F | F | 92201298828 | 92.201298828 |
| ultrafast | 1 H/F/R | H | 21163641221 | 21.163641221 |
| ultrafast | 1 H/F/R | F | 39733311374 | 39.733311374 |
| ultrafast | 1 H/F/R | R | 60125442549 | 60.125442549 |
| ultrafast | 2 F/R/H | F | 39229473920 | 39.229473920 |
| ultrafast | 2 F/R/H | R | 60012809861 | 60.012809861 |
| ultrafast | 2 F/R/H | H | 20704839205 | 20.704839205 |
| ultrafast | 3 R/H/F | R | 59564471586 | 59.564471586 |
| ultrafast | 3 R/H/F | H | 20679705204 | 20.679705204 |
| ultrafast | 3 R/H/F | F | 39251199575 | 39.251199575 |

| Preset | H median | F median | R median | F/H | R/H | R/F |
|---|---:|---:|---:|---:|---:|---:|
| medium | 69.156139448 s | 92.045448392 s | 152.316073808 s | 1.330980× | 2.202495× | 1.654792× |
| ultrafast | 20.704839205 s | 39.251199575 s | 60.012809861 s | 1.895750× | 2.898492× | 1.528942× |

Ratios are ratios of eligible Linux medians only (denominator engine listed after `/`).

## Eligibility and CPU-stage evidence

All repeats for each profile were byte-identical, so six unique outputs were measured once and bound by hash to all 24 saved paths. Every output decoded to exactly 300 frames with PTS `n/30`, `n=0…299`; H timescale was `1/30`, F `1/15360`, and R `1/90000`.

| Engine/preset | Output SHA-256 | SSIM Y min | PSNR Y/U/V minima (dB) | Pass |
|---|---|---:|---:|---:|
| H medium | `47ed717af6c671c2574a716540ce846d1eade6089bb438a0be923c62cba2f569` | 0.996564 | 45.88 / 46.00 / 45.93 | yes |
| F medium | `c20fd2a82fcf1803101de04504536e17ae77d49e4b1e7230760cee5bb1b616bc` | 0.995885 | 46.01 / 46.58 / 46.60 | yes |
| R medium | `932c100213ffa16888bad4dea143b17442266715c67534f6e37c405ca6059825` | 0.995812 | 45.81 / 45.06 / 44.85 | yes |
| H ultrafast | `ad82e6bc13985f428ea2e527da9efcf776985cfbec50acbec9f8439a3b4c4112` | 0.996119 | 47.08 / 46.09 / 46.04 | yes |
| F ultrafast | `760dbd4bd588f8c244d2c486e39cc10e8d2d1cf6676e64d0efa23cd85a320706` | 0.996283 | 47.16 / 46.29 / 46.30 | yes |
| R ultrafast | `8b827706fc2566c10eb0c3b45635a040bc1e7bdca9d41c8d807d2cbff284b2da` | 0.996127 | 47.04 / 45.04 / 44.98 | yes |

Every x264 SEI reports core 164 and the requested threads/preset/CRF/GOP/quantizer/scenecut settings. All 9 Remotion runs (qualification + 8 holdout) passed strict admission: `--disable-gpu`, `--disable-gpu-compositing`, and `--disable-gpu-rasterization`; compositing and rasterization `disabled_software`; video encoding `disabled_software`; GL renderer SwiftShader. Chrome still creates a software GPU process and reports WebGL readback support; no hardware GPU stage was observed or used.

F-ultrafast required repair. Each original hash was `218b09581f98c992039362e4d98715e0d5e98595fcc31ba9ad72eb1cdc32d7ee`; each repaired delivered hash was `760dbd4bd588f8c244d2c486e39cc10e8d2d1cf6676e64d0efa23cd85a320706`. Median repair cost was 0.460634610 s and is included above; exact commands and per-run costs are in `receipts/fframes-ultrafast-repairs.jsonl`.

## Measured bottlenecks

- **H medium:** median render critical path 60.500 s; max-worker draw 20.708 s and encoder wait 31.817 s. Finalization was 8.468 s, including 7.982 s final decode (11.5% of delivered time). Encoding is the dominant medium path.
- **H ultrafast:** render 17.164 s; max-worker draw 14.697 s and encoder wait 1.972 s. Final decode 2.674 s (12.9%). Raster/draw becomes dominant.
- **F:** medium engine process 83.056 s + 8.988 s final decode; ultrafast engine 35.865 s + 0.461 s repair + 2.945 s final decode.
- **R medium:** median `renderMedia` 143.762 s. All 300 JPEG100 frames were rasterized by 40.700 s; 103.187 s remained inside `renderMedia`, dominated by serial medium x264 encoding/stitch delivery. Final decode added 7.912 s.
- **R ultrafast:** frame rasterization remained 41.213 s; post-raster `renderMedia` fell to 15.360 s; final decode added 2.710 s. JPEG100 browser rasterization is the dominant ultrafast stage.

The cap-8 Helios final-decode behavior was exercised as `min(8, availableParallelism()) = 2`; no one-thread paired reconstruction was run, so this study makes **no new speedup claim** for that change and no optimized result distinct from baseline.

## Bindings, failures, and limitations

- Bundle: 297,712 bytes, SHA-256 `19415647a9696a034b46a8ff0cb7f98f481d6a49504a44d39e0127cbd3a50261`.
- Helios merge `ebf8e145538d454479d80f97f8f76893b2fdf96f` and tested head `0566d1108f922ea88294d4bbe1f11cdb49849834` share portable tree `bba6de4d9bfde1df81c37f4c1a9199978dc1047c` (115 files); all nine receipt-bound compiled JS modules match the historical candidate byte-for-byte.
- fframes `bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b`; Remotion 4.0.529; DM Sans SHA-256 `9ae2da663d64342031e59b5fa680dd355171d021b7ebf83774efc7c0330ae7b5`; Chrome 149.0.7790.0; benchmark Node 24.19.0; Rust/Cargo 1.90.0.
- H/R use Debian FFmpeg 5.1.9 with x264 core 164. Pinned fframes compiled vendored FFmpeg 9 via `ffmpeg-sys-next 9.0.0` and dynamically links the same x264 core 164. This differs from historical macOS FFmpeg 9/x264 core 165 and limits cross-study comparison.
- Quality is against each engine's own fresh lossless reference. Passing does not imply cross-rasterizer pixel identity.
- Setup failures and necessary repairs are preserved in `failures/setup-failures.md`. No repository files were changed, and nothing was pushed, published, deployed, or uploaded to production.

Primary manifest SHA-256: `e2a3af7c3c9ec342d40ba4e19aa24b4ecd0aef7a36e9833f009fa0e79084b62f`.
