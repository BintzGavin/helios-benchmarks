"""Freeze CPU bridge preparation without launching a producer or altering gates."""
import hashlib,json,os,pathlib,shutil,stat,sys,zipfile
import codec_orchestration as old

ROOT=old.ROOT;OUT=ROOT/'comparison/native-bridge-prep-20261005'
def write(name,data):
    p=OUT/name
    if p.exists():raise RuntimeError('freeze refuses overwrite: '+str(p))
    p.write_text(json.dumps(data,indent=2)+'\n');return old.pin(p)
main=json.loads((OUT/'validation-final-07/TEST-REPORT.json').read_text())
extra=json.loads((OUT/'validation-extra-final-08/TEST-REPORT.json').read_text())
assert main['testCount']==53 and extra['testCount']==10
assert all(x['passed'] for x in main['tests']+extra['tests'])
assert main['GPUExports']==extra['GPUExports']==0
assert main['nativeExecutionDisabled'] and not main['realDeviceAccepted']

sources=['native_stdout_bridge.mjs','native_bridge_runner.py','native_bridge_fixture.py','native_bridge_encoder_fixture.py','native_bridge_scene_fixture.mjs','test_native_bridge.py','test_native_bridge_additional.py','freeze_native_bridge_prep.py']
dependencies=['codec_orchestration.py','stream_nv12_reference.py','native_chroma_conformance.py','codec_fixture_scene.mjs','circles-scene.mts','LICENSE.fframes.txt']
(OUT/'source').mkdir()
source_pins=[]
for name in sources+dependencies:
    p=ROOT/'checkpoint'/name;shutil.copy2(p,OUT/'source'/name);assert old.sha(p)==old.sha(OUT/'source'/name)
    source_pins.append(old.pin(p))

# Recheck every file in previously accepted bounded generations, including
# symlink identity, without rerunning any tests or decodes.
accepted=[]
for name in ['native-conformance-prep-20261005','serial-4k-qualification-plan-20261005','streaming-reference-prep-20261005','codec-orchestration-prep-20261005']:
    folder=ROOT/'comparison'/name;manifest=folder/'RECEIPT-MANIFEST.json';j=json.loads(manifest.read_text())
    count=0
    for row in j['files']:
        p=folder/row['path']
        if row.get('type')=='symlink' or row.get('symlink') or p.is_symlink():
            target=os.readlink(p)
            assert target==row.get('target',row.get('symlinkTarget')),row
        else:assert p.stat().st_size==row['bytes'] and old.sha(p)==row['sha256'],str(p)
        count+=1
    accepted.append({'manifest':old.pin(manifest),'entriesChecked':count,'allBytesAndSymlinksUnchanged':True})
_,ledger,inputs=old.snapshot()
for p in inputs:old.check(p)
prior_sources=[]
for name in ['streaming-reference-prep-20261005','codec-orchestration-prep-20261005']:
    for p in json.loads((ROOT/'comparison'/name/'EXACT-SOURCE-PINS.json').read_text())['files']:
        old.check(p);prior_sources.append(p)
write('ACCEPTED-EVIDENCE-UNCHANGED.json',{'acceptedManifests':accepted,'serialInputPinsChecked':len(inputs),'acceptedSourcePins':prior_sources,'previousTestsRepeated':False,'previousDecodesRepeated':False})
runtime=[old.pin(p) for p in ['/opt/homebrew/bin/node','/opt/homebrew/bin/python3','/opt/homebrew/bin/ffmpeg','/opt/homebrew/bin/ffprobe','/usr/bin/xcrun']]
write('EXACT-SOURCE-RUNTIME-PINS.json',{'newSourcesAndReadOnlyDependencies':source_pins,'runtime':runtime,'serialNativeHelperSourceRuntimePins':inputs,'CPUProfileLibrary':main['CPUProfileLibrary'],'CPUProfileSHAIndependentWhitelist':True,'actualGPUProfileLibrariesLoaded':False})

cases=OUT/'cases/validation-final-07'
positive=[];bindings=0
for p in cases.glob('*/INDEPENDENT-BINDING.json'):
    j=json.loads(p.read_text());assert j['frames']==300 and len(j['pairs'])==300
    assert all(r['index']==i and r['commandSourceIndex']==i+3 and r['retainedRawFixtureOrdinal']==i and r['equal'] and r['rawNv12Sha256']==r['independentInverseSha256'] for i,r in enumerate(j['pairs']))
    positive.append(old.pin(p));bindings+=len(j['pairs'])
assert len(positive)==3 and bindings==900
waits=json.loads((OUT/'validation-extra-final-08/OWNED-PROCESS-WAITS.json').read_text())
tests=[json.loads(p.read_text()) for p in cases.glob('*/TEST.json')]
measurements=[x for x in tests if x.get('publishedFixtureBinding')]
usage={'status':'bounded CPU fixture measurements only; no 4K extrapolation accepted','activeSerialGateBytes':9*1024**3,'activeBalancedGateBytes':15*1024**3,'proposedStreamingGateBytes':6*1024**3,'streamingGateEnabled':False,'freeBytesAtFreeze':shutil.disk_usage(ROOT).free,'rawFixtureBytes':14745600,'CPUFixtureDimensions':[256,128],'CPUFixtureFrames':300,'referenceFrameBytes':49152,'pythonMaxRSSBytes':max(x['pythonMaxRSSBytes'] for x in measurements),'maxPlanarWriterQueueBytes':max(x['maxPlanarWriterQueuedBytes'] for x in measurements),'maxProducerStdoutWriterQueueBytes':max(x['producerMaxForwardQueue'] for x in measurements),'fixtureOutputCapBytes':32*1024*1024,'fixtureTimeoutSeconds':30,'fixtureMinFreeBytes':256*1024*1024,'geometrySourceOrderMemoryActualGPUAcceptance':False,'newCargoBuild':False,'GPUExports':0,'oldArtifactsDeleted':False,'diskGatesLowered':False,'nextRealDeviceResourceRequirements':{'minimumSerialFreeBytes':9*1024**3,'minimumBalancedFreeBytes':15*1024**3,'rawNV12Per4KFrameBytes':12441600,'referenceNV12Per300FramesBytes':3732480000,'retainedRawBudgetBytes':ledger['retainedRawGateBytes'],'actual4KPeakMemory':'unqualified'}}
write('RESOURCE-LEDGER.json',usage)
write('VALIDATION-COMMANDS.json',{'commands':[{'argv':['python3','checkpoint/test_native_bridge.py'],'exit':0,'observedStdout':{'status':main['status'],'tests':53,'GPUExports':0}},{'argv':['python3','checkpoint/test_native_bridge_additional.py'],'exit':0,'observedStdout':{'tests':10,'GPUExports':0}}],'sourceBoundBy':source_pins,'outerCommandReceiptsTranscribedFromSuccessfulExecResults':True,'actualChildStdoutStderrExitReceipts':'cases/validation-final-07 and cases/validation-extra-final-08','excludedAttemptsRetained':True})
report={'status':'completed bounded native bridge/codec/profile preparation; CPU subprocess fixtures only','testCount':63,'mainTests':old.pin(OUT/'validation-final-07/TEST-REPORT.json'),'additionalTests':old.pin(OUT/'validation-extra-final-08/TEST-REPORT.json'),'independentRawPlanarInverseBindings':{'frames':900,'streams':3,'receipts':positive,'commandSourceIndices':[3,302],'retainedPayloadFixtureOrdinals':[0,299],'renderedPixelCorrespondenceClaimed':False},'copiedCodecPayloadDecodedInvariance':{'H264Frames':300,'HEVCFrames':300,'CPUProfileHEVCFrames':300,'SPSConformanceAndCopyMuxIncludedInFixtureAttempt':True,'clockExcludedFromBenchmark':True},'explicitDirectProcessWaitsChecked':len(waits['groups']),'successfulHelperWaitsChecked':len(waits['completedHelperWaits']),'failedHelperWaitsChecked':len(waits['failedHelperShutdownWaits']),'independentAllOSDescendantCessationProof':False,'signal0GroupQuerySandboxBlocked':True,'descendantControls':'two CPU heartbeat controls plus owned group TERM/KILL; no OS-wide process/environment inspection','realDeviceAccepted':False,'nativeExecutionDisabled':True,'hardwareQualified':False,'GPUExports':0,'actualGPUProfileLibrariesLoaded':False,'actualGPUProducerBridgeAcceptance':False,'actual4KMemoryAcceptance':False,'zeroCopyProved':False,'newCargoBuild':False,'timingWindowOpen':False,'benchmarkTiming':False,'activeSerialGateBytes':9*1024**3,'activeBalancedGateBytes':15*1024**3,'streaming6GiBGateDisabled':True,'comparisonOwnership':'retained; F concurrency/capture/helper and all historical helpers/oracles/clocks remain unchanged','sourceLibraryPreparationId':'libfile_19c903c1d7508191ac4881f0e96e4229','historicalCheckpointLibraryId':'libfile_cd84375e4648819195364136245484c6','newLibraryDeliverableIds':[],'LibraryUploadAttemptThisSlice':False,'fullComparisonObjective':'ACTIVE, incomplete; no fully enabled production/M5/performance win asserted','remainingRequiredWork':['Resource headroom9GiB serial/15GiB balanced; pending unrelated-cache approval is not assumed','Separately scoped live-device acceptance of frozen stdout bridge and fresh per-attempt native profile library; disabled branch must remain off until authorized gates','Fresh all300 4K Metal H264/HEVC and MoltenVK H264/HEVC direct reference/centered color/quality/cadence/GOP/GPU/lifetime/positive controls; do not reuse CPU fixture receipts','Fresh shared-conformance modified concurrent F acceptance, preserving3contexts/5+5workers/queue10/64allocations percontext versus nativepool3','Only after all gates, sequential balanced matched settings timings including mandatory conformance/mux and separate delivered decode clocks','Native Vulkan publication destination approval and supported Library preparation/upload route remain pending']}
write('FINAL-REPORT.json',report)
readme='''This package is CPU/process preparation, not a GPU qualification or performance result.

The driver records real source indices3..302 with the independently pinned portable binary recorder. The helper is a CPU ABI stub: its raw frames and elementary videos are copied retained fixture ordinals0..299. The three reference checks independently reconstruct all900 fixture NV12 frames after FFV1 decode. No pixels were rendered by a GPU in this slice. Simulated encoder/GPU ABI flags are labeled under simulatedNativeContract and cannot enable native execution.

The supervisor enforces bounded frames/queues/logs/output/disk/time, per-source packet hashes, exact EOF, child exit checks, cancellation, process group cleanup and atomic no-replace publication. Graceful driver cleanup waits for its helper, including an actual CPU helper that ignores TERM and needs KILL. The sandbox refused independent signal0 group queries; explicit direct-child waits and two controlled heartbeat observations are reported without an OS-wide descendant-cessation claim.

Final accepted preparation generations: validation-final-07 (53 tests) and validation-extra-final-08 (10 tests). Earlier source generations/failed partials remain retained and excluded as current qualification. The compile attempt with an unwritable default temporary directory and all failure/publication-race receipts remain intact. A same-attempt monitor rename race and a concurrent shutdown receipt race were fixed and retested.

Codec/profile paths were exercised with H264/HEVC retained streams, the shared frozen b0a36 conformance adapter, full300 decoded invariance per codec and profile case, actual invalid copy-mux/conformance failures, and a harmless CPU-only constructor library. Only that exact SHA is allowed for fixture profile injection. Native Metal/Vulkan interposers were never loaded. No Cargo build or new GPU export was run.

Real-device launch is unconditionally disabled in both Python and Node. A sufficient-disk test and direct Node refusal confirm that fixtures/flags cannot activate it. The cold plan preserves protocol5/7/9, frozen helpers, source3..302,4K300@30/1,300Mbps/GOP30/nativepool3 and fresh profile path/compile commands. Fresh live native/profile qualification and actual4K memory measurements remain required; this preparation is not that acceptance.

Same-host CPU reproduction: inspect EXACT-SOURCE-RUNTIME-PINS and VALIDATION-COMMANDS first. The source scripts require the retained fixed workspace/runtime/recorder paths and exact whitelisted CPU profile binary. Use a separate validation generation/destination rather than overwriting these artifacts; updating generation names produces a new source pin and must be reported as a new attempt. The bundle includes copied fixtures and source dependencies; external engine/helper/runtime bindings are pinned, not substituted. Rehash every input before running. No real-device launch switch is available.

All real GPU lanes remain behind9GiB serial/15GiB balanced gates. The6GiB streaming proposal is disabled. Every new 4K lane needs its own all300 direct/lossless binding, unchanged quality floors, decoded cadence/color/GOP and actual GPU/lifetime/profile+positive controls before a timing window. Keep mandatory conformance/mux cost, nativepool3/F64 percontext, original pipeline failures and old clocks distinct. MoltenVK on this Mac is not Linux Vulkan Video. No zero-copy, original-product, M5 or benchmark-win claim is made.

Source Library identity and historical checkpoint identity are distinct in FINAL-REPORT. This slice did not attempt a Library upload and has no new Library IDs. Full comparison objective remains active; resource, publication and Library blockers remain.
'''
(OUT/'README.md').write_text(readme)
archive=OUT/'source.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted((OUT/'source').iterdir()):z.write(p,'checkpoint/'+p.name)
    for p in sorted((OUT/'fixtures').iterdir()):
        if p.is_file():z.write(p,'comparison/native-bridge-prep-20261005/fixtures/'+p.name)
    for name in ['CONFIG.json','RESOURCE-LEDGER.json','EXACT-INPUT-PINS.json','FINAL-REPORT.json']:
        p=old.PLAN/name;z.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
files=[]
for p in sorted(OUT.rglob('*')):
    if p.is_symlink():files.append({'path':str(p.relative_to(OUT)),'type':'symlink','target':os.readlink(p)});continue
    if p.is_file():files.append({'path':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':old.sha(p)})
write('RECEIPT-MANIFEST.json',{'files':files,'entries':len(files),'bytes':sum(p.get('bytes',0) for p in files),'excludesItself':True,'GPUExports':0,'preparationOnly':True})
print(json.dumps({'report':old.pin(OUT/'FINAL-REPORT.json'),'manifest':old.pin(OUT/'RECEIPT-MANIFEST.json'),'entries':len(files),'tests':63,'GPUExports':0}))
