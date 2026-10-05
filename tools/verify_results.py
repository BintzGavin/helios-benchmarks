#!/usr/bin/env python3
"""Recompute published CPU medians from immutable original timed durations."""
import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / 'data/study-summary.json').read_text())
local = json.loads((ROOT / 'evidence/cpu-macos/final-holdout-results-v1.json').read_text())
orb = json.loads((ROOT / 'evidence/cpu-orb-delivery/linux-evidence-verification.json').read_text())
checked = []
for item in local['summary']:
    for engine, ns in item['originalDeliveredWallNs'].items():
        assert len(ns) == 3
        median = statistics.median(ns)
        assert median == item['medianDeliveredWallNs'][engine]
        assert abs(median / 1e9 - summary['cpuMacos'][item['preset']][engine]) < 1e-10
        checked.append({'study': 'cpuMacos', 'preset': item['preset'], 'engine': engine, 'medianNs': median})
for preset in ['medium', 'ultrafast']:
    for engine in ['H', 'F', 'R']:
        ns = [r['deliveredWallNs'] for r in orb['timedRounds'] if r['engine'] == engine and r['preset'] == preset]
        assert len(ns) == 3
        median = statistics.median(ns)
        assert median == orb['mediansNanoseconds'][preset + '-' + engine]
        assert abs(median / 1e9 - summary['cpuOrb'][preset][engine]) < 1e-10
        checked.append({'study': 'cpuOrb', 'preset': preset, 'engine': engine, 'medianNs': median})
assert len(orb['warmups']) == 6
assert summary['zeroCopyProved'] is False
assert summary['productionOrM5WinEstablished'] is False
print(json.dumps({'medianChecks': checked, 'passed': True}, indent=2))
