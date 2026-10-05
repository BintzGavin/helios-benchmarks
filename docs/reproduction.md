# Reproduce and verify

## Verify this publication without running a benchmark

```sh
git clone https://github.com/BintzGavin/helios-benchmarks.git
cd helios-benchmarks
python3 tools/verify.py
python3 tools/verify_results.py
```

`verify.py` checks every Git evidence file's exact size/SHA against the publication catalog, and checks catalog and Markdown links. To verify an individual release asset, download the catalog's URL and compare its size/SHA-256. `tools/fetch_evidence.py --match <namespace-prefix> --directory <new-directory>` downloads only relevant assets, verifies their bytes before extraction, reconstructs bundle objects with safe paths, and checks original member hashes. Large datasets consume disk/network: select a study first. This operation never executes a helper or native binary.

The catalog maps original relative paths to Git or a content-addressed release object. Duplicate byte-identical files share one object; all original logical paths remain. Small binary objects are bundled without changing member bytes. Large media/reference/helper/source archives are direct assets, with exact SHA-256 filenames. Upload receipts and the archive/hash manifest document publication; no original experiment clocks are modified.

## Reproduce a new experiment

Begin with the retained protocol/source/runtime/build report for the chosen study, not a cross-study combined ranking. Historical absolute executor paths require explicit relocation and new recorded hashes. Install exact upstream versions or record all differences; source manifests alone are not a frozen runnable environment. Rebuilding a historical helper produces a new candidate requiring new qualification.

- CPU: `evidence/cpu-macos/public-reproduction-v1/README.md` and frozen holdout source/settings/references. The original portable reproduction flow was reviewed but not executed end to end on every platform.
- Orb: `evidence/cpu-orb/reports/` and adapted scripts/settings/host/source/runtime manifests. Do not transplant 11-worker macOS settings onto two logical CPUs.
- GPU TextGrid: [original recipe](../evidence/gpu-delivery/REPRODUCE-TEXTGRID.md).
- Serial common-converter4K: [original recipe](../evidence/gpu-delivery/REPRODUCE-CIRCLES.md).
- Vulkan/HEVC: final frozen BUILD-READY, protocol, source/runtime pins, reports and qualification manifests under `evidence/native/`. Read the canonical MoltenVK RPATH requirement. Do not imply Linux Vulkan Video or a fresh network installer is qualified.
- Centered/native/concurrent preparation: freeze new orchestration/source pins, keep old snapshots untouched, require actual device/runtime/GPU controls, codec-specific full invariance and all300 reference/quality/cadence/color/GOP gates before timing.

Use a new empty output directory, keep failures and warmups, run sequential balanced order, and never overwrite historical media/receipts. Enforce current per-lane disk/allocation caps and actual hardware checks. Timings require an announced noncompeting window. Full4K and production gaps remain explicit.
