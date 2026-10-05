CPU-only native exports spend substantial delivery time decoding the stitched output for final validation. This adds the experimental portable package needed to reproduce the measured native rendering path and caps that final decode at `min(8, availableParallelism())`; internal chunk packet probes stay single-threaded. Full decode and frame/geometry/codec/FPS/duration validation remain intact.

```mermaid
flowchart LR
  A[Native render workers] --> B[Software H.264 chunks]
  B --> C[Stitch output]
  C --> D[Full decode: available CPUs capped at 8]
  D --> E[Validated delivery]
```

The package includes its CPU rendering sources, worker/runtime interfaces, source examples, reproducible benchmark helpers, tests and licensed font fixtures. It remains private and experimental; this does not replace the browser renderer or claim arbitrary browser-composition speedups. Workspace lock changes preserve every existing dependency version, with the new package's dependencies nested locally.

Three fresh paired exports per preset on Apple M3 Pro / 11 available logical CPUs produce median within-pair delivery speedups of 1.588× (medium) and 1.669× (ultrafast) versus the frozen one-thread baseline. All six timed pairs produce byte-identical MP4s; every frame meets the existing fidelity floor and exact cadence. Delivery timers include final full decode. The paired study is separate from worker screening and the final competitor holdout. Current receipts and methodology are described in `docs/rfcs/2026-10-01-cpu-benchmarks.md`; unavailable historical temporary evidence is disclosed separately.

Validation: portable TypeScript and all 189 tests across 33 files pass; all 19 rebuilt JavaScript files match the frozen benchmark candidate byte for byte. The separate CPU TextGrid holdout qualifies every frame and exact cadence: delivered medians are Helios/fframes/Remotion 11.991/15.204/24.040 s medium and 4.211/7.358/18.166 s ultrafast, with three balanced timed rounds per engine/preset. These are native-scene local results, with JPEG100 strict CPU Remotion, tuned settings and own-rasterizer quality limits disclosed in the RFC. No remote or arbitrary-browser superiority is claimed.
