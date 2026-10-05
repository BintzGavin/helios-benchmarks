# Helios benchmarks

Rendering results, methodology, original receipts and reproducibility material from the September–October 2026 Helios studies. The engines are Helios (**H**), fframes (**F**) and Remotion (**R**). This repository preserves both successful and failed experiments.

**Read each result within its measured configuration.** CPU, GPU, codecs, adapters and hosts are separate studies. References measure each engine's own output fidelity; cross-engine pixel identity is not asserted. A qualified small-scene backend is not a qualified 4K performance result.

| Study | Host / configuration | H | F | R | Clock / scope |
| --- | --- | ---: | ---: | ---: | --- |
| [CPU medium](studies/cpu-macos.md) | M3 Pro, 11 logical CPUs, TextGrid | 11.990895 s | 15.203560 s | 24.039982 s | median delivered; 3 balanced rounds |
| [CPU ultrafast](studies/cpu-macos.md) | Same local CPU study | 4.210728 s | 7.357827 s | 18.165700 s | median delivered; 3 balanced rounds |
| [Orb CPU medium](studies/cpu-orb.md) | Linux a1.small, 1 physical core / 2 logical CPUs | 69.156139 s | 92.045448 s | 152.316074 s | median delivered; 3 balanced rounds |
| [Orb CPU ultrafast](studies/cpu-orb.md) | Same Linux CPU study | 20.704839 s | 39.251200 s | 60.012810 s | median delivered; 3 balanced rounds |
| [GPU TextGrid / software encode](studies/gpu-textgrid.md) | M3 Pro; GPU raster, matched x264 | 26.590 s | 31.122 s | 47.086 s | median export; 4 balanced rounds |
| [GPU TextGrid / hardware pipelines](studies/gpu-textgrid.md) | M3 Pro; different bitrate/color/concurrency | 6.294 s | 5.723 s | — | median export; configuration differences matter |
| [4K common-converter adapters](studies/gpu-circles.md) | M3 Pro; serial adapters, common 300 Mbps H.264 | 21.133668 s | 81.721465 s | — | median export; 4 balanced pairs; separately labeled adapters |

The Orb result is the remote CPU study. It is not a fourth engine or an independent GPU experiment. No general fastest-renderer, end-to-end zero-copy, original-product production win, or M5 Max claim is established.

**Evidence published:** 30,661 catalog paths, 12,581 readable Git evidence files, and 164 release assets (29,421,509,501 bytes). Every asset matches its original size and GitHub server SHA-256. Two bounded public download/restoration checks also pass; the full 29.4 GB was not independently downloaded again. See [publication receipts](data/publication-receipts.json).

## Explore

- [Methodology and eligibility](docs/methodology.md): clocks, ordering, settings, quality, actual CPU/GPU evidence and failure policy.
- [All study families](docs/study-index.md): holdouts, tuning, paired decoder work, original failures, backend qualification and preparation.
- [Metal, HEVC and Vulkan qualification](studies/native-backends.md): actual GPU stages, pools, source/binary pins and unsupported paths.
- [Concurrent fframes NV12 pipeline](studies/fframes-concurrent.md): separately modified pipeline; quality qualified, no timed result.
- [Corrections, exclusions and open work](docs/limitations.md).
- [Reproduce and verify](docs/reproduction.md).
- [Evidence catalog](data/evidence-catalog.json): exact paths, sizes, SHA-256, Git files, release assets and bundle members.
- [Evidence release](https://github.com/BintzGavin/helios-benchmarks/releases/tag/evidence-2026-10-05): raw media, lossless references, captures, frozen helpers and binary objects.

```mermaid
flowchart LR
    S[Source and runtime pins] --> R[Original process clocks and receipts]
    R --> Q[Cadence, color and every-frame quality gates]
    Q --> E[Eligible results with measured scope]
    R --> X[Failed and excluded attempts retained]
    E --> C[Reports and evidence catalog]
    X --> C
```

The publication snapshot includes available local evidence without rerendering any historical experiment. Original receipt bytes and absolute paths remain unchanged. Read the catalog for their relocated equivalents. Remote Orb raw media was omitted from the compact transfer; its full original index and omission are retained. Work still running when this snapshot was assembled is not promoted to a final result.
