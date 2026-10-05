# Qualified connected-Mac TextGrid GPU comparison

This is a completed 1080p TextGrid baseline. The separate 4K circle replication and further native encoder optimization are still active; the published M5 Max claim has not been beaten.

Apple M3 Pro:11 CPU / 14 GPU cores,18 GiB, macOS 26.3. Scene: 3,334 labels, 1920×1080, 300 frames at 30 fps, pinned DM Sans, no audio. Four balanced sequential rounds perengine, warmups excluded. All included outputs pass every-frame SSIM-Y≥.995, PSNR-Y≥40dB and U/V≥35dB against per-engine lossless references, plus exact decoded frame cadence.

| Lane / engine | Median export | Median including full decode |
|---|---:|---:|
| GPU raster + matched x264 / Helios |26.590s|28.142s|
| GPU raster + matched x264 / fframes |31.122s|32.703s|
| GPU raster + matched x264 / Remotion |47.086s|48.610s|
| Required hardware H.264 / Helios 100 Mbps |6.294s|7.929s|
| Required hardware H.264 / fframes 180 Mbps |5.723s|7.892s|

Helios is faster in every matched-software round. fframes is faster in every hardware export round. Hardware delivered times split two wins each and differ by about0.46% in the medians; these repeats do not establish a meaningful delivered-time winner. Hardware pipelines differ in bitrate, concurrency and color conversion: Helios GPU BT.709/NV12; fframes BGRA hardware targets with BT.601 attachments and opaque encoder conversion. These are whole pipeline clocks, not isolated GPU throughput.

The software lane uses serial native Helios/fframes adapters and one-tab Remotion, matched x264 medium / CRF11 / two threads / GOP90 / no B frames. Remotion's eight-tab warmup failed and is retained outside the timed summary. Its original reference differed at six frame indices, including one inspected black frame; the corrected one-tab reference is used. Candidate clocks were retained.

Actual GPU traces, external interposition and positive controls support GPU raster/conversion use and no observed application raw-frame download in native hardware exports. Unknown buffer accesses, pointer queries and opaque driver/encoder transfers remain: zeroCopyProved=false. Software exports intentionally download raw frames. Unsupported Helios paths include HEVC, Vulkan encoder interoperability, Intel/Windows GPU paths and GPU image/video nodes.

Implementation PR5009 and reference correction PR5010 were merged externally. Separate circle/GOP PR5011 is build-ready and still needs300-frame 4K quality/timing. Its source scene replication uses public fframes f89cbd and optimized SVG 1c2a088; the recorded claim renderer 0486526 does not contain the measured circle source byte-for-byte. A 1080p time below 7.225s does not beat the separate 4K M5 Max claim.

Raw per-round commands, source/executable/reference hashes, process samples, every-frame quality logs, failed screens and excluded attempts accompany this source/evidence package. Reproduction starts with PROTOCOL.md and the original preparation README/prerequisites; paths must be relocated explicitly while retaining hash identities.
