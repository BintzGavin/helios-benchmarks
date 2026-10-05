# Vulkan setup acceptance

The authorized target is an actual local Vulkan GPU raster path through MoltenVK,
sharing its private texture with the retained GPU BT.709 NV12 converter and
required hardware VideoToolbox encoder. This does not qualify Linux Vulkan Video.

- Given the pinned public-API MoltenVK runtime, initialization selects an actual
  integrated/discrete GPU and requires portability and Metal-object interoperability.
- Given the retained Metal private raster texture, Vulkan imports and exports the
  exact same object without application raw staging or a CPU pixel converter.
- Given three different Vulkan clears, each completed Vulkan fence precedes
  conversion/encoder submission, and all hardware callbacks drain before release.
- Given absent runtime, missing extension, CPU-only device, failed fence or encoder,
  reject without publishing success or silently falling back to Metal raster/software.
- Full public API support additionally requires actual Skia Vulkan rendering,
  explicit backend-bound receipts, existing bounds/atomic refusal/cancellation,
  independent direct/lossless references and all-frame decoded fidelity/cadence/color.
- No setup clock is a benchmark. Full4K and balanced comparison stay with the owner.

Initial executable acceptance failed because the interop helper was absent.
Hardware/GPU qualification and negative controls follow before API promotion.
