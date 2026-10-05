# Modified concurrent fframes GPU NV12

The separately modified H.264 pipeline preserves 3 GPU contexts, 5 generators, 5 encoders, queue 10 and a 64-buffer allocation threshold per context. Native H uses pool 3. The contracts differ and must remain visible. This lane is quality qualified on 300 4K frames, **with no performance result**.

All 300 direct NV12/lossless bindings pass; worst SSIM-Y.995261,PSNR Y/U/V40.23/40.54/40.48. The narrow luma margin makes every timed candidate's full 300 quality gate mandatory. Full-workload uncaptured profile independently recounted 300 GPU fences/owner lifetimes,0 hooked raw downloads;3 positive 4K controls detect 99,532,800 RGBA bytes/3 CV locks/6 planes. Pointer intent/opaque transfers remain unknown:zeroCopyProved=false.

Mandatory centered-chroma SPS signaling plus copy mux changes only the permitted syntax; actual original/conformed VCL payloads and saved decoded pairs are identical. Full semantic SPS comparison is retained. That cost belongs in all future clocks. Failed first conformance and ENOSPC reference attempts remain excluded. This is neither the original fframes product nor a reuse of serial-adapter qualification.

[Final report](../evidence/gpu-comparison/fframes-concurrent-nv12-20261004/FINAL-REPORT.json), [build-ready](../evidence/gpu-comparison/fframes-concurrent-nv12-20261004/BUILD-READY.json), [manifest](../evidence/gpu-comparison/fframes-concurrent-nv12-20261004/RECEIPT-MANIFEST.json), [independent audit](../evidence/audits/COMPARISON-MONITOR-FFRAMES-CONCURRENT-NV12-FINAL.json). Final audit checks 10,025 files/3,282,332,692 bytes, 168 source/278 dependency/14 harness pins, 6 helper copies and 3 archive CRCs. Frozen helper circles`665ce943531be9a35d61aa7629e12646e280d0568c1ca6a576816f15963210a8`, controls`ea36969d384cfb1de3fe5b02da832cab97003301ab3a7818133c82b942f363f3`, converter`11522ab92e119b84f9af86b9abf5864263c774a21ac7505b82a6556b6e9e132d`.

H.264 qualification does not imply HEVC. Balanced timings remain pending, require every-candidate qualification, resource gates and an announced noncompeting timing window.
