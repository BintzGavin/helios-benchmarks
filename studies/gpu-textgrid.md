# M3 Pro GPU TextGrid

Four balanced sequential repetitions, excluded warmups, actual GPU qualification and every-frame own-reference checks. Workload: 3,334 labels, 1920×1080, 300 frames at 30/1, DM Sans, no audio.

| Lane | H export | F export | R export | H delivered | F delivered | R delivered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GPU raster, matched software x264 | 26.590 s | 31.122 s | 47.086 s | 28.142 s | 32.703 s | 48.610 s |
| Hardware product pipelines | 6.294 s | 5.723 s | — | 7.929 s | 7.892 s | — |

Software lane uses matched x264 medium/CRF11/two-thread settings and explicit sRGB→limited BT.709 conversion. Native paths download raw GPU frames; Chromium uses PNG/CDP readback. These exports cannot be called readback-free.

Hardware lane compares H 100 Mbps/BT.709 GPU conversion to F 180 Mbps/BT.601 signaling and opaque encoder conversion, with different concurrency. F's export is shorter in all four pairs. A 0.46% delivered median difference does not establish a meaningful delivered winner. H's hardware reference is directly NV12 bound; F's proxy uses actual hardware-target BGRA plus disclosed FFmpeg conversion, not private VT precompression NV12.

[Original report](../evidence/gpu-delivery/helios-gpu-textgrid-results-20261003.md), [protocol](../evidence/gpu-comparison/PROTOCOL.md), [software config](../evidence/gpu-comparison/software-config.json), [hardware config](../evidence/gpu-comparison/hardware-config.json). Complete logs and clocks remain under their original comparison subdirectories; the catalog maps media assets.

Old invalid H color references and black-frame R references are retained, with failed screens. The historical child native 26.197/Chromium 30.199 s and100 Mbps 6.385/7.955 s are separate experiments and are not pooled with this root study. Later centered-chroma conformance work supersedes older signaling descriptions for new lanes while preserving the old artifacts and numerical qualification.
