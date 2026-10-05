# M3 Pro CPU TextGrid

The fresh three-engine holdout has 18 timed exports and six excluded warmups. All 24 outputs/receipts and all 1,800 unique-output metric rows were audited. The exact original delivered timers are in [the summary](../evidence/cpu-macos/final-holdout-results-v1.json); the authoritative [holdout manifest](../evidence/cpu-macos/final-cpu-studies-v1/results/holdout/full-v1/manifest.json) has SHA-256 `097fb0d8bd5381203a4755d05267fd04416e56f641be2798f226e510aed90461`.

| Preset | H median ns | F median ns | R median ns | F/H | R/H |
| --- | ---: | ---: | ---: | ---: | ---: |
| Medium | 11990895250 | 15203560167 | 24039981583 | 1.267925 | 2.004853 |
| Ultrafast | 4210728167 | 7357826791 | 18165699834 | 1.747400 | 4.314147 |

H has shorter delivered time in all three rounds against each competitor for both presets. This is the frozen M3 Pro native TextGrid configuration, with each engine's own lossless-reference fidelity and distinct rasterizers. It is not an arbitrary browser-composition or remote result.

The retained studies also include baseline, encoder-thread tuning, fframes worker counts, strict CPU Remotion JPEG screens, the final resource screens, all quality logs, failed attempts, clock corrections and original/repaired fframes files. JPEG80's faster screen failed the quality policy; JPEG100 was selected. An adjacent-frame comparison-timebase bug was corrected using saved videos/references without rerendering or changing original timing.

## Paired final-decoder change

Separately compare full-final-decode `min(8, availableParallelism())` with one thread. Three balanced pairs per preset retain identical output hashes and original fresh-process clocks. Median paired baseline/candidate ratios: **1.588287 medium**, **1.669010 ultrafast**, candidate shorter in all three pairs. This improvement is separate from competitor holdout ratios. See [all paired timers and component receipts](../evidence/cpu-macos/decoder-gain-chart-data.json) and [the paired study manifest](../evidence/cpu-macos/paired-decode-export-v1/results/full-v1/manifest.json).

The renderer change merged as [Helios #5006](https://github.com/BintzGavin/helios/pull/5006). Scheduler work and its validation are retained, with [scheduler #45](https://github.com/BintzGavin/durable-objects-requests-scheduler/pull/45); this is not a measured distributed-rendering speedup. The [public reproduction receipt](../evidence/cpu-macos/public-reproduction-archive-v1.json) binds a 297,712-byte archive, SHA-256 `19415647a9696a034b46a8ff0cb7f98f481d6a49504a44d39e0127cbd3a50261`. Its original publication review explicitly said the relocated reproduction flow was unexecuted. The later Linux study has its own fresh qualification.
