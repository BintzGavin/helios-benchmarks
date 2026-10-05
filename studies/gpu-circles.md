# 4K circles: common-converter serial adapters

Four balanced pairs on M3 Pro. 99,000 circles plus1,000 digits,3840×2160, source3–302,300 frames at30/1. Serial raster, common requested/configured300Mbps H.264, pool3, GOP30, GPU sRGB→limited BT.709 NV12, copy mux. H uses bounded binary Canvas transport/Skia0.91; F uses optimized SVG/Skia0.153.3 Metal HardwareFrames with one disclosed extra GPU texture copy into the common converter.

| Clock | H median | F median |
| --- | ---: | ---: |
| Export | 21.1336678125 s | 81.721465333 s |
| Delivered | 25.5339021875 s | 86.1813760625 s |

This is a **separately labeled task adapter comparison**. It does not measure the original concurrent fframes MaxPerformance product pipeline or fully enabled production superiority. The four H export times are20.118268542,21.114672917,21.152662708,22.077710834 s; F80.642841750,81.487102000,81.955828666,82.770407208 s. All8 candidates/all300 frames satisfy the unchanged floors, cadence/color/GOP and lifetime contracts. Worst H:SSIM-Y.996243, PSNR41.14/41.11/41.01; F.995262,40.27/40.63/40.52.

[Original combined report](../evidence/gpu-delivery/helios-gpu-comparison-results-20261003.md), [frozen protocol](../evidence/gpu-comparison/CIRCLES-COMMON-PROTOCOL.md), [config](../evidence/gpu-comparison/circles-common-binary-300-config.json), [independent audit](../evidence/audits/COMPARISON-MONITOR-BALANCED-4K300.json). Full raw clocks, all candidates, lossless references, quality rows, profile/capture records and source archives are cataloged.

Original F8/200/500Mbps product screens at25.713300583/25.048320292/27.400868292 s all fail quality and remain excluded. Original F500Mbps has U/V minima33.36/33.10 below35. The later original concurrent same-stream capture removed separate-raster ambiguity but still fails unchanged chroma floors on U296/V300 frames. Its fixed BT.601 proxy is not actual VT precompression NV12: no encoder-bug conclusion follows.

F common-converter v2 lossless reference binds all300 frames to its same raw stream. Independent raster repeatability differed by290 bytes in two frames (max delta47), cause unresolved and disclosed. Cross-rasterizer pixel identity is not asserted. The original M5 Max7.225018333 s claim has different hardware/encoding/clocks and unavailable exact measured uncommitted source; it is neither proven comparable nor beaten here.
