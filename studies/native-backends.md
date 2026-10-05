# Native Metal / HEVC / Vulkan qualification

These backend deliveries demonstrate bounded functionality and exact evidence bindings. They are separate from performance holdouts and full4K qualification.

Native Metal renders with Skia into shared GPU surfaces, performs BT.709 limited-range NV12 conversion on the GPU, then uses required VideoToolbox hardware H.264/HEVC. TypeScript Canvas feed, bounded binary packets, GOP and encoder-pool ownership are receipt bound. Historical helpers remain frozen, separately named and never rebuilt in this publication. PRs5009–5015 were externally merged; the benchmark task did not merge them.

## Vulkan on macOS arm64

Actual M3 Pro path: Skia Vulkan → public API shared private Metal texture → completed Vulkan fence → GPU NV12 conversion → required VideoToolbox H.264/HEVC. MoltenVK1.4.2, JSON protocol8 / binary9; HGF5 unchanged. Metal protocols4/5/6/7 remain separate.

Final source`63869ba529c89fc1a27f7f55057e4d876c42d26e`; external HEVC base`079356491449178e66ab8bbaac700684668c8951`. Helper03 SHA-256`6679452901c6535cc80b4b762cd6c7c13d222e91fb8212a837ca85e60f4af22b`. MoltenVK dylib`aef00b13bcc808adf15b85bef9ae67393d92be7ed5dfe41cad16fa809e4a4c5f`;56 headers and58 runtime files pinned. Final source archive`79255be24f4e86d18d4f5cb2f6afd611a07a50185d299c1dd1ea8b8a3ab22001`. Frozen helper RPATH needs the canonical runtime path documented in its build report, or identical pinned bytes restored there; do not patch a historical helper.

Both codecs qualify all300 frames at256×128,30000/1001,20Mbps,GOP30,pool3, direct NV12/lossless binding, full decoded cadence/color and unchanged every-frame floors.

| Codec | Worst SSIM-Y | PSNR Y | PSNR U | PSNR V |
| --- | ---: | ---: | ---: | ---: |
| HEVC | .999978 | 69.22 | 67.40 | 69.34 |
| H.264 | .999984 | 67.10 | 71.95 | 71.70 |

Actual300 Vulkan submissions/fences per codec, same-IOSurface identity and conversion/submission/callback/owner-release ordering, positive GPU timestamps and no early reuse. Uncaptured hooks find0 raw downloads; NV12 positive controls find6 locks and RGBA controls find3 VulkanCopyImageToBuffer calls. Pointer/mapped-memory intent and opaque driver/encoder transfers remain unknown. A separate3-frame device capture is excluded. Tests include219 portable checks/20 explicit native-path skips,9 actual Vk API and5 packet checks,5 killed receipt mutations and retained refusal controls. Candidate01/02, surface/init/profiler/ENOSPC/PATH failures are retained and excluded.

[Final Vulkan report](../evidence/native/vulkan-evidence/FINAL-REPORT.json), [build-ready](../evidence/native/vulkan-evidence/BUILD-READY.json), [receipt manifest](../evidence/native/vulkan-evidence/RECEIPT-MANIFEST.json), [independent acceptance](../evidence/audits/COMPARISON-MONITOR-VULKAN-HANDOFF-VERIFIED.json). This proves neither full4K Vulkan performance nor production/M5 superiority. Linux Vulkan Video, Intel/Windows GPU encoding and GPU media nodes remain unsupported. Fresh network installation and rebuilt default-Metal binary were not qualified.

## Historical helper generations

Original helper`87aec3f3d39db8956490942429e6a865741c04515ad6b98753aaf6599c197a90`; binary helper`1383da791a588731101f6dd22bea8e911d4bc97243b7f01541214981afc90ecc`; HEVC helper`9c2b3654ce681d9764643214a745878b8fecb72ed9fcd69f3aea7f0fa709d9ae`. Every intermediate source/helper/receipt pin is preserved in the native evidence subdirectories and catalog. Corrected NV12 references and invalidated old oracle attempts remain distinct. `zeroCopyProved=false` throughout.

Publishing this evidence repository does not mean the prepared Vulkan branch was pushed to the Helios source repository. That source publication remains a separate pending destination approval. The active new4K native acceptance slice is not included as a final result until its owner freezes a terminal delivery.
