# Helios CPU benchmark motion-graphics handoff

Ready to create the requested video from qualified local evidence and merged gains. The overall local/remote performance goal remains open because fresh scheduler/Orbs measurements are pending. This handoff authorizes preparation of a reviewable video, not publishing it. No new video thread has been created.

## Paste this assignment into the next thread

Create a polished 45–60 second Helios motion-graphics video for heliosrender.com using this document, `claims.json`, `chart-data.json`, and the receipt bundle. Apply the Helios composition and motion-design skills. Deliver the editable composition, a rendered review video, and a short list mapping each numerical claim to its receipt. Use continuous motion, the actual TextGrid scene, and a clear comparison chart. Keep the benchmark scope visible whenever ratios appear. Make no numerical remote or arbitrary-browser claims. Publishing and a public receipts URL remain separate work.

The intended headline is **“Faster CPU exports in the TextGrid benchmark.”** A suitable supporting line is **“1080p, 300 frames, software encoding, complete delivery validation.”** The strongest qualified number is 4.31× versus Remotion at ultrafast; keep “TextGrid · M3 Pro · CPU · ultrafast” alongside it. Avoid “fastest everywhere,” “all benchmarks,” or an implication that these native results measure Helios's general Chromium renderer.

## Qualified local holdout

| Software x264 preset | Helios | fframes CPU | Remotion CPU JPEG100 | Speedup vs fframes | Speedup vs Remotion |
| --- | ---: | ---: | ---: | ---: | ---: |
| Medium | 11.990895250 s | 15.203560167 s | 24.039981583 s | 1.27× | 2.00× |
| Ultrafast | 4.210728167 s | 7.357826791 s | 18.165699834 s | 1.75× | 4.31× |

These are medians of three fresh timed exports per engine/preset. One fresh warmup per engine/preset was excluded. Sequential round orders were HFR / FRH / RHF. Helios won every timed round against each competitor in both presets. Ratios divide the competitor's median delivered time by Helios's median delivered time; they are not percent reductions or ratios of screening medians. `chart-data.json` retains all18 original nanosecond timers and within-round ratios. Screening selected settings, then a separate holdout measured these comparisons.

Host: Apple M3 Pro,11 available logical CPUs, macOS arm64. Scene: 3334 changing DM Sans labels,1920×1080,300 frames at30fps. Encoding: actual software x264 core165,CRF11,GOP24,qmin15/qmax60/qcomp.6/qdiff4,BT.601 TV YUV420P. Preset parameters were matched and admitted from actual encoder SEI, with deliberately disclosed thread counts.

| Engine | Medium resources | Ultrafast resources |
| --- | --- | --- |
| Helios native Canvas | 4 drawing workers;4 threads per worker encoder | 8 drawing workers;2 threads per worker encoder |
| fframes CPU SVG | 11 workers;2 threads per segment encoder | 11 workers;2 threads per segment encoder |
| Remotion CPU DOM | JPEG100;11 renderer workers;8 threads per active encoder | JPEG100;11 renderer workers;8 threads per active encoder |

Renderer concurrency and encoder concurrency are different. These settings are the best eligible choices within the disclosed tested ranges, not a claim of exhaustive optimal tuning. Remotion4.0.529 and fframes revision `bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b` are pinned. Node24.19.0,FFmpeg9.0,x264165,Chrome149.0.7790.0 and exact source/runtime hashes are in the bundle.

## Delivery clock and quality disclosure

Each original external process clock includes startup, rendering, encoding, stitching where applicable, and successful full final decode validation. Helios's internal final decode is counted once; fframes and Remotion have one external8-thread final decode. fframes ultrafast also includes its stream-copy edit-list repair before final validation; originals remain preserved. Build/setup, hashing, quality measurement and exact-cadence analysis are outside delivery clocks. Their durations are not superiority results.

All24 saved warmup/timed outputs are source/runtime/output-bound and eligible. Six unique output/reference pairs cover all1,800 measured frames. Every frame meets the unchanged own-reference floor: SSIM Y≥.995;PSNR Y≥40dB,U/V≥35dB. All300 actual PTS values equal frame index/30. This verifies capture/codec fidelity against each engine's own lossless reference. Native Skia Canvas, fframes CPU SVG and Chromium DOM rasterizers differ; it does not establish pixel identity or equal perceptual quality between engines.

Remotion's timed captures use JPEG100. JPEG80 failed the fixed fidelity floor and was excluded. Initial PNG measurements lacked later CPU stage attestation and do not support strict CPU comparison claims. The final browser has actual `--disable-gpu`, `--disable-gpu-compositing`, `--disable-gpu-rasterization` flags and CDP software compositor/rasterization evidence on every export, with software video encoding. This attests required workload stages, not every unused browser capability.

An earlier floating metric-clock expression rounded some Remotion timestamps a tick early. Saved quality comparisons were corrected separately with exact `settb=expr=1/30,setpts=N` on both streams after actual-cadence validation. No export or original performance timer changed. Preserve that disclosure and original measurements in supporting methodology.

## Measured code gain versus previous Helios

Final full decode verification now uses `min(8,availableParallelism())` threads instead of one. Chunk packet-count probes remain single-threaded. Full frame/codec/geometry/FPS/duration validation remains in place.

```mermaid
flowchart LR
  A[Native Canvas drawing] --> B[Software H.264 encoding]
  B --> C[Stitch MP4]
  C --> D[Parallel full decode and validation]
  D --> E[Delivered video]
```

The separate three-pair study measured **1.59× medium** and **1.67× ultrafast** delivered speedup versus the frozen previous Helios implementation. Exact median within-pair ratios are1.5882869944569293 and1.669009825438181. All six timed pairs are byte-identical and meet full-frame quality/cadence. These ratios use a different definition and original settings from the competitor holdout: medium4workers/8encoder threads;ultrafast6/4. Do not combine their timers or imply worker tuning itself generated the entire decoder improvement.

## Merged code and closing checks

- [Helios PR5006](https://github.com/BintzGavin/helios/pull/5006), merged as `ebf8e145538d454479d80f97f8f76893b2fdf96f`. All115 portable package files are Git-tree identical to tested head `0566d1108f922ea88294d4bbe1f11cdb49849834`. All19 compiled JS modules matched the frozen candidate. Package typecheck and189 tests in33 files passed. The private experimental native package is available from the merged repository; do not describe it as a released npm version or a general browser-renderer speedup.
- [Scheduler PR45](https://github.com/BintzGavin/durable-objects-requests-scheduler/pull/45), merged as `597ab652c4d57f7abe021e0e643cf54b222a1e7b`. All eight performance/acceptance files are Git-tree identical to the checked head. Twenty focused tests, one bundled keep-names check and TypeScript passed; the20 focused tests and TypeScript also passed after upstream provider integration. Changes stream R2 media, stage audio with one write, and replace a fixed5-second delay with bounded HTTP readiness. No fresh remote speedup percentage is established.

Original dirty checkouts were preserved. No manual production deployment or new R2 source upload was performed. A source-control merge and a passing Workers Builds check alone do not establish which source is currently deployed.

## Suggested visual sequence

1. Start with the actual moving TextGrid, readable CPU-only/M3 Pro/native-workload label, and a10-second scene-duration cue.
2. Reveal a common start and animate delivered output finish times. Use two panels for medium and ultrafast. Keep three-run scatter marks faintly visible behind median bars.
3. Transform the chart into the1.27×/1.75× fframes and2.00×/4.31× Remotion ratios, with preset labels and scope retained on screen.
4. Show drawing→encoding→validation→delivery. Accelerate the final decode stage for the separate previous-Helios1.59×/1.67× claim and display “same encoded bytes, complete validation.”
5. Finish on Helios and a receipts/methodology call to action. Use a verified public receipt URL only after one exists; no fake URL or placeholder in a published export.

Essential on-screen footnote: **“TextGrid ·1080p/300frames · M3 Pro11CPU · CRF11 · native rasterizers ·3 timed runs · own-reference fidelity.”** Supporting copy explains JPEG100, resources, delivery validation and fframes ultrafast repair. Remote numbers are omitted until separately qualified.

## Receipts and reproduction inputs

- [Qualified holdout summary](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-holdout-results-v1.json) and [original manifest](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/results/holdout/full-v1/manifest.json); manifest SHA256 `097fb0d8bd5381203a4755d05267fd04416e56f641be2798f226e510aed90461`.
- [Original decoder paired chart data](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/decoder-gain-chart-data.json) and [paired manifest](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/paired-decode-export-v1/results/full-v1/manifest.json).
- [Verified merge receipts](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/merge-receipts-v1.json).
- [Compact reproduction README](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/public-reproduction-v1/README.md) and [original compact receipts](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/public-reproduction-v1/holdout-receipts.json).
- [Portable ZIP bundle](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/helios-cpu-reproduction-v1.zip): 297,712 bytes compressed;1.58MiB expanded;29files. SHA256 `19415647a9696a034b46a8ff0cb7f98f481d6a49504a44d39e0127cbd3a50261`.

Original representative medium clips, retained in place:

- Helios: [H medium output](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/results/holdout/full-v1/timed-1-H-medium-w4-t4/output.mp4)
- fframes: [F medium output](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/results/holdout/full-v1/timed-1-F-medium-w11-t2/output.mp4)
- Remotion: [R medium output](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/results/holdout/full-v1/timed-1-R-medium-w11-t8/output.mp4)

The compact bundle retains all original timers/components, actual encoder parameters, CPU-stage evidence, all-frame metrics/actual PTS and source/runtime/output/reference hashes. Numeric receipts were independently compared with the original holdout. It omits binaries, font, logs, original videos and NUT references. No historical export was rerun. The original evidence and failed attempts remain in their existing directories.

Reproduction preparation checked syntax and747 read-only input bindings. Its explicit-path Rust adaptation and fresh public reference/export flow have not been built/executed. Be clear about this limit: the historical benchmark is qualified; another engineer's adapted reproduction setup is not yet demonstrated. Setup commands and pinned font retrieval/hash are documented in the README. No bundle or marketing page has been published yet.

## Remote continuation and upstream claims

Amp CLI authentication was verified, but a new normal CLI project query still returned an empty project list. Orbs needs an explicit connected Helios project. Wrangler human sign-in completion remains separate. Next remote work should use normal platform-held credentials, recover retained scheduler receipts and measure actual CPU quotas/source bindings before selecting a fresh paired protocol. Do not upload a source capsule, deploy production, retrieve environment values or publish anything merely to obtain video numbers.

The upstream fframes6.80s medium/3.15s ultrafast CPU headline was measured on an M4 Max16CPU64GB at CRF18 and admits299 frames. Its Remotion headline uses JPEG80 and a different browser GPU policy. Our M3 Pro11CPU/CRF11/300-frame/full-delivery/quality-qualified study is different. Do not compare our absolute times directly with that headline or claim to reproduce its environment. Source: https://github.com/dmtrKovalenko/fframes/tree/bacfc3c3212d3d9429468435bfdc1ae2a21c7b3b/render-bench/vs-remotion

Older temporary evidence is unavailable locally and is not fresh public proof. This handoff uses only the durable October1 studies. Keep remote claims empty until fresh receipt-bound results qualify.
