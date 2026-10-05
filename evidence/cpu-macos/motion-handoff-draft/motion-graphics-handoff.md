# Motion graphics handoff — preparation draft

**Not ready for publication or a new production thread.** Complete the independent three-engine holdout, proportionate closing checks and both merges first. Populate competitor and remote sections only from qualified receipts. This document prepares the requested next-thread handoff; it does not claim those remaining requirements are complete.

## Assignment for the next thread

Create a polished Helios motion graphics video for heliosrender.com from the finalized claim manifest and original receipts. Start from the merged source revisions named below. Present benchmark scope and limitations legibly. Make wins, ties and losses visible; never turn one native-scene result into an all-workload claim. Render a reviewable video and provide its composition source. Publishing is a separate action.

## Supported local improvement

The experimental native Canvas TextGrid path now performs final full decode verification with `min(8, availableParallelism())` threads instead of one. Internal chunk packet probes remain single-threaded; complete decode/frame/geometry/codec/FPS/duration checks remain.

```mermaid
flowchart LR
  A[Native drawing and software H.264] --> B[Stitch MP4]
  B --> C[Full decode and validation]
  C --> D[Delivered output]
```

The measured source change accelerates step C. Medium has median within-pair speedup **1.588286994×**, ultrafast **1.669009825×**, with three fresh paired runs and three wins per preset. All six timed pairs produce byte-identical videos. Display rounded labels **1.59×** and **1.67×**, explicitly versus the previous Helios implementation. Do not substitute the ratio of separate time medians for the reported paired speedup.

Hardware: Apple M3 Pro, 11 available logical CPUs. Workload: pinned fframes TextGrid equations, 3334 changing labels, DM Sans, 1920×1080, 300 frames at 30 fps. Software x264, CRF11. Medium: four drawing workers, eight encoder threads per worker. Ultrafast: six drawing workers, four encoder threads per worker. Each preset/variant has an excluded warmup. Original external process timers include startup, preparation, render/encode, stitch and full decode verification; builds, hashes and later quality measurements are outside those timers.

## Competitor comparison — pending

Use only the separately completed matched holdout for final superiority ratios. Resource screening selects settings; its medians cannot be combined across independent studies into superiority ratios. The prepared holdout uses one new excluded warmup per engine/preset and three timed rounds in HFR / FRH / RHF order. Use original delivered nanosecond timers, and disclose fframes ultrafast stream-copy edit-list repair and full verification when included.

Required fields before this section can be used: holdout manifest/hash, all three engine versions and source revisions, selected settings, all three original times per engine/preset, summary calculation, all-frame quality and exact-cadence evidence, CPU runtime evidence, failed-attempt disclosure, hardware and reproducible commands. Keep a table of wins/ties/losses rather than hiding unfavorable outcomes.

Remotion JPEG100 passes the existing codec/capture fidelity floor. JPEG80 fails and must not be used as a matched-quality competitor result. Native rasterizers differ: own-reference codec fidelity does not prove identical cross-engine pixels or equal perceptual quality. Initial Remotion PNG outputs have unattested GPU stages and cannot support strict CPU superiority claims.

## Fidelity and timestamp correction disclosure

The existing per-frame floor is Y SSIM≥.995, PSNR Y≥40 dB and U/V≥35 dB, plus all 300 actual timestamps at exact 30 fps. Saved-output metrics use each engine’s own lossless source reference. The original floating comparison-clock expression rounded some Remotion timestamps a tick early. A separate correction uses exact common `settb=expr=1/30,setpts=N`, after actual-cadence validation. It reuses the same saved videos/references; no export or original render timer changed. Preserve both original and corrected measurements. Measurement durations are not render-performance results.

## Remote CPU results — pending

Amp authentication succeeded but no project resolved. Orbs requires an explicit connected project. Wrangler completion remains separate. Remote hardware, scheduler job receipts and deployed source bindings are required before presenting remote performance. Historical temporary receipts are unavailable; older RFC figures are not fresh proof. Do not infer remote gains from local results or deploy scheduler changes/upload new R2 source merely to make the video.

## Merges — pending

- Helios prepared branch: `gavin/perf-native-cpu-rendering`; isolated checkout `/Users/gavinbintz/.codex/worktrees/cpu-native-rendering/helios`. Add merged PR and commit here.
- Scheduler prepared branch: `gavin/perf-render-staging`; isolated checkout `/private/tmp/helios-scheduler-merge-20261001`. Add merged PR and commit here.
- Scheduler source changes stream R2 media, write staged audio in one operation and replace a fixed startup sleep with bounded readiness. Do not assign a remote speedup percentage without a fresh bound remote benchmark.

## Proposed visual sequence

1. Open on the actual animated TextGrid workload and a concise CPU-only label.
2. Show drawing → encoding → validation → delivery; animate the measured final-decode change and the byte-identical output proof.
3. Introduce the final matched competitor chart only after its receipts qualify. Show original repeated times, selected presets and quality floor with readable footnotes.
4. If a remote study qualifies, present it as a separate hardware/environment panel. Otherwise omit remote numerical claims.
5. End with a legible reproduction/receipts link and the Helios call to action. Avoid “fastest everywhere,” “all benchmarks” or GPU comparisons.

Treat this as continuous motion with causal transformations and live scene playback, not a slide deck of unrelated headline cards. The eventual thread should apply Helios composition and motion-design skills, using the smallest suitable native composition path. Keep receipt details accessible in supporting copy; essential scope belongs on screen.

## Receipt inputs

- [decoder-gain-chart-data.json](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/decoder-gain-chart-data.json)
- [manifest.json](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/paired-decode-export-v1/results/full-v1/manifest.json)
- [quality-policy-results-clock-v1.json](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/quality-policy-results-clock-v1.json)
- [manifest.json](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/quality-measurement-v1/results/full-v1/manifest.json)
- [manifest.json](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/quality-clock-revision-v1/results/full-v1/manifest.json)
- [README.md](/Users/gavinbintz/.codex/visualizations/2026/09/28/01a0e813-a2b5-78e0-978e-6a278c8e331e/cpu-benchmarks-20261001/final-cpu-studies-v1/README.md)
- [2026-10-01-cpu-benchmarks.md](/Users/gavinbintz/Developer/helios/docs/rfcs/2026-10-01-cpu-benchmarks.md)

Local absolute paths support this handoff only. Before public marketing, create a compact public reproducibility bundle and replace the on-screen receipt link with its verified public URL. No public bundle or marketing page has been published.
